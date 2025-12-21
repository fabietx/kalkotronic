import logging
from datetime import datetime
from urllib.parse import quote_plus

import aiohttp
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_services(hass: HomeAssistant):
    """Registra i servizi dell'integrazione Kalkotronic."""

    async def handle_update_datetime(call: ServiceCall):
        host = call.data.get("host")

        if not host:
            _LOGGER.error("Servizio update_datetime chiamato senza host")
            return

        # Data e ora correnti
        now = datetime.now()
        date_str = now.strftime("%d.%m.%Y %H:%M")
        date_encoded = quote_plus(date_str)

        url = f"http://{host}/?Mia_Data_ora={date_encoded}"

        _LOGGER.info("Aggiornamento orario Kalkotronic: %s", url)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    resp.raise_for_status()
        except Exception as err:
            _LOGGER.error("Errore aggiornando orario Kalkotronic: %s", err)

    hass.services.async_register(
        DOMAIN,
        "update_datetime",
        handle_update_datetime,
    )
