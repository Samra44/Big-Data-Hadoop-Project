# 🌍 EarthScape Climate Agency – Big-Data Climate Analytics Platform

Aptech eProject (Big Data – Hadoop & Machine Learning). Ingests satellite, weather-station and sensor data, stores it in HDFS, processes it with MapReduce/Spark, predicts with ML and shows live dashboards with real-time alerts.

## Live demo
🔗 **Hosted app:** _deploying – link added here once live_

## Quick start
Windows: double-click `run_windows.bat`. Linux/Mac: `./run_linux_mac.sh`. Or:
```
cd app
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 – `admin` / `Admin@123` (also `analyst` / `Analyst@123`, `viewer` / `Viewer@123`).
First start trains the models on your machine (about a minute).

## Features
* Role-based access (admin, analyst, viewer), hashed passwords, API key, optional HTTPS
* Ingestion: CSV, TXT, JSON, Excel, Parquet, NetCDF; REST API; live stream; simulator; Kafka
* **Real-time stream analytics** page: Server-Sent Events, sliding windows (2/5/15 min), throughput, anomaly rate, EWMA per station, live event feed
* **Deep learning**: Deep MLP forecasters/classifiers and a 32-8-32 autoencoder for anomalies in the app; stacked **LSTM** and **1-D CNN** (TensorFlow/Keras) in the Colab notebook
* ML: next-day temperature forecast, extreme-event classifier (heatwave/flood/storm/smog), anomaly detection, warming trends, 12-month outlook, explanations
* Runtime training, auto-retraining, model versions and rollback, drift monitoring
* Live dashboard, station map, explore (time series, correlation heat-map), Tableau extracts
* Configurable alert rules, pop-ups, e-mail/webhook notifications
* Performance monitoring, encrypted automated backups, support tickets, help/FAQ

## Results (2024 unseen test year)
Event classifier macro-F1 **0.91** · forecast MAE **1.70 °C** (hold-out 1.35 °C, R² 0.94, persistence 1.71) · anomaly precision **0.79** / recall **0.53** (Isolation Forest + deep autoencoder) · LSTM MAE 1.91 °C · 1-D CNN macro-F1 0.78 · warming **+0.41 °C/decade**.

## Folders
| Folder | Content |
|---|---|
| app/ | Flask app, `ml_engine.py`, `config.py`, `simulator.py`, `restore_backup.py` |
| data/ | generator, sample (35,064) & testing (4,392) datasets, stations, stream sample |
| ml/ | Colab notebook, training script, `earthscape_models.pkl`, `metrics.json` |
| hadoop/ | HDFS, Hive, Impala, MapReduce, Spark batch/streaming, Kafka, MongoDB |
| r/ | RStudio analysis |
| dashboard/ | Tableau data + guide |
| docs/ | Documentation, guides, papers, credentials, Figma spec, video script, GitHub guide |

## Docker / cloud deploy
```
docker build -t earthscape .
docker run -p 7860:7860 earthscape      # open http://localhost:7860
```
Render (free): New → Blueprint → pick this repo (`render.yaml`). Models are trained during the image build, so the container starts in seconds.

## Screenshots
See `docs/screenshots/`.
