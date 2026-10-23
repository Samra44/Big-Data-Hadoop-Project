---
date: October 2026
title: EarthScape – Developer Guide
---

# 1. Technology Stack

| Layer         | Technology                                                                                                  |
|---------------|-------------------------------------------------------------------------------------------------------------|
| Web           | Python 3.10+, Flask 3, Jinja2, Bootstrap 5, Chart.js 4, Leaflet 1.9                                         |
| ML            | scikit-learn (Ridge, RandomForest, HistGradientBoosting, IsolationForest), pandas, NumPy                    |
| Storage (app) | SQLite (indexed), automatic folder fallback, in-memory fallback                                             |
| Big data      | Hadoop HDFS, Hadoop Streaming MapReduce, Hive, Impala, Spark (batch + Structured Streaming), Kafka, MongoDB |
| Analytics     | Jupyter / Google Colab, RStudio, Tableau                                                                    |
| Ops           | psutil monitoring, cryptography (Fernet) backups, Docker, gunicorn                                          |

# 2. Project Structure

    EarthScape/
    ├── app/
    │   ├── app.py              Flask routes, ingestion, alerts, stream, backups, monitoring
    │   ├── ml_engine.py        Feature engineering, training, registry, scoring, explanations
    │   ├── config.py           .env settings, runtime detection, DB/folder selection
    │   ├── simulator.py        External real-time sensor feed (REST)
    │   ├── restore_backup.py   Decrypt + restore a backup
    │   ├── templates/          17 Jinja2 pages
    │   └── static/style.css
    ├── data/                   generate_data.py, sample_dataset.csv, testing_dataset.csv, stations.csv, sample_stream.json
    ├── ml/                     train_models.py, EarthScape_ML_Colab.ipynb, earthscape_models.pkl, metrics.json, registry/
    ├── hadoop/                 HDFS, Hive, Impala, MapReduce, Spark batch/streaming, Kafka, MongoDB scripts
    ├── r/climate_analysis.R    Statistical analysis (trend, Mann-Kendall, SARIMA)
    ├── dashboard/              Tableau extracts + guide
    ├── docs/                   Documentation set
    ├── backups/                Encrypted backups (created at runtime)
    ├── run_windows.bat · run_linux_mac.sh · Dockerfile · README.md

# 3. Runtime Lifecycle

1.  `config.py` reads `.env`, detects Python/OS/CPU, picks a writable database folder (app → LOCALAPPDATA → home → temp → memory) and creates `ml/registry` and `backups`.
2.  `init_db()` creates tables, seeds users, stations and default alert rules.
3.  If no model in the registry matches the installed scikit-learn, `ml.train()` runs on `sample_dataset.csv` (≈20–60 s).
4.  The historical archive is scored and stored; recent alerts are generated.
5.  Background threads: backup scheduler; optional live stream; asynchronous retraining.

# 4. Database Schema

| Table         | Key columns                                                                                                                                                                                                                    |
|---------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| users         | id, username (unique), password (hash), role, email, created                                                                                                                                                                   |
| stations      | station_id PK, name, region, lat, lon, elevation, climate_zone                                                                                                                                                                 |
| readings      | record_id, station_id, date, 12 metrics, source, event_type, is_anomaly, pred_event, event_prob, pred_anomaly, anomaly_score, max_zscore, temp_dev, model_version, ingest_source, ingested_at (indexes: station_id+date, date) |
| alert_rules   | id, metric, operator, threshold, level, label, enabled, region                                                                                                                                                                 |
| alerts        | id, station_id, region, date, rule, value, level, created, acknowledged, ack_by                                                                                                                                                |
| notifications | id, channel, target, message, status, created                                                                                                                                                                                  |
| feedback      | id, username, category, subject, message, status, reply, created                                                                                                                                                               |
| jobs          | id, job, records, seconds, detail, created                                                                                                                                                                                     |

# 5. ML Engine API (`ml_engine.py`)

| Function                                            | Purpose                                                         |
|-----------------------------------------------------|-----------------------------------------------------------------|
| `clean(df)`                                         | Type coercion, missing columns, seasonal features               |
| `climatology(df)` / `add_deviation(df, clim)`       | Station × month normals and z-scores                            |
| `lag_features(df)`                                  | Lags 1/2/3/7, 7-day rolling mean, next-day target               |
| `train(df, reason)`                                 | Trains all models with TimeSeriesSplit CV, registers version    |
| `train_async(loader, reason)`                       | Background retraining                                           |
| `score(df)`                                         | pred_event, event_prob, pred_anomaly, anomaly_score, max_zscore |
| `forecast_next(history)`                            | Next-day temperature for one station                            |
| `seasonal_outlook(months)`                          | Regional monthly outlook                                        |
| `explain_event(row)`                                | Per-reading contribution to event probability                   |
| `psi(q, actual)`                                    | Population Stability Index for drift                            |
| `list_versions / activate / load_latest_compatible` | Model registry                                                  |

