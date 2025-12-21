from homeassistant import config_entries
import voluptuous as vol

from .const import DOMAIN, CONF_HOST


class KalkotronicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kalkotronic."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # per ora NON validiamo l'IP
            return self.async_create_entry(
                title=f"Kalkotronic ({user_input[CONF_HOST]})",
                data={
                    CONF_HOST: user_input[CONF_HOST]
                },
            )

        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )