---
date: October 2026
title: EarthScape – Credentials
---

# Application Logins (demo)

| Role                 | Username | Password    | Access                                                |
|----------------------|----------|-------------|-------------------------------------------------------|
| Administrator        | admin    | Admin@123   | Full access incl. users, backups                      |
| Analyst              | analyst  | Analyst@123 | Ingestion, predictions, rules, models, monitoring     |
| Viewer (stakeholder) | viewer   | Viewer@123  | Dashboards, map, explore, alerts (read-only), support |

# API

| Item            | Value                                 |
|-----------------|---------------------------------------|
| Ingest endpoint | POST http://127.0.0.1:5000/api/ingest |
| Header          | X-API-Key: earthscape-demo-key        |

# Services (default local installs)

| Service              | Address                                                  |
|----------------------|----------------------------------------------------------|
| Web app              | http://127.0.0.1:5000                                    |
| HDFS NameNode UI     | http://localhost:9870                                    |
| YARN ResourceManager | http://localhost:8088                                    |
| Spark UI             | http://localhost:4040                                    |
| Kafka                | localhost:9092 (topics climate-readings, climate-alerts) |
| MongoDB              | mongodb://localhost:27017 (database earthscape)          |
| Impala               | impala-shell -i localhost:21000                          |

# Security Notes

- Passwords are stored only as salted hashes.
- Change `EARTHSCAPE_SECRET` and `EARTHSCAPE_API_KEY` in `app/.env` before any real deployment.
- The backup encryption key is `backups/.backup.key` – keep it separate from the backups.
