"""Sends simulated sensor readings to Kafka topic 'climate-readings' (pip install kafka-python)."""
import json, time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data"))
from kafka import KafkaProducer
from generate_data import live_record, STATIONS
import pandas as pd
p = KafkaProducer(bootstrap_servers="localhost:9092", value_serializer=lambda v: json.dumps(v).encode())
day = pd.Timestamp("2024-01-01"); i = 0
while True:
    r = live_record(i % len(STATIONS), day, seed=i).iloc[0]
    p.send("climate-readings", {k: (None if pd.isna(v) else v) for k, v in r[["station_id", "date", "temperature_c", "precipitation_mm", "wind_speed_kmh", "pm25_ugm3"]].items()})
    i += 1; day += pd.Timedelta(days=1) if i % len(STATIONS) == 0 else pd.Timedelta(0); time.sleep(0.5)
