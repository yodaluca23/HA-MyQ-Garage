"""Config flow for Minimal MyQ Garage Door integration."""

from __future__ import annotations

import logging
from typing import Any

import mypyq
import json
import mypyq.api

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_ACCOUNTID,
    CONF_REFRESH_TOKEN
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .api import API, APIAuthError, APIConnectionError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCOUNTID, description={"suggested_value": "test"}): str,
        vol.Required(CONF_REFRESH_TOKEN, description={"suggested_value": "1234"}): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data[CONF_USERNAME], data[CONF_PASSWORD]
    # )

    try:
        api = await hass.async_add_executor_job(
            mypyq.create, data[CONF_ACCOUNTID], data[CONF_REFRESH_TOKEN]
        )
        handle = mypyq.api.get_handle(api)
    except Exception as e:
        raise CannotConnect from e

    # Save the handle (as JSON string) and the authoritative refresh token
    handle_json = json.dumps(handle)
    refresh = handle.get("refreshToken", data[CONF_REFRESH_TOKEN])

    return {
        "title": f"MyQ Account {data[CONF_ACCOUNTID]}",
        "handle": handle_json,
        CONF_REFRESH_TOKEN: refresh,
    }


class ExampleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Example Integration."""

    VERSION = 1
    _input_data: dict[str, Any]

    @staticmethod
    @callback

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        # Called when you initiate adding an integration via the UI
        errors: dict[str, str] = {}

        if user_input is not None:
            # The form has been filled in and submitted, so process the data provided.
            try:
                # Validate that the setup data is valid and if not handle errors.
                # The errors["base"] values match the values in your strings.json and translation files.
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                # Validation was successful, so create a unique id for this instance of your integration
                # and create the config entry.
                await self.async_set_unique_id(info.get("title"))
                self._abort_if_unique_id_configured()
                # Merge returned info (handle/refresh) into stored data
                data = {**user_input}
                if info.get("handle"):
                    data["handle"] = info["handle"]
                if info.get(CONF_REFRESH_TOKEN):
                    data[CONF_REFRESH_TOKEN] = info[CONF_REFRESH_TOKEN]

                return self.async_create_entry(title=info["title"], data=data)

        # Show initial form.
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add reconfigure step to allow to reconfigure a config entry."""
        # This methid displays a reconfigure option in the integration and is
        # different to options.
        # It can be used to reconfigure any of the data submitted when first installed.
        # This is optional and can be removed if you do not want to allow reconfiguration.
        errors: dict[str, str] = {}
        config_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Merge returned handle/refresh into data to save
                new_data = {**config_entry.data, **user_input}
                if info.get("handle"):
                    new_data["handle"] = info["handle"]
                if info.get(CONF_REFRESH_TOKEN):
                    new_data[CONF_REFRESH_TOKEN] = info[CONF_REFRESH_TOKEN]

                return self.async_update_reload_and_abort(
                    config_entry,
                    unique_id=config_entry.unique_id,
                    data=new_data,
                    reason="reconfigure_successful",
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_REFRESH_TOKEN, default=config_entry.data[CONF_REFRESH_TOKEN]
                    ): str,
                    vol.Required(CONF_ACCOUNTID, default=config_entry.data[CONF_ACCOUNTID]): str,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
