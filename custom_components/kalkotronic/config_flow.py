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
    DEFAULT_SUBNET,
    DOMAIN,
    INTERVAL_LIMITS,
)

_LOGGER = logging.getLogger(__name__)

WIFI_KEYS = (CONF_WIFI_SSID, CONF_WIFI_PASSWORD, CONF_GATEWAY, CONF_SUBNET)
INTERVAL_DEFAULTS = {
    CONF_FAST_INTERVAL: DEFAULT_FAST_INTERVAL,
    CONF_HOME_INTERVAL: DEFAULT_HOME_INTERVAL,
    CONF_ENERGY_INTERVAL: DEFAULT_ENERGY_INTERVAL,
}


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


def _interval_schema(defaults: dict[str, Any]) -> dict:
    """Intervalli di lettura in minuti, con i limiti di INTERVAL_LIMITS."""
    schema = {}
    for key, default in INTERVAL_DEFAULTS.items():
        low, high = INTERVAL_LIMITS[key]
        schema[vol.Optional(key, default=defaults.get(key, default))] = (
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=low,
                    max=high,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            )
        )
    return schema


def _clean_intervals(user_input: dict[str, Any]) -> dict[str, int]:
    """Intervalli interi entro i limiti; Home ed energia mai sotto il ciclo base."""
    values = {}
    for key, default in INTERVAL_DEFAULTS.items():
        low, high = INTERVAL_LIMITS[key]
        try:
            value = int(round(float(user_input.get(key, default))))
        except (TypeError, ValueError):
            value = default
        values[key] = min(max(value, low), high)
    fast = values[CONF_FAST_INTERVAL]
    values[CONF_HOME_INTERVAL] = max(values[CONF_HOME_INTERVAL], fast)
    values[CONF_ENERGY_INTERVAL] = max(values[CONF_ENERGY_INTERVAL], fast)
    return values


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
    """Intervalli di lettura e parametri wifi modificabili su installazioni esistenti."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            wifi, errors = _clean_wifi(user_input)
            if not errors:
                return self.async_create_entry(
                    title="", data={**_clean_intervals(user_input), **wifi}
                )
            current = user_input
        else:
            current = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {**_interval_schema(current), **_wifi_schema(current)}
            ),
            errors=errors,
        )
