from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_time_change

from .client import KalkotronicClient
from .const import DOMAIN, UPDATE_FAST

_LOGGER = logging.getLogger(__name__)


class KalkotronicCoordinators:

    def __init__(self, hass: HomeAssistant, client: KalkotronicClient):
        self.fast = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_fast",
            update_method=client.fetch_fast_data,
            update_interval=timedelta(seconds=UPDATE_FAST),
        )
        self.daily = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_daily",
            update_method=client.fetch_daily_data,
            update_interval=None,  # nessun intervallo automatico
        )
        self.status = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_status",
            update_method=client.fetch_home_status,
            update_interval=timedelta(seconds=UPDATE_FAST),
        )
        self.energy = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_energy",
            update_method=client.fetch_energy_data,
            update_interval=timedelta(seconds=UPDATE_FAST),
        )

        # Trigger alle 00:01 ogni notte per il coordinator daily
        async_track_time_change(
            hass,
            self._refresh_daily,
            hour=0,
            minute=1,
            second=0,
        )

    async def _refresh_daily(self, now):
        """Chiamato automaticamente alle 00:01 ogni notte."""
        _LOGGER.debug("Aggiornamento notturno dati daily Kalkotronic")
        await self.daily.async_refresh()

    async def async_refresh_all(self):
        """Primo aggiornamento di tutti i coordinator al setup."""
        await self.fast.async_config_entry_first_refresh()
        await self.daily.async_config_entry_first_refresh()
        await self.status.async_config_entry_first_refresh()
        await self.energy.async_config_entry_first_refresh()
        