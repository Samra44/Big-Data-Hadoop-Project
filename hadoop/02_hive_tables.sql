-- EarthScape – Hive / Impala schema (partitioned, columnar curated layer)
CREATE DATABASE IF NOT EXISTS earthscape;
USE earthscape;

-- Raw external table over the partitioned HDFS folders
CREATE EXTERNAL TABLE IF NOT EXISTS readings_raw (
  record_id STRING, station_id STRING, station_name STRING, region_name STRING, latitude DOUBLE, longitude DOUBLE,
  elevation_m DOUBLE, climate_zone STRING, obs_date STRING, temperature_c DOUBLE, temp_max_c DOUBLE, temp_min_c DOUBLE,
  humidity_pct DOUBLE, precipitation_mm DOUBLE, wind_speed_kmh DOUBLE, pressure_hpa DOUBLE, co2_ppm DOUBLE,
  pm25_ugm3 DOUBLE, ndvi DOUBLE, land_surface_temp_c DOUBLE, soil_moisture_pct DOUBLE, source_type STRING,
  event_type STRING, is_anomaly INT)
PARTITIONED BY (source STRING, year STRING, month STRING, region STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ',' STORED AS TEXTFILE
LOCATION '/earthscape/raw';
MSCK REPAIR TABLE readings_raw;               -- discover partitions

-- Curated Parquet table (compressed, columnar, fast for Impala)
CREATE TABLE IF NOT EXISTS readings (
  record_id STRING, station_id STRING, region_name STRING, obs_date DATE, temperature_c DOUBLE, humidity_pct DOUBLE,
  precipitation_mm DOUBLE, wind_speed_kmh DOUBLE, pressure_hpa DOUBLE, co2_ppm DOUBLE, pm25_ugm3 DOUBLE, ndvi DOUBLE,
  land_surface_temp_c DOUBLE, soil_moisture_pct DOUBLE, event_type STRING, is_anomaly INT)
PARTITIONED BY (year INT, month INT)
STORED AS PARQUET TBLPROPERTIES ('parquet.compression'='SNAPPY');

SET hive.exec.dynamic.partition.mode=nonstrict;
INSERT OVERWRITE TABLE readings PARTITION (year, month)
SELECT record_id, station_id, region_name, CAST(obs_date AS DATE), temperature_c,
       -- graceful handling of missing values: fall back to the station/month average
       COALESCE(humidity_pct, AVG(humidity_pct) OVER (PARTITION BY station_id, month)),
       precipitation_mm, COALESCE(wind_speed_kmh, AVG(wind_speed_kmh) OVER (PARTITION BY station_id, month)),
       pressure_hpa, co2_ppm, pm25_ugm3, ndvi, land_surface_temp_c, soil_moisture_pct, event_type, is_anomaly,
       CAST(year AS INT), CAST(month AS INT)
FROM readings_raw;

CREATE EXTERNAL TABLE IF NOT EXISTS stations (station_id STRING, station_name STRING, region STRING, latitude DOUBLE,
  longitude DOUBLE, elevation_m DOUBLE, base_temp DOUBLE, temp_amp DOUBLE, rain_index DOUBLE)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ',' LOCATION '/earthscape/curated' TBLPROPERTIES ('skip.header.line.count'='1');
