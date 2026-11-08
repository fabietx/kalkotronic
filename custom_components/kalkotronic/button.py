"""Pulsante di rinvio dell'allarme manutenzione Kalkotronic."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([KalkotronicMaintenanceSnoozeButton(entry)])


class KalkotronicMaintenanceSnoozeButton(ButtonEntity):
    """Equivale a "RESET ALLARME MANUTENZIONE" della pagina ResAll.

    Silenzia l'allarme manutenzione per 7 giorni; dopo 180 giorni di ritardo
    l'impianto si blocca comunque. Non azzera i contatori allarmi.
    È tra i controlli di configurazione per evitare pressioni accidentali.
    """

    _attr_icon = "mdi:wrench-clock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: ConfigEntry) -> None:
        host = entry.data[CONF_HOST]
        self._client = entry.runtime_data.client
        self._coordinators = entry.runtime_data.coordinators
        self._attr_name = "Rinvio Manutenzione"
        # unique_id invariato dalla v0.4: entity_id e automazioni restano validi
        self._attr_unique_id = f"{host}_reset_alarms"
        self._attr_device_info = device_info(host)

    async def async_press(self) -> None:
        # Passa dal client: la richiesta viene accodata alle letture in corso
        try:
            await self._client.snooze_maintenance_alarm()
        except Exception as err:
            raise HomeAssistantError(
                f"Rinvio allarme manutenzione su {self._client.host} non riuscito: {err}"
            ) from err
        _LOGGER.info("Allarme manutenzione rinviato su %s", self._client.host)
        # Aggiorna lo stato dell'impianto e i giorni alla riattivazione
        await self._coordinators.fast.async_request_refresh()
        await self._coordinators.async_refresh_daily()
