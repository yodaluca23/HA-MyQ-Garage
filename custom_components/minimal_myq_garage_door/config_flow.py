import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_ACCOUNT_ID, CONF_REFRESH_TOKEN


class MyQConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Save account_id and refresh_token
            return self.async_create_entry(title="MyQ Garage", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ACCOUNT_ID): str,
                vol.Required(CONF_REFRESH_TOKEN): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
