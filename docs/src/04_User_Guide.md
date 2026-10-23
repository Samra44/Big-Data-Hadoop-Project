---
date: October 2026
title: EarthScape – User Guide
---

# 1. Signing In

Open the application, enter your username and password and press **Login**. Your role decides the menu:

| Role                 | Can do                                                    |
|----------------------|-----------------------------------------------------------|
| Administrator        | Everything, including users and backups                   |
| Analyst              | Ingest data, predictions, alert rules, models, monitoring |
| Viewer (stakeholder) | Dashboard, map, explore, alerts (read-only), support      |

# 2. Dashboard

- **KPI cards** – total readings, stations, latest date, 30-day average temperature, how far it is from normal (σ), anomalies, extreme-event readings, open alerts.
- **Warming trend** – annual mean temperature and CO₂.
- **Extreme events per year** – heatwave, flood, storm, smog.
- **Tomorrow’s forecast** – latest vs predicted temperature for each station.
- **12-month outlook** – expected monthly temperature per region.
- **Latest readings** – newest data with predicted event and anomaly flag.
- **Live stream** – analysts/admins can start simulated sensors; new Critical/High alerts pop up at the bottom right.

The page refreshes itself every 5 seconds.

# 3. Map

Select a metric at the top right. Circles are coloured from blue (low) to red (high); a thick red ring marks an anomaly or predicted event. Click a station for all its latest values.

# 4. Explore

Choose a metric, up to six stations (Ctrl+click), aggregation (daily/monthly/yearly) and dates, then **Update**. Red points mark periods with anomalies. The correlation heat-map shows how metrics move together (orange positive, blue negative) for all regions or one region. The trend chart shows warming per decade for each station.

# 5. Predict

Select a station and date, enter readings (blank fields are allowed) and press **Run models**. You get the predicted event, its probability, whether the reading is anomalous, tomorrow’s temperature, and a table explaining which readings raised or lowered the risk compared with normal.

# 6. Ingestion

Choose a file (CSV, TXT, JSON, Excel, Parquet, NetCDF) with `station_id` and `date` columns, pick the source type and press **Upload & process**. The message reports duplicates removed, missing values imputed, anomalies and events detected. The table lists recent jobs.

# 7. Alerts and Alert Rules

**Alerts** lists open alerts by level; press **Ack** (or **Acknowledge all**). The notification log shows what was sent by e-mail/webhook.

**Alert Rules** lets analysts change thresholds, add rules for a metric and region, and enable/disable or delete rules. Changes apply instantly.

# 8. Models

Shows the computer the models were trained on, current accuracy, comparison charts and version history. **Retrain on latest data** builds a new version in the background; **Activate** rolls back to an older one.

# 9. Monitor

CPU, memory, disk, uptime, database size, ingestion speed, response times and data drift. A drift status of **Drift** means recent data looks different from history – retrain the models.

# 10. Backups (admin)

Shows automated encrypted backups. **Back up now** creates one immediately; **Download** saves a copy.

# 11. Users (admin)

Create users with a role and e-mail, or delete users.

# 12. Support

Submit a ticket (assistance, issue, data quality, feature request, feedback). Administrators reply and set the status; you see replies on the same page.

# 13. FAQ

**Why does the first start take a minute?** The models are being trained on your computer.

**What does “vs normal (σ)” mean?** How many standard deviations recent temperatures are above (+) or below (−) the usual value for each station and month.

**Can I upload incomplete data?** Yes. Missing values are filled in automatically.

**How do I get e-mail alerts?** An administrator fills in the SMTP settings in `.env`.

**Is my data safe?** Passwords are hashed, pages are role-protected, the API needs a key, backups are encrypted and HTTPS can be switched on.
