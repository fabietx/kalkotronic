from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import services
from .const import DOMAIN

PLATFORMS = ["sensor", "button", "binary_sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    """Setup iniziale dell'integrazione."""
    await services.async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Setup via Config Flow."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)