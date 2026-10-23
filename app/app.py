"""EarthScape Climate Agency – Big-Data Climate Analytics Platform (Flask).

Dynamic at runtime: models are trained on this machine at first start, every incoming reading
(upload, REST API, live stream) is scored immediately, alert rules fire in real time, dashboards
refresh themselves, models retrain in the background as new data arrives, and the database is
backed up (encrypted) on a schedule.
"""
import os, io, sys, time, json, sqlite3, functools, threading, datetime, collections, smtplib, urllib.request
from email.message import EmailMessage
import numpy as np, pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g, abort, Response, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import config, ml_engine as ml
sys.path.insert(0, config.DATA_DIR)
from generate_data import generate, live_record, STATIONS, COLS

try:
    import psutil
except ImportError:
    psutil = None
try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", MAX_CONTENT_LENGTH=200 * 1024 * 1024)
STORE_COLS = COLS + ["pred_event", "event_prob", "pred_anomaly", "anomaly_score", "max_zscore", "temp_dev",
                     "model_version", "ingest_source", "ingested_at"]
STARTED = time.time()
stream = {"running": False, "count": 0, "since_retrain": 0}
LIVE = collections.deque(maxlen=2000)        # sliding window of real-time readings (stream / API / simulator)
EWMA = {}                                    # exponentially weighted moving average temperature per station
req_times = collections.defaultdict(lambda: collections.deque(maxlen=200))
ROLES = ["admin", "analyst", "viewer"]
METRIC_LABELS = {"temperature_c": "Temperature (°C)", "temp_max_c": "Max temp (°C)", "temp_min_c": "Min temp (°C)",
                 "humidity_pct": "Humidity (%)", "precipitation_mm": "Precipitation (mm)", "wind_speed_kmh": "Wind (km/h)",
                 "pressure_hpa": "Pressure (hPa)", "co2_ppm": "CO₂ (ppm)", "pm25_ugm3": "PM2.5 (µg/m³)", "ndvi": "NDVI",
                 "land_surface_temp_c": "Land surface temp (°C)", "soil_moisture_pct": "Soil moisture (%)"}

