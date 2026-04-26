from datetime import timedelta
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

EXCLUDED_FROM_SENSORS = {"serial", "model", "sw_version", "wifi_version"}

SENSOR_NAMES = {
    "temperature":           "Temperatura",
    "efficiency":            "Efficienza",
    "working_days":          "Giorni di lavoro",
    "maintenance_days_left": "Giorni alla manutenzione",
    "maintenance_delay":     "Ritardo manutenzione",
    "temp_alarms":           "Allarmi temperatura",
    "fuse_alarms":           "Allarmi fusibile",
    "status_message":        "Messaggio di stato",
    "energy":                "Energia consumata",
}

SENSOR_META = {
    "temperature": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class":  SensorStateClass.MEASUREMENT,
        "unit":         "°C",
        "icon":         "mdi:thermometer",
    },
    "efficiency": {
        "device_class": None,
        "state_class":  SensorStateClass.MEASUREMENT,
        "unit":         "%",
        "icon":         "mdi:percent",
    },
    "working_days": {
        "device_class": None,
        "state_class":  SensorStateClass.TOTAL_INCREASING,
        "unit":         "giorni",
        "icon":         "mdi:calendar-clock",
    },
    "maintenance_days_left": {
        "device_class": None,
        "state_class":  SensorStateClass.MEASUREMENT,
        "unit":         "giorni",
        "icon":         "mdi:calendar-alert",
    },
    "maintenance_delay": {
        "device_class": None,
        "state_class":  SensorStateClass.MEASUREMENT,
        "unit":         "giorni",
        "icon":         "mdi:calendar-remove",
    },
    "temp_alarms": {
        "device_class": None,
        "state_class":  SensorStateClass.TOTAL_INCREASING,
        "unit":         None,
        "icon":         "mdi:thermometer-alert",
    },
    "fuse_alarms": {
        "device_class": None,
        "state_class":  SensorStateClass.TOTAL_INCREASING,
        "unit":         None,
        "icon":         "mdi:fuse-alert",
    },
    "status_message": {
        "device_class": None,
        "state_class":  None,
        "unit":         None,
        "icon":         "mdi:information-outline",
    },
    "energy": {
        "device_class": SensorDeviceClass.ENERGY,
        "state_class":  SensorStateClass.TOTAL_INCREASING,
        "unit":         "kWh",
        "icon":         "mdi:lightning-bolt",
    },
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    host = entry.data["host"]
    daily_data = coordinators.daily.data
    entities = []

    for key in coordinators.fast.data:
        if key not in EXCLUDED_FROM_SENSORS:
            entities.append(
                KalkotronicSensor(coordinators.fast, key, host, daily_data)
            )

    for key in coordinators.energy.data:
        entities.append(
            KalkotronicSensor(coordinators.energy, key, host, daily_data)
        )

    async_add_entities(entities)


class KalkotronicSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator, key, host, daily_data):
        super().__init__(coordinator)
        self._key = key
        self._host = host
        self._daily_data = daily_data

        meta = SENSOR_META.get(key, {})
        self._attr_name                       = SENSOR_NAMES.get(key, key.replace("_", " ").title())
        self._attr_unique_id                  = f"{host}_{key}"
        self._attr_device_class               = meta.get("device_class")
        self._attr_state_class                = meta.get("state_class")
        self._attr_native_unit_of_measurement = meta.get("unit")
        self._attr_icon                       = meta.get("icon")

    @property
    def native_value(self):
        value = self.coordinator.data.get(self._key)
        if value is not None and self._attr_native_unit_of_measurement is not None:
            try:
                if "." in str(value):
                    return round(float(value), 2)
                else:
                    return int(value)
            except (ValueError, TypeError):
                pass
        return value

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