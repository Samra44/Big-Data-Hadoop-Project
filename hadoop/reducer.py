#!/usr/bin/env python3
"""Hadoop Streaming REDUCER – monthly climate summary per station:
mean/min/max temperature, total rain, max wind, mean PM2.5, extreme-event days, heat-stress days (>=40 °C)."""
import sys
def flush(key, acc):
    if not key: return
    t = acc["t"]; pm = acc["pm"]
    print("\t".join([*key.split("|"), f"{sum(t)/len(t):.2f}" if t else "", f"{min(t):.1f}" if t else "", f"{max(t):.1f}" if t else "",
                     f"{sum(acc['rain']):.1f}", f"{max(acc['wind'] or [0]):.1f}", f"{sum(pm)/len(pm):.1f}" if pm else "",
                     str(acc["events"]), str(sum(1 for x in t if x >= 40))]))
cur, acc = None, None
for line in sys.stdin:
    key, val = line.rstrip("\n").split("\t"); t, rain, wind, pm, ev = val.split(",")
    if key != cur:
        flush(cur, acc); cur, acc = key, {"t": [], "rain": [], "wind": [], "pm": [], "events": 0}
    if t: acc["t"].append(float(t))
    if rain: acc["rain"].append(float(rain))
    if wind: acc["wind"].append(float(wind))
    if pm: acc["pm"].append(float(pm))
    acc["events"] += ev != "none"
flush(cur, acc)
