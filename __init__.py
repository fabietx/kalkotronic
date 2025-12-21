from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

PLATFORMS = ["sensor", "button"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Setup via Config Flow."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)