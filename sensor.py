"""Platforma do integracji sensora cen energii PSE."""
from __future__ import annotations

import json
import logging
import requests
from statistics import mean, median
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant import config_entries
from homeassistant.helpers.device_registry import DeviceEntryType

from .const import (
    DOMAIN,
    DEFAULT_CURRENCY,
    DEFAULT_PRICE_TYPE,
    CONF_CUSTOM_PEAK_RANGE,
    CONF_CHEAP_HOURS,
    CONF_EXPENSIVE_HOURS,
    CONF_CHEAP_AM_HOURS,
    CONF_EXPENSIVE_AM_HOURS,
    CONF_CHEAP_PM_HOURS,
    CONF_EXPENSIVE_PM_HOURS,
    DEFAULT_CUSTOM_PEAK_RANGE,
    DEFAULT_CHEAP_HOURS,
    DEFAULT_EXPENSIVE_HOURS,
    DEFAULT_CHEAP_AM_HOURS,
    DEFAULT_EXPENSIVE_AM_HOURS,
    DEFAULT_CHEAP_PM_HOURS,
    DEFAULT_EXPENSIVE_PM_HOURS,
)

_LOGGER = logging.getLogger(__name__)

# URL API PSE (v2) - zwraca dane w odstępach 15-minutowych
URL = (
    "https://v2.api.raporty.pse.pl/api/rce-pln"
    "?$filter=business_date eq '{day}'"
    "&$select=business_date,dtime,rce_pln"
    "&$orderby=dtime"
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """
    Konfiguracja platformy sensorowej.
    """
    # Pobierz konfigurację z opcji
    custom_peak = config_entry.options.get(
        CONF_CUSTOM_PEAK_RANGE, DEFAULT_CUSTOM_PEAK_RANGE
    )
    cheap_hours = config_entry.options.get(
        CONF_CHEAP_HOURS, DEFAULT_CHEAP_HOURS
    )
    expensive_hours = config_entry.options.get(
        CONF_EXPENSIVE_HOURS, DEFAULT_EXPENSIVE_HOURS
    )
    cheap_am_hours = config_entry.options.get(
        CONF_CHEAP_AM_HOURS, DEFAULT_CHEAP_AM_HOURS
    )
    expensive_am_hours = config_entry.options.get(
        CONF_EXPENSIVE_AM_HOURS, DEFAULT_EXPENSIVE_AM_HOURS
    )
    cheap_pm_hours = config_entry.options.get(
        CONF_CHEAP_PM_HOURS, DEFAULT_CHEAP_PM_HOURS
    )
    expensive_pm_hours = config_entry.options.get(
        CONF_EXPENSIVE_PM_HOURS, DEFAULT_EXPENSIVE_PM_HOURS
    )

    # Dodaj sensor
    sensor = RCESensor(
        hass,
        custom_peak,
        cheap_hours,
        expensive_hours,
        cheap_am_hours,
        expensive_am_hours,
        cheap_pm_hours,
        expensive_pm_hours,
    )
    
    async_add_entities([sensor])


class RCESensor(SensorEntity):
    """
    Sensor przedstawiający Rynkową Cenę Energii (RCE) z PSE.
    
    Uwaga: 
    1. Średnia dla godziny X jest liczona z kwadransów:
       godzina X = średnia z (X:15, X:30, X:45, X+1:00)
    2. Godziny są numerowane 1-24 (zamiast 0-23)
    """
    
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        custom_peak: str,
        cheap_hours: int,
        expensive_hours: int,
        cheap_am_hours: int,
        expensive_am_hours: int,
        cheap_pm_hours: int,
        expensive_pm_hours: int,
    ) -> None:
        """Inicjalizacja sensora."""
        super().__init__()
        self.hass = hass
        
        _LOGGER.info("RCE sensor – API v2 z godzinami 1-24 i przesunięciem +15 min")

        # Czas ostatniego pobrania danych z sieci
        self.last_network_pull = datetime(
            year=2000, month=1, day=1, tzinfo=timezone.utc
        )
        
        # Ostatni dzień, w którym pobrano dane o 15:00
        self.last_15_update_day = None

        # Dane cenowe
        self._today = []      # Ceny na dzisiaj (godziny 1-24)
        self._tomorrow = []   # Ceny na jutro (godziny 1-24)

        # Statystyki cenowe
        self._average = None
        self._min = None
        self._max = None
        self._mean = None
        self._am_night_avg = None
        self._pm_night_avg = None
        self._day_avg = None
        self._custom_peak = None
        self.cheap_am_hours = min(max(cheap_am_hours, 1), 12)
        self.expensive_am_hours = min(max(expensive_am_hours, 1), 12)
        self.cheap_pm_hours = min(max(cheap_pm_hours, 1), 12)
        self.expensive_pm_hours = min(max(expensive_pm_hours, 1), 12)

        # Walidacja i parsowanie zakresu customowego szczytu
        try:
            start_str, end_str = custom_peak.split("-")
            self.custom_peak_start = int(start_str)
            self.custom_peak_end = int(end_str)
            # Sprawdź poprawność zakresu godzin (teraz 1-24)
            if not (1 <= self.custom_peak_start <= 24 and 
                    1 <= self.custom_peak_end <= 25 and 
                    self.custom_peak_start < self.custom_peak_end):
                raise ValueError("Nieprawidłowy zakres godzin")
        except (ValueError, AttributeError):
            _LOGGER.warning("Nieprawidłowy format custom_peak: %s. Używam domyślnego.", custom_peak)
            default_start, default_end = DEFAULT_CUSTOM_PEAK_RANGE.split("-")
            self.custom_peak_start = int(default_start)
            self.custom_peak_end = int(default_end)
        
        # Konfiguracja z opcji integracji
        self.cheap_hours = min(max(cheap_hours, 1), 24)
        self.expensive_hours = min(max(expensive_hours, 1), 24)
        
        # Aktualna wartość sensora
        self._attr_native_value = None
        self._attr_native_unit_of_measurement = f"{DEFAULT_CURRENCY}/{DEFAULT_PRICE_TYPE}"

    # -------------------------------------------------------------
    # METODY DO POBRANIA DANYCH Z API
    # -------------------------------------------------------------

    async def sday(self, dday: int):
        """
        Pobierz dane dla konkretnego dnia z API PSE.
        """
        now = datetime.now() + timedelta(days=dday)
        day_str = now.strftime("%Y-%m-%d")
        
        try:
            # Wykonaj zapytanie HTTP
            response = await self.hass.async_add_executor_job(
                lambda: requests.get(URL.format(day=day_str), timeout=10)
            )
            response.raise_for_status()
            
            json_data = response.json()
            if not json_data.get("value"):
                _LOGGER.warning("Brak danych cenowych dla %s", day_str)
                return None
                
            _LOGGER.debug("Pobrano dane dla %s", day_str)
            return json_data
            
        except requests.exceptions.Timeout:
            _LOGGER.error("Timeout przy pobieraniu danych PSE dla %s", day_str)
        except requests.exceptions.RequestException as e:
            _LOGGER.error("Błąd przy pobieraniu danych PSE dla %s: %s", day_str, e)
        except json.JSONDecodeError:
            _LOGGER.error("Nieprawidłowa odpowiedź JSON z API PSE dla %s", day_str)
        
        return None

    async def json_to_day_raw(self, dday: int):
        """
        Konwertuj odpowiedź JSON z API na ustrukturyzowane dane dzienne.
        
        Uwaga: 
        1. Średnia dla godziny X jest liczona z kwadransów: X:15, X:30, X:45, X+1:00
        2. Godziny są numerowane 1-24
        """
        json_data = await self.sday(dday)
        if not json_data:
            return []

        # Struktura do przechowywania kwadransów
        quarters_by_hour = defaultdict(list)

        # Przetwórz każdy 15-minutowy punkt danych
        for item in json_data.get("value", []):
            try:
                dt = datetime.fromisoformat(item["dtime"].replace('Z', '+00:00'))
                price = float(item["rce_pln"])
                
                # Określ do której godziny (1-24) należy ten kwadrans
                hour_0_23 = dt.hour
                minute = dt.minute
                
                if minute == 0:
                    target_hour_0_23 = (hour_0_23 - 1) % 24
                elif minute == 15:
                    target_hour_0_23 = hour_0_23
                elif minute == 30:
                    target_hour_0_23 = hour_0_23
                elif minute == 45:
                    target_hour_0_23 = hour_0_23
                else:
                    continue
                
                # Konwertuj z 0-23 na 1-24
                target_hour_1_24 = target_hour_0_23 + 1
                if target_hour_1_24 == 25:
                    target_hour_1_24 = 1
                    
                quarters_by_hour[target_hour_1_24].append(price)
                
            except (KeyError, ValueError, TypeError, AttributeError) as e:
                _LOGGER.warning("Nieprawidłowy element danych: %s, błąd: %s", item, e)
                continue

        # Zbuduj kompletny dzień z 24 godzinami (1-24)
        day = []
        for hour in range(1, 25):
            if hour in quarters_by_hour and len(quarters_by_hour[hour]) >= 3:
                avg_price = round(mean(quarters_by_hour[hour]), 2)
                day.append({
                    "hour": hour,
                    "start": f"{hour-1:02d}:00",
                    "tariff": avg_price,
                    "quarters_count": len(quarters_by_hour[hour]),
                })
            elif hour in quarters_by_hour:
                avg_price = round(mean(quarters_by_hour[hour]), 2)
                day.append({
                    "hour": hour,
                    "start": f"{hour-1:02d}:00",
                    "tariff": avg_price,
                    "quarters_count": len(quarters_by_hour[hour]),
                })
            else:
                day.append({
                    "hour": hour,
                    "start": f"{hour-1:02d}:00",
                    "tariff": None,
                    "quarters_count": 0,
                })

        hours_with_data = [h for h in range(1, 25) if h in quarters_by_hour]
        _LOGGER.debug("Godziny z danymi: %s, liczba punktów: %s", 
                     hours_with_data, 
                     {h: len(quarters_by_hour[h]) for h in hours_with_data})

        return day

    def _calculate_price_ranking(self, day):
        """
        Oblicz ranking cenowy dla godzin dnia.
        
        Ranking: 1 = najtańsza godzina, 24 = najdroższa godzina.
        Dodaje flagi h_price (drogie godziny) i l_price (tanie godziny).
        """
        if not day:
            return
        
        # Filtruj godziny z prawidłowymi danymi
        valid_hours = [(i, item) for i, item in enumerate(day) if item["tariff"] is not None]
        
        if not valid_hours:
            return
        
        # Sortuj po cenie (rosnąco)
        sorted_hours = sorted(valid_hours, key=lambda x: x[1]["tariff"])
        
        # Przypisz rankingi (1-24 zamiast 0-23)
        rank = 1
        prev_price = None
        same_price_count = 0
        
        for position, (index, hour_data) in enumerate(sorted_hours):
            current_price = hour_data["tariff"]
            
            if prev_price is None or current_price != prev_price:
                rank = position + 1
                prev_price = current_price
                same_price_count = 1
            else:
                same_price_count += 1
            
            day[index]["price_rank"] = rank
            day[index]["price_position"] = position + 1
        
        # Dodaj ranking procentowy
        for index, hour_data in enumerate(day):
            if hour_data["tariff"] is not None and "price_position" in hour_data:
                position = hour_data["price_position"]
                percentile = round((position - 1) / 23 * 100, 1) if len(valid_hours) > 1 else 50
                day[index]["price_percentile"] = percentile
        
        # PODZIEL NA AM (godziny 1-12) i PM (godziny 13-24)
        am_hours = [(i, item) for i, item in enumerate(day[:12]) if item["tariff"] is not None]
        pm_hours = [(i, item) for i, item in enumerate(day[12:], start=12) if item["tariff"] is not None]
        
        # RANKING AM (godziny 1-12)
        if am_hours:
            sorted_am = sorted(am_hours, key=lambda x: x[1]["tariff"])
            
            am_rank = 1
            prev_price = None
            for position, (index, hour_data) in enumerate(sorted_am):
                current_price = hour_data["tariff"]
                if prev_price is None or current_price != prev_price:
                    am_rank = position + 1
                    prev_price = current_price
                day[index]["am_rank"] = am_rank
                
        # RANKING PM (godziny 13-24)
        if pm_hours:
            sorted_pm = sorted(pm_hours, key=lambda x: x[1]["tariff"])
            
            pm_rank = 1
            prev_price = None
            for position, (index, hour_data) in enumerate(sorted_pm):
                current_price = hour_data["tariff"]
                if prev_price is None or current_price != prev_price:
                    pm_rank = position + 1
                    prev_price = current_price
                day[index]["pm_rank"] = pm_rank
        
        # Dodaj flagi AM (tylko dla godzin 1-12)
        total_am_hours = len(am_hours)
        for index, hour_data in enumerate(day[:12]):
            if hour_data["tariff"] is not None:
                am_rank_value = hour_data.get("am_rank")
                
                if am_rank_value and am_rank_value <= self.cheap_am_hours:
                    day[index]["am_l_price"] = True
                else:
                    day[index]["am_l_price"] = False
                
                if am_rank_value and am_rank_value > total_am_hours - self.expensive_am_hours:
                    day[index]["am_h_price"] = True
                else:
                    day[index]["am_h_price"] = False
            else:
                day[index]["am_l_price"] = False
                day[index]["am_h_price"] = False
        
        # Dodaj flagi PM (tylko dla godzin 13-24)
        total_pm_hours = len(pm_hours)
        for index, hour_data in enumerate(day[12:], start=12):
            if hour_data["tariff"] is not None:
                pm_rank_value = hour_data.get("pm_rank")
                
                if pm_rank_value and pm_rank_value <= self.cheap_pm_hours:
                    day[index]["pm_l_price"] = True
                else:
                    day[index]["pm_l_price"] = False
                
                if pm_rank_value and pm_rank_value > total_pm_hours - self.expensive_pm_hours:
                    day[index]["pm_h_price"] = True
                else:
                    day[index]["pm_h_price"] = False
            else:
                day[index]["pm_l_price"] = False
                day[index]["pm_h_price"] = False
            
            # Dodaj flagi h_price i l_price
            total_valid_hours = len(valid_hours)
            
            for index, hour_data in enumerate(day):
                if hour_data["tariff"] is not None:
                    rank_value = hour_data.get("price_rank")
                    
                    # l_price = true dla najtańszych godzin (cheap_hours)
                    if rank_value and rank_value <= self.cheap_hours:
                        day[index]["l_price"] = True
                    else:
                        day[index]["l_price"] = False
                    
                    # h_price = true dla najdroższych godzin (expensive_hours)
                    if rank_value and rank_value > total_valid_hours - self.expensive_hours:
                        day[index]["h_price"] = True
                    else:
                        day[index]["h_price"] = False
                else:
                    day[index]["l_price"] = False
                    day[index]["h_price"] = False
    
    # -------------------------------------------------------------
    # METODY DO OBLICZEŃ I AKTUALIZACJI
    # -------------------------------------------------------------

    def _update(self, day):
        """Aktualizuj statystyki cenowe dla danego dnia."""
        if not day:
            _LOGGER.warning("Brak danych dziennych do aktualizacji")
            return

        valid_prices = [item["tariff"] for item in day if item["tariff"] is not None]
        
        if not valid_prices:
            _LOGGER.warning("Brak poprawnych danych cenowych")
            return

        self._average = round(mean(valid_prices), 2)
        self._min = min(valid_prices)
        self._max = max(valid_prices)
        self._mean = round(median(valid_prices), 2)

        am_night_prices = [item["tariff"] for item in day[:8] if item["tariff"] is not None]
        self._am_night_avg = round(mean(am_night_prices), 2) if am_night_prices else None
        
        peak_prices = [item["tariff"] for item in day[8:20] if item["tariff"] is not None]
        self._day_avg = round(mean(peak_prices), 2) if peak_prices else None
        
        pm_night_prices = [item["tariff"] for item in day[20:] if item["tariff"] is not None]
        self._pm_night_avg = round(mean(pm_night_prices), 2) if pm_night_prices else None
        
        start_index = max(0, min(self.custom_peak_start - 1, 23))
        end_index = min(24, max(self.custom_peak_end - 1, start_index + 1))
        
        custom_peak_prices = [
            item["tariff"] for item in day[start_index:end_index] 
            if item["tariff"] is not None
        ]
        self._custom_peak = round(mean(custom_peak_prices), 2) if custom_peak_prices else None

    # -------------------------------------------------------------
    # METODY AKTUALIZACJI DANYCH
    # -------------------------------------------------------------

    async def full_update(self):
        """Wykonaj kompletną aktualizację wszystkich danych."""
        try:
            now = datetime.now()
            
            # Pobierz dane na dzisiaj (zawsze)
            self._today = await self.json_to_day_raw(0)
            
            # Pobierz dane na jutro TYLKO jeśli jest po 15:00
            if now.hour >= 15:
                self._tomorrow = await self.json_to_day_raw(1)
                _LOGGER.debug("Pobrano dane na jutro (godzina >= 15:00)")
            else:
                self._tomorrow = []
                _LOGGER.debug("Nie pobieram danych na jutro (godzina < 15:00)")

            if self._today:
                self._update(self._today)
                self._calculate_price_ranking(self._today)

                now_hour_0_23 = now.hour
                now_hour_1_24 = now_hour_0_23 + 1 if now_hour_0_23 < 23 else 24
                
                current_hour_data = None
                for hour_data in self._today:
                    if hour_data["hour"] == now_hour_1_24:
                        current_hour_data = hour_data
                        break
                
                if current_hour_data and current_hour_data["tariff"] is not None:
                    self._attr_native_value = current_hour_data["tariff"]
                else:
                    _LOGGER.warning("Brak danych cenowych dla bieżącej godziny %s", now_hour_1_24)
            else:
                _LOGGER.warning("Brak danych na dzisiaj")
                
        except Exception as e:
            _LOGGER.error("Błąd podczas pełnej aktualizacji: %s", e, exc_info=True)

    async def async_update(self):
        """Aktualizuj dane sensora."""
        now = datetime.now(ZoneInfo(self.hass.config.time_zone))
        
        if now.hour == 15:
            if self.last_15_update_day != now.date():
                _LOGGER.info("Godzina 15:00 - pobieram nowe dane z API PSE")
                await self.full_update()
                self.last_network_pull = now
                self.last_15_update_day = now.date()
                return
        
        if now.date() != self.last_network_pull.date() or not self._today:
            _LOGGER.debug("Nowy dzień lub brak danych - pobieram dane z API PSE")
            await self.full_update()
            self.last_network_pull = now
        else:
            now_hour_0_23 = now.hour
            now_hour_1_24 = now_hour_0_23 + 1 if now_hour_0_23 < 23 else 24
            
            for hour_data in self._today:
                if hour_data["hour"] == now_hour_1_24 and hour_data["tariff"] is not None:
                    self._attr_native_value = hour_data["tariff"]
                    break

    async def async_added_to_hass(self):
        """Wywoływane gdy encja jest dodawana do Home Assistant."""
        await super().async_added_to_hass()
        await self.full_update()
        now = datetime.now(ZoneInfo(self.hass.config.time_zone))
        if now.hour >= 15:
            self.last_15_update_day = now.date()

    # -------------------------------------------------------------
    # WŁAŚCIWOŚCI SENSORA
    # -------------------------------------------------------------

    @property
    def name(self):
        """Zwróć nazwę sensora."""
        return "Rynkowa Cena Energii Elektrycznej"

    @property
    def unique_id(self):
        """Zwróć unikalny ID sensora."""
        return "rce_pse_pln"

    @property
    def native_unit_of_measurement(self):
        """Zwróć jednostkę miary."""
        return f"{DEFAULT_CURRENCY}/{DEFAULT_PRICE_TYPE}"

    @property
    def device_info(self):
        """Zwróć informacje o urządzeniu."""
        return {
            "entry_type": DeviceEntryType.SERVICE,
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": "RCE PSE",
            "manufacturer": "PSE",
        }

    @property
    def available(self):
        """Zwróć True jeśli encja jest dostępna."""
        if not self._today:
            return False
            
        now_hour_0_23 = datetime.now().hour
        now_hour_1_24 = now_hour_0_23 + 1 if now_hour_0_23 < 23 else 24
        
        for hour_data in self._today:
            if hour_data["hour"] == now_hour_1_24:
                return hour_data["tariff"] is not None
        return False

    @property
    def extra_state_attributes(self):
        """Zwróć dodatkowe atrybuty stanu."""
        if not self._today:
            return {}

        now_hour_0_23 = datetime.now().hour
        now_hour_1_24 = now_hour_0_23 + 1 if now_hour_0_23 < 23 else 24
        
        current_hour_data = None
        for hour_data in self._today:
            if hour_data["hour"] == now_hour_1_24:
                current_hour_data = hour_data
                break
        
        next_price = None
        if now_hour_1_24 < 24:
            for hour_data in self._today:
                if hour_data["hour"] == now_hour_1_24 + 1:
                    next_price = hour_data.get("tariff")
                    break
        elif self._tomorrow and len(self._tomorrow) > 0:
            for hour_data in self._tomorrow:
                if hour_data["hour"] == 1:
                    next_price = hour_data.get("tariff")
                    break

        current_hour_rank = None
        current_hour_percentile = None
        current_h_price = None
        current_l_price = None
        current_am_h_price = None
        current_am_l_price = None
        current_pm_h_price = None
        current_pm_l_price = None
        current_am_rank = None
        current_pm_rank = None
        
        if current_hour_data:
            current_hour_rank = current_hour_data.get("price_rank")
            current_hour_percentile = current_hour_data.get("price_percentile")
            current_h_price = current_hour_data.get("h_price")
            current_l_price = current_hour_data.get("l_price")
            current_am_h_price = current_hour_data.get("am_h_price")
            current_am_l_price = current_hour_data.get("am_l_price")
            current_pm_h_price = current_hour_data.get("pm_h_price")
            current_pm_l_price = current_hour_data.get("pm_l_price")
            current_am_rank = current_hour_data.get("am_rank", 0)
            current_pm_rank = current_hour_data.get("pm_rank", 0)

        attributes = {
            "next_price": next_price,
            "average": self._average,
            "min": self._min,
            "max": self._max,
            "mean": self._mean,
            "am_night_avg": self._am_night_avg,
            "day_avg": self._day_avg,
            "pm_night_avg": self._pm_night_avg,
            "custom_peak": self._custom_peak,
            "custom_peak_range": f"{self.custom_peak_start}-{self.custom_peak_end}",
            "current_hour": now_hour_1_24,
            "current_hour_rank": current_hour_rank,
            "current_hour_percentile": current_hour_percentile,
            "current_h_price": current_h_price,
            "current_l_price": current_l_price,
            "current_am_h_price": current_am_h_price,
            "current_am_l_price": current_am_l_price,
            "current_pm_h_price": current_pm_h_price,
            "current_pm_l_price": current_pm_l_price,
            "current_am_rank": current_am_rank,
            "current_pm_rank": current_pm_rank,
            "currency": DEFAULT_CURRENCY,
            "last_updated": self.last_network_pull.isoformat() if self.last_network_pull else None,
        }

        today_prices = []
        for item in self._today:
            price_info = {
                "hour": item["hour"],
                "start": item["start"],
                "price": item["tariff"],
            }
            
            if "price_rank" in item:
                price_info["price_rank"] = item["price_rank"]
                price_info["price_position"] = item.get("price_position")
                price_info["price_percentile"] = item.get("price_percentile")
            
            if "h_price" in item:
                price_info["h_price"] = item["h_price"]
            if "l_price" in item:
                price_info["l_price"] = item["l_price"]
            if "am_h_price" in item:
                price_info["am_h_price"] = item["am_h_price"]
            if "am_l_price" in item:
                price_info["am_l_price"] = item["am_l_price"]
            if "pm_h_price" in item:
                price_info["pm_h_price"] = item["pm_h_price"]
            if "pm_l_price" in item:
                price_info["pm_l_price"] = item["pm_l_price"]
            if "am_rank" in item:
                price_info["am_rank"] = item["am_rank"]
            if "pm_rank" in item:
                price_info["pm_rank"] = item["pm_rank"]
            
            today_prices.append(price_info)
        
        attributes["today_prices"] = today_prices

        valid_ranks = [item.get("price_rank") for item in self._today if item.get("price_rank") is not None]
        if valid_ranks:
            attributes["ranking_stats"] = {
                "cheapest_hour": min(valid_ranks),
                "most_expensive_hour": max(valid_ranks),
                "average_rank": round(mean(valid_ranks), 1),
            }

        if self._tomorrow:
            tomorrow_prices = []
            for item in self._tomorrow:
                start_time = f"{item['hour']-1:02d}:00"
                tomorrow_prices.append({
                    "hour": item["hour"],
                    "start": start_time,
                    "price": item["tariff"],
                })
            attributes["tomorrow_prices"] = tomorrow_prices

        return attributes