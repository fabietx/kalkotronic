import logging
import aiohttp
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    host = entry.data["host"]
    entities = [
        KalkotronicResetButton(host)
    ]
    async_add_entities(entities)


class KalkotronicResetButton(ButtonEntity):
    """Pulsante per resettare gli allarmi del dispositivo Kalkotronic."""

    def __init__(self, host):
        self._host = host
        self._attr_name = "Reset Alarm"
        self._attr_icon = "mdi:alarm-bell"
        self._attr_unique_id = f"{host}_reset_alarm"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            name=f"Kalkotronic {self._host}",
            manufacturer="Kalko Tronic",
        )

    async def async_press(self) -> None:
        url = f"http://{self._host}/?pin=ResAllSET+"
        _LOGGER.debug("Premuto pulsante Reset Alarm, chiamo URL: %s", url)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    resp.raise_for_status()
                    _LOGGER.info("Reset allarmi eseguito correttamente")
        except Exception as e:
            _LOGGER.error("Errore nel reset allarmi: %s", e)
