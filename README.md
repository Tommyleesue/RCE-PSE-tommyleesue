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

Integracja dla Home Assistant, która pobiera dane o Rynkowej Cenie Energii (RCE) z Polskich Sieci Elektroenergetycznych (PSE).

## ✨ Funkcje

- **Aktualna cena energii** w PLN/MWh dla bieżącej godziny
- **Dane historyczne** z ostatnich 24 godzin
- **Prognoza cenowa** na kolejny dzień (dostępna od 15:00)
- **Szczegółowe statystyki**:
  - Średnia, minimalna i maksymalna cena doby
  - Średnia cena w różnych przedziałach czasowych (rano, dzień, wieczór)
  - Średnia cena w dowolnie skonfigurowanym przedziale godzinowym
- **Ranking cenowy**:
  - Ranking całej doby (1-24)
  - Oddzielne rankingi dla godzin porannych (1-12) i popołudniowych (13-24)
  - Oznaczenie tanich i drogich godzin w obu przedziałach
  - Percentyle cenowe
- **Automatyczna aktualizacja** danych o 15:00 każdego dnia
- **Elastyczna konfiguracja** przez interfejs użytkownika

## 📊 Przykładowy wykres

Oto przykład konfiguracji karty `apexcharts-card`:

```yaml
type: custom:apexcharts-card
graph_span: 48h
span:
  start: day
  offset: "-0h"
header:
  show: true
  title: Rynkowa Cena Energii PLN / MWh
  show_states: true
  colorize_states: true
update_interval: 1min
cache: false
apex_config:
  chart:
    height: 300
  legend:
    show: false
  xaxis:
    type: datetime
    labels:
      datetimeUTC: false
      format: HH
  yaxis:
    min: 0
series:
  - entity: sensor.rce
    show:
      in_header: true
      in_chart: false
    name: Aktualna
    float_precision: 1
    unit: " zł/MWh "
  - entity: sensor.rce
    show:
      in_header: true
      in_chart: false
    name: Maksymalna
    attribute: max
    float_precision: 1
    color: red
    unit: " zł/MWh "
  - entity: sensor.rce
    show:
      in_header: true
      in_chart: false
    name: Minimalna
    attribute: min
    float_precision: 1
    color: green
    unit: " zł/MWh "
  - entity: sensor.rce
    show:
      in_header: true
      in_chart: false
    name: Aktualna godzina
    attribute: current_hour
    float_precision: 0
    color: orange
    unit: " h"
  - entity: sensor.rce
    show:
      in_header: true
      in_chart: false
    name: Ranking doby
    attribute: current_hour_rank
    float_precision: 0
    color: brown
    unit: " rank"
  - entity: sensor.rce
    show:
      in_header: true
      in_chart: false
    name: Ranking AM
    attribute: current_am_rank
    float_precision: 0
    color: brown
    unit: " rank"
  - entity: sensor.rce
    show:
      in_header: true
      in_chart: false
    name: Ranking PM
    attribute: current_pm_rank
    float_precision: 0
    color: brown
    unit: " rank"
  - name: Dziś
    type: column
    entity: sensor.rce
    show:
      in_header: false
    extend_to: false
    data_generator: |
      var s = hass.states['sensor.rce'];
      if (!s?.attributes?.today_prices) {
        console.error('Brak today_prices');
        return [];
      }
      var todayStart = new Date();
      todayStart.setHours(0,0,0,0);
      var result = s.attributes.today_prices
        .filter(i => i.hour >= 1 && i.hour <= 24 && i.price !== null)
        .map(i => {
          var d = new Date(todayStart);
          if (i.hour === 24) {
            d.setDate(d.getDate() + 1);
            d.setHours(0,0,0,0);
          } else {
            d.setHours(i.hour,0,0,0);
          }
          var color = '#FFA726';
          if (i.am_h_price === true || i.pm_h_price === true) {
            color = '#EF5350';
          }
          else if (i.am_l_price === true || i.pm_l_price === true) {
            color = '#66BB6A';
          }
          return {
            x: d.getTime() - (1 * 60 * 60 * 1000),
            y: i.price,
            fillColor: color
          };
        });
      return result;
  - name: Jutro
    type: column
    entity: sensor.rce
    show:
      in_header: false
    extend_to: false
    opacity: 0.7
    data_generator: |
      var s = hass.states['sensor.rce'];
      if (!s?.attributes?.tomorrow_prices) return [];
      var tomorrowStart = new Date();
      tomorrowStart.setHours(0,0,0,0);
      tomorrowStart.setDate(tomorrowStart.getDate() + 1);
      return s.attributes.tomorrow_prices
        .filter(i => i.hour >= 1 && i.hour <= 24 && i.price !== null)
        .map(i => {
          var d = new Date(tomorrowStart);
          if (i.hour === 24) {
            d.setDate(d.getDate() + 1);
            d.setHours(0,0,0,0);
          } else {
            d.setHours(i.hour,0,0,0);
          }
          return {
            x: d.getTime() - (1 * 60 * 60 * 1000),
            y: i.price,
            fillColor: '#B0BEC5',
            opacity: 0.7
          };
        });
