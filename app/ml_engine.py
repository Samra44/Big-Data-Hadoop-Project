"""EarthScape ML engine – trained AT RUNTIME on this machine, versioned, refreshed with the latest data.

Models
  1. forecast   – next-day mean temperature per station (regression, lag + seasonal features)
  2. event      – extreme-event classifier (none / heatwave / flood / storm / smog)
  3. anomaly    – IsolationForest on climatology-standardised readings + z-score rules
  4. trends     – warming trend per station (°C per decade) and CO2 growth (ppm/yr)
  5. seasonal   – 12-month regional temperature outlook (trend + seasonality regression)
Missing values are handled by median imputation inside every pipeline and forward-fill for lag features.
"""
import os, glob, json, pickle, threading, time, datetime
import numpy as np, pandas as pd, sklearn
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import Ridge, LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, HistGradientBoostingRegressor, HistGradientBoostingClassifier, IsolationForest
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.metrics import mean_absolute_error, r2_score, f1_score, accuracy_score, classification_report
import config

METRICS = ["temperature_c","temp_max_c","temp_min_c","humidity_pct","precipitation_mm","wind_speed_kmh","pressure_hpa",
           "co2_ppm","pm25_ugm3","ndvi","land_surface_temp_c","soil_moisture_pct"]
EVENT_FEATS = METRICS + ["temp_dev","precip_dev","wind_dev","pm25_dev","doy_sin","doy_cos","elevation_m","latitude"]
FC_NUM = ["t_lag1","t_lag2","t_lag3","t_lag7","t_roll7","humidity_pct","pressure_hpa","wind_speed_kmh","precipitation_mm",
          "doy_sin","doy_cos","year","elevation_m","latitude"]
FC_CAT = ["climate_zone"]
ANOM_FEATS = ["temp_dev","precip_dev","wind_dev","pm25_dev","hum_dev","press_dev"]
os.makedirs(config.MODEL_DIR, exist_ok=True)
state = {"bundle": None, "training": False, "progress": "", "last_error": None}
_lock = threading.Lock()

# ---------------------------------------------------------------- feature engineering
def clean(df):
    df = df.copy()
    for c in METRICS + ["latitude", "longitude", "elevation_m"]:
        df[c] = pd.to_numeric(df[c], errors="coerce") if c in df else np.nan
    df["date"] = pd.to_datetime(df.get("date", pd.Timestamp.today()), errors="coerce").fillna(pd.Timestamp.today().normalize())
    for c in ["station_id", "station_name", "region", "climate_zone", "source"]:
        if c not in df: df[c] = None
    doy = df.date.dt.day_of_year
    df["doy_sin"], df["doy_cos"] = np.sin(2*np.pi*doy/365), np.cos(2*np.pi*doy/365)
    df["year"] = df.date.dt.year; df["month"] = df.date.dt.month
    return df

def climatology(df):
    """Mean/std of each metric per station and month = what is 'normal' for that place and season."""
    g = df.groupby(["station_id", "month"])
    return {"mean": g[METRICS].mean(), "std": g[METRICS].std().fillna(1).replace(0, 1),
            "global_mean": df.groupby("month")[METRICS].mean(), "global_std": df.groupby("month")[METRICS].std().fillna(1)}

def add_deviation(df, clim):
    df = df.copy()
    key = pd.MultiIndex.from_arrays([df.station_id.fillna("?"), df.month])
    mu = clim["mean"].reindex(key).reset_index(drop=True); sd = clim["std"].reindex(key).reset_index(drop=True)
    gmu = clim["global_mean"].reindex(df.month).reset_index(drop=True); gsd = clim["global_std"].reindex(df.month).reset_index(drop=True)
    mu = mu.fillna(gmu); sd = sd.fillna(gsd).replace(0, 1)
    for m, short in [("temperature_c","temp"),("precipitation_mm","precip"),("wind_speed_kmh","wind"),("pm25_ugm3","pm25"),
                     ("humidity_pct","hum"),("pressure_hpa","press")]:
        df[f"{short}_dev"] = ((df[m].reset_index(drop=True) - mu[m]) / sd[m]).values
    return df

