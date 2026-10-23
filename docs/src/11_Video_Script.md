---
date: October 2026
title: EarthScape – Video Demonstration Script (≈ 8 minutes)
---

| Time | Screen                    | Narration                                                                                                             |
|------|---------------------------|-----------------------------------------------------------------------------------------------------------------------|
| 0:00 | Title slide               | “This is EarthScape, a big-data and machine-learning platform for the EarthScape Climate Agency.”                     |
| 0:20 | Architecture diagram      | Explain sources → Kafka/API → HDFS, MapReduce, Spark → Hive/Impala, ML → dashboards and alerts (Lambda architecture). |
| 1:00 | Terminal: `python app.py` | Show runtime detection and models training on this machine.                                                           |
| 1:30 | Login as admin            | Mention three roles and hashed passwords.                                                                             |
| 1:50 | Dashboard                 | KPIs, warming trend with CO₂, events per year, tomorrow’s forecast, 12-month outlook.                                 |
| 2:40 | Start live sensor stream  | Readings arrive, table updates, an alert toast pops up.                                                               |
| 3:10 | Map                       | Switch metric to PM2.5 and temperature, open a popup.                                                                 |
| 3:40 | Explore                   | Compare Karachi, Lahore, Quetta monthly; correlation heat-map for Punjab; warming per station.                        |
| 4:20 | Predict                   | Heatwave scenario → 98% probability, explanation table, next-day forecast.                                            |
| 5:00 | Ingestion                 | Upload testing_dataset.csv → imputation, anomalies, events; show API curl.                                            |
| 5:40 | Models                    | Auto-retrain to v2, version history, CV charts, activate v1 (rollback).                                               |
| 6:10 | Alert Rules + Alerts      | Lower the heat threshold, see new alerts, acknowledge, notification log.                                              |
| 6:40 | Monitor + Backups         | CPU/RAM, latency, drift (run `simulator.py --drift`), encrypted backup.                                               |
| 7:10 | Hadoop                    | `hdfs dfs -ls /earthscape/raw`, MapReduce output, Impala query, Spark job; MongoDB Compass.                           |
| 7:40 | Colab + Tableau           | Notebook results and Tableau dashboard.                                                                               |
| 8:00 | Viewer login              | Show restricted menu and 403 page; close.                                                                             |

Recording tips: OBS Studio or Xbox Game Bar (Win+G), 1080p, zoom browser to 90%, rehearse once, upload to YouTube/Drive as unlisted and add the link to the submission.
