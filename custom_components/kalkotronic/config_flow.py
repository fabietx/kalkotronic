"""Config flow e options flow Kalkotronic."""

from __future__ import annotations

import ipaddress
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_GATEWAY,
    CONF_SUBNET,
    CONF_WIFI_PASSWORD,
    CONF_WIFI_SSID,
    DEFAULT_SUBNET,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

WIFI_KEYS = (CONF_WIFI_SSID, CONF_WIFI_PASSWORD, CONF_GATEWAY, CONF_SUBNET)


def _is_ipv4(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        return False
    return True


def _is_netmask(value: str) -> bool:
    try:
        ipaddress.IPv4Network(f"0.0.0.0/{value}")
    except ValueError:
        return False
    return True


async def _test_connection(host: str) -> bool:
    """Verifica che il dispositivo risponda sulla porta 80."""
    try:
        connector = aiohttp.TCPConnector(force_close=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                f"http://{host}/", timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                return resp.status == 200
    except Exception:  # noqa: BLE001
        return False


def _clean_wifi(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Normalizza e valida i parametri wifi (tutti opzionali, ma coerenti)."""
    data = {key: str(user_input.get(key) or "").strip() for key in WIFI_KEYS}
    if not data[CONF_SUBNET]:
        data[CONF_SUBNET] = DEFAULT_SUBNET

    errors: dict[str, str] = {}
    if data[CONF_GATEWAY] and not _is_ipv4(data[CONF_GATEWAY]):
        errors[CONF_GATEWAY] = "invalid_gateway"
    if not _is_netmask(data[CONF_SUBNET]):
        errors[CONF_SUBNET] = "invalid_subnet"

    # Il recupero automatico funziona solo con SSID, password e gateway insieme
    required = (data[CONF_WIFI_SSID], data[CONF_WIFI_PASSWORD], data[CONF_GATEWAY])
    if any(required) and not all(required) and not errors:
        errors["base"] = "incomplete_wifi"
    return data, errors


def _wifi_schema(defaults: dict[str, Any]) -> dict:
    """Campi opzionali per il recupero automatico della rete wifi."""
    return {
        vol.Optional(
            CONF_WIFI_SSID, default=defaults.get(CONF_WIFI_SSID, "")
        ): str,
        vol.Optional(
            CONF_WIFI_PASSWORD, default=defaults.get(CONF_WIFI_PASSWORD, "")
        ): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_GATEWAY, default=defaults.get(CONF_GATEWAY, "")): str,
        vol.Optional(
            CONF_SUBNET, default=defaults.get(CONF_SUBNET, DEFAULT_SUBNET)
        ): str,
    }


class KalkotronicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KalkotronicOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        defaults: dict[str, Any] = {}

        if user_input is not None:
            defaults = user_input
            host = str(user_input[CONF_HOST]).strip()
            wifi, errors = _clean_wifi(user_input)

            if not _is_ipv4(host):
                errors[CONF_HOST] = "invalid_ip"
            elif not errors:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                if not await _test_connection(host):
                    errors[CONF_HOST] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=f"Kalkotronic {host}",
                        data={CONF_HOST: host, **wifi},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
                    **_wifi_schema(defaults),
                }
            ),
            errors=errors,
        )


class KalkotronicOptionsFlow(config_entries.OptionsFlow):
    """Parametri wifi modificabili su installazioni esistenti."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            wifi, errors = _clean_wifi(user_input)
            if not errors:
                return self.async_create_entry(title="", data=wifi)
            current = user_input
        else:
            current = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(_wifi_schema(current)),
            errors=errors,
        )