def lag_features(df):
    df = df.sort_values(["station_id", "date"]).copy()
    g = df.groupby("station_id")["temperature_c"]
    t = g.transform(lambda s: s.ffill())
    df["_t"] = t
    gg = df.groupby("station_id")["_t"]
    df["t_lag1"] = df["_t"]; df["t_lag2"] = gg.shift(1); df["t_lag3"] = gg.shift(2); df["t_lag7"] = gg.shift(6)
    df["t_roll7"] = gg.transform(lambda s: s.rolling(7, min_periods=1).mean())
    df["target_next"] = gg.shift(-1)
    return df.drop(columns="_t")

def _num_pipe(cols):
    return ColumnTransformer([("n", Pipeline([("i", SimpleImputer(strategy="median")), ("s", StandardScaler())]), cols)])

# ---------------------------------------------------------------- training
def train(df, reason="manual"):
    t0 = time.time(); M = {}
    df = clean(df); clim = climatology(df); df = add_deviation(df, clim)
    df = df.sort_values("date"); cut = df.date.quantile(0.85)        # time-based hold-out (no future leakage)
    tr, te = df[df.date <= cut], df[df.date > cut]
    tscv = TimeSeriesSplit(n_splits=config.CV_FOLDS)

    # 1. next-day temperature forecast
    state["progress"] = "Forecast model: comparing Ridge, RandomForest, HistGradientBoosting, Deep MLP…"
    L = lag_features(df).dropna(subset=["target_next", "t_lag1"]); L = L.sort_values("date")
    Ltr, Lte = L[L.date <= cut], L[L.date > cut]
    prep = lambda: ColumnTransformer([("n", Pipeline([("i", SimpleImputer(strategy="median")), ("s", StandardScaler())]), FC_NUM),
                                      ("c", OneHotEncoder(handle_unknown="ignore"), FC_CAT)])
    cands = {"Ridge": Ridge(alpha=1.0),
             "RandomForest": RandomForestRegressor(n_estimators=120, max_depth=14, min_samples_leaf=5, n_jobs=config.N_JOBS, random_state=42),
             "HistGradientBoosting": HistGradientBoostingRegressor(max_iter=250, learning_rate=0.08, random_state=42),
             "DeepMLP (64-32-16)": MLPRegressor(hidden_layer_sizes=(64, 32, 16), activation="relu", alpha=1e-3, learning_rate_init=2e-3,
                                               max_iter=200, early_stopping=True, n_iter_no_change=10, random_state=42)}
    sub = Ltr.iloc[-min(len(Ltr), 20000):]
    cv = {k: round(float(-cross_val_score(Pipeline([("p", prep()), ("m", v)]), sub[FC_NUM + FC_CAT], sub.target_next,
                                          cv=tscv, scoring="neg_mean_absolute_error", n_jobs=config.N_JOBS).mean()), 3) for k, v in cands.items()}
    best = min(cv, key=cv.get)
    fc = Pipeline([("p", prep()), ("m", cands[best])]).fit(Ltr[FC_NUM + FC_CAT], Ltr.target_next)
    pred = fc.predict(Lte[FC_NUM + FC_CAT]); persist = Lte.t_lag1
    M["forecast"] = {"cv_mae": cv, "best": best, "test_mae": round(float(mean_absolute_error(Lte.target_next, pred)), 3),
                     "test_r2": round(float(r2_score(Lte.target_next, pred)), 3),
                     "persistence_mae": round(float(mean_absolute_error(Lte.target_next, persist.fillna(persist.mean()))), 3)}

    # 2. extreme-event classifier
    state["progress"] = "Event classifier: comparing RandomForest, HistGradientBoosting, Deep MLP…"
    ec = {"RandomForest": RandomForestClassifier(n_estimators=200, min_samples_leaf=2, class_weight="balanced", n_jobs=config.N_JOBS, random_state=42),
          "HistGradientBoosting": HistGradientBoostingClassifier(max_iter=200, class_weight="balanced", random_state=42),
          "DeepMLP (128-64-32)": MLPClassifier(hidden_layer_sizes=(128, 64, 32), activation="relu", alpha=1e-3, learning_rate_init=2e-3,
                                               max_iter=200, early_stopping=True, n_iter_no_change=10, random_state=42)}
    sub = tr.iloc[-min(len(tr), 20000):]
    ecv = {k: round(float(cross_val_score(Pipeline([("p", _num_pipe(EVENT_FEATS)), ("m", v)]), sub[EVENT_FEATS], sub.event_type,
                                          cv=tscv, scoring="f1_macro", n_jobs=config.N_JOBS).mean()), 4) for k, v in ec.items()}
    ebest = max(ecv, key=ecv.get)
    ev = Pipeline([("p", _num_pipe(EVENT_FEATS)), ("m", ec[ebest])]).fit(tr[EVENT_FEATS], tr.event_type)
    ep = ev.predict(te[EVENT_FEATS])
    rep = classification_report(te.event_type, ep, output_dict=True, zero_division=0)
    M["event"] = {"cv_f1_macro": ecv, "best": ebest, "test_accuracy": round(float(accuracy_score(te.event_type, ep)), 4),
                  "test_f1_macro": round(float(f1_score(te.event_type, ep, average="macro")), 4),
                  "per_class_f1": {k: round(v["f1-score"], 3) for k, v in rep.items() if k in ev.classes_}}

    # 3. anomaly detection
    state["progress"] = "Anomaly detector…"
    iso = Pipeline([("i", SimpleImputer(strategy="median")), ("m", IsolationForest(n_estimators=200, contamination=0.03, random_state=42))]).fit(tr[ANOM_FEATS])
    state["progress"] = "Deep autoencoder (anomaly) …"
    Xa = tr[ANOM_FEATS].clip(-6, 6)
    imp = Pipeline([("i", SimpleImputer(strategy="median")), ("s", StandardScaler())]).fit(Xa)
    Z = imp.transform(Xa); net = MLPRegressor(hidden_layer_sizes=(32, 8, 32), activation="tanh", max_iter=150, early_stopping=True, random_state=42).fit(Z, Z)
    err = ((net.predict(Z) - Z) ** 2).mean(1); ae_thr = float(np.quantile(err, 0.975))
    autoenc = {"prep": imp, "net": net, "threshold": ae_thr}
    ap = combined_anomaly(iso, te, autoenc)[0]
    tp = int(((ap == 1) & (te.is_anomaly == 1)).sum())
    M["anomaly"] = {"flagged_test": int(ap.sum()), "true_anomalies_test": int(te.is_anomaly.sum()),
                    "method": "IsolationForest ∧ Deep Autoencoder (32-8-32) ∨ |z|>4", "precision": round(float(tp / max(ap.sum(), 1)), 3), "recall": round(float(tp / max(te.is_anomaly.sum(), 1)), 3)}

    # 4. trends + correlation
    state["progress"] = "Trend & correlation analysis…"
    ann = df.groupby(["station_id", "year"])[["temperature_c", "co2_ppm", "precipitation_mm", "ndvi"]].mean().reset_index()
    trends = {}
    for s, g in ann.groupby("station_id"):
        if len(g) >= 3:
            sl = np.polyfit(g.year, g.temperature_c, 1)[0]; co = np.polyfit(g.year, g.co2_ppm, 1)[0]
            trends[s] = {"temp_c_per_decade": round(float(sl * 10), 2), "co2_ppm_per_year": round(float(co), 2)}
    M["trends_mean_c_per_decade"] = round(float(np.mean([v["temp_c_per_decade"] for v in trends.values()])), 2) if trends else None

    # 5. seasonal regional outlook
    mon = df.assign(t=(df.year - df.year.min()) * 12 + df.month).groupby(["region", "t", "month"]).temperature_c.mean().reset_index()
    seasonal = {}
    for r, g in mon.groupby("region"):
        X = np.c_[g.t, np.sin(2*np.pi*g.month/12), np.cos(2*np.pi*g.month/12)]
        seasonal[r] = LinearRegression().fit(X, g.temperature_c)
    M["seasonal_regions"] = list(seasonal)

    v = _next_version()
    b = {"version": v, "trained_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "reason": reason, "n_rows": int(len(df)),
         "train_seconds": round(time.time() - t0, 1), "date_range": [str(df.date.min().date()), str(df.date.max().date())],
         "forecast_model": fc, "event_model": ev, "anomaly_model": iso, "autoencoder": autoenc, "seasonal_model": seasonal, "climatology": clim,
         "trends": trends, "t0_year": int(df.year.min()), "last_t": int(mon.t.max()), "last_date": str(df.date.max().date()),
         "metrics": M, "runtime": {**config.RUNTIME, "sklearn": sklearn.__version__}}
    pickle.dump(b, open(os.path.join(config.MODEL_DIR, f"v{v}.pkl"), "wb"))
    meta = {k: b[k] for k in ["version","trained_at","reason","n_rows","train_seconds","date_range","metrics","runtime"]}
    json.dump(meta, open(os.path.join(config.MODEL_DIR, f"v{v}.json"), "w"), indent=2, default=str)
    with _lock: state["bundle"] = b
    state["progress"] = f"Model v{v} ready ({b['train_seconds']} s)"
    return b

