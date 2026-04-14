from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import KalkotronicClient
from .const import DOMAIN, UPDATE_FAST, UPDATE_DAILY

_LOGGER = logging.getLogger(__name__)


class KalkotronicCoordinators:
    """Contenitore per i tre coordinator dell'integrazione."""

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
            update_interval=timedelta(seconds=UPDATE_DAILY),
        )
        self.status = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_status",
            update_method=client.fetch_home_status,
            update_interval=timedelta(seconds=UPDATE_FAST),
        )

    async def async_refresh_all(self):
        """Primo aggiornamento di tutti i coordinator al setup."""
        await self.fast.async_config_entry_first_refresh()
        await self.daily.async_config_entry_first_refresh()
        await self.status.async_config_entry_first_refresh()