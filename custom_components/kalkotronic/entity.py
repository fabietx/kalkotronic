"""Entità base Kalkotronic."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN


def device_info(host: str) -> DeviceInfo:
    """Collega l'entità al dispositivo creato in __init__."""
    return DeviceInfo(identifiers={(DOMAIN, host)})


class KalkotronicEntity(CoordinatorEntity[DataUpdateCoordinator[dict[str, Any]]]):
    """Entità legata a una chiave dei dati di un coordinator (fast o daily)."""

    def __init__(
        self, coordinator: DataUpdateCoordinator[dict[str, Any]], host: str, key: str
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_device_info = device_info(host)

    @property
    def _value(self) -> Any:
        data = self.coordinator.data or {}
        return data.get(self._key)

    @property
    def available(self) -> bool:
        # Non disponibile solo se il dato ha superato la tenuta della sua pagina
        # o se l'impianto non risponde affatto
        return super().available and self._value is not None
