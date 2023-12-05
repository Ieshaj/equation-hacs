"""The Equation Heaters integration."""
from __future__ import annotations

from equationsdk.equation_api import ApiResponse, EquationAPI

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_INSTALLATION,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    LOGGER,
    PLATFORMS,
)
from .coordinator import EquationDataUpdateCoordinator
from .device_manager import EquationDeviceManager


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Equation Heaters from a config entry."""

    equation_api = EquationAPI(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

    # Login to the Equation API.
    login_result: ApiResponse = await hass.async_add_executor_job(
        equation_api.initialize_authentication
    )

    if not login_result.success:
        raise ConfigEntryNotReady("Unable to connect to the Equation API")

    equation_device_manager = EquationDeviceManager(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        installation_id=entry.data[CONF_INSTALLATION],
        hass=hass,
        equation_api=equation_api,
    )

    equation_coordinator = EquationDataUpdateCoordinator(hass, equation_device_manager)

    await equation_coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = equation_coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and removes event handlers."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def init_device_manager(
    hass: HomeAssistant, entry: ConfigEntry
) -> EquationDataUpdateCoordinator:
    """Initialize the device manager, API and coordinator."""

    equation_api = EquationAPI(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])

    LOGGER.debug("Device manager: Logging in")

    # Login to the Equation API.
    login_result: ApiResponse = await hass.async_add_executor_job(
        equation_api.initialize_authentication
    )

    if not login_result.success:
        raise ConfigEntryNotReady("Unable to connect to the Equation API")

    equation_device_manager = EquationDeviceManager(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        installation_id=entry.data[CONF_INSTALLATION],
        hass=hass,
        equation_api=equation_api,
    )

    return EquationDataUpdateCoordinator(hass, equation_device_manager)
