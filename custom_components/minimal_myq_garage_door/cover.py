import logging

from homeassistant.components.cover import CoverEntity
from homeassistant.const import STATE_CLOSED, STATE_OPEN

from .const import DOMAIN, CONF_ACCOUNT_ID, CONF_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    def _get_devices():
        return api.devices()

    devices = await hass.async_add_executor_job(_get_devices)

    entities = []
    for device in devices:
        entities.append(MyQGarageCover(device, entry))

    async_add_entities(entities, True)


class MyQGarageCover(CoverEntity):
    def __init__(self, door, entry):
        self._door = door
        self._entry = entry
        self._state = None

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
        return {
            "identifiers": {(DOMAIN, device_id)},
            "name": self.name,
            "manufacturer": getattr(self._door, "manufacturer", "MyQ"),
            "model": getattr(self._door, "device_type", "Garage Door"),
        }

    @property
    def is_closed(self):
        if self._state is None:
            return None
        return self._state.get("door_state") != "open"

    @property
    def should_poll(self):
        return True

    async def async_open_cover(self, **kwargs):
        def _open():
            return self._door.open()

        await self.hass.async_add_executor_job(_open)

    async def async_close_cover(self, **kwargs):
        def _close():
            return self._door.close()

        await self.hass.async_add_executor_job(_close)

    async def async_update(self):
        def _status():
            try:
                return self._door.status()
            except Exception:
                return {}

        self._state = await self.hass.async_add_executor_job(_status)
