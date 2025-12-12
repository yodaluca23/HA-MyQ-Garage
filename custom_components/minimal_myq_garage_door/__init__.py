import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, PLATFORMS, CONF_ACCOUNT_ID, CONF_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)

import mypyq


async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    account_id = entry.data.get(CONF_ACCOUNT_ID)
    refresh_token = entry.data.get(CONF_REFRESH_TOKEN)

    def _create_api():
        return mypyq.create(account_id=account_id, refresh_token=refresh_token)

    api = await hass.async_add_executor_job(_create_api)

    # Try to detect a refreshed token and persist it to the config entry
    try:
        handle = getattr(api, "handle", None)
        if isinstance(handle, dict):
            new_refresh = handle.get("refresh_token")
            if new_refresh and new_refresh != refresh_token:
                new_data = {**entry.data, CONF_REFRESH_TOKEN: new_refresh}
                hass.config_entries.async_update_entry(entry, data=new_data)
    except Exception:  # pragma: no cover - defensive
        _LOGGER.debug("Could not inspect api.handle for refresh token", exc_info=True)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"api": api}

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

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
