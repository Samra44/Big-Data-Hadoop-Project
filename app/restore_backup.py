"""Restore an EarthScape backup:  python restore_backup.py <backup file> [target.db]"""
import sys, os, sqlite3, config
src = sys.argv[1]; target = sys.argv[2] if len(sys.argv) > 2 else os.path.join(config.BASE_DIR, "earthscape_restored.db")
data = open(src, "rb").read()
if src.endswith(".enc"):
    from cryptography.fernet import Fernet
    data = Fernet(open(config.KEY_FILE, "rb").read()).decrypt(data)
con = sqlite3.connect(target); con.executescript(data.decode()); con.close()
print(f"Restored to {target}. Set EARTHSCAPE_DB={target} in .env to use it.")
