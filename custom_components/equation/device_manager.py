"""Equation app data model."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from equationsdk.device import EquationDevice, ScheduleMode
from equationsdk.dto import EnergyConsumptionData
from equationsdk.model import EquationProduct
from equationsdk.equation_api import ApiResponse, EquationAPI
from equationsdk.utils import get_product_by_type_version

from homeassistant.components.climate import PRESET_COMFORT, PRESET_ECO, HVACMode
from homeassistant.core import HomeAssistant

from .const import (
    CMD_SET_HVAC_MODE,
    CMD_SET_PRESET,
    CMD_SET_TEMP,
    LOGGER,
    PRESET_EQUATION_ICE,
    RADIATOR_DEFAULT_TEMPERATURE,
    RADIATOR_MODE_MANUAL,
    RADIATOR_PRESET_COMFORT,
    RADIATOR_PRESET_ECO,
    RADIATOR_PRESET_ICE,
    RADIATOR_PRESET_NONE,
    EQUATION_SUPPORTED_DEVICES,
)


def determine_latest_firmware(
    device_data: dict[str, Any], fw_map: dict[EquationProduct, dict[str, str]]
) -> str | None:
    """Determine the latest FW available for a device."""

    if not device_data or "data" not in device_data:
        return None

    product_type = device_data["data"].get("type", None)
    version = device_data["data"].get("product_version", None)
    current_firmware = device_data["firmware"].get("firmware_version_device", None)

    if not any((product_type, version, current_firmware)):
        LOGGER.warning(
            "Unable to determine latest FW for [%s][%s] at v[%s]",
            product_type,
            version,
            current_firmware,
        )
        return None

    if (product := get_product_by_type_version(product_type, version)) is None:
        LOGGER.warning(
            "Product not found: [%s][%s] at v[%s]",
            product_type,
            version,
            current_firmware,
        )
        return None

    if product in fw_map and current_firmware in fw_map[product]:
        return fw_map[product][current_firmware]

    # If no update path available return the current firmware string.
    return current_firmware


class EquationDeviceManager:
    """Device Manager."""

    def __init__(
        self,
        username: str,
        password: str,
        installation_id: str,
        hass: HomeAssistant,
        equation_api: EquationAPI,
    ) -> None:
        """Initialize the device manager."""
        self.username = username
        self.password = password
        self.installation_id = installation_id
        self.equation_api = equation_api

        self.hass = hass
        self.auth_token = None
        self.auth_token_expire_date: datetime | None = None

        self.equation_devices: dict[str, EquationDevice] = {}

    def _fail_all_devices(self):
        """Set all devices as unavailable."""

        if self.equation_devices:
            for device in self.equation_devices.values():
                device.hass_available = False

    async def update(self) -> dict[str, list[EquationDevice]]:
        """Retrieve the devices from the user's installation.

        Returns a list of newly discovered devices.
        """

        LOGGER.debug("Device manager updating")

        installation_devices_response: ApiResponse = (
            await self.hass.async_add_executor_job(
                self.equation_api.get_installation_devices, self.installation_id
            )
        )

        if not installation_devices_response.success:
            LOGGER.error(
                "Unable to get zone devices. Error: %s",
                installation_devices_response.error_message,
            )
            self._fail_all_devices()
            return {}

        user_device_ids: list[str] = installation_devices_response.data
        discovered_devices: dict[str, list[EquationDevice]] = {}

        # device_id -> (base data future, energy data future)
        device_data_futures: dict[str, tuple[asyncio.Future, asyncio.Future]] = {}
        pending_futures: list[asyncio.Future] = []

        # Firmware data.
        firmware_map_future: asyncio.Future = self.hass.async_add_executor_job(
            self.equation_api.get_latest_firmware
        )
        pending_futures.append(firmware_map_future)

        # Dispatch API calls for all devices, in all zones. Each device requires a call
        # to retrieve its base data and another one for energy data.
        for device_id in user_device_ids:
            LOGGER.debug("Found device ID: %s", device_id)
            futures = (
                self.hass.async_add_executor_job(self.equation_api.get_device, device_id),
                self.hass.async_add_executor_job(
                    self.equation_api.get_latest_energy_stats, device_id
                ),
            )

            pending_futures.extend([futures[0], futures[1]])
            device_data_futures[device_id] = futures

        # Gather all futures.
        await asyncio.gather(*pending_futures)

        # Firmware data result.
        firmware_map_response: ApiResponse = firmware_map_future.result()

        if firmware_map_response.success and firmware_map_response.data:
            firmware_map: dict[
                EquationProduct, dict[str, str]
            ] | None = firmware_map_response.data
        else:
            LOGGER.error(
                "Unable to fetch firmware map: %s",
                firmware_map_response.error_message,
            )
            firmware_map = None

        # Process all completed device data futures.
        for device_id, device_futures in device_data_futures.items():
            base_data_response: ApiResponse = device_futures[0].result()
            energy_data_response: ApiResponse = device_futures[1].result()

            if not base_data_response.success:
                LOGGER.warning(
                    "Failed getting device status for %s. Error: %s",
                    device_id,
                    base_data_response.error_message,
                )

            new_device = await self._process_api_data(
                base_data_response, device_id, energy_data_response, firmware_map
            )

            if new_device:
                self.equation_devices[device_id] = new_device
                discovered_devices[new_device.id] = new_device

        return discovered_devices

    async def _process_api_data(
        self,
        base_data_response: ApiResponse,
        device_id: str,
        energy_data_response: ApiResponse,
        firmware_map: dict[EquationProduct, dict[str, str]] | None,
    ) -> EquationDevice | None:
        """Process the data related to a single device."""

        LOGGER.debug("Processing data for device ID: %s", device_id)

        if base_data_response.success:
            base_data = base_data_response.data
        else:
            LOGGER.warning(
                "Failed getting device status for %s. Error: %s",
                device_id,
                base_data_response.error_message,
            )

            # Mark the device as unavailable on our existing devices cache.
            if device_id in self.equation_devices:
                self.equation_devices[device_id].hass_available = False

            return None

        if energy_data_response.success:
            energy_data = energy_data_response.data
        else:
            energy_data = None

        if firmware_map:
            latest_fw = determine_latest_firmware(base_data_response.data, firmware_map)
        else:
            latest_fw = None

        new_device = self._add_or_update_device(
            base_data, energy_data, device_id, latest_fw
        )

        return new_device

    def _add_or_update_device(
        self,
        device_data,
        energy_stats: EnergyConsumptionData,
        device_id: str,
        latest_fw: str | None,
    ) -> EquationDevice:
        """Process a device from the API and add or update it.

        Return the device if it's new or None if it's an existing one.
        """

        device_data_data = device_data.get("data", None)

        if not device_data_data:
            LOGGER.error("Device ID %s has no valid data. Ignoring", device_id)
            return None

        # Existing device, update it.
        if device_id in self.equation_devices:

            target_device = self.equation_devices[device_id]

            if not target_device.hass_available:
                LOGGER.debug("Restoring device %s", target_device.name)
                target_device.hass_available = True

            target_device.update_data(device_data, energy_stats, latest_fw)

            LOGGER.debug(
                "Updating existing device [%s]",
                device_data_data.get("name", "N/A"),
            )

            return None

        # New device.
        device_type = device_data["data"]["type"]

        if device_type not in EQUATION_SUPPORTED_DEVICES:
            LOGGER.warning("Ignoring Equation device of type %s", device_type)
            return None

        firmware_data = device_data.get("firmware", None)
        LOGGER.debug(
            "Found new device %s [%s] - %s. FW: %s - %s",
            device_data_data.get("name", "N/A"),
            device_data_data.get("type", "N/A"),
            device_data_data.get("product_version", "N/A"),
            firmware_data.get("firmware_version_device", "N/A")
            if firmware_data
            else "N/A",
            device_data,
        )

        equation_device = EquationDevice(
            device_info=device_data,
            device_id=device_id,
            energy_data=energy_stats,
            latest_fw=latest_fw,
        )

        return equation_device

    async def send_command(self, device: EquationDevice, command: str, arg) -> bool:
        """Send command to the device."""

        LOGGER.debug("Sending command [%s] to device ID [%s]", command, device.id)

        if command == CMD_SET_TEMP:
            return await self._set_device_temp(device, arg)

        if command == CMD_SET_PRESET:
            return await self._set_device_preset(device, arg)

        if command == CMD_SET_HVAC_MODE:
            return await self._set_device_mode(device, arg)

        LOGGER.warning("Ignoring unsupported command: %s", command)
        return False

    async def _set_device_temp(self, device: EquationDevice, new_temp: float) -> bool:
        """Set device temperature."""

        result: ApiResponse = await self.hass.async_add_executor_job(
            self.equation_api.set_device_temp, device, new_temp
        )

        if not result.success:
            # Set the device as unavailable.
            device.hass_available = False
            return False

        # Update the device internal status
        device.temp = new_temp
        device.mode = RADIATOR_MODE_MANUAL
        device.power = True

        if new_temp == device.comfort_temp:
            device.preset = RADIATOR_PRESET_COMFORT
        elif new_temp == device.eco_temp:
            device.preset = RADIATOR_PRESET_ECO
        elif new_temp == device.ice_temp:
            device.preset = RADIATOR_PRESET_ICE
        else:
            device.preset = RADIATOR_PRESET_NONE

        return True

    async def _set_device_mode(self, device: EquationDevice, hvac_mode: str) -> bool:
        """Set the device hvac mode."""

        result = await self.hass.async_add_executor_job(
            self.equation_api.set_device_mode, device, hvac_mode
        )

        if not result.success:
            # Set the device as unavailable.
            device.hass_available = False
            return False

        # Update the device's internal status
        if hvac_mode == HVACMode.OFF:
            if device.mode == RADIATOR_MODE_MANUAL:
                device.temp = RADIATOR_DEFAULT_TEMPERATURE

            device.power = False
            device.preset = HVACMode.OFF

        elif hvac_mode == HVACMode.HEAT:
            device.temp = device.comfort_temp
            device.power = True
            device.mode = RADIATOR_MODE_MANUAL
            device.preset = RADIATOR_PRESET_NONE

        elif hvac_mode == RADIATOR_MODE_MANUAL:
            current_mode: ScheduleMode = device.get_current_schedule_mode()

            # Set the appropriate temperature and preset according to the schedule.
            if current_mode == ScheduleMode.COMFORT:
                device.temp = device.comfort_temp
                device.preset = RADIATOR_PRESET_COMFORT
            elif current_mode == ScheduleMode.ECO:
                device.temp = device.eco_temp
                device.preset = RADIATOR_PRESET_ECO
            elif device.ice_mode:
                device.temp = device.ice_temp
                device.preset = RADIATOR_PRESET_ICE
            else:
                device.temp = RADIATOR_DEFAULT_TEMPERATURE

            device.power = True
            device.mode = RADIATOR_MODE_MANUAL

        return True

    async def _set_device_preset(self, device: EquationDevice, preset: str) -> bool:
        """Set device preset mode."""

        device_power = device.power
        device_mode = device.mode
        device_preset = device.preset

        # Update the device internal status
        if preset == PRESET_COMFORT:
            device_power = True
            device_mode = RADIATOR_MODE_MANUAL
            device_preset = RADIATOR_PRESET_COMFORT
        elif preset == PRESET_ECO:
            device_power = True
            device_mode = RADIATOR_MODE_MANUAL
            device_preset = RADIATOR_PRESET_ECO
        elif preset == PRESET_EQUATION_ICE:
            device_power = True
            device_mode = RADIATOR_MODE_MANUAL
            device_preset = RADIATOR_PRESET_ICE

        result = await self.hass.async_add_executor_job(
            self.equation_api.set_device_preset, device, device_preset
        )

        if not result.success:
            # Set the device as unavailable.
            device.hass_available = False
            return False

        # Update the device internal status
        device.power = device_power
        device.mode = device_mode
        device.preset = device_preset

        return True
