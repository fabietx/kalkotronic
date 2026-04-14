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

# Chiavi da non esporre come sensori (usate solo per device_info)
EXCLUDED_FROM_SENSORS = {"serial", "model", "sw_version", "wifi_version"}

# Metadati per ogni sensore: unità, device_class, state_class, icona
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
        "icon":         "mdi:flash-alert",
    },
    "status_message": {
        "device_class": None,
        "state_class":  None,
        "unit":         None,
        "icon":         "mdi:information-outline",
    },
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    host = entry.data["host"]
    daily_data = coordinators.daily.data
    entities = []

    # Sensori aggiornati ogni 2 minuti (coordinator fast)
    for key in coordinators.fast.data:
        if key not in EXCLUDED_FROM_SENSORS:
            entities.append(
                KalkotronicSensor(coordinators.fast, key, host, daily_data)
            )

    async_add_entities(entities)


class KalkotronicSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator, key, host, daily_data):
        super().__init__(coordinator)
        self._key = key
        self._host = host
        self._daily_data = daily_data

        meta = SENSOR_META.get(key, {})
        self._attr_name                     = key.replace("_", " ").title()
        self._attr_unique_id                = f"{host}_{key}"
        self._attr_device_class             = meta.get("device_class")
        self._attr_state_class              = meta.get("state_class")
        self._attr_native_unit_of_measurement = meta.get("unit")
        self._attr_icon                     = meta.get("icon")

    @property
    def native_value(self):
        value = self.coordinator.data.get(self._key)
        # Converti in numero i valori numerici per HA
        if value is not None and self._attr_native_unit_of_measurement is not None:
            try:
                return float(value) if "." in str(value) else int(value)
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