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
    conf = {**entry.data, **entry.options}
    client = KalkotronicClient(
        conf["host"],
        wifi_ssid=conf.get("wifi_ssid"),
        wifi_password=conf.get("wifi_password"),
        gateway=conf.get("gateway"),
        subnet=conf.get("subnet"),
    )
    coordinators = KalkotronicCoordinators(hass, client)
    await coordinators.async_refresh_all()

    # Rendi i coordinator disponibili alle piattaforme
    data = hass.data.setdefault(DOMAIN, {})
    data[entry.entry_id] = {"coordinators": coordinators, "client": client}

    # Ricarica l'integrazione quando cambiano le opzioni (parametri wifi)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload_on_update(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, {})
        client = entry_data.get("client")
        if client:
            await client.close()
    return unloaded