def ae_error(autoenc, df):
    Z = autoenc["prep"].transform(df[ANOM_FEATS].clip(-6, 6)); return ((autoenc["net"].predict(Z) - Z) ** 2).mean(1)

def combined_anomaly(iso, df, autoenc=None):
    """Ensemble: Isolation Forest + deep autoencoder reconstruction error (2 of 2) OR extreme z-score."""
    score = -iso.decision_function(df[ANOM_FEATS])          # higher = more unusual
    z = df[ANOM_FEATS].abs().max(axis=1).fillna(0).values
    iso_f = iso.predict(df[ANOM_FEATS]) == -1
    if autoenc is not None:
        ae_f = ae_error(autoenc, df) > autoenc["threshold"]; flag = ((iso_f & ae_f) | (z > 4)).astype(int)
    else: flag = (iso_f | (z > 4)).astype(int)
    return flag, np.round(score, 3), np.round(z, 2)

def train_async(loader, reason):
    if state["training"]: return False
    def run():
        state["training"] = True; state["last_error"] = None
        try: train(loader(), reason)
        except Exception as e: state["last_error"] = repr(e); state["progress"] = "Training failed"
        finally: state["training"] = False
    threading.Thread(target=run, daemon=True).start(); return True

# ---------------------------------------------------------------- registry
def _versions(): return sorted(int(os.path.basename(p)[1:-4]) for p in glob.glob(os.path.join(config.MODEL_DIR, "v*.pkl")))
def _next_version(): v = _versions(); return v[-1] + 1 if v else 1
def list_versions():
    return [json.load(open(os.path.join(config.MODEL_DIR, f"v{v}.json"))) for v in reversed(_versions())
            if os.path.exists(os.path.join(config.MODEL_DIR, f"v{v}.json"))]
