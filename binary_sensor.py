from datetime import timedelta
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from homeassistant.helpers.entity import DeviceInfo

from .client import KalkotronicClient
from .const import DOMAIN, MANUFACTURER, UPDATE_FAST

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    host = entry.data["host"]
    client = KalkotronicClient(host)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Kalkotronic Status",
        update_method=client.fetch_status,
        update_interval=timedelta(seconds=UPDATE_FAST),
    )

    await coordinator.async_config_entry_first_refresh()

    async_add_entities([KalkotronicProblemSensor(coordinator, host)])


class KalkotronicProblemSensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, host):
        super().__init__(coordinator)
        self._host = host
        self._attr_name = "System Problem"
        self._attr_unique_id = f"{host}_system_problem"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:alert"

    @property
    def is_on(self) -> bool:
        # True = problema presente
        return self.coordinator.data.get("system_problem", True)

    @property
    def extra_state_attributes(self):
        # Espone anche il colore grezzo come attributo, utile per debug
        return {
            "status_color": self.coordinator.data.get("system_status_color"),
        }

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            name=f"Kalkotronic {self._host}",
            manufacturer=MANUFACTURER,
        )