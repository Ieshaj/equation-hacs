"""A sensor for the current Equation radiator temperature."""
from __future__ import annotations

from datetime import datetime

from equationsdk.device import EquationDevice

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .coordinator import EquationDataUpdateCoordinator
from .equation_entity import EquationRadiatorEntity
from .sensor_descriptions import SENSOR_DESCRIPTIONS, EquationSensorEntityDescription


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the radiator sensors from the config entry."""
    coordinator: EquationDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    coordinator.add_sensor_entities_for_seen_keys(
        async_add_entities, SENSOR_DESCRIPTIONS, EquationGenericSensor
    )


class EquationGenericSensor(EquationRadiatorEntity, SensorEntity):
    """Generic radiator sensor."""

    entity_description: EquationSensorEntityDescription

    def __init__(
        self,
        radiator: EquationDevice,
        coordinator: EquationDataUpdateCoordinator,
        description: EquationSensorEntityDescription,
    ) -> None:
        """Initialize a generic sensor."""
        super().__init__(
            coordinator,
            radiator,
            name=f"{radiator.name} {description.name}",
            unique_id=f"{radiator.id}-{description.key}",
        )

        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        return self.entity_description.value_fn(self._radiator)

    @property
    def last_reset(self) -> datetime | None:
        """Return the last time the sensor was initialized, if relevant."""
        return self.entity_description.last_reset_fn(self._radiator)
