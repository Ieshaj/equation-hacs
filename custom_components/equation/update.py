"""Update entity platform for Equation devices."""
from __future__ import annotations

from abc import ABC

from equationsdk.device import EquationDevice

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EquationDataUpdateCoordinator
from .equation_entity import EquationRadiatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the radiator sensors from the config entry."""
    coordinator: EquationDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Register the Entity classes and platform on the coordinator.
    coordinator.add_entities_for_seen_keys(
        async_add_entities,
        [EquationUpdateEntity],
        "update",
    )


class EquationUpdateEntity(EquationRadiatorEntity, UpdateEntity, ABC):
    """Update entity."""

    def __init__(
        self,
        radiator: EquationDevice,
        coordinator: EquationDataUpdateCoordinator,
    ) -> None:
        """Init the update entity."""

        self.entity_description = UpdateEntityDescription(
            key="fw_update_available",
            name="Update Available",
            device_class=UpdateDeviceClass.FIRMWARE,
            entity_category=EntityCategory.DIAGNOSTIC,
        )

        # Set the name and ID of this entity to be the radiator name/id and a prefix.
        super().__init__(
            coordinator,
            radiator,
            name=f"{radiator.name} Update Available",
            unique_id=f"{radiator.id}-fw_update_available",
        )

    @property
    def installed_version(self) -> str | None:
        """Version installed and in use."""
        return self._radiator.firmware_version

    @property
    def latest_version(self) -> str | None:
        """Latest version available for install."""
        return self._radiator.latest_firmware_version