def now(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ================================================================ database
def connect():
    con = config.db_connect(); con.row_factory = sqlite3.Row; return con
def db():
    if "db" not in g: g.db = connect()
    return g.db
@app.teardown_appcontext
def _close(_):
    d = g.pop("db", None)
    if d: d.close()

DEFAULT_RULES = [("temperature_c", ">=", 45, "Critical", "Extreme heat"), ("temperature_c", "<=", -15, "High", "Extreme cold"),
                 ("precipitation_mm", ">=", 100, "Critical", "Flash-flood rainfall"), ("wind_speed_kmh", ">=", 70, "High", "Wind storm"),
                 ("pm25_ugm3", ">=", 250, "High", "Hazardous air quality"), ("event_prob", ">=", 0.7, "High", "Model: extreme event likely"),
                 ("pred_anomaly", ">=", 1, "Medium", "Model: anomalous reading")]

def init_db():
    con = connect(); c = con.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, email TEXT, created TEXT);
    CREATE TABLE IF NOT EXISTS stations(station_id TEXT PRIMARY KEY, station_name TEXT, region TEXT, latitude REAL, longitude REAL, elevation_m REAL, climate_zone TEXT);
    CREATE TABLE IF NOT EXISTS alert_rules(id INTEGER PRIMARY KEY, metric TEXT, operator TEXT, threshold REAL, level TEXT, label TEXT, enabled INTEGER DEFAULT 1, region TEXT DEFAULT 'All');
    CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, station_id TEXT, region TEXT, date TEXT, rule TEXT, value REAL, level TEXT, created TEXT, acknowledged INTEGER DEFAULT 0, ack_by TEXT);
    CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY, channel TEXT, target TEXT, message TEXT, status TEXT, created TEXT);
    CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY, username TEXT, category TEXT, subject TEXT, message TEXT, status TEXT DEFAULT 'Open', reply TEXT, created TEXT);
    CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, job TEXT, records INTEGER, seconds REAL, detail TEXT, created TEXT);
    """)
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        for u, p, r in [("admin", "Admin@123", "admin"), ("analyst", "Analyst@123", "analyst"), ("viewer", "Viewer@123", "viewer")]:
            c.execute("INSERT INTO users(username,password,role,email,created) VALUES(?,?,?,?,?)", (u, generate_password_hash(p), r, f"{u}@earthscape.org", now()))
    if c.execute("SELECT COUNT(*) FROM stations").fetchone()[0] == 0:
        c.executemany("INSERT INTO stations VALUES(?,?,?,?,?,?,?)", [(s[0], s[1], s[2], s[3], s[4], s[5], s[9]) for s in STATIONS])
    if c.execute("SELECT COUNT(*) FROM alert_rules").fetchone()[0] == 0:
        c.executemany("INSERT INTO alert_rules(metric,operator,threshold,level,label) VALUES(?,?,?,?,?)", DEFAULT_RULES)
    con.commit()
    seed = None
    if not c.execute("SELECT name FROM sqlite_master WHERE name='readings'").fetchone():
        p = os.path.join(config.DATA_DIR, "sample_dataset.csv")
        seed = pd.read_csv(p) if os.path.exists(p) else generate("2016-01-01", "2023-12-31", 1)
    print(f"[EarthScape] Database: {config.DB_PATH}")
    if ml.load_latest_compatible() is None:
        print(f"[EarthScape] No model for this runtime (Python {config.RUNTIME['python']}) – training on this machine, please wait…")
        ml.train(seed if seed is not None else load_labelled(con), reason="first start on this machine")
    b = ml.bundle(); print(f"[EarthScape] Model v{b['version']} active (trained {b['trained_at']} on {b['n_rows']:,} readings)")
    if seed is not None:
        print("[EarthScape] Loading historical archive into the database…")
        store(seed, con, "historical_archive", alerts=False)
        c.executescript("CREATE INDEX IF NOT EXISTS ix_sd ON readings(station_id,date); CREATE INDEX IF NOT EXISTS ix_d ON readings(date);")
        _alerts_for(ml.score(seed[seed.date >= "2023-12-15"]), con)   # recent alerts so the demo has some
    con.close()

def load_labelled(con=None):
    return pd.read_sql("SELECT * FROM readings WHERE event_type IS NOT NULL", con or connect())

def _fill_station_meta(df, con):
    st = pd.read_sql("SELECT * FROM stations", con).set_index("station_id")
    for c in ["station_name", "region", "latitude", "longitude", "elevation_m", "climate_zone"]:
        if c not in df: df[c] = None
        df[c] = df[c].where(df[c].notna(), df.station_id.map(st[c]) if "station_id" in df else None)
    return df

def store(df, con, source, alerts=True):
    """Validate → score with the active model → store → evaluate alert rules → count towards auto-retrain."""
    if df is None or len(df) == 0: return pd.DataFrame()
    t0 = time.time(); df = df.copy()
    if "record_id" not in df: df["record_id"] = [f"{source[:3].upper()}{int(time.time()*1000)}{i}" for i in range(len(df))]
    df = _fill_station_meta(df, con)
    out = ml.score(df); out["ingest_source"] = source; out["ingested_at"] = now()
    for c in STORE_COLS:
        if c not in out: out[c] = None
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out[STORE_COLS].to_sql("readings", con, if_exists="append", index=False, chunksize=5000)
    n_alerts = _alerts_for(out, con) if alerts else 0
    if source in ("live_stream", "api_realtime"):
        ts = time.time()
        for r in out[["station_id", "station_name", "region", "date", "temperature_c", "precipitation_mm", "wind_speed_kmh",
                      "pm25_ugm3", "pred_event", "event_prob", "pred_anomaly", "anomaly_score"]].to_dict("records"):
            t = r["temperature_c"]
            if t is not None and t == t:
                EWMA[r["station_id"]] = round(0.3 * t + 0.7 * EWMA.get(r["station_id"], t), 2)
            LIVE.append({**{k: (None if isinstance(v, float) and v != v else v) for k, v in r.items()}, "ts": ts})
    sec = round(time.time() - t0, 3)
    con.execute("INSERT INTO jobs(job,records,seconds,detail,created) VALUES(?,?,?,?,?)",
                (f"ingest:{source}", len(out), sec, f"{n_alerts} alerts, model v{ml.bundle()['version']}", now()))
    con.commit()
    if source not in ("historical_archive", "noop"):
        stream["since_retrain"] += int(out["event_type"].notna().sum())
        if stream["since_retrain"] >= config.RETRAIN_EVERY and ml.train_async(load_labelled, f"auto: {stream['since_retrain']} new readings"):
            stream["since_retrain"] = 0
    return out

OPS = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b}
def _alerts_for(out, con):
    rules = con.execute("SELECT * FROM alert_rules WHERE enabled=1").fetchall(); rows = []
    for r in rules:
        if r["metric"] not in out: continue
        vals = pd.to_numeric(out[r["metric"]], errors="coerce")
        mask = OPS[r["operator"]](vals, r["threshold"]).fillna(False)
        if r["region"] and r["region"] != "All": mask &= out["region"] == r["region"]
        for i in np.where(mask)[0]:
            o = out.iloc[i]
            rows.append((o.station_id, o.region, str(o.date)[:10], f"{r['label']} ({METRIC_LABELS.get(r['metric'], r['metric'])} {r['operator']} {r['threshold']:g})",
                         float(vals.iat[i]), r["level"], now()))
    if rows:
        con.executemany("INSERT INTO alerts(station_id,region,date,rule,value,level,created) VALUES(?,?,?,?,?,?,?)", rows); con.commit()
        crit = [x for x in rows if x[5] in ("Critical", "High")]
        if crit: threading.Thread(target=notify, args=(crit[:20],), daemon=True).start()
    return len(rows)

def notify(rows):
    """Send real-time notifications on configured channels (e-mail, webhook). Always logged."""
    msg = "\n".join(f"[{r[5]}] {r[0]} {r[1]} {r[2]}: {r[3]} = {r[4]:.1f}" for r in rows)
    con = connect(); sent = []
    if config.SMTP_HOST and config.ALERT_EMAIL_TO:
        try:
            m = EmailMessage(); m["Subject"] = f"EarthScape alert: {len(rows)} event(s)"; m["From"] = config.SMTP_USER; m["To"] = config.ALERT_EMAIL_TO
            m.set_content(msg); s = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15); s.starttls()
            s.login(config.SMTP_USER, config.SMTP_PASSWORD); s.send_message(m); s.quit(); sent.append(("email", config.ALERT_EMAIL_TO, "sent"))
        except Exception as e: sent.append(("email", config.ALERT_EMAIL_TO, f"failed: {e}"))
    if config.WEBHOOK_URL:
        try:
            req = urllib.request.Request(config.WEBHOOK_URL, json.dumps({"text": msg}).encode(), {"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10); sent.append(("webhook", config.WEBHOOK_URL[:40], "sent"))
        except Exception as e: sent.append(("webhook", config.WEBHOOK_URL[:40], f"failed: {e}"))
    if not sent: sent.append(("in-app", "dashboard", "shown"))
    for ch, tgt, st in sent:
        con.execute("INSERT INTO notifications(channel,target,message,status,created) VALUES(?,?,?,?,?)", (ch, tgt, msg[:1000], st, now()))
    con.commit(); con.close()

# ================================================================ background workers
def _stream_loop():
    con = connect(); i = 0
    day = pd.Timestamp(con.execute("SELECT MAX(date) FROM readings").fetchone()[0]) + pd.Timedelta(days=1)
    while stream["running"]:
        try:
            # one tick = one new observation day from every station in the network
            rec = pd.concat([live_record(k, day, seed=(int(time.time() * 1000) + k) % 2**31) for k in range(len(STATIONS))], ignore_index=True)
            rec["record_id"] = [f"LIVE{int(time.time()*1000)}{k}" for k in range(len(rec))]
            store(rec, con, "live_stream"); stream["count"] += len(rec); i += 1
            day += pd.Timedelta(days=1)
        except Exception as e: print("[stream]", e)
        time.sleep(config.STREAM_INTERVAL)
    con.close()

def _fernet():
    if not Fernet: return None
    if not os.path.exists(config.KEY_FILE): open(config.KEY_FILE, "wb").write(Fernet.generate_key())
    return Fernet(open(config.KEY_FILE, "rb").read())

def backup_now(reason="scheduled"):
    t0 = time.time(); src = connect(); mem = sqlite3.connect(":memory:"); src.backup(mem); src.close()
    raw = "\n".join(mem.iterdump()).encode(); mem.close()
    f = _fernet(); ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"earthscape_{ts}.sql.enc" if f else f"earthscape_{ts}.sql"
    open(os.path.join(config.BACKUP_DIR, name), "wb").write(f.encrypt(raw) if f else raw)
    files = sorted(x for x in os.listdir(config.BACKUP_DIR) if x.startswith("earthscape_"))
    for old in files[:-config.BACKUP_KEEP]: os.remove(os.path.join(config.BACKUP_DIR, old))
    con = connect(); con.execute("INSERT INTO jobs(job,records,seconds,detail,created) VALUES(?,?,?,?,?)",
                                 (f"backup:{reason}", 0, round(time.time() - t0, 2), name, now())); con.commit(); con.close()
    return name

def _backup_loop():
    while True:
        time.sleep(config.BACKUP_HOURS * 3600)
        try: backup_now()
        except Exception as e: print("[backup]", e)

# ================================================================ auth & helpers
def login_required(*roles):
    def deco(f):
        @functools.wraps(f)
        def wrap(*a, **k):
            if "user" not in session: return redirect(url_for("login"))
            if roles and session["role"] not in roles: abort(403)
            return f(*a, **k)
        return wrap
    return deco

@app.before_request
def _t0(): g.t0 = time.time()
@app.after_request
def _t1(resp):
    if hasattr(g, "t0") and request.endpoint not in (None, "static"): req_times[request.endpoint].append((time.time() - g.t0) * 1000)
    resp.headers["X-Content-Type-Options"] = "nosniff"; resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    return resp

@app.context_processor
def inject():
    b = ml.bundle()
    return {"model_v": b["version"] if b else "-", "training": ml.state["training"], "streaming": stream["running"],
            "stations_all": STATIONS, "metric_labels": METRIC_LABELS}

def q(sql, args=()): return [dict(r) for r in db().execute(sql, args).fetchall()]

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db().execute("SELECT * FROM users WHERE username=?", (request.form["username"].strip(),)).fetchone()
        if u and check_password_hash(u["password"], request.form["password"]):
            session.clear(); session.update(user=u["username"], role=u["role"]); return redirect(url_for("dashboard"))
        flash("Invalid username or password", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("login"))

# ================================================================ dashboard
@app.route("/dashboard")
@login_required()
def dashboard(): return render_template("dashboard.html")

@app.route("/api/stats")
@login_required()
def api_stats():
    last = db().execute("SELECT MAX(date) FROM readings").fetchone()[0]
    d30 = (pd.Timestamp(last) - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    k = q("""SELECT COUNT(*) n, COUNT(DISTINCT station_id) stations, ROUND(AVG(CASE WHEN date>=? THEN temperature_c END),1) t30,
             ROUND(AVG(CASE WHEN date>=? THEN temp_dev END),2) dev30, SUM(CASE WHEN date>=? THEN pred_anomaly END) anom30,
             SUM(CASE WHEN date>=? AND pred_event!='none' THEN 1 END) ev30 FROM readings""", (d30, d30, d30, d30))[0]
    k["open_alerts"] = db().execute("SELECT COUNT(*) FROM alerts WHERE acknowledged=0").fetchone()[0]; k["last_date"] = last
    annual = q("SELECT substr(date,1,4) y, ROUND(AVG(temperature_c),2) t, ROUND(AVG(co2_ppm),1) co2, ROUND(SUM(precipitation_mm)/COUNT(DISTINCT station_id),0) rain FROM readings GROUP BY y ORDER BY y")
    events = q("SELECT substr(date,1,4) y, event_type e, COUNT(*) c FROM readings WHERE event_type!='none' GROUP BY y,e ORDER BY y")
    latest = q("""SELECT r.* FROM readings r JOIN (SELECT station_id, MAX(rowid) mr FROM readings GROUP BY station_id) x ON r.rowid=x.mr ORDER BY r.station_id""")
    fc = []
    for s in latest:
        hist = pd.read_sql("SELECT * FROM readings WHERE station_id=? ORDER BY date DESC, rowid DESC LIMIT 10", db(), params=(s["station_id"],))
        t, d = ml.forecast_next(hist); fc.append({"station": s["station_name"], "today": s["temperature_c"], "tomorrow": t, "date": d})
    labels, outlook = ml.seasonal_outlook(12)
    recent = q("SELECT station_name, region, date, temperature_c, precipitation_mm, wind_speed_kmh, pm25_ugm3, pred_event, event_prob, pred_anomaly, ingest_source FROM readings ORDER BY rowid DESC LIMIT 10")
    new_alerts = q("SELECT * FROM alerts WHERE id>? ORDER BY id DESC LIMIT 5", (request.args.get("since", 10**12, int),))
    b = ml.bundle()
    return jsonify(kpi=k, annual=annual, events=events, latest=latest, forecast=fc, outlook_labels=labels, outlook=outlook,
                   recent=recent, new_alerts=new_alerts, max_alert=db().execute("SELECT COALESCE(MAX(id),0) FROM alerts").fetchone()[0],
                   model={"version": b["version"], "trained_at": b["trained_at"], "fc": b["metrics"]["forecast"], "ev": b["metrics"]["event"],
                          "trend": b["metrics"]["trends_mean_c_per_decade"]},
                   stream={**stream, "training": ml.state["training"], "progress": ml.state["progress"], "retrain_every": config.RETRAIN_EVERY},
                   server_time=now())

# ================================================================ explore / visualise
@app.route("/explore")
@login_required()
def explore(): return render_template("explore.html", regions=[r["region"] for r in q("SELECT DISTINCT region FROM stations ORDER BY region")])

@app.route("/api/series")
@login_required()
def api_series():
    metric = request.args.get("metric", "temperature_c"); stations = request.args.getlist("station") or ["ST01"]
    agg = request.args.get("agg", "month"); start = request.args.get("start", "2016-01-01"); end = request.args.get("end", "2100-01-01")
    if metric not in METRIC_LABELS: abort(400)
    key = {"day": "date", "month": "substr(date,1,7)", "year": "substr(date,1,4)"}[agg]
    out = {}
    for s in stations[:6]:
        rows = q(f"SELECT {key} k, ROUND(AVG({metric}),2) v, SUM(pred_anomaly) a, SUM(pred_event!='none') e FROM readings WHERE station_id=? AND date BETWEEN ? AND ? GROUP BY k ORDER BY k", (s, start, end))
        out[s] = rows
    return jsonify(series=out, label=METRIC_LABELS[metric])

@app.route("/api/correlation")
@login_required()
def api_correlation():
    region = request.args.get("region", "All")
    sql = "SELECT " + ",".join(METRIC_LABELS) + " FROM readings" + (" WHERE region=?" if region != "All" else "")
    df = pd.read_sql(sql + " ORDER BY RANDOM() LIMIT 20000", db(), params=(region,) if region != "All" else None)
    c = df.corr().round(2)
    return jsonify(labels=[METRIC_LABELS[x] for x in c.columns], matrix=c.fillna(0).values.tolist())

@app.route("/api/trends")
@login_required()
def api_trends():
    b = ml.bundle(); st = {s[0]: s for s in STATIONS}
    return jsonify([{"station": st[k][1] if k in st else k, "region": st[k][2] if k in st else "", **v} for k, v in b["trends"].items()])

@app.route("/map")
@login_required()
def map_view(): return render_template("map.html")

# ================================================================ prediction
@app.route("/predict", methods=["GET", "POST"])
@login_required("admin", "analyst")
def predict():
    res = None
    if request.method == "POST":
        row = {k: request.form.get(k) for k in ["station_id", "date"] + list(METRIC_LABELS)}
        for k in METRIC_LABELS: row[k] = float(row[k]) if row[k] not in (None, "") else None
        sdf = _fill_station_meta(pd.DataFrame([row]), db()); row = sdf.iloc[0].to_dict()
        o = ml.score(sdf).iloc[0]
        lo = (pd.Timestamp(row["date"]) - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
        hist = pd.read_sql("SELECT * FROM readings WHERE station_id=? AND date<? AND date>=? ORDER BY date DESC LIMIT 9", db(), params=(row["station_id"], row["date"], lo))
        t, d = ml.forecast_next(pd.concat([hist, sdf], ignore_index=True))
        res = {"event": o.pred_event, "prob": round(float(o.event_prob) * 100, 1), "anomaly": bool(o.pred_anomaly), "z": o.max_zscore,
               "forecast": t, "fdate": d, "factors": ml.explain_event(row), "version": ml.bundle()["version"]}
    return render_template("predict.html", res=res, f=request.form)

# ================================================================ ingestion
def read_any(f, name):
    name = name.lower()
    if name.endswith(".csv") or name.endswith(".txt"): return pd.read_csv(f)
    if name.endswith(".json"): return pd.read_json(f)
    if name.endswith((".xlsx", ".xls")): return pd.read_excel(f)
    if name.endswith(".parquet"): return pd.read_parquet(f)
    if name.endswith(".nc"):
        import xarray as xr   # NetCDF – the standard climate-science format (pip install xarray netCDF4)
        tmp = os.path.join(config.BACKUP_DIR, "_upload.nc"); f.save(tmp)
        return xr.open_dataset(tmp).to_dataframe().reset_index()
    raise ValueError("Unsupported format")

@app.route("/ingest", methods=["GET", "POST"])
@login_required("admin", "analyst")
def ingest():
    if request.method == "POST":
        f = request.files.get("file")
        try:
            df = read_any(f, f.filename)
        except ImportError:
            flash("NetCDF needs: pip install xarray netCDF4", "danger"); return redirect(url_for("ingest"))
        except Exception as e:
            flash(f"Could not read file: {e}", "danger"); return redirect(url_for("ingest"))
        if "station_id" not in df or "date" not in df:
            flash("File must contain station_id and date columns", "danger"); return redirect(url_for("ingest"))
        before = len(df); df = df.drop_duplicates(subset=["station_id", "date"]) if request.form.get("dedupe") else df
        miss = int(df[[c for c in METRIC_LABELS if c in df]].isna().sum().sum())
        t0 = time.time(); out = store(df, db(), request.form.get("mode", "historical_upload"))
        flash(f"Ingested {len(out):,} readings in {time.time()-t0:.1f}s ({before-len(df)} duplicates removed, {miss:,} missing values imputed). "
              f"{int(out.pred_anomaly.sum())} anomalies, {int((out.pred_event!='none').sum())} extreme-event readings detected.", "success")
    return render_template("ingest.html", jobs=q("SELECT * FROM jobs WHERE job LIKE 'ingest:%' ORDER BY id DESC LIMIT 10"))

@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    if request.headers.get("X-API-Key") != config.API_KEY: return jsonify(error="unauthorized"), 401
    data = request.get_json(force=True)
    out = store(pd.DataFrame(data if isinstance(data, list) else [data]), db(), "api_realtime")
    return jsonify(out[["record_id", "station_id", "date", "pred_event", "event_prob", "pred_anomaly", "model_version"]].to_dict("records"))

@app.route("/api/stream/<action>", methods=["POST"])
@login_required("admin", "analyst")
def stream_ctl(action):
    if action == "start" and not stream["running"]:
        stream["running"] = True; threading.Thread(target=_stream_loop, daemon=True).start()
    elif action == "stop": stream["running"] = False
    return jsonify(stream)

# ================================================================ real-time analytics (sliding windows + SSE)
def realtime_snapshot(window=300):
    now_ts = time.time(); w = [r for r in LIVE if now_ts - r["ts"] <= window]
    per_min = collections.Counter(int((now_ts - r["ts"]) // 60) for r in w)
    st = {}
    for r in w:
        s = st.setdefault(r["station_id"], {"station": r["station_name"], "n": 0, "t": [], "anom": 0, "events": 0})
        s["n"] += 1; s["anom"] += int(r["pred_anomaly"] or 0); s["events"] += r["pred_event"] != "none"
        if r["temperature_c"] is not None: s["t"].append(r["temperature_c"])
    stations = [{"station_id": k, "station": v["station"], "n": v["n"], "avg_t": round(float(np.mean(v["t"])), 1) if v["t"] else None,
                 "ewma_t": EWMA.get(k), "anomalies": v["anom"], "events": v["events"]} for k, v in sorted(st.items())]
    ev = collections.Counter(r["pred_event"] for r in w if r["pred_event"] != "none")
    return {"window_s": window, "n": len(w), "rate_per_min": round(len(w) / max(window / 60, 1), 1),
            "throughput": [per_min.get(i, 0) for i in range(window // 60 - 1, -1, -1)],
            "anomaly_rate": round(100 * sum(int(r["pred_anomaly"] or 0) for r in w) / max(len(w), 1), 1),
            "events": dict(ev), "stations": stations, "latest": list(LIVE)[-15:][::-1], "streaming": stream["running"],
            "total_live": len(LIVE), "server_time": now()}

@app.route("/realtime")
@login_required()
def realtime(): return render_template("realtime.html")

@app.route("/api/realtime")
@login_required()
def api_realtime(): return jsonify(realtime_snapshot(request.args.get("window", 300, int)))

@app.route("/api/live")
@login_required()
def api_live():
    """Server-Sent Events: pushes a fresh sliding-window snapshot every 2 seconds."""
    window = request.args.get("window", 300, int)
    def gen():
        for _ in range(900):                      # ~30 min per connection, browser reconnects automatically
            yield f"data: {json.dumps(realtime_snapshot(window), default=str)}\n\n"; time.sleep(2)
    return Response(gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/export")
@login_required("admin", "analyst")
def export():
    start = request.args.get("start", "1900-01-01"); end = request.args.get("end", "2100-01-01")
    df = pd.read_sql("SELECT * FROM readings WHERE date BETWEEN ? AND ?", db(), params=(start, end))
    return Response(df.to_csv(index=False), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename=earthscape_{start}_{end}.csv"})

# ================================================================ alerts & rules
@app.route("/alerts", methods=["GET", "POST"])
@login_required()
def alerts():
    if request.method == "POST" and session["role"] != "viewer":
        if request.form.get("all"): db().execute("UPDATE alerts SET acknowledged=1, ack_by=? WHERE acknowledged=0", (session["user"],))
        else: db().execute("UPDATE alerts SET acknowledged=1, ack_by=? WHERE id=?", (session["user"], request.form["id"]))
        db().commit()
    lvl = request.args.get("level", "All")
    rows = q("SELECT * FROM alerts WHERE acknowledged=0" + (" AND level=?" if lvl != "All" else "") + " ORDER BY id DESC LIMIT 300", (lvl,) if lvl != "All" else ())
    return render_template("alerts.html", rows=rows, lvl=lvl, notes=q("SELECT * FROM notifications ORDER BY id DESC LIMIT 10"))

@app.route("/rules", methods=["GET", "POST"])
@login_required("admin", "analyst")
def rules():
    if request.method == "POST":
        a = request.form.get("action")
        if a == "add":
            db().execute("INSERT INTO alert_rules(metric,operator,threshold,level,label,region) VALUES(?,?,?,?,?,?)",
                         (request.form["metric"], request.form["operator"], float(request.form["threshold"]), request.form["level"],
                          request.form["label"] or "Custom rule", request.form.get("region", "All")))
        elif a == "toggle": db().execute("UPDATE alert_rules SET enabled=1-enabled WHERE id=?", (request.form["id"],))
        elif a == "delete": db().execute("DELETE FROM alert_rules WHERE id=?", (request.form["id"],))
        elif a == "update": db().execute("UPDATE alert_rules SET threshold=? WHERE id=?", (float(request.form["threshold"]), request.form["id"]))
        db().commit(); flash("Alert rules updated – they apply to every new reading immediately.", "success")
        return redirect(url_for("rules"))
    return render_template("rules.html", rows=q("SELECT * FROM alert_rules ORDER BY id"),
                           regions=["All"] + [r["region"] for r in q("SELECT DISTINCT region FROM stations ORDER BY region")],
                           metrics=list(METRIC_LABELS) + ["event_prob", "pred_anomaly", "max_zscore"])

# ================================================================ models
@app.route("/models", methods=["GET", "POST"])
@login_required("admin", "analyst")
def models():
    if request.method == "POST":
        if request.form.get("action") == "retrain":
            ok = ml.train_async(load_labelled, f"manual by {session['user']}")
            flash("Retraining on all current data started in the background." if ok else "Training already running.", "info")
        elif request.form.get("action") == "activate":
            try: ml.activate(int(request.form["version"])); flash(f"Model v{request.form['version']} activated", "success")
            except Exception as e: flash(str(e), "danger")
        return redirect(url_for("models"))
    return render_template("models.html", versions=ml.list_versions(), b=ml.bundle(), runtime=config.RUNTIME)

@app.route("/api/training")
@login_required()
def api_training():
    return jsonify(training=ml.state["training"], progress=ml.state["progress"], error=ml.state["last_error"], version=ml.bundle()["version"])

# ================================================================ monitoring / performance / backups
@app.route("/monitor")
@login_required("admin", "analyst")
def monitor():
    b = ml.bundle(); recent = pd.read_sql("SELECT * FROM readings WHERE ingest_source!='historical_archive' ORDER BY rowid DESC LIMIT 3000", db())
    if len(recent) < 30: recent = pd.read_sql("SELECT * FROM readings ORDER BY rowid DESC LIMIT 3000", db())
    ref = pd.read_sql("SELECT " + ",".join(METRIC_LABELS) + " FROM readings WHERE ingest_source='historical_archive' ORDER BY RANDOM() LIMIT 20000", db())
    drift = []
    for m in METRIC_LABELS:
        if ref[m].notna().sum() < 30: continue
        p = ml.psi(ref[m].dropna().quantile(np.linspace(0, 1, 11)).values, recent[m])
        if p is not None: drift.append({"metric": METRIC_LABELS[m], "psi": p, "ref": round(float(ref[m].mean()), 2), "recent": round(float(recent[m].mean()), 2),
                                        "status": "Stable" if p < .1 else "Moderate" if p < .25 else "Drift"})
    return render_template("monitor.html", drift=sorted(drift, key=lambda r: -r["psi"]), n=len(recent),
                           jobs=q("SELECT * FROM jobs ORDER BY id DESC LIMIT 15"))

@app.route("/api/system")
@login_required("admin", "analyst")
def api_system():
    sysm = {}
    if psutil:
        vm = psutil.virtual_memory(); dk = psutil.disk_usage(os.path.abspath(os.sep))
        sysm = {"cpu": psutil.cpu_percent(interval=0.2), "ram": vm.percent, "ram_used_gb": round(vm.used / 1e9, 1), "disk": dk.percent,
                "proc_mb": round(psutil.Process().memory_info().rss / 1e6, 0)}
    lat = {k: {"avg": round(float(np.mean(v)), 1), "p95": round(float(np.percentile(v, 95)), 1), "n": len(v)} for k, v in req_times.items() if v}
    tp = q("SELECT ROUND(SUM(records)/MAX(SUM(seconds),0.001),0) rps, COUNT(*) jobs FROM jobs WHERE job LIKE 'ingest:%' AND job!='ingest:historical_archive'")[0]
    dbsize = os.path.getsize(config.DB_PATH) / 1e6 if os.path.exists(config.DB_PATH) else None
    return jsonify(system=sysm, latency=lat, throughput=tp, uptime_h=round((time.time() - STARTED) / 3600, 2),
                   db_mb=round(dbsize, 1) if dbsize else "in-memory", rows=db().execute("SELECT COUNT(*) FROM readings").fetchone()[0])

@app.route("/backups", methods=["GET", "POST"])
@login_required("admin")
def backups():
    if request.method == "POST":
        flash(f"Backup created: {backup_now('manual')}", "success"); return redirect(url_for("backups"))
    files = sorted((x for x in os.listdir(config.BACKUP_DIR) if x.startswith("earthscape_")), reverse=True)
    info = [{"name": x, "mb": round(os.path.getsize(os.path.join(config.BACKUP_DIR, x)) / 1e6, 2)} for x in files]
    return render_template("backups.html", files=info, encrypted=bool(Fernet), every=config.BACKUP_HOURS, keep=config.BACKUP_KEEP, folder=config.BACKUP_DIR)

@app.route("/backups/<name>")
@login_required("admin")
def backup_download(name):
    if "/" in name or "\\" in name or not name.startswith("earthscape_"): abort(400)
    return send_file(os.path.join(config.BACKUP_DIR, name), as_attachment=True)

# ================================================================ support & users
@app.route("/support", methods=["GET", "POST"])
@login_required()
def support():
    admin = session["role"] == "admin"
    if request.method == "POST":
        if admin and request.form.get("reply_id"):
            db().execute("UPDATE feedback SET reply=?, status=? WHERE id=?", (request.form["reply"], request.form["status"], request.form["reply_id"]))
        else:
            db().execute("INSERT INTO feedback(username,category,subject,message,created) VALUES(?,?,?,?,?)",
                         (session["user"], request.form["category"], request.form["subject"], request.form["message"], now()))
            flash("Thank you – your ticket has been submitted.", "success")
        db().commit()
    rows = q("SELECT * FROM feedback ORDER BY id DESC") if admin else q("SELECT * FROM feedback WHERE username=? ORDER BY id DESC", (session["user"],))
    return render_template("support.html", rows=rows)

@app.route("/users", methods=["GET", "POST"])
@login_required("admin")
def users():
    if request.method == "POST":
        if request.form.get("delete"):
            if request.form["delete"] != session["user"]: db().execute("DELETE FROM users WHERE username=?", (request.form["delete"],))
        else:
            try:
                db().execute("INSERT INTO users(username,password,role,email,created) VALUES(?,?,?,?,?)",
                             (request.form["username"], generate_password_hash(request.form["password"]), request.form["role"], request.form.get("email"), now()))
                flash("User created", "success")
            except sqlite3.IntegrityError: flash("Username already exists", "danger")
        db().commit()
    return render_template("users.html", rows=q("SELECT id,username,role,email,created FROM users"), roles=ROLES)

@app.route("/help")
@login_required()
def help_page(): return render_template("help.html")

@app.route("/api/health")
def health():
    b = ml.bundle()
    return jsonify(status="ok", model_version=b["version"] if b else None, uptime_h=round((time.time() - STARTED) / 3600, 2), runtime=config.RUNTIME)

@app.errorhandler(403)
def forbidden(_): return render_template("base.html", error="You do not have permission to view this page."), 403

init_db()
threading.Thread(target=_backup_loop, daemon=True).start()
if os.environ.get("EARTHSCAPE_AUTOSTREAM") == "1":          # hosted demo: sensors stream continuously
    stream["running"] = True; threading.Thread(target=_stream_loop, daemon=True).start()

if __name__ == "__main__":
    print(f"[EarthScape] Runtime: Python {config.RUNTIME['python']} · {config.RUNTIME['platform']} · {config.RUNTIME['cpu_cores']} cores")
    scheme = "https" if config.HTTPS else "http"
    print(f"[EarthScape] Open {scheme}://{config.HOST}:{config.PORT}  (admin / Admin@123)")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, use_reloader=False, threaded=True,
            ssl_context="adhoc" if config.HTTPS else None)
