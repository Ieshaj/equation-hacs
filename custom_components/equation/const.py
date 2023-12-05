"""Constants for the Equation Heaters integration."""

import logging

from homeassistant.const import Platform

LOGGER = logging.getLogger(__package__)

DOMAIN = "equation"
DEVICE_DOMAIN = "climate"
PLATFORMS: list[str] = [Platform.CLIMATE, Platform.SENSOR, Platform.UPDATE]
CONF_USERNAME = "equation_username"
CONF_PASSWORD = "equation_password"
CONF_INSTALLATION = "equation_installation"

EQUATION_MANUFACTURER = "Equation"

EQUATION_SUPPORTED_DEVICES = ["radiator", "towel", "therm"]

CMD_SET_TEMP = "cmd_set_temp"
CMD_SET_PRESET = "cmd_set_preset"
CMD_HVAC_OFF = "cmd_turn_off"
CMD_SET_HVAC_MODE = "cmd_set_hvac_mode"

RADIATOR_DEFAULT_TEMPERATURE = 20

PRESET_EQUATION_ICE = "Anti-frost"

RADIATOR_TEMP_STEP = 0.5
RADIATOR_TEMP_MIN = 7.0
RADIATOR_TEMP_MAX = 30.0

RADIATOR_PRESET_ECO = "eco"
RADIATOR_PRESET_COMFORT = "comfort"
RADIATOR_PRESET_ICE = "ice"
RADIATOR_PRESET_NONE = "none"

RADIATOR_MODE_AUTO = "auto"
RADIATOR_MODE_MANUAL = "manual"
