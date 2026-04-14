from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN


class KalkotronicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Qui in futuro si può aggiungere un test di connessione
            return self.async_create_entry(
                title=f"Kalkotronic {user_input['host']}",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("host"): str,
            }),
            errors=errors,
        )