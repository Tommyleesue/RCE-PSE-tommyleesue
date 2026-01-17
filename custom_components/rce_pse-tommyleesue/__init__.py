"""The rce_pse-tommyleesue component."""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform
import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up this integration using YAML is not supported."""
    if DOMAIN not in hass.data:
        hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up rce_pse-tommyleesue integration."""
    _LOGGER.info("rce_pse-tommyleesue-async_setup_entry " + str(entry))
    
    # Dodaj listener do aktualizacji opcji
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload the integration."""
    _LOGGER.info("Options updated, reloading integration")
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    _LOGGER.info("rce_pse-tommyleesue-async_unload_entry remove entities")
    
    # USUŃ problematyczny kod:
    # if DOMAIN in hass.data:
    #     for unsub in hass.data[DOMAIN].listeners:  # <--- TO JEST BŁĘDNE
    #         unsub()
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Możesz wyczyścić dane jeśli chcesz
        # hass.data.pop(DOMAIN, None)
        _LOGGER.info("rce_pse-tommyleesue unloaded successfully")
        return True

    _LOGGER.error("Failed to unload rce_pse-tommyleesue")
    return False