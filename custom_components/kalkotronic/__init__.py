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
    data = hass.data.setdefault(DOMAIN, {})
    data[entry.entry_id] = {"coordinators": coordinators, "client": client}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, {})
        client = entry_data.get("client")
        if client:
            await client.close()
    return unloaded