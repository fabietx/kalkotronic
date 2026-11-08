"""Sensori Kalkotronic."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import KalkotronicEntity

# Nomi, unità e unique_id invariati rispetto alla v0.4 per non perdere lo storico
SENSOR_NAMES = {
    "temperature": "Temperatura",
    "efficiency": "Efficienza",
    "working_days": "Giorni di lavoro",
    "maintenance_days_left": "Giorni alla manutenzione",
    "maintenance_delay": "Ritardo manutenzione",
    "temp_alarms": "Allarmi temperatura",
    "fuse_alarms": "Allarmi fusibile",
    "status_message": "Messaggio di stato",
    "energy": "Energia consumata",
}

SENSOR_META: dict[str, dict[str, Any]] = {
    "temperature": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "°C",
        "icon": "mdi:thermometer",
    },
    "efficiency": {
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "%",
        "icon": "mdi:percent",
    },
    "working_days": {
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": "giorni",
        "icon": "mdi:calendar-clock",
    },
    "maintenance_days_left": {
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "giorni",
        "icon": "mdi:calendar-alert",
    },
    "maintenance_delay": {
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "giorni",
        "icon": "mdi:calendar-remove",
    },
    "temp_alarms": {
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": None,
        "icon": "mdi:thermometer-alert",
    },
    "fuse_alarms": {
        "device_class": None,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": None,
        "icon": "mdi:fuse-alert",
    },
    "status_message": {
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:information-outline",
    },
    "energy": {
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": "kWh",
        "icon": "mdi:lightning-bolt",
    },
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    fast = entry.runtime_data.coordinators.fast
    host = entry.data[CONF_HOST]
    # Un sensore per ogni chiave nota, anche se una pagina non ha risposto al setup
    async_add_entities(KalkotronicSensor(fast, host, key) for key in SENSOR_META)


class KalkotronicSensor(KalkotronicEntity, SensorEntity):
    def __init__(self, coordinator, host: str, key: str) -> None:
        super().__init__(coordinator, host, key)
        meta = SENSOR_META[key]
        self._attr_name = SENSOR_NAMES[key]
        self._attr_unique_id = f"{host}_{key}"
        self._attr_device_class = meta["device_class"]
        self._attr_state_class = meta["state_class"]
        self._attr_native_unit_of_measurement = meta["unit"]
        self._attr_icon = meta["icon"]

    @property
    def native_value(self) -> Any:
        value = self._value
        if isinstance(value, float):
            return round(value, 2)
        return value
