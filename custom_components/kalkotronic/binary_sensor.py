"""Sensore binario di problema Kalkotronic."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import KalkotronicEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    fast = entry.runtime_data.coordinators.fast
    async_add_entities([KalkotronicProblemSensor(fast, entry.data[CONF_HOST])])


class KalkotronicProblemSensor(KalkotronicEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert"

    def __init__(self, coordinator, host: str) -> None:
        super().__init__(coordinator, host, "system_problem")
        self._attr_name = "System Problem"
        self._attr_unique_id = f"{host}_system_problem"

    @property
    def is_on(self) -> bool | None:
        # True = problema rilevato, False = tutto OK
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {"status_color": data.get("status_color")}
