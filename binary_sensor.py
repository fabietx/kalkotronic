import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    host = entry.data["host"]
    daily_data = coordinators.daily.data

    async_add_entities([
        KalkotronicProblemSensor(coordinators.status, host, daily_data)
    ])


class KalkotronicProblemSensor(CoordinatorEntity, BinarySensorEntity):

    def __init__(self, coordinator, host, daily_data):
        super().__init__(coordinator)
        self._host = host
        self._daily_data = daily_data
        self._attr_name        = "System Problem"
        self._attr_unique_id   = f"{host}_system_problem"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon        = "mdi:alert"

    @property
    def is_on(self) -> bool:
        # True = problema rilevato, False = tutto OK
        return self.coordinator.data.get("system_problem", True)

    @property
    def extra_state_attributes(self):
        return {
            "status_color": self.coordinator.data.get("status_color"),
        }

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