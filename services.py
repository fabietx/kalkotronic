import logging
from datetime import datetime
from urllib.parse import quote_plus

import aiohttp
from yarl import URL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_services(hass: HomeAssistant):

    async def handle_update_datetime(call: ServiceCall):
        entries: list[ConfigEntry] = hass.config_entries.async_entries(DOMAIN)

        if not entries:
            _LOGGER.error("Nessun dispositivo Kalkotronic configurato")
            return

        now = datetime.now()
        date_str = now.strftime("%d.%m.%Y %H:%M")
        date_encoded = quote_plus(date_str)  # → 13.04.2026+21%3A00

        for entry in entries:
            host = entry.data["host"]
            # encoded=True impedisce ad aiohttp di ri-codificare %3A in %253A
            url = URL(f"http://{host}/?Mia_Data_ora={date_encoded}", encoded=True)

            _LOGGER.debug("Aggiornamento orario Kalkotronic [%s]: %s", host, url)

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as resp:
                        resp.raise_for_status()
                        _LOGGER.info("Orario aggiornato su %s → %s", host, date_str)
            except aiohttp.ClientError as err:
                _LOGGER.error("Errore di rete su %s: %s", host, err)
            except Exception as err:
                _LOGGER.error("Errore inatteso su %s: %s", host, err)

    hass.services.async_register(
        DOMAIN,
        "update_datetime",
        handle_update_datetime,
    )