"""Constants for the RCE integration."""

from datetime import timedelta
from typing import Final
import logging

DOMAIN: Final = "rce"
DEFAULT_CURRENCY: Final = "PLN"
DEFAULT_PRICE_TYPE: Final = "MWh"

DEFAULT_CUSTOM_PEAK_RANGE = "10-17"
DEFAULT_EXPENSIVE_HOURS = 5
DEFAULT_CHEAP_HOURS = 3
DEFAULT_EXPENSIVE_AM_HOURS = 2
DEFAULT_CHEAP_AM_HOURS = 2
DEFAULT_EXPENSIVE_PM_HOURS = 2
DEFAULT_CHEAP_PM_HOURS = 2

CONF_CUSTOM_PEAK_RANGE: Final = "custom_peak_range"
CONF_EXPENSIVE_HOURS: Final = "expensive_hours"
CONF_CHEAP_HOURS: Final = "cheap_hours"
CONF_EXPENSIVE_AM_HOURS = "expensive_am_hours"
CONF_CHEAP_AM_HOURS = "cheap_am_hours"
CONF_EXPENSIVE_PM_HOURS = "expensive_pm_hours"
CONF_CHEAP_PM_HOURS = "cheap_pm_hours"

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
