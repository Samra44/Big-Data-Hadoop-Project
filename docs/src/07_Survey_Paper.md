---
date: October 2026
subtitle: Survey Paper
title: A Survey of Big-Data and Machine-Learning Technologies for Climate Monitoring Platforms
---

# Abstract

This survey reviews the technologies available for building a climate monitoring and analytics platform – storage, batch and stream processing, query engines, databases, machine-learning approaches and visualisation – and justifies the choices made for EarthScape. It closes with a stakeholder questionnaire that the agency can use to validate requirements.

# 1. Climate Data Characteristics

| “V”      | Climate example                                               | Consequence                                    |
|----------|---------------------------------------------------------------|------------------------------------------------|
| Volume   | Decades of station records, multi-terabyte satellite archives | Distributed storage                            |
| Velocity | Sensors every minute, satellite passes daily                  | Stream processing                              |
| Variety  | CSV, JSON, NetCDF, GeoTIFF, HDF5                              | Schema-on-read, flexible ingestion             |
| Veracity | Sensor faults, cloud-covered pixels, gaps                     | Quality control, imputation, anomaly detection |
| Value    | Early warnings, policy evidence                               | ML and dashboards                              |

# 2. Storage

| Technology                | Strengths                                                  | Weaknesses                         | Use in EarthScape                |
|---------------------------|------------------------------------------------------------|------------------------------------|----------------------------------|
| HDFS                      | Fault-tolerant replication, data locality, cheap scale-out | Small-file problem, batch-oriented | Master dataset, partitioned      |
| Object storage (S3, ADLS) | Elastic, cheap                                             | Network latency                    | Cloud deployment option          |
| Parquet / ORC             | Columnar, compressed, predicate push-down                  | Write-once                         | Curated layer                    |
| NetCDF / HDF5             | Climate-science standard, multidimensional                 | Not distributed natively           | Ingestion format                 |
| MongoDB                   | Flexible JSON documents, geospatial indexes                | Not for heavy analytics            | Stations, alerts, model registry |
| SQLite / PostgreSQL       | Simple, transactional                                      | Single node                        | Application store                |

# 3. Processing

| Engine           | Model                                          | Latency      | Notes                                                                |
|------------------|------------------------------------------------|--------------|----------------------------------------------------------------------|
| Hadoop MapReduce | Batch, disk-based                              | Minutes      | Robust, simple; used for monthly summaries                           |
| Apache Spark     | In-memory batch + Structured Streaming + MLlib | Seconds      | Unified batch/stream; used for curation, trends and streaming alerts |
| Apache Flink     | True streaming                                 | Milliseconds | Alternative for very high-rate sensors                               |
| Kafka            | Distributed log / message bus                  | Milliseconds | Decouples sensors from processing                                    |

**Lambda architecture** (batch + speed + serving layers) was chosen over **Kappa** (stream only) because historical reprocessing and climatology computation are central to climate analysis.

# 4. Query Engines

| Engine       | Strength                               |
|--------------|----------------------------------------|
| Hive         | SQL on HDFS, ETL, partition management |
| Impala       | Low-latency interactive SQL on Parquet |
| Spark SQL    | SQL inside Spark pipelines             |
| Presto/Trino | Federated queries across sources       |

# 5. Machine-Learning Approaches for Climate

| Family                    | Examples                                                     | Typical use                                    | Pros                                   | Cons                     |
|---------------------------|--------------------------------------------------------------|------------------------------------------------|----------------------------------------|--------------------------|
| Statistical               | Linear/Ridge regression, ARIMA/SARIMA, Mann-Kendall          | Trends, seasonal forecasts                     | Interpretable, robust                  | Linear assumptions       |
| Tree ensembles            | Random Forest, gradient boosting (XGBoost, LightGBM, HistGB) | Classification of events, tabular forecasting  | Non-linear, handles missing data, fast | Less suited to raw grids |
| Anomaly detection         | Isolation Forest, One-Class SVM, z-scores, autoencoders      | Quality control, extreme detection             | Unsupervised                           | Threshold tuning         |
| Deep learning             | LSTM, ConvLSTM, CNN, Transformers, graph neural networks     | Spatio-temporal forecasting, satellite imagery | State-of-the-art accuracy              | Data- and compute-hungry |
| Foundation/weather models | GraphCast, Pangu-Weather                                     | Global medium-range forecasting                | Very high skill                        | Huge training cost       |

EarthScape uses statistical models and tree ensembles: they train in under a minute, work with missing values and tabular station data, and can be explained to stakeholders.

# 6. Visualisation

| Tool                               | Strength                                      |
|------------------------------------|-----------------------------------------------|
| Tableau                            | Drag-and-drop dashboards, maps, sharing       |
| Web dashboards (Chart.js, Leaflet) | Live updates, embedded alerts, role-based     |
| Jupyter / Colab                    | Exploratory analysis, reproducible notebooks  |
| RStudio                            | Statistical analysis and publication graphics |

# 7. Security and Compliance Practices

Role-based access control, password hashing, API keys, TLS, encryption at rest (HDFS transparent encryption, encrypted backups), audit logs, data minimisation and retention policies; open data standards (CF conventions, ISO 8601, WGS-84) and FAIR principles for sharing.

# 8. Comparison of Existing Platforms

| Platform type                            | Example capabilities   | Gap addressed by EarthScape              |
|------------------------------------------|------------------------|------------------------------------------|
| National met-service portals             | Forecasts, warnings    | Usually closed; limited custom analytics |
| Climate data stores / reanalysis portals | Large gridded datasets | Download-oriented, no alerts             |
| Generic BI tools                         | Dashboards             | No ML or streaming                       |
| IoT platforms                            | Real-time sensor data  | Little historical/climate analysis       |

EarthScape combines ingestion, big-data storage, ML, alerts and dashboards in one workflow.

# 9. Stakeholder Questionnaire (to be filled by the agency)

1.  Which data sources do you use today (satellite, station, sensor, other)?
2.  How often do you need updates (real-time, hourly, daily)?
3.  Which events matter most (heatwave, flood, storm, smog, drought, other)?
4.  Who must receive alerts and through which channel (dashboard, e-mail, SMS, chat)?
5.  What alert thresholds do you use now?
6.  How important is the explanation of a prediction (1–5)?
7.  Which reports or dashboards do you produce for decision-makers?
8.  What are your data-retention and data-sharing rules?
9.  How many users and of which roles will use the system?
10. What would make you trust an automated warning?

# 10. Conclusion

Hadoop/HDFS for durable storage, Spark and Kafka for processing, Hive/Impala for SQL, MongoDB for flexible documents and explainable tree-based ML give the best balance of scalability, cost and usability for a climate agency’s monitoring platform.

# References

Dean & Ghemawat (2008); Shvachko et al. (2010); Zaharia et al. (2016); Marz & Warren (2015); Rolnick et al. (2022); Reichstein et al. (2019); Lam et al. (2023); Bi et al. (2023) – full details in the Literature Review.
