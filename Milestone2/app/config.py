"""Shared configuration. APP_KIND (Franchise | Freight) is set by the launcher. No Google Drive prompts: data lives in DATA_DIR (set PERSIST_DIR to keep it between sessions)."""
import os
KIND = os.environ.get("APP_KIND", "Franchise")
APP_DIR = os.path.dirname(os.path.abspath(__file__))
_default = "/content/app_data" if os.path.isdir("/content") else os.path.join(APP_DIR, "runtime_data")
DATA_DIR = os.environ.get("PERSIST_DIR") or os.environ.get("APP_DATA_DIR") or os.environ.get("FRANCHISEOPS_DATA_DIR") or os.environ.get("FREIGHTQUOTE_DATA_DIR") or _default
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "franchise_database.db" if KIND == "Franchise" else "freight_database.db")
def _secret(key, default=""):
    try:
        from google.colab import userdata
        v = userdata.get(key)
        if v: return str(v).strip()
    except Exception: pass
    return str(os.environ.get(key, default) or "").strip()
HF_TOKEN = _secret("HF_TOKEN") or _secret("HUGGINGFACE_TOKEN")
def _persisted_secret():
    """No JWT_SECRET_KEY given: generate a random one once and keep it beside the database, so sessions survive restarts and are never signed with a public default."""
    import secrets as _s
    p = os.path.join(DATA_DIR, ".jwt_secret")
    try:
        if os.path.exists(p): return open(p).read().strip()
        v = _s.token_urlsafe(48); fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600); os.write(fd, v.encode()); os.close(fd); return v
    except Exception: return _s.token_urlsafe(48)
JWT_SECRET_KEY = _secret("JWT_SECRET") or _secret("JWT_SECRET_KEY") or _persisted_secret()
ADMIN_EMAIL_ID = _secret("ADMIN_EMAIL_ID", "admin@infosys.com")
def _admin_pw():
    """ADMIN_PASSWORD comes from Colab Secrets / env. There is no built-in default: without it a random password is generated once, stored beside the database and printed in the server log."""
    v = _secret("ADMIN_PASSWORD")
    if v: return v
    import secrets as _s; p = os.path.join(DATA_DIR, ".admin_initial")
    if os.path.exists(p): return open(p).read().strip()
    v = _s.token_urlsafe(9) + "1aA"; open(p, "w").write(v); print("*** ADMIN_PASSWORD secret not set: generated initial admin password:", v, "(stored in", p, ") ***"); return v
ADMIN_PASSWORD = _admin_pw()
EMAIL_ID = _secret("EMAIL_ADDRESS") or _secret("EMAIL_ID"); EMAIL_PASSWORD = _secret("EMAIL_PASSWORD").replace(" ", "")
MODEL_NAME = os.environ.get("LLM_MODEL", "")
NLLB_MODEL = os.environ.get("NLLB_MODEL", "facebook/nllb-200-distilled-600M")