# 6. REST API

| Endpoint                                | Method | Auth          | Description                                             |
|-----------------------------------------|--------|---------------|---------------------------------------------------------|
| `/api/ingest`                           | POST   | `X-API-Key`   | Object or list of readings → scored results             |
| `/api/stats`                            | GET    | session       | Dashboard data (`?since=<alert id>` returns new alerts) |
| `/api/series`                           | GET    | session       | `metric`, `station` (multi), `agg`, `start`, `end`      |
| `/api/correlation`                      | GET    | session       | `region`                                                |
| `/api/trends`                           | GET    | session       | Warming per station                                     |
| `/api/system`                           | GET    | admin/analyst | CPU, RAM, latency, throughput                           |
| `/api/training`                         | GET    | session       | Training status                                         |
| `/api/stream/start`, `/api/stream/stop` | POST   | admin/analyst | Live stream                                             |
| `/api/health`                           | GET    | none          | Uptime check                                            |
| `/export`                               | GET    | admin/analyst | CSV export (`start`, `end`)                             |

Example:

    curl -X POST http://127.0.0.1:5000/api/ingest -H "X-API-Key: earthscape-demo-key" -H "Content-Type: application/json" \
         -d '[{"station_id":"ST04","date":"2024-11-10","temperature_c":17,"pm25_ugm3":420}]'

# 7. Configuration (`app/.env`)

| Variable                               | Default              | Purpose                               |
|----------------------------------------|----------------------|---------------------------------------|
| EARTHSCAPE_SECRET / EARTHSCAPE_API_KEY | demo                 | Change in production                  |
| EARTHSCAPE_PORT / HOST / DEBUG         | 5000 / 127.0.0.1 / 1 | Server                                |
| EARTHSCAPE_HTTPS                       | 0                    | 1 = encrypted transport (self-signed) |
| EARTHSCAPE_RETRAIN_EVERY               | 2000                 | New readings before auto-retrain      |
| EARTHSCAPE_STREAM_INTERVAL             | 3                    | Seconds between live readings         |
| EARTHSCAPE_BACKUP_HOURS / KEEP         | 24 / 7               | Backup schedule and retention         |
| EARTHSCAPE_CV_FOLDS / N_JOBS           | 4 / -1               | Training                              |
| EARTHSCAPE_SMTP\_\* / ALERT_EMAIL_TO   | empty                | E-mail alerts                         |
| EARTHSCAPE_WEBHOOK_URL                 | empty                | Slack/Teams/any webhook               |
| EARTHSCAPE_DB / MODEL_DIR / BACKUP_DIR | auto                 | Override locations                    |

# 8. Hadoop / Spark Workflows

1.  `01_hdfs_ingest.sh` – partitions CSV into `source/year/month/region` and puts it in HDFS (replication 3).
2.  `02_hive_tables.sql` – external raw table, curated partitioned Parquet table with missing-value handling.
3.  `03_impala_analytics.sql` – trends, z-score anomalies, events, correlations, monsoon totals, air quality.
4.  `04_run_mapreduce.sh` + `mapper.py`/`reducer.py` – monthly station summary with bad-record counters. Local test: `tail -n +2 ../data/sample_dataset.csv | python3 mapper.py | sort | python3 reducer.py`.
5.  `05_spark_batch.py` – imputation, z-scores, Parquet output, trends with Spark MLlib.
6.  `06_spark_streaming.py` + `07_kafka_producer.py` – streaming alerts joined with batch climatology.
7.  `08_mongodb_load.py` – stations (2dsphere index), stream sample and model registry into MongoDB.

# 9. Extending

- **New metric** – add it to `METRICS` in `ml_engine.py`, `METRIC_LABELS` in `app.py` and the generator; retrain.
- **New model** – add a candidate to the dictionaries in `train()`; it is compared automatically.
- **New alert channel** – extend `notify()`.
- **Production DB** – replace `config.db_connect` with a PostgreSQL/Impala connector; SQL is ANSI-style.

# 10. Coding Standards

PEP 8, functions documented with docstrings, configuration only through environment variables, no secrets in code, every route protected by `login_required`.
