import logging
from datetime import datetime

from homeassistant.components.cover import CoverEntity, CoverEntityFeature, CoverDeviceClass
from homeassistant.const import STATE_CLOSED, STATE_OPEN

from .const import DOMAIN, CONF_ACCOUNT_ID, CONF_REFRESH_TOKEN
from . import check_and_update_refresh_token

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    api = data["api"]

    def _get_devices():
        return api.devices()

    devices = await hass.async_add_executor_job(_get_devices)

    # Check for token update after fetching devices
    check_and_update_refresh_token(hass, entry, api)

    entities = []
    for device in devices:
        entities.append(MyQGarageCover(hass, device, entry, api))

    async_add_entities(entities, True)


class MyQGarageCover(CoverEntity):
    def __init__(self, hass, door, entry, api):
        self._hass = hass
        self._door = door
        self._entry = entry
        self._api = api
        self._state = None
        self._added_to_hass = False

    async def async_added_to_hass(self):
        """Run when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self._added_to_hass = True

    @property
    def unique_id(self):
        return getattr(self._door, "device_id", None)

    @property
    def name(self):
        return getattr(self._door, "name", self.unique_id)

    @property
    def device_info(self):
        """Return device information for this door so HA creates a Device per door."""
        device_id = getattr(self._door, "device_id", None) or self.unique_id
        device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": self.name,
            "manufacturer": getattr(self._door, "manufacturer", "MyQ"),
            "model": getattr(self._door, "device_type", "Garage Door"),
        }
        
        # Add serial number if available
        serial_number = getattr(self._door, "serial_number", None)
        if serial_number:
            device_info["serial_number"] = serial_number
        
        return device_info

    @property
    def is_closed(self):
        if self._state is None:
            return None
        return self._state.get("door_state") != "open"

    @property
    def available(self):
        """Return True if the device is online."""
        if self._state is None:
            return None  # Don't mark as unavailable until we have actual data
        return self._state.get("online", False)

    @property
    def device_class(self):
        """Return the device class."""
        return CoverDeviceClass.GARAGE

    @property
    def extra_state_attributes(self):
        """Return extra state attributes for battery and last update info."""
        attrs = {}
        if self._state is None:
            return attrs
        
        # Add battery status attributes
        if self._state.get("dps_battery_critical"):
            attrs["battery_critical"] = True
        if self._state.get("dps_low_battery_mode"):
            attrs["low_battery"] = True
        
        # Add last update timestamp
        last_update = self._state.get("last_update")
        if last_update:
            attrs["last_update"] = last_update
        
        return attrs

    @property
    def should_poll(self):
        return True

    @property
    def supported_features(self):
        """Return supported features bitmask.

        Only support open and close to avoid showing Stop control in the UI.
        """
        return CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    async def async_open_cover(self, **kwargs):
        def _open():
            return self._door.open()

        await self.hass.async_add_executor_job(_open)
        check_and_update_refresh_token(self.hass, self._entry, self._api)

    async def async_close_cover(self, **kwargs):
        def _close():
            return self._door.close()

        await self.hass.async_add_executor_job(_close)
        check_and_update_refresh_token(self.hass, self._entry, self._api)

    async def async_update(self):
        def _status():
            try:
                return self._door.status()
            except Exception:
                return {}

        self._state = await self.hass.async_add_executor_job(_status)

        # Check for token update after status call
        check_and_update_refresh_token(self.hass, self._entry, self._api)
        
        # Update the internal last_changed timestamp based on device's last_update
        if self._state and self._state.get("last_update"):
            try:
                last_update_dt = datetime.fromisoformat(self._state.get("last_update").replace("Z", "+00:00"))
                self._last_changed = last_update_dt
            except (ValueError, AttributeError):
                pass
        
        # Force Home Assistant to update the entity state and refresh last_changed
        # Only call this after the entity is added to HA (has entity_id)
        if self._added_to_hass:
            self.async_write_ha_state()
