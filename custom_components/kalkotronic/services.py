"""Servizi dell'integrazione Kalkotronic."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_UPDATE_DATETIME = "update_datetime"


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Registra i servizi dell'integrazione."""

    async def handle_update_datetime(call: ServiceCall) -> None:
        entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ]
        if not entries:
            raise ServiceValidationError("Nessun dispositivo Kalkotronic attivo")

        # Ora nel fuso configurato in Home Assistant, non in quello del sistema
        now = dt_util.now()
        errors: list[str] = []
        for entry in entries:
            client = entry.runtime_data.client
            try:
                await client.set_datetime(now)
            except Exception as err:  # noqa: BLE001
                errors.append(f"{client.host}: {err}")
                continue
            _LOGGER.info(
                "Orario aggiornato su %s: %s", client.host, now.strftime("%d.%m.%Y %H:%M")
            )

        if errors:
            raise HomeAssistantError(
                "Sincronizzazione orario non riuscita: " + "; ".join(errors)
            )

    hass.services.async_register(DOMAIN, SERVICE_UPDATE_DATETIME, handle_update_datetime)
