"""Cover platform for Minimal MyQ Garage Door integration."""

from __future__ import annotations

from typing import Any
import logging

from homeassistant.components.cover import CoverEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ExampleCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up MyQ cover entities for each garage door."""
    coordinator: ExampleCoordinator = entry.runtime_data.coordinator

    devices = coordinator.data.devices if coordinator.data else []

    entities = []
    for device in devices:
        # recognize door-like devices by presence of open/close methods
        if hasattr(device, "open") and hasattr(device, "close"):
            entities.append(MyQCover(coordinator, device.device_id, getattr(device, "name", f"Garage {device.device_id}")))

    async_add_entities(entities)


class MyQCover(CoordinatorEntity, CoverEntity):
    """Representation of a MyQ garage door as a Cover entity."""

    def __init__(self, coordinator: ExampleCoordinator, device_id: int, name: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_name = name
        self._available = True

    @property
    def unique_id(self) -> str | None:
        return f"{DOMAIN}_{self._device_id}"

    @property
    def is_closed(self) -> bool | None:
        device = self._get_device()
        if not device:
            return None
        try:
            state = device.status().get("door_state")
        except Exception as err:
            _LOGGER.debug("Error reading device status: %s", err)
            return None
        if state is None:
            return None
        return state != "open"

    def _get_device(self):
        return self.coordinator.get_device_by_id(self._device_id)

    async def async_open_cover(self, **kwargs: Any) -> None:
        device = self._get_device()
        if not device:
            return
        await self.hass.async_add_executor_job(device.open)
        await self.coordinator.async_request_refresh()

    async def async_close_cover(self, **kwargs: Any) -> None:
        device = self._get_device()
        if not device:
            return
        await self.hass.async_add_executor_job(device.close)
        await self.coordinator.async_request_refresh()
