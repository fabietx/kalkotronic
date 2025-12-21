from datetime import timedelta
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from .client import KalkotronicClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL_DAY = timedelta(hours=24)
SCAN_INTERVAL_FAST = timedelta(minutes=2)


async def async_setup_entry(hass, entry, async_add_entities):
    host = entry.data["host"]
    client = KalkotronicClient(host)

    # Coordinatori
    coordinator_daily = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Kalkotronic Daily",
        update_method=_fetch_daily_data(client),
        update_interval=SCAN_INTERVAL_DAY,
    )
    await coordinator_daily.async_config_entry_first_refresh()

    coordinator_fast = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Kalkotronic Fast",
        update_method=_fetch_fast_data(client),
        update_interval=SCAN_INTERVAL_FAST,
    )
    await coordinator_fast.async_config_entry_first_refresh()

    # Legge info statiche da TipoImpianto e le mette nel device info
    tipoimpianto_data = await client.fetch_tipoimpianto()
    device_info_extra = {
        "model": tipoimpianto_data.get("model"),
        "sw_version": tipoimpianto_data.get("sw_version"),
        "hw_version": tipoimpianto_data.get("serial"),
    }

    # Creazione sensori
    entities = []

    # Stato online (sempre)
    entities.append(
        KalkotronicSensor(
            coordinator_daily,
            host,
            "Stato",
            "online",
            "mdi:checkbox-marked-circle",
            "stato",
            device_info_extra,
        )
    )

    # Sensori diagnostici dal coordinatore giornaliero
    daily_keys = [
        ("status_message", "Messaggio Stato", "mdi:information"),
        ("working_days", "Giorni Lavorati", "mdi:calendar-check"),
        ("maintenance_expiration", "Giorni alla Revisione", "mdi:calendar-clock"),
        ("maintenance_delay", "Ritardo Revisione", "mdi:calendar-remove"),
        ("frequency", "Frequenza Lavoro", "mdi:sine-wave"),
        ("temp_alarms", "Allarmi Temperatura", "mdi:alert-circle"),
        ("fuse_alarms", "Allarmi Fusibile", "mdi:alert-octagon"),
        ("wifi_version", "Versione WiFi", "mdi:wifi"),
    ]

    for key, name, icon in daily_keys:
        entities.append(KalkotronicSensor(coordinator_daily, host, name, None, icon, key))

    # Sensori aggiornamento rapido
    fast_keys = [
        ("temperature", "Temperatura Impianto", "mdi:thermometer"),
        ("efficiency", "Efficienza Stimata", "mdi:percent"),
    ]
    for key, name, icon in fast_keys:
        entities.append(KalkotronicSensor(coordinator_fast, host, name, None, icon, key))

    async_add_entities(entities)


def _fetch_daily_data(client):
    async def inner():
        data = await client.fetch_caricadati()
        tipoimpianto_data = await client.fetch_tipoimpianto()
        # aggiunge wifi_version dalla pagina TipoImpianto
        data["wifi_version"] = tipoimpianto_data.get("wifi_version")
        return data

    return inner


def _fetch_fast_data(client):
    async def inner():
        data = await client.fetch_caricadati()
        # ritorna solo temperature ed efficiency
        return {
            "temperature": data.get("temperature"),
            "efficiency": data.get("efficiency"),
        }

    return inner


class KalkotronicSensor(CoordinatorEntity, SensorEntity):
    """Sensore collegato al device con unique_id e device_info."""

    def __init__(self, coordinator, device_identifier, name, value, icon, unique_suffix, info=None):
        super().__init__(coordinator)
        self._device_identifier = device_identifier
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_value = value
        self._unique_suffix = unique_suffix
        self._device_info_extra = info or {}

    @property
    def unique_id(self):
        return f"{self._device_identifier}_{self._unique_suffix}"

    @property
    def device_info(self):
        info = {
            "identifiers": {(DOMAIN, self._device_identifier)},
            "name": f"Kalkotronic {self._device_identifier}",
            "manufacturer": "Kalko Tronic",
        }
        if self._device_info_extra:
            info.update(self._device_info_extra)
        return info

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        if self._unique_suffix == "stato":
            return "online"
        val = data.get(self._unique_suffix)
        if self._unique_suffix == "temperature" and val is not None:
            return f"{val}°C"
        return val

    @property
    def available(self):
        return self.coordinator.last_update_success
