"""Integration 101 Template integration using DataUpdateCoordinator."""

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_REFRESH_TOKEN,
    CONF_ACCOUNTID
)
from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

import json
import mypyq
import mypyq.api

_LOGGER = logging.getLogger(__name__)


@dataclass
class ExampleAPIData:
    """Class to hold api data."""

    controller_name: str
    devices: list


class ExampleCoordinator(DataUpdateCoordinator):
    """My example coordinator."""

    data: ExampleAPIData

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""

        # Set variables from values entered in config flow setup
        self.account = config_entry.data[CONF_ACCOUNTID]
        self.refresh = config_entry.data[CONF_REFRESH_TOKEN]
        self.config_entry = config_entry

        # set variables from options.  You need a default here incase options have not been set
        self.poll_interval = 10

        # Initialise DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            # Method to call on every update interval.
            update_method=self.async_update_data,
            # Polling interval. Will only be polled if there are subscribers.
            # Using config option here but you can just use a value.
            update_interval=timedelta(seconds=self.poll_interval),
        )

        # Initialise your api here. Prefer creating from saved handle if available
        handle_json = config_entry.data.get("handle")
        if handle_json:
            try:
                handle = json.loads(handle_json)
                self.api = mypyq.create(handle=handle)
            except Exception:  # fallback to account/refresh
                self.api = mypyq.create(account_id=self.account, refresh_token=self.refresh)
        else:
            self.api = mypyq.create(account_id=self.account, refresh_token=self.refresh)

    async def async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            devices = await self.hass.async_add_executor_job(self.api.devices)
        except Exception as err:
            # This will show entities as unavailable by raising UpdateFailed exception
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        # Persist refresh token if library rotated it in the handle
        try:
            handle = mypyq.api.get_handle(self.api)
            new_refresh = handle.get("refreshToken")
            if new_refresh and new_refresh != self.config_entry.data.get(CONF_REFRESH_TOKEN):
                # update the config entry with new refresh token and handle
                await self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, CONF_REFRESH_TOKEN: new_refresh, "handle": json.dumps(handle)},
                )
        except Exception:
            # Ignore handle update errors
            pass

        # What is returned here is stored in self.data by the DataUpdateCoordinator
        return ExampleAPIData(self.api.controller_name, devices)

    # Might have to change below !!!!!
    def get_device_by_id(self, device_id: int):
        """Return device by device id."""
        try:
            return [
                device for device in self.data.devices if getattr(device, "device_id", None) == device_id
            ][0]
        except Exception:
            return None
