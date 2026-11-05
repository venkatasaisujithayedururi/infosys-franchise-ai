"""Accounts: the Milestone 1 login brought into FastAPI (signup, login, forgot/reset), the users table, JWT sessions,
the Admin dashboard API (add, delete, promote/demote, lock/unlock, activity log) and the Profile API.

Rules: passwords are hashed with bcrypt and never returned; the JWT carries only the user id (role, outlet and lock state are read
from the database on EVERY request, so a promotion, demotion or lock takes effect immediately); an unknown user and a wrong password
give the same error; 5 wrong passwords lock the account; the last Admin can never be removed, demoted or locked."""
import re, time, secrets, sqlite3, datetime, hashlib, base64
import bcrypt, jwt
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import config, rbac, mailer, validators as V
import live_engine as LE

router = APIRouter()
COOKIE = "fo_token"                       # EventSource (live pulse) cannot send headers, so GET requests may also use this cookie
TOKEN_HOURS = 8
MAX_FAILS = 5
OTP_MINUTES, OTP_TRIES, OTP_COOLDOWN, OTP_BLOCK_MIN = 5, 3, 60, 15      # as in Milestone 1: a code lives 5 minutes, 3 wrong codes pause recovery for 15 minutes, a new code after 60 seconds
SECURITY_QUESTIONS = ["What was the name of your first school?", "What is your mother's maiden name?", "What was your favorite childhood pet's name?",
                      "What is the name of the city where you were born?", "What was the make of your family's first car?"]      # same list as Milestone 1
SQ_TRIES, SQ_BLOCK_MIN = 3, 15                  # 3 wrong security answers pause that route for the account for 15 minutes
SIGNUP_ROLES = [r for r in rbac.ROLES if r != "Admin"]      # a person may pick their own role at signup, but never Admin (only an Admin can promote)
GENERIC = "Invalid email/username or password."
_DUMMY = bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt())

def db():
    c = sqlite3.connect(config.DB_PATH, timeout=30); c.row_factory = sqlite3.Row; c.execute("PRAGMA journal_mode=WAL;"); c.execute("PRAGMA busy_timeout=30000;"); return c
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")      # stored with its time zone; the browser shows it in IST
def iso(ts):
    """Any stored time as an ISO string WITH an offset (an old naive value is the server's local time), so the front end can show it in IST."""
    if not ts: return None
    try: d = datetime.datetime.fromisoformat(str(ts).replace(" ", "T"))
    except Exception: return str(ts)
    return (d.astimezone() if d.tzinfo is None else d).isoformat(timespec="seconds")
def hash_pw(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def check_pw(p, h):
    try: return bcrypt.checkpw(p.encode(), (h or "").encode())
    except Exception: return False

# ------------------------------------------------------------------ users table (extends the table db.py creates)
NEW_COLS = {"outlet": "TEXT", "sq_tries": "INTEGER NOT NULL DEFAULT 0", "sq_blocked_until": "REAL", "locked": "INTEGER NOT NULL DEFAULT 0", "last_login": "TEXT", "token_version": "INTEGER NOT NULL DEFAULT 0",
            "otp_hash": "TEXT", "otp_expires": "REAL", "otp_tries": "INTEGER NOT NULL DEFAULT 0", "otp_sent": "REAL", "otp_blocked_until": "REAL"}
def init():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, email TEXT UNIQUE, password_hash TEXT, role TEXT, security_question TEXT, security_answer TEXT, profile_picture TEXT, failed_attempts INTEGER DEFAULT 0, lock_until DATETIME DEFAULT NULL, account_status TEXT DEFAULT 'active', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        have = {r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()}
        for col, ddl in NEW_COLS.items():
            if col not in have: c.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_lc ON users(lower(email))")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username_lc ON users(lower(username))")
        seed = not c.execute("SELECT 1 FROM users WHERE role='Admin'").fetchone()
        if seed: c.execute("INSERT INTO users(username,email,password_hash,role,locked,created_at) VALUES(?,?,?,?,0,?)", ("admin", config.ADMIN_EMAIL_ID.lower(), hash_pw(config.ADMIN_PASSWORD), "Admin", now()))
    if seed: LE.audit("system", "admin_seeded", config.ADMIN_EMAIL_ID.lower(), "first Admin created from the ADMIN_PASSWORD secret")

