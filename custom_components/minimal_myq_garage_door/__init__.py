import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, PLATFORMS, CONF_ACCOUNT_ID, CONF_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)

import mypyq


def check_and_update_refresh_token(hass: HomeAssistant, entry: ConfigEntry, api) -> None:
    """Check if the refresh token has been updated by the library and persist it."""
    try:
        handle = getattr(api, "handle", None)
        if isinstance(handle, dict):
            new_refresh = handle.get("refresh_token")
            current_refresh = entry.data.get(CONF_REFRESH_TOKEN)
            if new_refresh and new_refresh != current_refresh:
                new_data = {**entry.data, CONF_REFRESH_TOKEN: new_refresh}
                hass.config_entries.async_update_entry(entry, data=new_data)
                _LOGGER.debug("Persisted updated refresh token from mypyq library")
    except Exception:  # pragma: no cover - defensive
        _LOGGER.debug("Could not inspect api.handle for refresh token", exc_info=True)


async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    account_id = entry.data.get(CONF_ACCOUNT_ID)
    refresh_token = entry.data.get(CONF_REFRESH_TOKEN)

    def _create_api():
        return mypyq.create(account_id=account_id, refresh_token=refresh_token)

    api = await hass.async_add_executor_job(_create_api)

    # Check for a refreshed token after initial API creation
    check_and_update_refresh_token(hass, entry, api)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"api": api, "entry": entry}

    # Forward setup for all platforms using the plural API
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    results = await asyncio.gather(
        *[
            hass.config_entries.async_forward_entry_unload(entry, platform)
            for platform in PLATFORMS
        ]
    )
    if all(results):
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        return True
    return False
