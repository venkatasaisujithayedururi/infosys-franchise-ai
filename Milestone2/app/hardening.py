"""Production hardening for the FastAPI app: request ids + JSON access log, security headers (CSP, frame, permissions), per-IP rate limits on auth routes,
a global JSON error handler that never leaks tracebacks, and Prometheus-style metrics. Install with hardening.install(app)."""
import os, time, json, uuid, threading, logging, traceback, collections
from logging.handlers import RotatingFileHandler
from fastapi import Request
from fastapi.responses import JSONResponse, PlainTextResponse
import config

_LOG = logging.getLogger("access"); _LOG.setLevel(logging.INFO); _LOG.propagate = False
try:
    _h = RotatingFileHandler(os.path.join(config.DATA_DIR, "access.log"), maxBytes=2_000_000, backupCount=3); _h.setFormatter(logging.Formatter("%(message)s")); _LOG.addHandler(_h)
except Exception: pass
_ERR = logging.getLogger("errors"); _ERR.propagate = False
try:
    _e = RotatingFileHandler(os.path.join(config.DATA_DIR, "errors.log"), maxBytes=1_000_000, backupCount=2); _e.setFormatter(logging.Formatter("%(asctime)s %(message)s")); _ERR.addHandler(_e)
except Exception: pass

M = {"requests": collections.Counter(), "status": collections.Counter(), "lat_sum": collections.Counter(), "lat_n": collections.Counter(), "errors": 0, "limited": 0, "started": time.time()}
_L = threading.Lock(); _BUCKET = {}
CSP = "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; font-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
# path prefix -> (max requests, per seconds). Everything else: 900 per minute per IP.
LIMITS = {"/api/login": (10, 60), "/api/register": (6, 600), "/api/otp": (5, 300), "/api/reset": (8, 600), "/api/profile/password": (8, 600), "/api/copilot": (40, 60), "/api/translate": (60, 60)}
def _ip(r):
    f = r.headers.get("x-forwarded-for"); return (f.split(",")[0].strip() if f else (r.client.host if r.client else "?"))
def _allow(ip, path):
    key, (n, per) = next(((p, v) for p, v in LIMITS.items() if path.startswith(p)), ("*", (900, 60))); k = (ip, key); now = time.time()
    with _L:
        q = _BUCKET.setdefault(k, collections.deque())
        while q and now - q[0] > per: q.popleft()
        if len(q) >= n: return False, int(per - (now - q[0])) + 1
        q.append(now)
        if len(_BUCKET) > 20000: _BUCKET.clear()
    return True, 0
def _route(path):
    parts = path.split("/")
    return "/".join(parts[:3]) if path.startswith("/api/") else "static"

def install(app, kind="app"):
    @app.middleware("http")
    async def guard(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]; t0 = time.time(); path = request.url.path
        if os.environ.get("RATE_LIMIT_OFF") != "1" and (path.startswith("/api/") and request.method != "GET" or path.startswith("/api/login")):
            ok, wait = _allow(_ip(request), path)
            if not ok:
                M["limited"] += 1; return JSONResponse({"ok": False, "msg": f"Too many requests. Try again in {wait}s.", "request_id": rid}, status_code=429, headers={"Retry-After": str(wait), "X-Request-ID": rid})
        try: r = await call_next(request)
        except Exception as e:
            M["errors"] += 1; _ERR.error("%s %s %s\n%s", rid, request.method, path, traceback.format_exc())
            return JSONResponse({"ok": False, "msg": "Something went wrong on the server. Quote this id to the admin: " + rid, "request_id": rid}, status_code=500, headers={"X-Request-ID": rid})
        ms = (time.time() - t0) * 1000; rt = _route(path)
        with _L: M["requests"][rt] += 1; M["status"][r.status_code // 100] += 1; M["lat_sum"][rt] += ms; M["lat_n"][rt] += 1
        h = r.headers; h["X-Request-ID"] = rid; h["X-Frame-Options"] = "DENY"; h["Content-Security-Policy"] = CSP; h["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"; h["Cross-Origin-Opener-Policy"] = "same-origin"
        if request.headers.get("x-forwarded-proto") == "https": h["Strict-Transport-Security"] = "max-age=31536000"
        if path.startswith("/api/") and path not in ("/api/stream", "/api/pulse"): _LOG.info(json.dumps({"t": round(t0), "id": rid, "ip": _ip(request), "m": request.method, "p": path, "s": r.status_code, "ms": round(ms)}))
        return r

    @app.get("/api/ready")
    def ready(): return {"ok": True, "kind": kind, "uptime_s": round(time.time() - M["started"])}

    @app.get("/api/metrics")
    def metrics(request: Request):
        """Prometheus text format. Set METRICS_TOKEN to require ?token=..., otherwise only logged-in admins (cookie) may read it."""
        tok = os.environ.get("METRICS_TOKEN")
        if tok and request.query_params.get("token") != tok: return PlainTextResponse("forbidden", status_code=403)
        if not tok:
            try:
                u = request.app.state.user_of(request)          # server.py registers its user_of here; no registered user_of means forbidden
                if not u or u.get("role") != "Admin": return PlainTextResponse("forbidden", status_code=403)
            except Exception: return PlainTextResponse("forbidden", status_code=403)
        L = ["# TYPE app_requests_total counter"] + [f'app_requests_total{{route="{k}"}} {v}' for k, v in M["requests"].items()] + ["# TYPE app_responses_total counter"] + [f'app_responses_total{{class="{k}xx"}} {v}' for k, v in M["status"].items()]
        L += ["# TYPE app_latency_ms_avg gauge"] + [f'app_latency_ms_avg{{route="{k}"}} {M["lat_sum"][k] / max(1, M["lat_n"][k]):.1f}' for k in M["lat_n"]] + [f"app_errors_total {M['errors']}", f"app_rate_limited_total {M['limited']}", f"app_uptime_seconds {time.time() - M['started']:.0f}"]
        try:
            import live_engine as LE; c = LE.conn(); L += [f"app_open_tickets {c.execute('SELECT COUNT(*) FROM agent_actions WHERE status=?', ('open',)).fetchone()[0]}"]
        except Exception: pass
        try:
            import gpu; g = gpu.status(); L += [f'app_model_ready{{model="{k}"}} {1 if v["state"] == "ready" else 0}' for k, v in g["models"].items()]
        except Exception: pass
        return PlainTextResponse("\n".join(L) + "\n")
