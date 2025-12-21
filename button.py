import aiohttp
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, MANUFACTURER

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([KalkotronicResetButton(entry.data["host"])])


class KalkotronicResetButton(ButtonEntity):
    def __init__(self, host):
        self._host = host
        self._attr_name = "Reset Alarm"
        self._attr_icon = "mdi:alarm-bell"
        self._attr_unique_id = f"{host}_reset_alarm"

    async def async_press(self):
        url = f"http://{self._host}/?pin=ResAllSET+"
        async with aiohttp.ClientSession() as session:
            await session.get(url, timeout=10)

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            name=f"Kalkotronic {self._host}",
            manufacturer=MANUFACTURER,
        )
