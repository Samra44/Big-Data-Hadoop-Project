---
date: October 2026
title: EarthScape – Tableau Dashboard Guide
---

# Data Sources (folder `dashboard/`)

| File                        | Rows   | Content                                                                                                              |
|-----------------------------|--------|----------------------------------------------------------------------------------------------------------------------|
| tableau_readings_scored.csv | 39,456 | Every daily reading 2016–2024 with ML predictions (pred_event, event_prob, pred_anomaly, anomaly_score), year, month |
| tableau_monthly_station.csv | 1,296  | Monthly station summary: mean/max temp, rain, PM2.5, CO₂, NDVI, anomalies, event days, lat/lon                       |
| tableau_trends.csv          | 12     | °C per decade and CO₂ ppm/year per station                                                                           |
| tableau_outlook.csv         | 72     | 12-month regional temperature outlook                                                                                |

# Sheets to Build

1.  **Station Map** – Longitude → Columns, Latitude → Rows (Geographic role), Mark type Circle, Colour = AVG(mean_temp), Size = SUM(event_days), Tooltip = station, rain, PM2.5. Filter: year.
2.  **Warming Trend** – YEAR(year) → Columns, AVG(mean_temp) → Rows, Colour = region; Analytics → Trend Line (linear); dual axis AVG(co2).
3.  **Extreme Events** – year → Columns, CNT(record_id) → Rows from readings file filtered pred_event ≠ none, Colour = pred_event, stacked bars.
4.  **Anomaly Heat-map** – station_name → Rows, month → Columns, Colour = SUM(anomalies), Mark Square.
5.  **Warming by Station** – tableau_trends: temp_c_per_decade bar, sorted, colour diverging.
6.  **Regional Outlook** – tableau_outlook: month → Columns, forecast_temp_c → Rows, Colour = region.
7.  **Correlation scatter** – AVG(co2) vs AVG(mean_temp) per station-year with trend line.

# Dashboard

Size 1366×768. Layout: title + region/year filters at top; Map (left, large) and Warming Trend (right); Extreme Events and Anomaly Heat-map below; Outlook and Warming by Station as a second dashboard tab. Add **Actions → Filter**: clicking a station on the map filters all sheets. Add a parameter **Heat threshold** (default 45) and a calculated field `IF [temp_max_c] >= [Heat threshold] THEN "Alert" ELSE "OK" END` to colour readings.

# Saving

File → Save As → **EarthScape_Dashboard.twbx** (packaged workbook includes the data). Publish to Tableau Public for a shareable link.
