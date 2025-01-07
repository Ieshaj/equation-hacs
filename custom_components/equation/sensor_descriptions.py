"""Sensor descriptions for Equation."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass
)
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.typing import StateType

from .device_manager import EquationDevice


@dataclass
class EquationSensorEntityDescriptionMixin:
    """Define a description mixin for Equation sensor entities."""

    value_fn: Callable[[EquationDevice], StateType]
    last_reset_fn: Callable[[EquationDevice], datetime | None]


@dataclass
class EquationSensorEntityDescription(
    SensorEntityDescription, EquationSensorEntityDescriptionMixin
):
    """Define an object to describe Equation sensor entities."""


SENSOR_DESCRIPTIONS = [
    # Current room temperature sensor (probe value).
    EquationSensorEntityDescription(
        key="current_temperature",
        name="Current Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda radiator: radiator.temp_probe,
        last_reset_fn=lambda radiator: None,
    ),
    # Window open sensor.
    EquationSensorEntityDescription(
        key="window_open",
        name="Window Open",
        device_class=BinarySensorDeviceClass.WINDOW,
        value_fn=lambda radiator: radiator.windows_open_status,
        last_reset_fn=lambda radiator: None,
    ),
    # Energy usage in Kw/h.
    EquationSensorEntityDescription(
        key="energy",
        name="Energy Consumption",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda radiator: radiator.energy_data.kwh
        if radiator.energy_data
        else None,
        last_reset_fn=lambda radiator: radiator.energy_data.start
        if radiator.energy_data
        else None,
    ),
    # Effective power usage in W.
    EquationSensorEntityDescription(
        key="power",
        name="Effective Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda radiator: radiator.energy_data.effective_power
        if radiator.energy_data
        else None,
        last_reset_fn=lambda radiator: None,
    ),
]
