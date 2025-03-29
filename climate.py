import asyncio
import logging

import voluptuous as vol

from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_FAN_MODE,
    SUPPORT_SWING_MODE,
    ATTR_HVAC_MODE,
)
from homeassistant.const import (
    CONF_NAME,
    ATTR_TEMPERATURE,
    PRECISION_WHOLE,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity

from .controller import ESPHomeController
from .utils.mitsubishi import (
    Mitsubishi,
    ClimateMode,
    FanMode,
    VanneVerticalMode,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "HVAC IR Climate"

CONF_UNIQUE_ID = "unique_id"
CONF_CONTROLLER_DATA = "controller_data"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_UNIQUE_ID): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_CONTROLLER_DATA): cv.string,
})


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):
    async_add_entities([HvacIrClimate(hass, config)])


class HvacIrClimate(ClimateEntity, RestoreEntity):
    def __init__(self, hass, config):
        self.hass = hass
        self._unique_id = config.get(CONF_UNIQUE_ID)
        self._name = config.get(CONF_NAME)
        self._controller_data = config.get(CONF_CONTROLLER_DATA)

        self._manufacturer = "Mitsubishi Electric"
        self._supported_models = ["MSZ-HJ25VA", "MSZ-HJ35VA"]
        self._supported_controller = "ESPHome"
        self._commands_encoding = "Raw"
        self._min_temperature = 16
        self._max_temperature = 31
        self._precision = 1
        self._operation_modes = {
            HVAC_MODE_OFF: None,  # PowerMode.PowerOff
            HVAC_MODE_COOL: ClimateMode.Cold,
            HVAC_MODE_DRY: ClimateMode.Dry,
            HVAC_MODE_HEAT: ClimateMode.Hot,
            HVAC_MODE_FAN_ONLY: ClimateMode.Auto,
        }
        self._fan_modes = {
            "Auto": FanMode.Auto,
            "Speed1": FanMode.Speed1,
            "Speed2": FanMode.Speed2,
            "Speed3": FanMode.Speed3,
            "Speed4": FanMode.Speed4,
        }
        self._swing_modes = {
            "Top": VanneVerticalMode.Top,
            "MiddleTop": VanneVerticalMode.MiddleTop,
            "Middle": VanneVerticalMode.Middle,
            "MiddleBottom": VanneVerticalMode.MiddleBottom,
            "Bottom": VanneVerticalMode.Bottom,
            "Swing": VanneVerticalMode.Swing,
            "Auto": VanneVerticalMode.Auto,
        }

        self._target_temperature = self._min_temperature
        self._hvac_mode = HVAC_MODE_OFF
        self._current_fan_mode = "Speed1"
        self._current_swing_mode = "Top"
        self._last_on_operation = None

        self._unit = hass.config.units.temperature_unit

        # Supported features
        self._support_flags = (
            SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE | SUPPORT_SWING_MODE
        )

        self._temp_lock = asyncio.Lock()

        # Init the IR/RF controller
        self._controller = ESPHomeController(self.hass, self._controller_data)

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()

        if last_state is not None:
            self._hvac_mode = last_state.state
            self._current_fan_mode = last_state.attributes["fan_mode"]
            self._current_swing_mode = last_state.attributes.get("swing_mode")
            self._target_temperature = last_state.attributes["temperature"]

            if "last_on_operation" in last_state.attributes:
                self._last_on_operation = last_state.attributes[
                    "last_on_operation"
                ]

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def state(self):
        """Return the current state."""
        if self.hvac_mode != HVAC_MODE_OFF:
            return self.hvac_mode
        return HVAC_MODE_OFF

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def min_temp(self):
        """Return the polling state."""
        return self._min_temperature

    @property
    def max_temp(self):
        """Return the polling state."""
        return self._max_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._precision

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return list(self._operation_modes.keys())

    @property
    def hvac_mode(self):
        """Return hvac mode ie. heat, cool."""
        return self._hvac_mode

    @property
    def last_on_operation(self):
        """Return the last non-idle operation ie. heat, cool."""
        return self._last_on_operation

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return list(self._fan_modes.keys())

    @property
    def fan_mode(self):
        """Return the fan setting."""
        return self._current_fan_mode

    @property
    def swing_modes(self):
        """Return the swing modes currently supported for this device."""
        return list(self._swing_modes.keys())

    @property
    def swing_mode(self):
        """Return the current swing mode."""
        return self._current_swing_mode

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def device_state_attributes(self) -> dict:
        """Platform specific attributes."""
        return {
            "last_on_operation": self._last_on_operation,
            "manufacturer": self._manufacturer,
            "supported_models": self._supported_models,
            "supported_controller": self._supported_controller,
            "commands_encoding": self._commands_encoding,
        }

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        hvac_mode = kwargs.get(ATTR_HVAC_MODE)
        temperature = kwargs.get(ATTR_TEMPERATURE)

        if temperature is None:
            return

        if (
            temperature < self._min_temperature
            or temperature > self._max_temperature
        ):
            _LOGGER.warning('The temperature value is out of min/max range')
            return

        if self._precision == PRECISION_WHOLE:
            self._target_temperature = round(temperature)
        else:
            self._target_temperature = round(temperature, 1)

        if hvac_mode:
            await self.async_set_hvac_mode(hvac_mode)
            return

        if not self._hvac_mode.lower() == HVAC_MODE_OFF:
            await self.send_command()

        await self.async_update_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        self._hvac_mode = hvac_mode

        if not hvac_mode == HVAC_MODE_OFF:
            self._last_on_operation = hvac_mode

        await self.send_command()
        await self.async_update_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        """Set fan mode."""
        self._current_fan_mode = fan_mode

        if not self._hvac_mode.lower() == HVAC_MODE_OFF:
            await self.send_command()
        await self.async_update_ha_state()

    async def async_set_swing_mode(self, swing_mode):
        """Set swing mode."""
        self._current_swing_mode = swing_mode

        if not self._hvac_mode.lower() == HVAC_MODE_OFF:
            await self.send_command()
        await self.async_update_ha_state()

    async def async_turn_off(self):
        """Turn off."""
        await self.async_set_hvac_mode(HVAC_MODE_OFF)

    async def async_turn_on(self):
        """Turn on."""
        if self._last_on_operation is not None:
            await self.async_set_hvac_mode(self._last_on_operation)
        else:
            await self.async_set_hvac_mode(HVAC_MODE_COOL)

    async def send_command(self):
        async with self._temp_lock:
            try:
                mitsubishi = Mitsubishi()
                hvac_mode = self._operation_modes[self._hvac_mode]
                target_temperature = self._target_temperature
                fan_mode = self._fan_modes[self._current_fan_mode]
                swing_mode = self._swing_modes[self._current_swing_mode]

                if self._hvac_mode.lower() == HVAC_MODE_OFF:
                    command = mitsubishi.power_off()
                else:
                    command = mitsubishi.send_command(
                        climate_mode=hvac_mode,
                        temperature=target_temperature,
                        fan_mode=fan_mode,
                        vanne_vertical_mode=swing_mode,
                    )
                await self._controller.send(command)

            except Exception as e:
                _LOGGER.exception(e)