def load_latest_compatible():
    for v in reversed(_versions()):
        try:
            b = pickle.load(open(os.path.join(config.MODEL_DIR, f"v{v}.pkl"), "rb"))
            if b["runtime"]["sklearn"] == sklearn.__version__:
                state["bundle"] = b; return b
        except Exception: continue
    return None
def activate(v):
    b = pickle.load(open(os.path.join(config.MODEL_DIR, f"v{v}.pkl"), "rb"))
    if b["runtime"]["sklearn"] != sklearn.__version__: raise ValueError("Trained with another scikit-learn version – retrain instead.")
    state["bundle"] = b; return b
def bundle(): return state["bundle"]

# ---------------------------------------------------------------- inference
def score(df):
    """Score raw readings: event class + probability, anomaly flag/score. Handles missing columns/values."""
    b = bundle(); raw = df.reset_index(drop=True); d = add_deviation(clean(raw), b["climatology"])
    proba = b["event_model"].predict_proba(d[EVENT_FEATS]); cls = b["event_model"].classes_
    out = raw.copy()
    out["pred_event"] = cls[proba.argmax(1)]
    none_idx = list(cls).index("none") if "none" in cls else None
    out["event_prob"] = np.round(1 - proba[:, none_idx] if none_idx is not None else proba.max(1), 3)
    flag, s, z = combined_anomaly(b["anomaly_model"], d, b.get("autoencoder"))
    out["pred_anomaly"], out["anomaly_score"], out["max_zscore"] = flag, s, z
    out["temp_dev"] = np.round(d["temp_dev"].values, 2)
    out["model_version"] = b["version"]
    return out

