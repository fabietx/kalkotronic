import logging
import aiohttp
from datetime import datetime
from urllib.parse import quote_plus
from homeassistant.core import HomeAssistant, ServiceCall

_LOGGER = logging.getLogger(__name__)
DOMAIN = "kalkotronic"

async def async_setup(hass: HomeAssistant):
    """Registrazione servizio custom update_datetime."""

    async def update_datetime_service(call: ServiceCall):
        host = call.data.get("host")
        if not host:
            _LOGGER.error("Nessun host specificato per il servizio update_datetime")
            return

        now = datetime.now()
        date_str = now.strftime("%d.%m.%Y %H:%M")
        date_encoded = quote_plus(date_str)

        url = f"http://{host}/?Mia_Data_ora={date_encoded}"
        _LOGGER.info("Aggiornamento orario sul dispositivo %s: %s", host, url)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    resp.raise_for_status()
                    _LOGGER.info("Aggiornamento orario eseguito correttamente su %s", host)
        except Exception as e:
            _LOGGER.error("Errore aggiornando orario su %s: %s", host, e)

    hass.services.async_register(DOMAIN, "update_datetime", update_datetime_service)
    return True
