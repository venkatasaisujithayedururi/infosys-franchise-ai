"""Real weather for every port: Open-Meteo forecast + marine APIs (free, no key), fetched in batches and stored in wx_live.
Falls back to the simulated values already in weather_risks when the network is closed; the page says which one it is showing."""
import time, threading, datetime, json
import live_engine as LE

try: import requests
except Exception: requests = None

FORECAST = "https://api.open-meteo.com/v1/forecast"
MARINE = "https://marine-api.open-meteo.com/v1/marine"
WMO = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain",
       71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains", 80: "Rain showers", 81: "Rain showers", 82: "Violent showers", 85: "Snow showers", 86: "Snow showers", 95: "Thunderstorm", 96: "Thunderstorm, hail", 99: "Thunderstorm, heavy hail"}
_get = None   # tests can replace this with a function(url, params) -> json

def ensure():
    c = LE.conn(); c.execute("CREATE TABLE IF NOT EXISTS wx_live(port_name TEXT PRIMARY KEY, ts TEXT, wind_ms REAL, gust_ms REAL, wind_dir REAL, temp_c REAL, precip_mm REAL, wcode INT, wave_m REAL, wave_dir REAL, src TEXT)"); c.commit()

def _fetch(url, params):
    if _get: return _get(url, params)
    r = requests.get(url, params=params, timeout=10); r.raise_for_status(); return r.json()

def _listify(j): return j if isinstance(j, list) else [j]

def refresh(batch=50):
    """Fetch current weather for every port. Returns (rows_updated, message)."""
    ensure(); c = LE.conn(); ports = c.execute("SELECT port_name, lat, lon FROM ports").fetchall()
    if not ports: return 0, "no ports"
    n = 0; err = ""; ts = datetime.datetime.utcnow().isoformat(timespec="seconds")
    for i in range(0, len(ports), batch):
        chunk = ports[i:i + batch]; la = ",".join(f"{p[1]:.3f}" for p in chunk); lo = ",".join(f"{p[2]:.3f}" for p in chunk)
        try:
            f = _listify(_fetch(FORECAST, {"latitude": la, "longitude": lo, "current": "temperature_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m", "wind_speed_unit": "ms", "timezone": "UTC"}))
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:120]}"; break
        try: m = _listify(_fetch(MARINE, {"latitude": la, "longitude": lo, "current": "wave_height,wave_direction", "timezone": "UTC"}))
        except Exception: m = [{}] * len(chunk)
        for p, a, b in zip(chunk, f, m + [{}] * (len(chunk) - len(m))):
            cur = (a or {}).get("current") or {}
            if cur.get("wind_speed_10m") is None: continue
            mc = (b or {}).get("current") or {}; wave = mc.get("wave_height")
            c.execute("INSERT OR REPLACE INTO wx_live VALUES(?,?,?,?,?,?,?,?,?,?,?)", (p[0], ts, cur.get("wind_speed_10m"), cur.get("wind_gusts_10m"), cur.get("wind_direction_10m"), cur.get("temperature_2m"), cur.get("precipitation") or 0.0, cur.get("weather_code"), wave, mc.get("wave_direction"), "Open-Meteo"))
            wind = float(cur["wind_speed_10m"]); lvl = "High" if wind > 15 else "Medium" if wind >= 8 else "Low"
            c.execute("INSERT OR REPLACE INTO weather_risks(port_name,current_severity,forecast,wind_speed,wave_height,temperature) VALUES(?,?,?,?,?,?)", (p[0], lvl, f"Open-Meteo live {ts[11:16]} UTC · {WMO.get(cur.get('weather_code'), '')}", wind * 3.6, float(wave) if wave is not None else 1.2, cur.get("temperature_2m")))
            n += 1
    c.commit(); LE.set_state("wx_status", {"ts": ts if n else (LE.get_state("wx_status", {}) or {}).get("ts"), "ok": n, "total": len(ports), "err": err, "tried": ts})
    return n, (err or f"{n} ports updated")

def status():
    s = LE.get_state("wx_status", {}) or {}; ok = int(s.get("ok") or 0); age = None
    if s.get("ts"):
        try: age = (datetime.datetime.utcnow() - datetime.datetime.fromisoformat(s["ts"])).total_seconds() / 60
        except Exception: pass
    live = bool(ok) and age is not None and age < 120
    return {"live": live, "ts": s.get("ts"), "age_min": age, "ok": ok, "total": s.get("total"), "err": s.get("err", ""), "tried": s.get("tried")}

def fresh_ports(max_age_min=90):
    """Ports whose real weather is recent: the simulator must not overwrite them."""
    try:
        cut = (datetime.datetime.utcnow() - datetime.timedelta(minutes=max_age_min)).isoformat(timespec="seconds")
        return {r[0] for r in LE.conn().execute("SELECT port_name FROM wx_live WHERE ts>=?", (cut,)).fetchall()}
    except Exception: return set()

_T = {"t": None}
def start(every_min=20):
    if _T["t"]: return
    def loop():
        time.sleep(5)
        while True:
            try: refresh()
            except Exception: pass
            time.sleep(every_min * 60 if status()["live"] else 120)
    _T["t"] = threading.Thread(target=loop, daemon=True); _T["t"].start()

def table():
    import pandas as pd
    ensure()
    return pd.read_sql("SELECT w.*, p.lat, p.lon FROM wx_live w JOIN ports p USING(port_name)", LE.conn())
