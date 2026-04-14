from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .client import KalkotronicClient
from .coordinator import KalkotronicCoordinators
from .const import DOMAIN
from . import services

PLATFORMS = ["sensor", "binary_sensor", "button"]


async def async_setup(hass: HomeAssistant, config: dict):
    await services.async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    client = KalkotronicClient(entry.data["host"])
    coordinators = KalkotronicCoordinators(hass, client)
    await coordinators.async_refresh_all()

    # Rendi i coordinator disponibili alle piattaforme
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded