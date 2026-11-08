"""Pulsante di reset allarmi Kalkotronic."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([KalkotronicResetButton(entry)])


class KalkotronicResetButton(ButtonEntity):
    _attr_icon = "mdi:alarm-light-off"

    def __init__(self, entry: ConfigEntry) -> None:
        host = entry.data[CONF_HOST]
        self._client = entry.runtime_data.client
        self._fast = entry.runtime_data.coordinators.fast
        self._attr_name = "Reset Allarmi"
        self._attr_unique_id = f"{host}_reset_alarms"
        self._attr_device_info = device_info(host)

    async def async_press(self) -> None:
        # Passa dal client: la richiesta viene accodata alle letture in corso
        try:
            await self._client.reset_alarms()
        except Exception as err:
            raise HomeAssistantError(
                f"Reset allarmi su {self._client.host} non riuscito: {err}"
            ) from err
        _LOGGER.info("Reset allarmi eseguito su %s", self._client.host)
        # Aggiorna subito i contatori allarmi
        await self._fast.async_request_refresh()
