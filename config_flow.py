import asyncio
import logging
import re

import aiohttp
from homeassistant import config_entries
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

IPV4_REGEX = re.compile(
    r"^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)


async def _test_connection(host: str) -> bool:
    """Verifica che il dispositivo risponda sulla porta 80."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{host}/",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                return resp.status == 200
    except Exception:
        return False


class KalkotronicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input["host"].strip()

            # Validazione formato IPv4
            if not IPV4_REGEX.match(host):
                errors["host"] = "invalid_ip"

            # Test connessione
            elif not await _test_connection(host):
                errors["host"] = "cannot_connect"

            else:
                # Evita duplicati
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Kalkotronic {host}",
                    data={"host": host},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host"): str,
            }),
            errors=errors,
        )