import logging

import aiohttp
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    host = entry.data["host"]
    daily_data = coordinators.daily.data

    async_add_entities([
        KalkotronicResetButton(host, daily_data)
    ])


class KalkotronicResetButton(ButtonEntity):

    def __init__(self, host, daily_data):
        self._host = host
        self._daily_data = daily_data
        self._attr_name      = "Reset Allarmi"
        self._attr_unique_id = f"{host}_reset_alarms"
        self._attr_icon      = "mdi:alarm-light-off"

    async def async_press(self):
        url = f"http://{self._host}/?pin=ResAllSET+"
        try:
            async with aiohttp.ClientSession() as session:
                await session.get(url, timeout=10)
                _LOGGER.info("Reset allarmi eseguito su %s", self._host)
        except Exception as err:
            _LOGGER.error("Errore reset allarmi su %s: %s", self._host, err)

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