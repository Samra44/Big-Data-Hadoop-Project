"""Synthetic but physically plausible climate dataset for EarthScape Climate Agency.
Sources simulated: weather stations, environmental sensors (CO2, PM2.5) and satellite products (NDVI, land-surface temp).
Includes seasonality, warming trend, regional climate, injected extreme events, sensor faults and missing values."""
import numpy as np, pandas as pd, os

STATIONS = [  # id, name, region, lat, lon, elevation_m, base_temp, temp_amp, rain_base, climate
    ("ST01","Karachi","Sindh",24.86,67.01,8,26.5,6.5,0.6,"arid-coastal"),
    ("ST02","Hyderabad","Sindh",25.40,68.37,13,28.0,9.0,0.4,"arid"),
    ("ST03","Sukkur","Sindh",27.70,68.86,67,27.5,11.0,0.3,"arid"),
    ("ST04","Lahore","Punjab",31.55,74.34,217,24.5,10.5,1.7,"semi-arid"),
    ("ST05","Multan","Punjab",30.20,71.47,122,26.5,11.0,0.6,"arid"),
    ("ST06","Faisalabad","Punjab",31.45,73.13,184,25.0,10.5,1.0,"semi-arid"),
    ("ST07","Islamabad","Federal",33.68,73.05,540,21.5,9.5,3.2,"humid-subtropical"),
    ("ST08","Peshawar","Khyber Pakhtunkhwa",34.01,71.58,331,23.0,10.0,1.4,"semi-arid"),
    ("ST09","Swat","Khyber Pakhtunkhwa",35.22,72.43,980,17.0,9.0,3.0,"temperate"),
    ("ST10","Quetta","Balochistan",30.18,66.97,1680,16.5,11.5,0.7,"cold-arid"),
    ("ST11","Gwadar","Balochistan",25.12,62.33,10,26.0,5.0,0.3,"arid-coastal"),
    ("ST12","Gilgit","Gilgit-Baltistan",35.92,74.31,1500,15.5,11.5,0.4,"cold-desert"),
]
COLS = ["record_id","station_id","station_name","region","latitude","longitude","elevation_m","climate_zone","date",
        "temperature_c","temp_max_c","temp_min_c","humidity_pct","precipitation_mm","wind_speed_kmh","pressure_hpa",
        "co2_ppm","pm25_ugm3","ndvi","land_surface_temp_c","soil_moisture_pct","source","event_type","is_anomaly"]

