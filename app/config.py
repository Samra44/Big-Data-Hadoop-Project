"""EarthScape runtime configuration. Every value can be overridden by an environment variable or app/.env,
so the same code runs on any machine (Windows/Linux/Mac, Python 3.10+)."""
import os, sys, platform, tempfile
BASE_DIR = os.path.dirname(os.path.abspath(__file__)); ROOT_DIR = os.path.dirname(BASE_DIR)

def _load_dotenv():
    p = os.path.join(BASE_DIR, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
_load_dotenv()
def env(k, d, cast=str):
    v = os.environ.get(k); return cast(v) if v not in (None, "") else d

SECRET_KEY      = env("EARTHSCAPE_SECRET", "change-this-secret-key")
API_KEY         = env("EARTHSCAPE_API_KEY", "earthscape-demo-key")
HOST            = env("EARTHSCAPE_HOST", "127.0.0.1")
PORT            = int(os.environ.get("PORT") or env("EARTHSCAPE_PORT", 5000, int))   # PORT is set by cloud hosts (Render, Railway…)
DEBUG           = env("EARTHSCAPE_DEBUG", "1") == "1"
HTTPS           = env("EARTHSCAPE_HTTPS", "0") == "1"           # encrypted transport (self-signed, needs 'cryptography')
DATA_DIR        = env("EARTHSCAPE_DATA_DIR", os.path.join(ROOT_DIR, "data"))
RETRAIN_EVERY   = env("EARTHSCAPE_RETRAIN_EVERY", 5000, int)    # new labelled readings before auto-retrain
STREAM_INTERVAL = env("EARTHSCAPE_STREAM_INTERVAL", 5.0, float)
BACKUP_HOURS    = env("EARTHSCAPE_BACKUP_HOURS", 24, float)     # automated backup interval
BACKUP_KEEP     = env("EARTHSCAPE_BACKUP_KEEP", 7, int)
CV_FOLDS        = env("EARTHSCAPE_CV_FOLDS", 4, int)
N_JOBS          = env("EARTHSCAPE_N_JOBS", -1, int)
SMTP_HOST       = env("EARTHSCAPE_SMTP_HOST", "")                # optional e-mail notifications
SMTP_PORT       = env("EARTHSCAPE_SMTP_PORT", 587, int)
SMTP_USER       = env("EARTHSCAPE_SMTP_USER", "")
SMTP_PASSWORD   = env("EARTHSCAPE_SMTP_PASSWORD", "")
ALERT_EMAIL_TO  = env("EARTHSCAPE_ALERT_EMAIL_TO", "")
WEBHOOK_URL     = env("EARTHSCAPE_WEBHOOK_URL", "")              # optional Slack/Teams/any webhook

RUNTIME = {"python": sys.version.split()[0], "platform": platform.platform(), "cpu_cores": os.cpu_count(), "machine": platform.machine()}

def _dirs(sub):
    yield os.path.join(ROOT_DIR, sub) if sub != "db" else BASE_DIR
    for root in (os.environ.get("LOCALAPPDATA"), os.path.expanduser("~"), tempfile.gettempdir()):
        if root: yield os.path.join(root, ".earthscape" if root == os.path.expanduser("~") else "EarthScape", "" if sub == "db" else sub)

DB_PRAGMAS = ("PRAGMA journal_mode=MEMORY", "PRAGMA synchronous=OFF", "PRAGMA temp_store=MEMORY")
MEMORY_URI = "file:earthscape_mem?mode=memory&cache=shared"
def db_connect(path=None):
    """SQLite without extra journal files – antivirus/OneDrive/Controlled Folder Access on Windows often lock them."""
    import sqlite3
    path = path or DB_PATH
    con = sqlite3.connect(path, timeout=30, check_same_thread=False, uri=path.startswith("file:"))
    for p in DB_PRAGMAS:
        try: con.execute(p)
        except Exception: pass
    return con

_keep = None
def _pick_db():
    global _keep
    if os.environ.get("EARTHSCAPE_DB"): return os.environ["EARTHSCAPE_DB"]
    for d in _dirs("db"):
        p = os.path.join(d, "earthscape.db")
        try:
            os.makedirs(d, exist_ok=True); con = db_connect(p)
            con.executescript("CREATE TABLE IF NOT EXISTS _p(x); INSERT INTO _p VALUES(1); DROP TABLE _p;"); con.commit(); con.close()
            return p
        except Exception as e:
            print(f"[EarthScape] Database not usable in {d} ({e}); trying another folder…")
            try: os.remove(p)
            except Exception: pass
    print("[EarthScape] WARNING: no folder allows SQLite writes (antivirus / Controlled Folder Access / full disk?). Using in-memory database.")
    _keep = db_connect(MEMORY_URI); return MEMORY_URI

def _pick_dir(sub, envkey):
    if os.environ.get(envkey): os.makedirs(os.environ[envkey], exist_ok=True); return os.environ[envkey]
    for d in _dirs(sub):
        try:
            os.makedirs(d, exist_ok=True); t = os.path.join(d, ".probe"); open(t, "w").write("ok"); os.remove(t); return d
        except Exception: continue
    raise RuntimeError(f"No writable folder for {sub}")

DB_PATH    = _pick_db()
MODEL_DIR  = _pick_dir(os.path.join("ml", "registry"), "EARTHSCAPE_MODEL_DIR")
BACKUP_DIR = _pick_dir("backups", "EARTHSCAPE_BACKUP_DIR")
KEY_FILE   = os.path.join(BACKUP_DIR, ".backup.key")
