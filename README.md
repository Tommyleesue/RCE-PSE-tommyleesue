---
name: "RCE PSE"
content_in_root: false
filename: "rce_pse.zip"
hide_default_branch: true
homeassistant: "2022.11.0"
persistent_directory: "rce_pse"
render_readme: true
zip_release: true
---
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![License](https://img.shields.io/github/license/Tommyleesue/RCE-PSE-tommyleesue.svg)](https://github.com/Tommyleesue/RCE-PSE-tommyleesue/blob/main/LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/Tommyleesue/RCE-PSE-tommyleesue)](https://github.com/Tommyleesue/RCE-PSE-tommyleesue/releases)
[![GitHub last commit](https://img.shields.io/github/last-commit/Tommyleesue/RCE-PSE-tommyleesue)](https://github.com/Tommyleesue/RCE-PSE-tommyleesue/commits/main)

# 🇵🇱 RCE PSE – Rynkowa Cena Energii (PLN/MWh)

![logo](https://raw.githubusercontent.com/Tommyleesue/RCE-PSE-tommyleesue/main/icons/icon.png)

Integracja **RCE PSE** dla **Home Assistant** udostępnia aktualne oraz prognozowane
**Rynkowe Ceny Energii Elektrycznej (RCE)** publikowane przez  
**Polskie Sieci Elektroenergetyczne (PSE)**.

Integracja opiera się na **jednym, rozbudowanym sensorze**, który dostarcza:
- aktualną cenę energii dla bieżącej godziny,
- pełne ceny godzinowe dla całej doby (1–24),
- ceny na jutro (publikowane po 15:00),
- rankingi tanich i drogich godzin,
- statystyki dobowo-czasowe,
- dane gotowe do automatyzacji i wizualizacji.

---

## ✨ Funkcjonalności

- 📡 Dane bezpośrednio z **API PSE v2**
- ⏱️ Agregacja danych 15-minutowych do **godzin 1–24**
- 📊 Ranking cen doby (najtańsze / najdroższe godziny)
- 🌙 Podział **AM (1–12)** oraz **PM (13–24)**
- 🔥 Konfigurowalny zakres szczytu dobowego
- 📅 Ceny na jutro dostępne po godzinie **15:00**
- 🎨 Flagi tanich i drogich godzin (AM / PM) do kolorowania wykresów
- 🧠 Jeden sensor – wiele atrybutów

---

## 🧠 sensor.rce


### Wartość sensora
Aktualna cena energii dla **bieżącej godziny RCE**.

---

## 🧩 Atrybuty

### Statystyki doby
| Atrybut | Opis |
|------|------|
| `average` | średnia cena doby |
| `min` | najniższa cena |
| `max` | najwyższa cena |
| `mean` | mediana |
| `am_night_avg` | średnia 1–8 |
| `day_avg` | średnia 9–20 |
| `pm_night_avg` | średnia 21–24 |
| `custom_peak` | średnia z własnego zakresu |

---

### Bieżąca godzina
| Atrybut | Opis |
|------|------|
| `current_hour` | aktualna godzina (1–24) |
| `current_hour_rank` | ranking w dobie |
| `current_hour_percentile` | percentyl |
| `current_l_price` | flga zadeklarowanego rankingu tanich godzin |
| `current_h_price` | flga zadeklarowanego rankingu drogich godzin |
| `current_am_rank` | ranking przedpołudniowy |
| `current_pm_rank` | ranking popołudniowy |

---

### Ceny godzinowe – dziś
Atrybut:


Przykład:
```json
{
  "hour": 14,
  "price": 523.41,
  "price_rank": 18,
  "am_l_price": false,
  "pm_h_price": true
}

