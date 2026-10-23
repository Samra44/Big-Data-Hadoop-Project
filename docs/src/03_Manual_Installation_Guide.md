---
date: October 2026
title: EarthScape – Manual (Installation) Guide
---

# 1. Requirements

- Windows 10/11 64-bit (also Linux/macOS), i5 4-core or better, 8–16 GB RAM.
- Python 3.10 – 3.14 (Anaconda is fine). Check with `python --version`.
- Internet the first time (to install packages and load chart/map libraries).
- Optional: Hadoop 3, Spark 3.5, Hive/Impala, Kafka, MongoDB + Compass, RStudio, Tableau.

# 2. Quick Start (Windows)

1.  Extract `EarthScape.zip`, e.g. to `C:\EarthScape` (outside OneDrive-synced folders is best).
2.  Double-click **run_windows.bat**. It creates a virtual environment, installs packages, trains the models on your PC (first start ≈ 1 minute) and opens the browser.
3.  Log in with `admin` / `Admin@123`.

# 3. Manual Start

    cd EarthScape\app
    pip install -r requirements.txt
    python app.py

Open `http://127.0.0.1:5000`. Important: run `pip install` from inside the `app` folder.

# 4. Real-time Demo

In a second terminal:

    cd EarthScape\app
    python simulator.py --rate 2 --batch 12
    python simulator.py --rate 1 --batch 12 --drift

Or click **▶ Start live sensor stream** on the dashboard.

# 5. Configuration

Copy `app\.env.example` to `app\.env` and edit values (port, alert e-mail, webhook, retrain threshold, backup schedule). Restart the app.

# 6. Optional Components

| Component               | Command                                                                                                                                      |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| NetCDF / Parquet upload | `pip install xarray netCDF4 pyarrow`                                                                                                         |
| HTTPS                   | set `EARTHSCAPE_HTTPS=1` in `.env`                                                                                                           |
| Docker                  | `docker build -t earthscape .` then `docker run -p 5000:5000 earthscape`                                                                     |
| HDFS + Hive             | `cd hadoop && bash 01_hdfs_ingest.sh && hive -f 02_hive_tables.sql`                                                                          |
| Impala                  | `impala-shell -f 03_impala_analytics.sql`                                                                                                    |
| MapReduce               | `bash 04_run_mapreduce.sh`                                                                                                                   |
| Spark                   | `spark-submit 05_spark_batch.py`                                                                                                             |
| Kafka + streaming       | start Kafka, `python 07_kafka_producer.py`, `spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 06_spark_streaming.py` |
| MongoDB                 | `pip install pymongo && python 08_mongodb_load.py`, open Compass → `earthscape`                                                              |
| Jupyter / Colab         | open `ml/EarthScape_ML_Colab.ipynb`                                                                                                          |
| RStudio                 | open `r/climate_analysis.R`                                                                                                                  |
| Offline training        | `cd ml && python train_models.py`                                                                                                            |
| Restore backup          | `cd app && python restore_backup.py ..\backups\<file>`                                                                                       |

# 7. Troubleshooting

| Problem                                    | Fix                                                                                                                                                                               |
|--------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `No such file requirements.txt`            | `cd app` first                                                                                                                                                                    |
| `sqlite3.OperationalError: disk I/O error` | Handled automatically (another folder or memory). Move the project out of Desktop/OneDrive or allow Python in Windows Security → Ransomware protection → Controlled folder access |
| Port 5000 busy                             | set `EARTHSCAPE_PORT=5050` in `.env`                                                                                                                                              |
| Charts/map not showing                     | Internet needed for CDN libraries                                                                                                                                                 |
| Model error after upgrading scikit-learn   | Delete `ml\registry`; the app retrains                                                                                                                                            |
| Slow first start                           | Normal – models are training (see console)                                                                                                                                        |