PUBLIC_COLS = "id, email, username, role, outlet, locked, failed_attempts, created_at, last_login"
def public(r): return {"id": r["id"], "email": r["email"], "username": r["username"], "role": r["role"], "outlet": r["outlet"] if r["role"] in rbac.SCOPED_ROLES else None, "locked": bool(r["locked"]), "created_at": iso(r["created_at"]), "last_login": iso(r["last_login"])}
def outlets():
    with db() as c: return [r[0] for r in c.execute("SELECT outlet_id FROM outlets ORDER BY outlet_id").fetchall()]

# ------------------------------------------------------------------ sessions
def make_token(r): return jwt.encode({"sub": str(r["id"]), "tv": r["token_version"], "iat": int(time.time()), "exp": int(time.time()) + TOKEN_HOURS * 3600}, config.JWT_SECRET_KEY, algorithm="HS256")
def current_user(request: Request):
    """user_of(): reads the Bearer token, checks the user still exists and is not locked, and returns the REAL user. 401 otherwise."""
    h = request.headers.get("authorization", ""); tok = h[7:].strip() if h.lower().startswith("bearer ") else (request.cookies.get(COOKIE) if request.method == "GET" else None)
    if not tok: raise HTTPException(401, "Sign in to continue.")
    try: p = jwt.decode(tok, config.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError: raise HTTPException(401, "Your session expired. Sign in again.")
    except Exception: raise HTTPException(401, "Invalid session. Sign in again.")
    with db() as c: r = c.execute(f"SELECT {PUBLIC_COLS}, token_version FROM users WHERE id=?", (p.get("sub"),)).fetchone()
    if not r or r["token_version"] != p.get("tv"): raise HTTPException(401, "Your session is no longer valid. Sign in again.")
    if r["locked"]: raise HTTPException(401, "This account is locked. Contact an administrator.")
    return {k: r[k] for k in ("id", "email", "username", "role", "outlet", "created_at", "last_login")}

def body_of(d, *keys): return [str(d.get(k) if d.get(k) is not None else "") for k in keys]
async def jbody(request):
    try: d = await request.json()
    except Exception: raise HTTPException(400, "Send the form as JSON.")
    if not isinstance(d, dict): raise HTTPException(400, "Send the form as JSON.")
    return d
def ok(msg="Done", **kw): return {"ok": True, "msg": msg, **kw}
def fail(msg, code=400): raise HTTPException(code, msg)
def check(r):
    good, msg = r
    if not good: fail(msg)

def validate_new_account(email, username, password, confirm, role, outlet, allowed_roles):
    check(V.validate_mandatory_fields({"Email": email, "Username": username, "Password": password, "Confirm Password": confirm, "Role": role}))
    check(V.validate_email_format(email)); check(V.validate_username(username))
    check(V.validate_password_complexity(password)); check(V.validate_password_confirmation(password, confirm))
    if role not in allowed_roles: fail("Choose a valid role.")
    outlet = (outlet or "").strip().upper()
    if role in rbac.SCOPED_ROLES:
        if not outlet: fail(f"Choose the outlet for a {role}.")
        if outlet not in outlets(): fail("That outlet does not exist.")
    else: outlet = None
    return email.strip().lower(), username.strip(), outlet
def norm_answer(s): return re.sub(r"\s+", " ", (s or "").strip().lower())
def validate_security(question, answer):
    check(V.validate_mandatory_fields({"Security question": question, "Security answer": answer}))
    if question not in SECURITY_QUESTIONS: fail("Choose a security question from the list.")
    if len(norm_answer(answer)) < 2: fail("The security answer must be at least 2 characters.")
    if len(answer) > 100: fail("The security answer is too long.")
def decoy_question(email):
    """Unknown, locked or question-less accounts get a stable, believable question, so the form never reveals which e-mails are registered."""
    return SECURITY_QUESTIONS[int(hashlib.sha256(email.strip().lower().encode()).hexdigest()[:8], 16) % len(SECURITY_QUESTIONS)]
def insert_user(email, username, password, role, outlet, question=None, answer=None):
    with db() as c:
        if c.execute("SELECT 1 FROM users WHERE lower(email)=?", (email,)).fetchone(): fail("This email is already registered.")
        if c.execute("SELECT 1 FROM users WHERE lower(username)=lower(?)", (username,)).fetchone(): fail("This username is taken.")
        cur = c.execute("INSERT INTO users(username,email,password_hash,role,outlet,locked,failed_attempts,created_at,security_question,security_answer) VALUES(?,?,?,?,?,0,0,?,?,?)",
                        (username, email, hash_pw(password), role, outlet, now(), question, hash_pw(norm_answer(answer)) if answer else None))
        return cur.lastrowid

# ------------------------------------------------------------------ public auth routes
@router.get("/api/auth/options")
def auth_options(): return {"roles": SIGNUP_ROLES, "scoped_roles": sorted(rbac.SCOPED_ROLES), "outlets": outlets(), "questions": SECURITY_QUESTIONS}

@router.post("/api/auth/signup")
async def signup(request: Request):
    d = await jbody(request); email, username, password, confirm, role, outlet = body_of(d, "email", "username", "password", "confirm_password", "role", "outlet")
    email, username, outlet = validate_new_account(email, username, password, confirm, role, outlet, SIGNUP_ROLES)      # Admin is not offered and is refused here
    question, answer = body_of(d, "security_question", "security_answer"); validate_security(question, answer)
    uid = insert_user(email, username, password, role, outlet, question, answer); LE.audit(email, "signup", str(uid), f"role={role} outlet={outlet or '-'}")
    return ok("Account created. You can sign in now.")

@router.post("/api/auth/login")
async def login(request: Request):
    d = await jbody(request); ident, password = body_of(d, "identity", "password"); ident = ident.strip()
    if not ident or not password: fail("Enter your email or username and password.")
    locked_now = False
    with db() as c:
        r = c.execute(f"SELECT {PUBLIC_COLS}, password_hash, token_version FROM users WHERE lower(email)=lower(?) OR lower(username)=lower(?)", (ident, ident)).fetchone()
        if not r: bcrypt.checkpw(password.encode(), _DUMMY); fail(GENERIC, 401)            # same text and similar time as a wrong password
        if not check_pw(password, r["password_hash"]):
            n = (r["failed_attempts"] or 0) + 1; lock = 0
            if n >= MAX_FAILS:
                others = c.execute("SELECT COUNT(*) FROM users WHERE role='Admin' AND locked=0 AND id<>?", (r["id"],)).fetchone()[0]
                lock = 0 if r["role"] == "Admin" and not others else 1        # the last active Admin is never auto-locked
            c.execute("UPDATE users SET failed_attempts=?, locked=? WHERE id=?", (n, 1 if (lock or r["locked"]) else 0, r["id"])); c.commit()       # commit: raising below would roll the count back
            locked_now = bool(lock) and not r["locked"]
        elif r["locked"]: fail("This account is locked. Contact an administrator.", 403)
        else:
            c.execute("UPDATE users SET failed_attempts=0, last_login=? WHERE id=?", (now(), r["id"])); token = make_token(r); u = public(r); u["last_login"] = now()
    if not check_pw(password, r["password_hash"]):
        if locked_now: LE.audit(r["email"], "auto_lock", str(r["id"]), f"{MAX_FAILS} wrong passwords")
        fail(GENERIC, 401)
    LE.audit(r["email"], "login", str(r["id"]), r["role"])
    resp = JSONResponse({"ok": True, "msg": "Signed in.", "token": token, "user": u})
    resp.set_cookie(COOKIE, token, max_age=TOKEN_HOURS * 3600, httponly=True, samesite="lax", path="/"); return resp

@router.post("/api/auth/logout")
def logout():
    resp = JSONResponse({"ok": True, "msg": "Signed out."}); resp.delete_cookie(COOKIE, path="/"); return resp

# ---- password recovery: look the account up by e-mail OR username; prove who you are by an e-mailed code or by the security question.
#      A locked account cannot recover (an Admin must unlock it). 3 wrong codes (or 3 wrong answers) pause that route for 15 minutes.
def _find(c, ident):
    return c.execute("SELECT id, email, username, role, locked, security_question, security_answer, otp_hash, otp_expires, otp_tries, otp_sent, otp_blocked_until, sq_tries, sq_blocked_until FROM users WHERE lower(email)=lower(?) OR lower(username)=lower(?)", (ident, ident)).fetchone()
def _ident(d):
    v = d.get("identity") if d.get("identity") not in (None, "") else d.get("email"); return str(v or "").strip()
def _minutes(ts): return int(((ts or 0) - time.time() + 59) // 60) if (ts or 0) > time.time() else 0
def _open(r):
    if r and r["locked"]: fail("This account is locked. Contact an administrator.", 403)         # an Admin must unlock it first; no code, no question, no reset

def _otp_ok(c, r, code, consume):
    """True when the code is right. Counts tries, enforces expiry, and after OTP_TRIES wrong codes pauses e-mail recovery for OTP_BLOCK_MIN minutes."""
    if not r or not r["otp_hash"] or (r["otp_expires"] or 0) < time.time(): return False
    if not re.fullmatch(r"\d{6}", code or "") or not check_pw(code, r["otp_hash"]):
        n = (r["otp_tries"] or 0) + 1
        if n >= OTP_TRIES: c.execute("UPDATE users SET otp_hash=NULL, otp_expires=NULL, otp_tries=0, otp_blocked_until=? WHERE id=?", (time.time() + OTP_BLOCK_MIN * 60, r["id"]))
        else: c.execute("UPDATE users SET otp_tries=? WHERE id=?", (n, r["id"]))
        c.commit()                                                                                  # commit: the caller raises, which would roll the counter back
        if n >= OTP_TRIES: LE.audit(r["email"], "recovery_paused", str(r["id"]), f"{OTP_TRIES} wrong e-mail codes, paused {OTP_BLOCK_MIN} minutes")
        return False
    if consume: c.execute("UPDATE users SET otp_hash=NULL, otp_expires=NULL, otp_tries=0, otp_blocked_until=NULL WHERE id=?", (r["id"],)); c.commit()
    return True
def _code_failed(c, ident):
    r = _find(c, ident); w = _minutes(r["otp_blocked_until"]) if r else 0
    if w: fail(f"Too many wrong codes. Recovery by e-mail code is paused for {w} more minute(s). You can still use your security question.", 429)
    fail("That code is wrong or has expired.")

@router.post("/api/auth/forgot")
async def forgot(request: Request):
    d = await jbody(request); ident = _ident(d)
    if not ident: fail("Enter your email or username.")
    msg = "If an account exists for that email or username, a 6-digit code has been sent to its e-mail. It is valid for %d minutes." % OTP_MINUTES
    send = None
    with db() as c:
        r = _find(c, ident); _open(r)
        if r:
            w = _minutes(r["otp_blocked_until"])
            if w: fail(f"Too many wrong codes. Recovery by e-mail code is paused for {w} more minute(s). You can still use your security question.", 429)
            if time.time() - (r["otp_sent"] or 0) >= OTP_COOLDOWN:
                code = f"{secrets.randbelow(10**6):06d}"
                c.execute("UPDATE users SET otp_hash=?, otp_expires=?, otp_tries=0, otp_sent=? WHERE id=?", (hash_pw(code), time.time() + OTP_MINUTES * 60, time.time(), r["id"]))
                send = (r["email"], code, r["username"])
    if send:                                                                                        # sent after the transaction closes, so the database is never held during the network call
        to, code, name = send
        sent, info = mailer.send(to, "Your FranchiseOps AI verification code", mailer.otp_text(code, OTP_MINUTES, name), html=mailer.otp_html(code, OTP_MINUTES, name))
        if not sent: print(f"[forgot-password] e-mail not sent ({info}); code for {to}: {code}")       # visible in the server log when Gmail is not configured
    return ok(msg)

@router.post("/api/auth/verify")
async def verify(request: Request):
    d = await jbody(request); ident = _ident(d); (otp,) = body_of(d, "otp")
    with db() as c:
        r = _find(c, ident); _open(r)
        w = _minutes(r["otp_blocked_until"]) if r else 0
        if w: fail(f"Too many wrong codes. Recovery by e-mail code is paused for {w} more minute(s). You can still use your security question.", 429)
        if not _otp_ok(c, r, otp.strip(), False): _code_failed(c, ident)
    return ok("Code verified.")

@router.post("/api/auth/reset")
async def reset(request: Request):
    d = await jbody(request); ident = _ident(d); otp, pw, cf = body_of(d, "otp", "password", "confirm_password")
    check(V.validate_password_complexity(pw)); check(V.validate_password_confirmation(pw, cf))
    with db() as c:
        r = _find(c, ident); _open(r)
        if not _otp_ok(c, r, otp.strip(), True): _code_failed(c, ident)
        c.execute("UPDATE users SET password_hash=?, failed_attempts=0, token_version=token_version+1 WHERE id=?", (hash_pw(pw), r["id"]))     # old sessions end
    LE.audit(r["email"], "password_reset", str(r["id"]), "e-mail code"); return ok("Password changed. You can sign in with the new password.")

@router.post("/api/auth/security-question")
async def security_question(request: Request):
    d = await jbody(request); ident = _ident(d)
    if not ident: fail("Enter your email or username.")
    with db() as c: r = _find(c, ident); _open(r)
    return {"ok": True, "question": r["security_question"] if r and r["security_question"] else decoy_question(ident)}      # unknown or question-less: a stable decoy, so nobody can tell which accounts exist

@router.post("/api/auth/reset-with-answer")
async def reset_with_answer(request: Request):
    d = await jbody(request); ident = _ident(d); answer, pw, cf = body_of(d, "answer", "password", "confirm_password")
    check(V.validate_mandatory_fields({"Security answer": answer})); check(V.validate_password_complexity(pw)); check(V.validate_password_confirmation(pw, cf))
    blocked_now = False
    with db() as c:
        r = _find(c, ident); _open(r)
        wait = _minutes(r["sq_blocked_until"]) if r else 0
        if wait: fail(f"Too many wrong answers. Recovery by security question is paused for {wait} more minute(s). You can still use the e-mail code.", 429)
        usable = bool(r and r["security_answer"])
        if usable: good = check_pw(norm_answer(answer), r["security_answer"])
        else: bcrypt.checkpw(b"x", _DUMMY); good = False                      # unknown or question-less account: same work, same answer
        if not good:
            if usable:
                n = (r["sq_tries"] or 0) + 1; blocked_now = n >= SQ_TRIES
                c.execute("UPDATE users SET sq_tries=?, sq_blocked_until=? WHERE id=?", (0 if blocked_now else n, time.time() + SQ_BLOCK_MIN * 60 if blocked_now else None, r["id"])); c.commit()      # commit: raising below would roll it back
        else:
            c.execute("UPDATE users SET password_hash=?, failed_attempts=0, sq_tries=0, sq_blocked_until=NULL, token_version=token_version+1 WHERE id=?", (hash_pw(pw), r["id"]))
    if not good:
        if blocked_now: LE.audit(r["email"], "recovery_paused", str(r["id"]), f"{SQ_TRIES} wrong security answers, paused {SQ_BLOCK_MIN} minutes")
        fail("That answer is wrong." + (f" Recovery by security question is now paused for {SQ_BLOCK_MIN} minutes." if blocked_now else ""))
    LE.audit(r["email"], "password_reset", str(r["id"]), "security question"); return ok("Password changed. You can sign in with the new password.")

# ------------------------------------------------------------------ profile
def _server():
    import server; return server
def me_ctx(request):
    s = _server(); u = s.user_of(request); return u, s.ctx(u)

@router.get("/api/profile")
def profile(request: Request):
    u, c = me_ctx(request); rbac.need(c, "profile")
    with db() as cn: r = cn.execute(f"SELECT {PUBLIC_COLS}, security_question, profile_picture FROM users WHERE id=?", (u["id"],)).fetchone()
    return {"ok": True, "profile": {**public(r), "security_question": r["security_question"], "picture": r["profile_picture"]}}        # the question (never the answer) so the person can see what they chose

MAX_PICTURE = 150_000                           # bytes after decoding; the browser shrinks the photo to a small square first
MAGIC = {"png": b"\x89PNG", "jpeg": b"\xff\xd8\xff", "webp": b"RIFF"}
def picture_of(uid):
    with db() as c: r = c.execute("SELECT profile_picture FROM users WHERE id=?", (uid,)).fetchone()
    return r[0] if r else None

@router.post("/api/profile/picture")
async def profile_picture(request: Request):
    u, c = me_ctx(request); rbac.need(c, "profile"); d = await jbody(request)
    if d.get("remove") is True:
        with db() as cn: cn.execute("UPDATE users SET profile_picture=NULL WHERE id=?", (u["id"],))
        return ok("Photo removed.", picture=None)
    img = str(d.get("image") or ""); m = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)", img)
    if not m: fail("Choose a PNG, JPEG or WebP image.")
    try: raw = base64.b64decode(m.group(2), validate=True)
    except Exception: fail("That image could not be read.")
    if len(raw) > MAX_PICTURE: fail("The photo is too large. Choose a smaller one (under 150 KB after resizing).")
    if not raw.startswith(MAGIC[m.group(1)]): fail("That file is not a real " + m.group(1).upper() + " image.")
    with db() as cn: cn.execute("UPDATE users SET profile_picture=? WHERE id=?", (img, u["id"]))
    LE.audit(u["email"], "profile_picture_changed", str(u["id"]), ""); return ok("Photo saved.", picture=img)

@router.post("/api/profile/security")
async def profile_security(request: Request):
    u, c = me_ctx(request); rbac.need(c, "profile"); d = await jbody(request); cur, question, answer = body_of(d, "current_password", "security_question", "security_answer")
    check(V.validate_mandatory_fields({"Current password": cur})); validate_security(question, answer)
    with db() as cn:
        r = cn.execute("SELECT password_hash FROM users WHERE id=?", (u["id"],)).fetchone()
        if not check_pw(cur, r["password_hash"]): fail("The current password is wrong.")
        cn.execute("UPDATE users SET security_question=?, security_answer=?, sq_tries=0, sq_blocked_until=NULL WHERE id=?", (question, hash_pw(norm_answer(answer)), u["id"]))
    LE.audit(u["email"], "security_question_changed", str(u["id"]), ""); return ok("Security question saved.", security_question=question)

@router.post("/api/profile/username")
async def profile_username(request: Request):
    u, c = me_ctx(request); rbac.need(c, "profile"); d = await jbody(request); (name,) = body_of(d, "username"); name = name.strip(); check(V.validate_username(name))
    with db() as cn:
        if cn.execute("SELECT 1 FROM users WHERE lower(username)=lower(?) AND id<>?", (name, u["id"])).fetchone(): fail("This username is taken.")
        cn.execute("UPDATE users SET username=? WHERE id=?", (name, u["id"]))
    LE.audit(u["email"], "username_changed", str(u["id"]), name); return ok("Username updated.", username=name)

@router.post("/api/profile/password")
async def profile_password(request: Request):
    u, c = me_ctx(request); rbac.need(c, "profile"); d = await jbody(request); cur, new, cf = body_of(d, "current_password", "new_password", "confirm_password")
    check(V.validate_mandatory_fields({"Current password": cur, "New password": new, "Confirm password": cf}))
    with db() as cn:
        r = cn.execute("SELECT password_hash, token_version FROM users WHERE id=?", (u["id"],)).fetchone()
        if not check_pw(cur, r["password_hash"]): fail("The current password is wrong.")
        check(V.validate_password_complexity(new)); check(V.validate_password_confirmation(new, cf))
        if check_pw(new, r["password_hash"]): fail("Choose a password you have not used just now.")
        cn.execute("UPDATE users SET password_hash=?, token_version=token_version+1 WHERE id=?", (hash_pw(new), u["id"])); tv = r["token_version"] + 1
        row = cn.execute(f"SELECT {PUBLIC_COLS}, token_version FROM users WHERE id=?", (u["id"],)).fetchone()
    LE.audit(u["email"], "password_changed", str(u["id"]), ""); token = make_token(row)
    resp = JSONResponse({"ok": True, "msg": "Password changed.", "token": token}); resp.set_cookie(COOKIE, token, max_age=TOKEN_HOURS * 3600, httponly=True, samesite="lax", path="/"); return resp

# ------------------------------------------------------------------ admin dashboard (every route needs the "users" capability)
def admin_ctx(request):
    u, c = me_ctx(request); rbac.need(c, "users"); return u, c
def _active_admins(cn, excluding=None):
    return cn.execute("SELECT COUNT(*) FROM users WHERE role='Admin' AND locked=0 AND id<>?", (excluding or 0,)).fetchone()[0]
def _target(cn, uid):
    r = cn.execute(f"SELECT {PUBLIC_COLS} FROM users WHERE id=?", (uid,)).fetchone()
    if not r: raise HTTPException(404, "User not found.")
    return r

@router.get("/api/admin/overview")
def admin_overview(request: Request):
    admin_ctx(request)
    with db() as cn:
        rows = cn.execute(f"SELECT {PUBLIC_COLS}, profile_picture FROM users ORDER BY id").fetchall(); per = {r: 0 for r in rbac.ROLES}
        for r in rows: per[r["role"]] = per.get(r["role"], 0) + 1
        log = [{**dict(x), "ts": iso(x["ts"])} for x in cn.execute("SELECT ts, actor, event, target, detail FROM audit_log ORDER BY audit_id DESC LIMIT 50").fetchall()]
    return {"ok": True, "users": [{**public(r), "saved_outlet": r["outlet"], "picture": r["profile_picture"]} for r in rows], "kpis": {"total": len(rows), "locked": sum(1 for r in rows if r["locked"]), "active": sum(1 for r in rows if not r["locked"]), "per_role": per},
            "activity": log, "roles": rbac.ROLES, "scoped_roles": sorted(rbac.SCOPED_ROLES), "outlets": outlets(), "matrix": rbac.permission_table()}

@router.post("/api/admin/users")
async def admin_add(request: Request):
    u, c = admin_ctx(request); d = await jbody(request); email, username, password, role, outlet = body_of(d, "email", "username", "password", "role", "outlet")
    email, username, outlet = validate_new_account(email, username, password, password, role, outlet, rbac.ROLES)
    uid = insert_user(email, username, password, role, outlet); LE.audit(u["email"], "user_added", email, f"role={role} outlet={outlet or '-'}"); return ok(f"User {username} added.", id=uid)

@router.post("/api/admin/users/{uid}/role")
async def admin_role(uid: int, request: Request):
    u, c = admin_ctx(request); d = await jbody(request); role, outlet = body_of(d, "role", "outlet"); outlet = outlet.strip().upper()
    if role not in rbac.ROLES: fail("Choose a valid role.")
    with db() as cn:
        t = _target(cn, uid)
        if t["id"] == u["id"]: fail("You cannot change your own role.")
        if t["role"] == "Admin" and role != "Admin" and not _active_admins(cn, t["id"]): fail("The last remaining Admin cannot be demoted.")
        if role in rbac.SCOPED_ROLES:
            outlet = outlet or (t["outlet"] or "")
            if not outlet: fail(f"Choose the outlet for a {role}.")
            if outlet not in outlets(): fail("That outlet does not exist.")
        else: outlet = t["outlet"]                         # keep it: the person may go back to a one-outlet role later
        cn.execute("UPDATE users SET role=?, outlet=? WHERE id=?", (role, outlet, uid))
    LE.audit(u["email"], "role_changed", t["email"], f"{t['role']} -> {role}" + (f" ({outlet})" if outlet and role in rbac.SCOPED_ROLES else "")); return ok(f"{t['username']} is now {role}.")

@router.post("/api/admin/users/{uid}/lock")
def admin_lock(uid: int, request: Request): return _set_lock(uid, request, 1)
@router.post("/api/admin/users/{uid}/unlock")
def admin_unlock(uid: int, request: Request): return _set_lock(uid, request, 0)
def _set_lock(uid, request, lock):
    u, c = admin_ctx(request)
    with db() as cn:
        t = _target(cn, uid)
        if lock and t["id"] == u["id"]: fail("You cannot lock your own account.")
        if lock and t["role"] == "Admin" and not _active_admins(cn, t["id"]): fail("The last active Admin cannot be locked.")
        cn.execute("UPDATE users SET locked=?, failed_attempts=0 WHERE id=?", (lock, uid))
    LE.audit(u["email"], "user_locked" if lock else "user_unlocked", t["email"], ""); return ok(f"{t['username']} is now {'locked' if lock else 'unlocked'}.")

@router.post("/api/admin/users/{uid}/delete")
async def admin_delete(uid: int, request: Request):
    u, c = admin_ctx(request); d = await jbody(request)
    if d.get("confirm") is not True: fail("Confirm the deletion first.")
    with db() as cn:
        t = _target(cn, uid)
        if t["id"] == u["id"]: fail("You cannot delete your own account.")
        if t["role"] == "Admin" and not _active_admins(cn, t["id"]): fail("The last remaining Admin cannot be removed.")
        cn.execute("DELETE FROM users WHERE id=?", (uid,))
    LE.audit(u["email"], "user_deleted", t["email"], f"role={t['role']}"); return ok(f"{t['username']} was deleted.")
