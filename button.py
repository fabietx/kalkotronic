import logging

import aiohttp
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinators = entry_data["coordinators"]
    host = entry.data["host"]
    daily_data = coordinators.daily.data or {}

    async_add_entities([
        KalkotronicResetButton(host, daily_data, coordinators.fast)
    ])


class KalkotronicResetButton(ButtonEntity):

    def __init__(self, host, daily_data, fast_coordinator):
        self._host = host
        self._fast = fast_coordinator
        self._daily_data = daily_data
        self._attr_name      = "Reset Allarmi"
        self._attr_unique_id = f"{host}_reset_alarms"
        self._attr_icon      = "mdi:alarm-light-off"

    async def async_press(self):
        url = f"http://{self._host}/?pin=ResAllSET+"
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as resp:
                    resp.raise_for_status()
            _LOGGER.info("Reset allarmi eseguito su %s", self._host)
        except Exception as err:
            _LOGGER.error("Errore reset allarmi su %s: %s", self._host, err)
            return

        # Aggiorna subito i contatori allarmi
        await self._fast.async_request_refresh()

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            name=f"Kalkotronic {self._host}",
            manufacturer=MANUFACTURER,
            model=self._daily_data.get("model"),
            serial_number=self._daily_data.get("serial"),
            sw_version=self._daily_data.get("sw_version"),
        )