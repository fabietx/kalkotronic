"""Integrazione Home Assistant per gli addolcitori Kalkotronic."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from . import services
from .client import KalkotronicClient
from .const import (
    CONF_ENERGY_INTERVAL,
    CONF_FAST_INTERVAL,
    CONF_GATEWAY,
    CONF_HOME_INTERVAL,
    CONF_SUBNET,
    CONF_WIFI_PASSWORD,
    CONF_WIFI_SSID,
    DEFAULT_ENERGY_INTERVAL,
    DEFAULT_FAST_INTERVAL,
    DEFAULT_HOME_INTERVAL,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import KalkotronicCoordinators

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class KalkotronicRuntimeData:
    """Oggetti condivisi tra le piattaforme di un'entry."""

    client: KalkotronicClient
    coordinators: KalkotronicCoordinators


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    services.async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    conf = {**entry.data, **entry.options}
    host = conf[CONF_HOST]
    # Intervalli in minuti nelle opzioni, in secondi per client e coordinator
    fast = int(conf.get(CONF_FAST_INTERVAL, DEFAULT_FAST_INTERVAL)) * 60
    home = int(conf.get(CONF_HOME_INTERVAL, DEFAULT_HOME_INTERVAL)) * 60
    energy = int(conf.get(CONF_ENERGY_INTERVAL, DEFAULT_ENERGY_INTERVAL)) * 60
    client = KalkotronicClient(
        host,
        wifi_ssid=conf.get(CONF_WIFI_SSID),
        wifi_password=conf.get(CONF_WIFI_PASSWORD),
        gateway=conf.get(CONF_GATEWAY),
        subnet=conf.get(CONF_SUBNET),
        fast_interval=fast,
        home_interval=home,
        energy_interval=energy,
    )
    coordinators = KalkotronicCoordinators(hass, entry, client, fast)

    try:
        await coordinators.async_setup()
    except BaseException:
        # Setup fallito (HA lo riproverà): non lasciare sessioni aperte
        await client.close()
        raise

    entry.runtime_data = KalkotronicRuntimeData(client, coordinators)

    # Il dispositivo viene creato qui e aggiornato a ogni lettura giornaliera,
    # così modello, seriale e versione restano allineati
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, host)},
        manufacturer=MANUFACTURER,
        name=f"Kalkotronic {host}",
    )

    @callback
    def _async_update_device() -> None:
        info = coordinators.daily.data
        if not info:
            return
        device = device_registry.async_get_device(identifiers={(DOMAIN, host)})
        if device is None:
            return
        device_registry.async_update_device(
            device.id,
            model=info.get("model"),
            serial_number=info.get("serial"),
            sw_version=info.get("sw_version"),
        )

    _async_update_device()
    entry.async_on_unload(coordinators.daily.async_add_listener(_async_update_device))

    # Ricarica l'integrazione quando cambiano le opzioni (wifi, intervalli)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.close()
    return unloaded
