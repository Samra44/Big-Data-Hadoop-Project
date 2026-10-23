---
date: October 2026
title: "Literature Review: Machine Learning and Big Data for Climate Analytics"
---

# 1. Introduction

This review summarises research relevant to EarthScape: big-data infrastructure, machine learning for weather and climate, anomaly detection, trend analysis and explainability.

# 2. Big-Data Foundations

- **Dean & Ghemawat (2008)** introduced MapReduce, a programming model that parallelises processing across commodity clusters with automatic fault tolerance – the basis of EarthScape’s monthly summary job.
- **Shvachko et al. (2010)** described HDFS: large blocks, replication and data locality, enabling reliable storage of multi-terabyte archives.
- **Zaharia et al. (2016)** presented Apache Spark as a unified engine for batch, streaming, SQL and ML with in-memory computation, outperforming disk-based MapReduce for iterative workloads.
- **Marz & Warren (2015)** formalised the Lambda architecture (batch, speed and serving layers), which EarthScape follows to combine historical climatology with live streams.
- **Faghmous & Kumar (2014)** argued that climate science needs data-driven methods that respect physical structure, spatio-temporal dependence and non-stationarity.

# 3. Machine Learning for Weather and Climate

- **Reichstein et al. (2019)** reviewed deep learning in Earth-system science and called for hybrid models combining process understanding with data-driven learning.
- **Rolnick et al. (2022)** surveyed how ML can help tackle climate change, highlighting forecasting, extreme-event detection and monitoring as high-impact areas.
- **Rasp et al. (2020)** released WeatherBench, a benchmark showing simple baselines (persistence, climatology, linear regression) must always be reported – a practice EarthScape follows with its persistence baseline.
- **Shi et al. (2015)** proposed ConvLSTM for precipitation nowcasting, capturing spatial and temporal patterns jointly.
- **Lam et al. (2023)** (GraphCast) and **Bi et al. (2023)** (Pangu-Weather) showed that ML models trained on reanalysis can match or exceed numerical weather prediction at medium range.
- **Lim & Zohren (2021)** surveyed deep-learning time-series forecasting, noting that well-engineered features and simpler models often remain competitive on small data.
- **Hochreiter & Schmidhuber (1997)** introduced the LSTM, the foundation of many sequence forecasters.

# 4. Ensemble Learning on Tabular Data

- **Breiman (2001)** – Random Forests: bagged decision trees with random feature selection; robust to noise and good for imbalanced classification with class weighting.
- **Friedman (2001)** – gradient boosting machines.
- **Ke et al. (2017)** – LightGBM’s histogram-based boosting, the design behind scikit-learn’s HistGradientBoosting.
- **Pedregosa et al. (2011)** – scikit-learn, the library used for all EarthScape models.

# 5. Anomaly Detection

- **Chandola, Banerjee & Kumar (2009)** categorised anomaly detection into statistical, distance, density and model-based methods and discussed contextual anomalies – values abnormal only in a given context, such as season and place, which motivates EarthScape’s station-month climatology.
- **Liu, Ting & Zhou (2008)** – Isolation Forest isolates anomalies with random partitioning in linear time, suitable for large sensor datasets.

# 6. Trend Detection

- **Mann (1945)** and **Kendall (1975)** – the non-parametric Mann-Kendall test for monotonic trends, standard in climatology (implemented in the R script).
- **IPCC (2021)**, AR6 WG I – the scientific assessment of observed warming and extremes that frames the problem.

# 7. Explainability

- **Lundberg & Lee (2017)** – SHAP values unify feature attribution methods. EarthScape uses a simpler counterfactual “replace with normal” attribution that stakeholders understand directly; SHAP is planned future work.

# 8. Research Gaps and How EarthScape Responds

| Gap                                            | EarthScape response                                    |
|------------------------------------------------|--------------------------------------------------------|
| Models built once and not updated              | Runtime retraining, drift monitoring, version registry |
| Research prototypes without operational alerts | Rule engine + ML-based alerts, notifications           |
| Black-box predictions                          | Per-prediction explanations                            |
| Separate tools for storage, ML and dashboards  | Integrated Lambda architecture                         |

# References

1.  Bi, K. et al. (2023). Accurate medium-range global weather forecasting with 3D neural networks. *Nature*, 619, 533–538.
2.  Breiman, L. (2001). Random Forests. *Machine Learning*, 45(1), 5–32.
3.  Chandola, V., Banerjee, A., & Kumar, V. (2009). Anomaly detection: a survey. *ACM Computing Surveys*, 41(3), 15.
4.  Dean, J., & Ghemawat, S. (2008). MapReduce: simplified data processing on large clusters. *Communications of the ACM*, 51(1), 107–113.
5.  Faghmous, J. H., & Kumar, V. (2014). A big data guide to understanding climate change. *Big Data*, 2(3), 155–163.
6.  Friedman, J. H. (2001). Greedy function approximation: a gradient boosting machine. *Annals of Statistics*, 29(5), 1189–1232.
7.  Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. *Neural Computation*, 9(8), 1735–1780.
8.  IPCC (2021). *Climate Change 2021: The Physical Science Basis*. Cambridge University Press.
9.  Ke, G. et al. (2017). LightGBM: a highly efficient gradient boosting decision tree. *NeurIPS 30*.
10. Kendall, M. G. (1975). *Rank Correlation Methods*. Griffin.
11. Lam, R. et al. (2023). Learning skillful medium-range global weather forecasting. *Science*, 382, 1416–1421.
12. Lim, B., & Zohren, S. (2021). Time-series forecasting with deep learning: a survey. *Phil. Trans. R. Soc. A*, 379.
13. Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. *Proc. IEEE ICDM*, 413–422.
14. Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *NeurIPS 30*.
15. Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13(3), 245–259.
16. Marz, N., & Warren, J. (2015). *Big Data: Principles and Best Practices of Scalable Realtime Data Systems*. Manning.
17. Pedregosa, F. et al. (2011). Scikit-learn: machine learning in Python. *JMLR*, 12, 2825–2830.
18. Rasp, S. et al. (2020). WeatherBench: a benchmark data set for data-driven weather forecasting. *JAMES*, 12(11).
19. Reichstein, M. et al. (2019). Deep learning and process understanding for data-driven Earth system science. *Nature*, 566, 195–204.
20. Rolnick, D. et al. (2022). Tackling climate change with machine learning. *ACM Computing Surveys*, 55(2), 1–96.
21. Shi, X. et al. (2015). Convolutional LSTM network: a machine learning approach for precipitation nowcasting. *NeurIPS 28*.
22. Shvachko, K. et al. (2010). The Hadoop Distributed File System. *Proc. IEEE MSST*.
23. Zaharia, M. et al. (2016). Apache Spark: a unified engine for big data processing. *Communications of the ACM*, 59(11), 56–65.
