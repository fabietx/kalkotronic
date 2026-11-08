"""Test dell'integrazione su un'istanza Home Assistant reale."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry, async_fire_time_changed,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.kalkotronic import coordinator as coord_mod
from custom_components.kalkotronic.const import DOMAIN

HOST = "192.168.1.50"
PAGES = {
    "CaricaDatiImp": "Temperatura impianto: <b>21.5</b> Efficienza stimata: <b>87</b>"
        " lavoro per un totale di 120 giorni. Giorni mancanti prima della revisione: 30"
        " Giorni di ritardo revisione fasce: 0 Allarmi Temperatura: 2"
        " Allarmi Fusibile: 0 <p>MESSAGGIO CARD: Tutto OK</p>",
    "Home": '<div style="background-color: #00FF00; border-radius: 50%"></div>',
    "Consumielettrici": "Watt consumati dall'inizio del periodo sono: 12,5 Kwh",
    "TipoImpianto": "Modello: KT100<br>Codice Seriale: ABC123<br>"
        "V.Software Scheda: 3.2<br>Versione KT WiFi V 1.4",
    "ResAll": "<p> L'allarme si riattiverà tra: 0 giorni</p>"
        '<p><a href="?pin=ResAllSET+"><button>RESET ALLARME MANUTENZIONE</button></a></p>',
}


class FakeEsp:
    def __init__(self):
        self.fail = set()
        self.calls = []

    async def request(self, client, url):
        url = str(url)
        self.calls.append(url)
        pin_now = url.split("pin=")[-1] if "pin=" in url else None
        for pin, html in PAGES.items():
            if pin_now == pin:
                if pin in self.fail:
                    raise TimeoutError(f"timeout {pin}")
                return html
        return "OK"


@pytest.fixture
def esp():
    fake = FakeEsp()
    async def _req(self, url):
        return await fake.request(self, url)
    with patch("custom_components.kalkotronic.client.KalkotronicClient._request", _req), \
         patch("custom_components.kalkotronic.client.REQUEST_PAUSE", 0):
        yield fake


@pytest.fixture
def timer_tracker():
    """Conta i trigger notturni attivi."""
    active = set()
    real = coord_mod.async_track_time_change
    def tracked(*args, **kwargs):
        unsub = real(*args, **kwargs)
        token = object(); active.add(token)
        def _unsub():
            active.discard(token); unsub()
        return _unsub
    with patch.object(coord_mod, "async_track_time_change", tracked):
        yield active


def _state(hass, platform, key):
    ent = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{HOST}_{key}")
    return hass.states.get(ent)


async def _setup(hass):
    entry = MockConfigEntry(domain=DOMAIN, unique_id=HOST, data={"host": HOST})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_e_device(hass, esp):
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert _state(hass, "sensor", "temperature").state == "21.5"
    assert _state(hass, "sensor", "status_message").state == "Tutto OK"
    assert _state(hass, "sensor", "energy").state == "12.5"
    assert _state(hass, "binary_sensor", "system_problem").state == "off"
    dev = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, HOST)})
    assert (dev.model, dev.serial_number, dev.sw_version) == ("KT100", "ABC123", "3.2")
    assert _state(hass, "sensor", "maintenance_snooze_days").state == "0"


async def test_errore_parziale_mantiene_valore(hass, esp):
    await _setup(hass)
    esp.fail = {"CaricaDatiImp", "Home"}
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=130))
    await hass.async_block_till_done()
    assert _state(hass, "sensor", "status_message").state == "Tutto OK"
    assert _state(hass, "binary_sensor", "system_problem").state == "off"


async def test_valore_scaduto_diventa_non_disponibile(hass, esp):
    await _setup(hass)
    esp.fail = {"CaricaDatiImp"}
    with patch("custom_components.kalkotronic.client.time.monotonic",
               return_value=10**9):
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=130))
        await hass.async_block_till_done()
    assert _state(hass, "sensor", "status_message").state == "unavailable"
    assert _state(hass, "sensor", "energy").state == "12.5"


async def test_giornaliero_parziale_mantiene_e_ritenta(hass, esp):
    await _setup(hass)
    esp.fail = {"ResAll"}
    PAGES["TipoImpianto"] = PAGES["TipoImpianto"].replace("3.2", "3.3")
    try:
        # Prossime 00:01 nel fuso di Home Assistant
        nightly = (dt_util.now() + timedelta(days=1)).replace(
            hour=0, minute=1, second=0, microsecond=0
        )
        async_fire_time_changed(hass, nightly)
        await hass.async_block_till_done()
    finally:
        PAGES["TipoImpianto"] = PAGES["TipoImpianto"].replace("3.3", "3.2")
    # Il rinvio resta all'ultimo valore valido, la versione si aggiorna
    assert _state(hass, "sensor", "maintenance_snooze_days").state == "0"
    dev = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, HOST)})
    assert dev.sw_version == "3.3"


async def test_setup_ok_senza_tipoimpianto(hass, esp):
    esp.fail = {"TipoImpianto"}
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert _state(hass, "sensor", "temperature").state == "21.5"


async def test_reload_non_duplica_trigger(hass, esp, timer_tracker):
    entry = await _setup(hass)
    assert len(timer_tracker) == 1
    for _ in range(3):
        hass.config_entries.async_update_entry(entry, options={"wifi_ssid": "x"})
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert len(timer_tracker) == 1
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert len(timer_tracker) == 0


async def test_pulsante_e_servizio(hass, esp):
    await hass.config.async_set_time_zone("Europe/Rome")
    await _setup(hass)
    reg = er.async_get(hass)
    ent = reg.async_get_entity_id("button", DOMAIN, f"{HOST}_reset_alarms")
    assert reg.async_get(ent).entity_category == "config"
    assert hass.states.get(ent).attributes["icon"] == "mdi:wrench-clock"
    PAGES["ResAll"] = PAGES["ResAll"].replace("tra: 0", "tra: 7")
    try:
        await hass.services.async_call("button", "press", {"entity_id": ent}, blocking=True)
        await hass.async_block_till_done()
    finally:
        PAGES["ResAll"] = PAGES["ResAll"].replace("tra: 7", "tra: 0")
    assert "http://192.168.1.50/?pin=ResAllSET+" in esp.calls
    # Dopo il rinvio viene riletta la pagina ResAll
    assert esp.calls.index("http://192.168.1.50/?pin=ResAllSET+") < len(esp.calls) - 1
    assert _state(hass, "sensor", "maintenance_snooze_days").state == "7"
    await hass.services.async_call(DOMAIN, "update_datetime", {}, blocking=True)
    sent = [c for c in esp.calls if "Mia_Data_ora=" in c][-1]
    expected = dt_util.now().strftime("%d.%m.%Y+%H")
    assert expected in sent


async def test_config_flow(hass, esp):
    from homeassistant import config_entries
    with patch("custom_components.kalkotronic.config_flow._test_connection", return_value=True):
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"host": "300.1.1.1"})
        assert r["errors"] == {"host": "invalid_ip"}
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"host": HOST, "wifi_ssid": "casa"})
        assert r["errors"] == {"base": "incomplete_wifi"}
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {
            "host": HOST, "wifi_ssid": "casa", "wifi_password": "pw", "gateway": "192.168.1.1"})
        assert r["type"] == "create_entry"
        assert r["data"]["subnet"] == "255.255.255.0"
    await hass.async_block_till_done()


async def test_options_flow(hass, esp):
    entry = await _setup(hass)
    r = await hass.config_entries.options.async_init(entry.entry_id)
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"gateway": "abc"})
    assert r["errors"] == {"gateway": "invalid_gateway"}
    r = await hass.config_entries.options.async_configure(r["flow_id"], {
        "wifi_ssid": "casa", "wifi_password": "pw", "gateway": "192.168.1.1"})
    assert r["type"] == "create_entry"
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
