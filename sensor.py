from datetime import timedelta
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from homeassistant.helpers.entity import DeviceInfo

from .client import KalkotronicClient
from .const import DOMAIN, MANUFACTURER, UPDATE_FAST, UPDATE_DAILY

_LOGGER = logging.getLogger(__name__)

EXCLUDED_SENSORS = {"serial"}

SENSOR_META = {
    "temperature": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "°C",
    },
    "efficiency": {
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
    },
    "working_days": {
        "state_class": SensorStateClass.TOTAL,
        "unit": "days",
    },
    "maintenance_expiration": {
        "state_class": SensorStateClass.TOTAL,
        "unit": "days",
    },
    "maintenance_delay": {
        "state_class": SensorStateClass.TOTAL,
        "unit": "days",
    },
}


async def async_setup_entry(hass, entry, async_add_entities):
    host = entry.data["host"]
    client = KalkotronicClient(host)

    device_info_data = await client.fetch_device_info()

    coordinator_daily = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Kalkotronic Daily",
        update_method=client.fetch_daily_data,
        update_interval=timedelta(seconds=UPDATE_DAILY),
    )

    coordinator_fast = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Kalkotronic Fast",
        update_method=client.fetch_fast_data,
        update_interval=timedelta(seconds=UPDATE_FAST),
    )

    await coordinator_daily.async_config_entry_first_refresh()
    await coordinator_fast.async_config_entry_first_refresh()

    entities = []

    for key in coordinator_daily.data:
        if key not in EXCLUDED_SENSORS:
            entities.append(
                KalkotronicSensor(
                    coordinator_daily, key, host, device_info_data
                )
            )

    for key in coordinator_fast.data:
        entities.append(
            KalkotronicSensor(
                coordinator_fast, key, host, device_info_data
            )
        )

    async_add_entities(entities)


class KalkotronicSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key, host, device_data):
        super().__init__(coordinator)
        self._key = key
        self._host = host
        self._device_data = device_data

        self._attr_name = key.replace("_", " ").title()
        self._attr_unique_id = f"{host}_{key}"

        meta = SENSOR_META.get(key, {})
        self._attr_device_class = meta.get("device_class")
        self._attr_state_class = meta.get("state_class")
        self._attr_native_unit_of_measurement = meta.get("unit")

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            name=f"Kalkotronic {self._host}",
            manufacturer=MANUFACTURER,
            model=self._device_data.get("model"),
            serial_number=self._device_data.get("serial"),
            sw_version=self._device_data.get("sw_version"),
        )