def generate(start="2016-01-01", end="2024-12-31", seed=1, missing=0.02):
    rng = np.random.default_rng(seed); days = pd.date_range(start, end, freq="D"); rows = []
    for sid, name, region, lat, lon, elev, bt, amp, rain, zone in STATIONS:
        n = len(days); doy = days.day_of_year.values; yrs = (days.year.values - 2016) + doy / 365
        season = -np.cos(2 * np.pi * (doy - 15) / 365)                      # coldest mid-Jan, hottest mid-July
        temp = bt + amp * season + 0.035 * yrs + rng.normal(0, 1.4, n)        # ~0.35 °C/decade warming
        monsoon = np.exp(-((doy - 210) / 28) ** 2)                           # Jul–Aug monsoon
        p_rain = np.clip(0.06 + 0.45 * monsoon * (rain / 2), 0, .9)
        precip = np.where(rng.random(n) < p_rain, rng.gamma(1.3, 4 + 10 * rain * monsoon + 2), 0)
        hum = np.clip(45 + 25 * monsoon + (15 if "coastal" in zone else 0) - 0.8 * (temp - bt) + rng.normal(0, 6, n), 5, 100)
        wind = np.clip(rng.gamma(2.2, 4.5, n) + (6 if "coastal" in zone else 0), 0, None)
        press = 1013 - elev * 0.11 - 4 * season + rng.normal(0, 2.5, n)
        co2 = 404 + 2.4 * yrs + 3 * np.sin(2 * np.pi * doy / 365) + rng.normal(0, 1.2, n) + (6 if region in ("Punjab", "Sindh") else 0)
        pm = np.clip(rng.lognormal(3.6 if region == "Punjab" else 3.2, .45, n) * (1 + 0.9 * (season < -0.6) * (region == "Punjab")), 3, None)
        ndvi = np.clip(0.18 + 0.12 * monsoon + (0.25 if zone in ("temperate", "humid-subtropical") else 0) - 0.002 * yrs + rng.normal(0, .03, n), -0.1, 0.95)
        soil = np.clip(15 + 2.2 * pd.Series(precip).rolling(7, center=True, min_periods=1).sum().values ** .6 + rng.normal(0, 3, n), 1, 60)
        event = np.array(["none"] * n, dtype=object); anom = np.zeros(n, int)
        if n < 60:   # short windows (live readings): extremes are injected by live_record instead
            ev_loops = False
        else:
            ev_loops = True
        # heatwaves: 3-6 day spells in summer
        for _ in range(0 if not ev_loops else int(rng.integers(6, 12))):
            s = int(rng.choice(np.where((doy > 120) & (doy < 200))[0])); L = int(rng.integers(3, 7))
            temp[s:s + L] += rng.uniform(5, 8); hum[s:s + L] -= 10; event[s:s + L] = "heatwave"
        # extreme rain / floods in monsoon
        for _ in range(0 if not ev_loops else int(rng.integers(3, 8))):
            s = int(rng.choice(np.where((doy > 185) & (doy < 245))[0])); L = int(rng.integers(1, 4))
            precip[s:s + L] += rng.uniform(60, 180) * (0.5 + rain / 3); hum[s:s + L] = np.clip(hum[s:s + L] + 20, 0, 100)
            soil[s:s + L] = np.clip(soil[s:s + L] + 25, 0, 60); event[s:s + L] = "flood"
        # windstorms
        for _ in range(0 if not ev_loops else int(rng.integers(3, 7))):
            s = int(rng.integers(0, n)); wind[s] += rng.uniform(45, 80); press[s] -= rng.uniform(8, 15); event[s] = "storm"
        # smog episodes (winter, Punjab heavy)
        for _ in range(0 if not ev_loops else int(rng.integers(2, 10 if region == "Punjab" else 4))):
            s = int(rng.choice(np.where((doy > 305) | (doy < 30))[0])); L = int(rng.integers(2, 6))
            pm[s:s + L] *= rng.uniform(3, 5); event[s:s + L] = "smog"
        anom[event != "none"] = 1
        # sensor faults (spikes not linked to an event)
        f = rng.choice(n, int(n * 0.003), replace=False); temp[f] += rng.choice([-25, 25], len(f)); anom[f] = 1
        tmax = temp + rng.uniform(4, 8, n) + (2 if "arid" in zone else 0); tmin = temp - rng.uniform(4, 8, n)
        lst = temp + 3 + 4 * (1 - ndvi) + rng.normal(0, 1.5, n)
        df = pd.DataFrame({"station_id": sid, "station_name": name, "region": region, "latitude": lat, "longitude": lon,
                           "elevation_m": elev, "climate_zone": zone, "date": days.strftime("%Y-%m-%d"),
                           "temperature_c": temp.round(1), "temp_max_c": tmax.round(1), "temp_min_c": tmin.round(1),
                           "humidity_pct": hum.round(1), "precipitation_mm": precip.round(1), "wind_speed_kmh": wind.round(1),
                           "pressure_hpa": press.round(1), "co2_ppm": co2.round(1), "pm25_ugm3": pm.round(1), "ndvi": ndvi.round(3),
                           "land_surface_temp_c": lst.round(1), "soil_moisture_pct": soil.round(1),
                           "source": rng.choice(["weather_station", "env_sensor", "satellite"], n, p=[.6, .25, .15]),
                           "event_type": event, "is_anomaly": anom})
        rows.append(df)
    df = pd.concat(rows, ignore_index=True)
    # missing values (sensor dropouts / cloud-covered satellite passes)
    for c, rate in [("humidity_pct", missing), ("wind_speed_kmh", missing), ("pm25_ugm3", missing * 2),
                    ("ndvi", missing * 3), ("land_surface_temp_c", missing * 3), ("soil_moisture_pct", missing)]:
        df.loc[rng.random(len(df)) < rate, c] = np.nan
    df.insert(0, "record_id", [f"R{seed}{i:07d}" for i in range(len(df))])
    return df[COLS]

def live_record(station_idx=None, date=None, seed=None):
    """One realistic real-time reading for the live stream / simulator."""
    rng = np.random.default_rng(seed); st = STATIONS[station_idx if station_idx is not None else int(rng.integers(len(STATIONS)))]
    date = pd.Timestamp(date or pd.Timestamp.today().normalize())
    g = generate(date.strftime("%Y-%m-%d"), date.strftime("%Y-%m-%d"), int(rng.integers(1e9)), 0.01)
    g = g[g.station_id == st[0]].copy()
    if rng.random() < 0.06:  # occasional extreme reading
        k = rng.choice(["heatwave", "flood", "storm", "smog"])
        if k == "heatwave": g["temperature_c"] += 7; g["temp_max_c"] += 7
        if k == "flood": g["precipitation_mm"] += 120
        if k == "storm": g["wind_speed_kmh"] += 60
        if k == "smog": g["pm25_ugm3"] *= 4
        g["event_type"] = k; g["is_anomaly"] = 1
    return g

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    s = generate("2016-01-01", "2023-12-31", 1); s.to_csv("sample_dataset.csv", index=False)
    t = generate("2024-01-01", "2024-12-31", 2); t.to_csv("testing_dataset.csv", index=False)
    s.head(500).to_json("sample_stream.json", orient="records", indent=1)
    pd.DataFrame([x[:9] for x in STATIONS], columns=["station_id","station_name","region","latitude","longitude",
                 "elevation_m","base_temp","temp_amp","rain_index"]).to_csv("stations.csv", index=False)
    print(len(s), len(t), s.event_type.value_counts().to_dict())
