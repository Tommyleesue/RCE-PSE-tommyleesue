"""rce_pse-tommyleesue config flow"""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_CUSTOM_PEAK_RANGE,
    CONF_EXPENSIVE_HOURS,
    CONF_CHEAP_HOURS,
    CONF_EXPENSIVE_AM_HOURS,
    CONF_CHEAP_AM_HOURS,
    CONF_EXPENSIVE_PM_HOURS,
    CONF_CHEAP_PM_HOURS,
    DEFAULT_CUSTOM_PEAK_RANGE,
    DEFAULT_EXPENSIVE_HOURS,
    DEFAULT_CHEAP_HOURS,
    DEFAULT_EXPENSIVE_AM_HOURS,
    DEFAULT_CHEAP_AM_HOURS,
    DEFAULT_EXPENSIVE_PM_HOURS,
    DEFAULT_CHEAP_PM_HOURS,
)


class PSESensorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for rce_pse-tommyleesue."""
    
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        
        if user_input is not None:
            return self.async_create_entry(title="rce_pse-tommyleesue", data={})
        
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get the options flow for this handler."""
        return PSESensorOptionFlow(config_entry)


class PSESensorOptionFlow(OptionsFlow):
    """Handle options flow for rce_pse-tommyleesue."""
    
    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        if user_input is not None:
            # Prosta walidacja
            errors = {}
            
            # Walidacja zakresu godzin
            custom_peak = user_input.get(CONF_CUSTOM_PEAK_RANGE, DEFAULT_CUSTOM_PEAK_RANGE)
            try:
                start_str, end_str = custom_peak.split("-")
                start = int(start_str)
                end = int(end_str)
                if not (1 <= start <= 24 and 1 <= end <= 25 and start < end):
                    errors[CONF_CUSTOM_PEAK_RANGE] = "invalid_range"
            except (ValueError, AttributeError):
                errors[CONF_CUSTOM_PEAK_RANGE] = "invalid_format"
            
            # Walidacja liczby godzin
            expensive_hours = user_input.get(CONF_EXPENSIVE_HOURS, DEFAULT_EXPENSIVE_HOURS)
            if not (1 <= expensive_hours <= 24):
                errors[CONF_EXPENSIVE_HOURS] = "invalid_hours"
            
            cheap_hours = user_input.get(CONF_CHEAP_HOURS, DEFAULT_CHEAP_HOURS)
            if not (1 <= cheap_hours <= 24):
                errors[CONF_CHEAP_HOURS] = "invalid_hours"
            
            
            expensive_am_hours = user_input.get(CONF_EXPENSIVE_AM_HOURS, DEFAULT_EXPENSIVE_AM_HOURS)
            if not (1 <= expensive_am_hours <= 12):  # Maksymalnie 12 godzin w AM
                errors[CONF_EXPENSIVE_AM_HOURS] = "invalid_hours"

            cheap_am_hours = user_input.get(CONF_CHEAP_AM_HOURS, DEFAULT_CHEAP_AM_HOURS)
            if not (1 <= cheap_am_hours <= 12):
                errors[CONF_CHEAP_AM_HOURS] = "invalid_hours"

            expensive_pm_hours = user_input.get(CONF_EXPENSIVE_PM_HOURS, DEFAULT_EXPENSIVE_PM_HOURS)
            if not (1 <= expensive_pm_hours <= 12):  # Maksymalnie 12 godzin w PM
                errors[CONF_EXPENSIVE_PM_HOURS] = "invalid_hours"

            cheap_pm_hours = user_input.get(CONF_CHEAP_PM_HOURS, DEFAULT_CHEAP_PM_HOURS)
            if not (1 <= cheap_pm_hours <= 12):
                errors[CONF_CHEAP_PM_HOURS] = "invalid_hours"
            
            
            if not errors:
                return self.async_create_entry(title="", data=user_input)
            
            # Jeśli są błędy, pokaż formularz ponownie z błędami
            return self.async_show_form(
                step_id="init",
                data_schema=self._get_options_schema(),
                errors=errors
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema()
        )

    def _get_options_schema(self):
        """Zwróć schemat opcji z polami ze strzałkami."""
        return vol.Schema({
            vol.Optional(
                CONF_CUSTOM_PEAK_RANGE,
                default=self._config_entry.options.get(
                    CONF_CUSTOM_PEAK_RANGE, DEFAULT_CUSTOM_PEAK_RANGE
                ),
                description="Zakaz godzin szczytu (np. 16-22)"
            ): str,
            
            vol.Optional(
                CONF_EXPENSIVE_HOURS,
                default=self._config_entry.options.get(
                    CONF_EXPENSIVE_HOURS, DEFAULT_EXPENSIVE_HOURS
                ),
                description="Liczba drogich godzin do oznaczenia (1-24)"
            ): vol.Coerce(int),  # TYLKO Coerce - da pole ze strzałkami
            
            vol.Optional(
                CONF_CHEAP_HOURS,
                default=self._config_entry.options.get(
                    CONF_CHEAP_HOURS, DEFAULT_CHEAP_HOURS
                ),
                description="Liczba tanich godzin do oznaczenia (1-24)"
            ): vol.Coerce(int),  # TYLKO Coerce - da pole ze strzałkami
            
            vol.Optional(
                CONF_EXPENSIVE_AM_HOURS,
                default=self._config_entry.options.get(
                    CONF_EXPENSIVE_AM_HOURS, DEFAULT_EXPENSIVE_AM_HOURS
                ),
                description="Liczba drogich godzin w pierwszej połowie doby (1-12)"
            ): vol.Coerce(int),

            vol.Optional(
                CONF_CHEAP_AM_HOURS,
                default=self._config_entry.options.get(
                    CONF_CHEAP_AM_HOURS, DEFAULT_CHEAP_AM_HOURS
                ),
                description="Liczba tanich godzin w pierwszej połowie doby (1-12)"
            ): vol.Coerce(int),

            vol.Optional(
                CONF_EXPENSIVE_PM_HOURS,
                default=self._config_entry.options.get(
                    CONF_EXPENSIVE_PM_HOURS, DEFAULT_EXPENSIVE_PM_HOURS
                ),
                description="Liczba drogich godzin w drugiej połowie doby (1-12)"
            ): vol.Coerce(int),

            vol.Optional(
                CONF_CHEAP_PM_HOURS,
                default=self._config_entry.options.get(
                    CONF_CHEAP_PM_HOURS, DEFAULT_CHEAP_PM_HOURS
                ),
                description="Liczba tanich godzin w drugiej połowie doby (1-12)"
            ): vol.Coerce(int),
        })