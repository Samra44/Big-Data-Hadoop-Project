"""External real-time data source (weather stations / IoT sensors) posting to the EarthScape REST API.
    python simulator.py --rate 2 --batch 12            # normal readings
    python simulator.py --rate 1 --batch 12 --drift    # progressive warming → shows drift + auto-retrain"""
import argparse, os, sys, time, requests, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
import config
from generate_data import live_record, STATIONS
p = argparse.ArgumentParser()
p.add_argument("--url", default=f"http://{config.HOST}:{config.PORT}/api/ingest")
p.add_argument("--rate", type=float, default=2); p.add_argument("--batch", type=int, default=12)
p.add_argument("--count", type=int, default=0); p.add_argument("--start", default="2024-01-01"); p.add_argument("--drift", action="store_true")
a = p.parse_args(); http = requests.Session(); http.trust_env = False; day = pd.Timestamp(a.start); i = 0
while a.count == 0 or i < a.count:
    recs = pd.concat([live_record(k % len(STATIONS), day, seed=int(time.time()*1000) % 2**31 + k) for k in range(a.batch)])
    recs["record_id"] = [f"SIM{int(time.time()*1000)}{k}" for k in range(len(recs))]
    if a.drift: recs["temperature_c"] += min(i / 50, 4); recs["temp_max_c"] += min(i / 50, 4)
    r = http.post(a.url, json=recs.astype(object).where(recs.notna(), None).to_dict("records"), headers={"X-API-Key": config.API_KEY}, timeout=60)
    ev = sum(x["pred_event"] != "none" for x in r.json()) if r.ok else "?"
    print(f"{day.date()} batch {i+1}: HTTP {r.status_code} · {len(recs)} readings · events {ev}")
    i += 1; day += pd.Timedelta(days=1); time.sleep(a.rate)
