import logging
import re

import aiohttp
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
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


def _wifi_schema(defaults: dict) -> dict:
    """Campi opzionali per il recupero automatico della rete wifi."""
    return {
        vol.Optional("wifi_ssid", default=defaults.get("wifi_ssid", "")): str,
        vol.Optional(
            "wifi_password", default=defaults.get("wifi_password", "")
        ): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Optional("gateway", default=defaults.get("gateway", "")): str,
        vol.Optional("subnet", default=defaults.get("subnet", "255.255.255.0")): str,
    }


class KalkotronicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KalkotronicOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input["host"].strip()

            if not IPV4_REGEX.match(host):
                errors["host"] = "invalid_ip"

            elif not await _test_connection(host):
                errors["host"] = "cannot_connect"

            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Kalkotronic {host}",
                    data={**user_input, "host": host},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host"): str,
                **_wifi_schema({}),
            }),
            errors=errors,
        )


class KalkotronicOptionsFlow(config_entries.OptionsFlow):
    """Permette di impostare i parametri wifi su installazioni esistenti."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(_wifi_schema(current)),
        )