def forecast_next(history):
    """history: recent readings of ONE station (≥1 row). Returns next-day temperature forecast."""
    b = bundle(); h = clean(history).sort_values("date")
    L = lag_features(h).iloc[[-1]].copy()
    for c in ["t_lag2", "t_lag3", "t_lag7"]:
        L[c] = L[c].fillna(L["t_lag1"])
    nd = L.date.iloc[0] + pd.Timedelta(days=1); L["doy_sin"] = np.sin(2*np.pi*nd.day_of_year/365); L["doy_cos"] = np.cos(2*np.pi*nd.day_of_year/365)
    return round(float(b["forecast_model"].predict(L[FC_NUM + FC_CAT])[0]), 1), str(nd.date())

def seasonal_outlook(months=12):
    b = bundle(); res = {}; last = pd.Timestamp(b["last_date"]); labels = []
    for i in range(1, months + 1):
        m = (last + pd.DateOffset(months=i)); labels.append(m.strftime("%b %Y"))
    for r, lr in b["seasonal_model"].items():
        ts = [b["last_t"] + i for i in range(1, months + 1)]; ms = [(last + pd.DateOffset(months=i)).month for i in range(1, months + 1)]
        X = np.c_[ts, np.sin(2*np.pi*np.array(ms)/12), np.cos(2*np.pi*np.array(ms)/12)]
        res[r] = [round(float(v), 1) for v in lr.predict(X)]
    return labels, res

def explain_event(row):
    """Which readings drive the extreme-event probability (replace each with the station's normal value)."""
    b = bundle(); base = add_deviation(clean(pd.DataFrame([row])), b["climatology"])
    cls = list(b["event_model"].classes_); ni = cls.index("none")
    p0 = 1 - b["event_model"].predict_proba(base[EVENT_FEATS])[0, ni]; out = []
    month = int(base.month.iat[0]); sid = row.get("station_id")
    try: normal = b["climatology"]["mean"].loc[(sid, month)]
    except KeyError: normal = b["climatology"]["global_mean"].loc[month]
    for m in ["temperature_c","precipitation_mm","wind_speed_kmh","pm25_ugm3","humidity_pct","pressure_hpa","soil_moisture_pct"]:
        alt = dict(row); alt[m] = float(normal[m]); a = add_deviation(clean(pd.DataFrame([alt])), b["climatology"])
        p = 1 - b["event_model"].predict_proba(a[EVENT_FEATS])[0, ni]
        out.append({"feature": m, "value": row.get(m), "normal": round(float(normal[m]), 1), "impact": round(float(p0 - p) * 100, 1)})
    return sorted(out, key=lambda x: -abs(x["impact"]))

def psi(q, actual):
    a = pd.to_numeric(pd.Series(actual), errors="coerce").dropna()
    if len(a) < 30: return None
    edges = np.unique(q)
    if len(edges) < 3: return 0.0
    e = np.full(len(edges) - 1, 1 / (len(edges) - 1)); h = np.histogram(np.clip(a, edges[0], edges[-1]), bins=edges)[0] / len(a)
    h = np.where(h == 0, 1e-4, h); return round(float(np.sum((h - e) * np.log(h / e))), 3)
