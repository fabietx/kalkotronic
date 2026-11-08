"""Coordinator dei dati Kalkotronic."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import KalkotronicClient
from .const import (
    DAILY_REFRESH_HOUR,
    DAILY_REFRESH_MINUTE,
    DAILY_RETRY,
    DOMAIN,
    UPDATE_FAST,
)

_LOGGER = logging.getLogger(__name__)


class KalkotronicCoordinators:
    """Coordinator "fast" (ogni UPDATE_FAST secondi) e "daily" (alle 00:01 e
    dopo ogni rinvio dell'allarme manutenzione)."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: KalkotronicClient
    ) -> None:
        self._hass = hass
        self._client = client
        self._unsub_retry: CALLBACK_TYPE | None = None

        self.fast: DataUpdateCoordinator[dict] = DataUpdateCoordinator(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_fast",
            update_method=client.fetch_all_fast,
            update_interval=timedelta(seconds=UPDATE_FAST),
            # Le entità vengono riscritte solo se i dati cambiano
            always_update=False,
        )
        self.daily: DataUpdateCoordinator[dict] = DataUpdateCoordinator(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_daily",
            update_method=client.fetch_daily_data,
            update_interval=None,  # aggiornato dal trigger notturno
            always_update=False,
        )

        # Trigger notturno e retry vengono rimossi all'unload/reload dell'entry
        entry.async_on_unload(
            async_track_time_change(
                hass,
                self._async_nightly_refresh,
                hour=DAILY_REFRESH_HOUR,
                minute=DAILY_REFRESH_MINUTE,
                second=0,
            )
        )
        entry.async_on_unload(self._cancel_retry)

    async def async_setup(self) -> None:
        """Primo aggiornamento al setup.

        Il fast è bloccante: se l'impianto non risponde, HA riprova il setup
        da solo. Il daily non lo è: modello e seriale servono solo alle
        informazioni del dispositivo e arriveranno al primo tentativo riuscito.
        """
        await self.fast.async_config_entry_first_refresh()
        await self.async_refresh_daily()

    async def _async_nightly_refresh(self, _now: datetime) -> None:
        _LOGGER.debug("Aggiornamento notturno dei dati giornalieri Kalkotronic")
        await self.async_refresh_daily()

    async def async_refresh_daily(self) -> None:
        """Aggiorna i dati giornalieri; se falliscono, pianifica un nuovo tentativo."""
        self._cancel_retry()
        await self.daily.async_refresh()
        # Ritenta anche se una sola delle pagine giornaliere non ha risposto
        if not self.daily.last_update_success or self._client.daily_incomplete:
            self._unsub_retry = async_call_later(
                self._hass, DAILY_RETRY, self._async_retry_daily
            )

    async def _async_retry_daily(self, _now: datetime) -> None:
        self._unsub_retry = None
        await self.async_refresh_daily()

    @callback
    def _cancel_retry(self) -> None:
        if self._unsub_retry is not None:
            self._unsub_retry()
            self._unsub_retry = None
