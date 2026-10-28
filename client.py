import aiohttp
import re
import asyncio
import logging
import time
from urllib.parse import urlencode

from yarl import URL
from homeassistant.helpers.update_coordinator import UpdateFailed

_LOGGER = logging.getLogger(__name__)

# Se uno di questi testi compare nella risposta, l'ESP sta servendo
# la pagina di configurazione wifi invece dei dati dell'impianto
PORTAL_MARKERS = ("wifisave",)

RECOVERY_COOLDOWN = 300   # secondi minimi tra due tentativi di recupero
REBOOT_WAIT = 30          # attesa riavvio ESP dopo il salvataggio
REQUEST_PAUSE = 2         # pausa tra due richieste consecutive (l'ESP8266 è fragile)


class KalkotronicClient:
    """Client con sessione HTTP persistente per ridurre il carico sull'ESP8266.

    Se il modulo risponde con la pagina di configurazione wifi (succede dopo
    alcuni giorni), reinvia automaticamente i parametri di rete.
    """

    def __init__(
        self,
        host: str,
        wifi_ssid: str | None = None,
        wifi_password: str | None = None,
        gateway: str | None = None,
        subnet: str | None = None,
    ):
        self._host = host
        self._ssid = wifi_ssid
        self._password = wifi_password
        self._gateway = gateway
        self._subnet = subnet or "255.255.255.0"
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()
        self._recovery_lock = asyncio.Lock()
        self._last_recovery = float("-inf")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Ottiene o crea una sessione persistente."""
        async with self._lock:
            if self._session is None or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=15, sock_connect=10)
                self._session = aiohttp.ClientSession(timeout=timeout)
            return self._session

    async def close(self):
        """Chiude la sessione (da chiamare in unload)."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, url) -> str:
        session = await self._get_session()
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()

    async def _get_page(self, pin: str) -> str:
        """GET con rilevamento pagina di configurazione e recupero automatico."""
        url = f"http://{self._host}/?pin={pin}"
        html = await self._request(url)

        if not _is_config_portal(html):
            return html

        _LOGGER.warning(
            "Kalkotronic %s sta rispondendo con la pagina di configurazione wifi",
            self._host,
        )
        await self._recover_wifi()

        html = await self._request(url)
        if _is_config_portal(html):
            raise UpdateFailed(
                f"{self._host} risponde ancora con la pagina di configurazione"
            )
        return html

    async def _recover_wifi(self) -> None:
        """Reinvia ssid/password/ip all'ESP (equivale a cliccare Salva)."""
        if not (self._ssid and self._password and self._gateway):
            raise UpdateFailed(
                "Pagina di configurazione rilevata ma parametri wifi non "
                "configurati nell'integrazione"
            )

        async with self._recovery_lock:
            # Se il recupero è già stato tentato da poco, non rifarlo
            if time.monotonic() - self._last_recovery < RECOVERY_COOLDOWN:
                return
            self._last_recovery = time.monotonic()

            query = urlencode(
                {
                    "s": self._ssid,
                    "p": self._password,
                    "server": "",
                    "port": "8080",
                    "blynk": "YOUR_BLYNK_TOKEN",
                    "ip": self._host,
                    "gw": self._gateway,
                    "sn": self._subnet,
                }
            )
            # encoded=True evita la doppia codifica da parte di aiohttp
            url = URL(f"http://{self._host}/wifisave?{query}", encoded=True)

            try:
                await self._request(url)
            except Exception as err:  # l'ESP può chiudere la connessione mentre si riavvia
                _LOGGER.debug("Risposta wifisave su %s: %s", self._host, err)

            _LOGGER.warning(
                "Parametri wifi reinviati a %s, attendo il riavvio", self._host
            )
            await asyncio.sleep(REBOOT_WAIT)

    async def fetch_fast_data(self) -> dict:
        """Pagina CaricaDatiImp — aggiornamento frequente."""
        html = await self._get_page("CaricaDatiImp")
        return _parse_fast_data(html)

    async def fetch_daily_data(self) -> dict:
        """Pagina TipoImpianto — aggiornamento giornaliero."""
        html = await self._get_page("TipoImpianto")
        return _parse_daily_data(html)

    async def fetch_home_status(self) -> dict:
        """Home page — stato sistema."""
        html = await self._get_page("Home")
        return _parse_home_status(html)

    async def fetch_energy_data(self) -> dict:
        """Pagina Consumielettrici."""
        html = await self._get_page("Consumielettrici")
        return _parse_energy_data(html)

    async def fetch_all_fast(self) -> dict:
        """Fetch combinato, in sequenza con pausa tra le richieste.

        L'ESP8266 va in difficoltà con richieste concorrenti, quindi le pagine
        vengono lette una alla volta.
        """
        fetchers = (
            self.fetch_fast_data,
            self.fetch_home_status,
            self.fetch_energy_data,
        )

        data = {}
        errors = []
        for i, fetch in enumerate(fetchers):
            if i:
                await asyncio.sleep(REQUEST_PAUSE)
            try:
                data.update(await fetch())
            except Exception as err:
                errors.append(err)
                _LOGGER.warning("Errore durante fetch fast data: %s", err)

        # Se nessuna pagina ha risposto, i sensori devono risultare non disponibili
        if not data:
            raise UpdateFailed(f"Nessun dato ricevuto da {self._host}: {errors}")
        return data


def _is_config_portal(html: str) -> bool:
    low = html.lower()
    return any(marker in low for marker in PORTAL_MARKERS)


def _find(pattern: str, html: str):
    """Cerca un pattern nell'HTML e restituisce il primo gruppo."""
    match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def _parse_fast_data(html: str) -> dict:
    return {
        "temperature":           _find(r"Temperatura impianto:\s*(?:<[^>]+>\s*)*([\d.]+)", html),
        "efficiency":            _find(r"Efficienza stimata:\s*(?:<[^>]+>\s*)*(\d+)", html),
        "working_days":          _find(r"totale di\s+(\d+)\s+giorni", html),
        "maintenance_days_left": _find(r"Giorni mancanti prima della revisione:\s*(\d+)", html),
        "maintenance_delay":     _find(r"Giorni di ritardo revisione fasce:\s*(\d+)", html),
        "temp_alarms":           _find(r"Allarmi Temperatura:\s*(\d+)", html),
        "fuse_alarms":           _find(r"Allarmi Fusibile:\s*(\d+)", html),
        "status_message":        _find(r"MESSAGGIO CARD:\s*([^<]+)", html),
    }


def _parse_daily_data(html: str) -> dict:
    return {
        "model":        _find(r"Modello:\s*([^<]+)", html),
        "serial":       _find(r"Codice Seriale:\s*([^<]+)", html),
        "sw_version":   _find(r"V\.Software Scheda:\s*([^<]+)", html),
        "wifi_version": _find(r"Versione\s*KT\s*WiFi\s*V\s*([0-9.]+)", html),
    }


def _parse_home_status(html: str) -> dict:
    color = _find(r'background-color:\s*(#[0-9A-Fa-f]{6});\s*border-radius:\s*50%', html)
    if color is None:
        raise ValueError("Colore stato non trovato nell'HTML — risposta incompleta")
    is_ok = color.upper() == "#00FF00"
    return {
        "system_problem": not is_ok,
        "status_color":   color,
    }


def _parse_energy_data(html: str) -> dict:
    raw = _find(r"Watt consumati dall'inizio del periodo sono:\s*([\d,]+)\s*Kwh", html)
    if raw is None:
        raise ValueError("Valore energia non trovato nell'HTML")
    value = float(raw.replace(",", "."))
    return {
        "energy": value,
    }
