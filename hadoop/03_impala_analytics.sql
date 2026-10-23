-- EarthScape – interactive analytics on Impala (run: impala-shell -f 03_impala_analytics.sql)
INVALIDATE METADATA earthscape.readings;  COMPUTE STATS earthscape.readings;
USE earthscape;

-- 1. Annual warming trend per region
SELECT region_name, year, ROUND(AVG(temperature_c),2) mean_temp, ROUND(AVG(co2_ppm),1) mean_co2
FROM readings GROUP BY region_name, year ORDER BY region_name, year;

-- 2. Climate anomalies: readings > 3 standard deviations from station/month normal
WITH clim AS (SELECT station_id, month, AVG(temperature_c) mu, STDDEV(temperature_c) sd FROM readings GROUP BY station_id, month)
SELECT r.station_id, r.obs_date, r.temperature_c, ROUND((r.temperature_c - c.mu)/c.sd,2) z
FROM readings r JOIN clim c ON r.station_id=c.station_id AND r.month=c.month
WHERE ABS((r.temperature_c - c.mu)/c.sd) > 3 ORDER BY z DESC LIMIT 100;

-- 3. Extreme events per year and type
SELECT year, event_type, COUNT(*) days FROM readings WHERE event_type <> 'none' GROUP BY year, event_type ORDER BY year;

-- 4. Correlation temperature vs CO2 / NDVI (Pearson via aggregates)
SELECT region_name,
  (AVG(temperature_c*co2_ppm) - AVG(temperature_c)*AVG(co2_ppm)) / (STDDEV_POP(temperature_c)*STDDEV_POP(co2_ppm)) corr_temp_co2,
  (AVG(land_surface_temp_c*ndvi) - AVG(land_surface_temp_c)*AVG(ndvi)) / (STDDEV_POP(land_surface_temp_c)*STDDEV_POP(ndvi)) corr_lst_ndvi
FROM readings WHERE ndvi IS NOT NULL GROUP BY region_name;

-- 5. Monsoon rainfall totals (Jul–Sep) per station and year
SELECT station_id, year, ROUND(SUM(precipitation_mm),0) monsoon_mm FROM readings WHERE month BETWEEN 7 AND 9 GROUP BY station_id, year ORDER BY year, monsoon_mm DESC;

-- 6. Hazardous air-quality days (PM2.5 >= 250) in winter
SELECT region_name, year, COUNT(*) hazardous_days FROM readings WHERE pm25_ugm3 >= 250 GROUP BY region_name, year ORDER BY hazardous_days DESC;
