---
date: October 2026
subtitle: Blog Paper
title: "From Sensors to Decisions: How EarthScape Turns Climate Big Data into Early Warnings"
---

Every day, satellites, weather stations and air-quality sensors produce millions of numbers about our planet. Most of them are never looked at. For a climate agency, the real challenge isn’t collecting data any more – it’s turning that flood of data into a warning that reaches the right person before the heatwave, the flash flood or the smog arrives.

## The problem with climate data

Climate data is big (years of daily readings from many places), varied (CSV logs from stations, JSON from IoT sensors, NetCDF grids from satellites) and fast (sensors report continuously). It is also messy: sensors fail, satellite passes are blocked by clouds, and a broken thermometer can report 50 °C in January.

## What we built

EarthScape is a full platform for a climate agency:

1.  **Ingest anything** – files in five formats, a REST API for live sensors and a streaming pipeline (Kafka → Spark).
2.  **Store it safely** – HDFS keeps three copies of every block and organises data by source, year, month and region, so queries only read the folders they need.
3.  **Process in parallel** – MapReduce and Spark summarise years of readings across many machines.
4.  **Learn from it** – machine-learning models forecast tomorrow’s temperature, recognise heatwaves, floods, storms and smog, and flag readings that don’t make sense.
5.  **Act on it** – configurable alert rules push notifications to dashboards, e-mail or chat in real time.

## The trick that makes the models work: “normal for here, normal for now”

45 °C is normal in Sukkur in June but alarming in Swat. Instead of feeding raw values to the models, EarthScape first computes a *climatology* – the typical value for every station and calendar month – and measures how unusual each reading is (a z-score). The heatwave classifier, the anomaly detector and the dashboard’s “vs normal” card all build on this one idea.

## Results

On a full unseen year of data (2024), the extreme-event classifier reached a macro-F1 of **0.91**, the next-day temperature forecast was off by about **1.7 °C** on average, and the anomaly detector caught most sensor faults with about **79%** precision. Across all stations the data shows warming of roughly **0.4 °C per decade**, moving with rising CO₂.

## Models that keep up

Climate is changing, so a model trained once will slowly go stale. EarthScape watches incoming data for *drift*, retrains itself automatically after a set number of new readings, keeps every version and lets an analyst roll back with one click. Each prediction comes with a plain explanation – for example, “extreme temperature +62 points, low humidity +8 points”.

## Why it matters

Early warnings save lives. A platform that can say *“Multan, tomorrow, 47 °C, heatwave probability 96%”* and send it automatically to the people who run hospitals and schools is the difference between data and protection.

*EarthScape is an Aptech eProject built with Hadoop, Spark, Hive/Impala, Kafka, MongoDB, Python, scikit-learn, Flask and Tableau.*
