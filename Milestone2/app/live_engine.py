"""Shared live agent runtime (FranchiseOps AI + FreightQuote AI).
Domain modules (domain_franchise.py / domain_freight.py) plug in agents, a simulator and action handlers."""
import os, re, json, time, sqlite3, threading, datetime, smtplib, ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
import requests
from config import DB_PATH

_DB_LOCK = threading.RLock()
_TL = threading.local()
def conn():
    """One SQLite connection per thread: nested helpers (emit/set_state) share the caller's transaction instead of deadlocking."""
    c = getattr(_TL, "c", None)
    if c is None:
        c = sqlite3.connect(DB_PATH, timeout=30); c.execute("PRAGMA journal_mode=WAL;"); c.execute("PRAGMA busy_timeout=30000;"); _TL.c = c
    return c
def now(): return datetime.datetime.now().isoformat(timespec="seconds")

@dataclass
class AgentResult:
    agent: str
    score: float = 100.0
    risk: str = "Low"
    summary: str = ""
    findings: dict = field(default_factory=dict)
    actions: list = field(default_factory=list)   # {"type","target","detail","severity","owner"?,"sla_h"?}
    confidence: float = 0.8

def risk_label(score): return "High" if score < 60 else "Medium" if score < 80 else "Low"

def init_live_tables():
    with _DB_LOCK, conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS agent_runs(run_id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, cycle_id TEXT, trigger_src TEXT, agent TEXT, risk TEXT, score REAL, latency_ms INT, summary TEXT, output TEXT);
        CREATE TABLE IF NOT EXISTS agent_actions(action_id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, type TEXT, target TEXT, detail TEXT, severity TEXT, owner TEXT, status TEXT DEFAULT 'open', due TEXT, resolved_ts TEXT, source_cycle TEXT, note TEXT);
        CREATE TABLE IF NOT EXISTS live_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, etype TEXT, entity TEXT, payload TEXT);
        CREATE TABLE IF NOT EXISTS live_state(k TEXT PRIMARY KEY, v TEXT, ts TEXT);
        CREATE TABLE IF NOT EXISTS decisions(decision_id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, cycle_id TEXT, trigger_src TEXT, score REAL, risk TEXT, narrative TEXT, evidence TEXT);
        CREATE TABLE IF NOT EXISTS audit_log(audit_id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, actor TEXT, event TEXT, target TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS ticket_comments(comment_id INTEGER PRIMARY KEY AUTOINCREMENT, action_id INT, ts TEXT, author TEXT, body TEXT);
        CREATE INDEX IF NOT EXISTS ix_act_status ON agent_actions(status, type, target);
        CREATE INDEX IF NOT EXISTS ix_runs_agent ON agent_runs(agent, run_id);
        CREATE INDEX IF NOT EXISTS ix_runs_cycle ON agent_runs(cycle_id);
        CREATE INDEX IF NOT EXISTS ix_cm_act ON ticket_comments(action_id);
        CREATE INDEX IF NOT EXISTS ix_audit_ts ON audit_log(audit_id);
        """)
        for col in ("assignee TEXT", "approval TEXT"):
            try: c.execute(f"ALTER TABLE agent_actions ADD COLUMN {col}")
            except sqlite3.OperationalError: pass
        for t, cols in (("sales", "outlet_id, ts"), ("attendance", "outlet_id, ts"), ("feedback", "outlet_id, date")):
            try: c.execute(f"CREATE INDEX IF NOT EXISTS ix_{t}_o ON {t}({cols})")
            except sqlite3.OperationalError: pass

def audit(actor, event, target="", detail=""):
    with _DB_LOCK, conn() as c:
        c.execute("INSERT INTO audit_log(ts,actor,event,target,detail) VALUES(?,?,?,?,?)", (now(), str(actor), event, str(target), str(detail)[:500]))

RETAIN = {"sales": ("ts", 6000), "attendance": ("ts", 3000), "feedback": ("date", 2000), "agent_runs": ("ts", 4000), "decisions": ("ts", 800), "live_events": ("ts", 2000), "audit_log": ("ts", 20000)}
def maintenance():
    """Keep the live DB bounded: prune to the newest N rows per table (never touches seed/master data)."""
    n = 0
    with _DB_LOCK, conn() as c:
        for t, (col, keep) in RETAIN.items():
            try:
                pk = c.execute(f"PRAGMA table_info({t})").fetchall()
                if not pk: continue
                if t in ("sales", "attendance"):
                    cnt = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    if cnt > keep * 4: n += c.execute(f"DELETE FROM {t} WHERE rowid IN (SELECT rowid FROM {t} ORDER BY rowid ASC LIMIT ?)", (cnt - keep * 2,)).rowcount
                else:
                    cnt = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    if cnt > keep * 2: n += c.execute(f"DELETE FROM {t} WHERE rowid IN (SELECT rowid FROM {t} ORDER BY rowid ASC LIMIT ?)", (cnt - keep,)).rowcount
            except sqlite3.OperationalError: pass
    return n

def set_state(k, v):
    with _DB_LOCK, conn() as c:
        c.execute("INSERT OR REPLACE INTO live_state(k,v,ts) VALUES(?,?,?)", (k, json.dumps(v, default=str), now()))
def get_state(k, default=None):
    with _DB_LOCK, conn() as c:
        r = c.execute("SELECT v FROM live_state WHERE k=?", (k,)).fetchone()
    return json.loads(r[0]) if r else default
def emit(etype, entity, payload=None):
    with _DB_LOCK, conn() as c:
        c.execute("INSERT INTO live_events(ts,etype,entity,payload) VALUES(?,?,?,?)", (now(), etype, str(entity), json.dumps(payload or {}, default=str)))

# ---------------- notifications (real channels, all optional via env) ----------------
_SENT = {}
def _nk(s): return re.sub(r"\d+(?:\.\d+)?", "#", str(s))
def notify(dom, target, severity, category, message):
    with _DB_LOCK, conn() as c:
        c.execute(f"INSERT INTO alerts ({dom.ENTITY_COL}, severity, category, message, date) VALUES (?,?,?,?,?)",
                  (target, severity, category, message, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
    if severity not in ("Critical", "High"): return
    key = (target, category, _nk(message))
    if time.time() - _SENT.get(key, 0) < 3600: return          # no alert spam
    _SENT[key] = time.time()
    text = f"[{dom.NAME}] {severity} · {target} · {category}: {message}"
    for var in ("SLACK_WEBHOOK_URL", "TEAMS_WEBHOOK_URL"):
        if os.environ.get(var):
            try: requests.post(os.environ[var], json={"text": text}, timeout=5)
            except Exception: pass
    em, pw, to = os.environ.get("EMAIL_ADDRESS") or os.environ.get("EMAIL_ID"), (os.environ.get("EMAIL_APP_PASSWORD") or os.environ.get("EMAIL_PASSWORD") or "").replace(" ", ""), os.environ.get("ALERT_EMAIL_TO")
    if em and pw and to:
        try:
            m = EmailMessage(); m["Subject"] = text[:90]; m["From"] = em; m["To"] = to; m.set_content(text)
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=15) as s:
                s.login(em, pw); s.send_message(m)
        except Exception: pass
    def _mail_subscribers():
        try:
            import mailer
            if not mailer.configured(): return
            with conn() as cc: rows = [r[0] for r in cc.execute("SELECT email FROM user_prefs WHERE email_alerts=1")]
            for e in rows: mailer.send(e, text[:90], text)
        except Exception: pass
    threading.Thread(target=_mail_subscribers, daemon=True).start()
    sid, tok, frm, tph = (os.environ.get(k) for k in ("TWILIO_SID", "TWILIO_TOKEN", "TWILIO_FROM", "ALERT_SMS_TO"))
    if sid and tok and frm and tph and getattr(dom, "SMS", False):
        try: requests.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", auth=(sid, tok),
                           data={"From": frm, "To": tph, "Body": text[:300]}, timeout=8)
        except Exception: pass

# ---------------- action layer ----------------
SLA_H = {"Critical": 24, "Warning": 72, "Info": 168}
def policy(dom):
    """Autonomy policy per action type: 'auto' (agent executes) or 'approval' (human approves first). Admin-editable."""
    return {}      # no approval queue in this version: agents act on their own
def set_policy(t, mode, actor="admin"):
    p = get_state("policy", {}) or {}; p[t] = mode; set_state("policy", p); audit(actor, "policy", t, mode)
# ---------------------------------------------------------------- multi-level approval chains
# Each ticket that needs a human gets an ordered chain of steps (table approval_steps). Every step names a role; the next step opens only after the previous one is approved.
# Four-eyes rule: nobody can approve two steps of the same ticket, and nobody can approve a request they raised. Any step rejection rejects the whole ticket.
LADDER = ["Operations Manager", "Franchise Owner", "Admin"]
def _role_ok(role, need): return role == "Admin" or role == need or (need == "Operations Manager" and role == "Franchise Owner")
def chain_for(severity, typ, levels=None):
    cfg = get_state("approval_chain", {}) or {}
    if levels: return LADDER[:1] + (["Admin"] if int(levels) >= 2 else [])
    if typ in cfg and cfg[typ]: return list(cfg[typ])
    return ["Operations Manager", "Admin"] if severity == "Critical" else ["Operations Manager"]
def _steps_ddl(c): c.execute("CREATE TABLE IF NOT EXISTS approval_steps(action_id INT, step INT, role TEXT, status TEXT DEFAULT 'pending', by TEXT, ts TEXT, note TEXT, PRIMARY KEY(action_id, step))")
def _ensure_chain(c, aid, severity, typ):
    _steps_ddl(c)
    if not c.execute("SELECT 1 FROM approval_steps WHERE action_id=?", (aid,)).fetchone():
        for i, r in enumerate(chain_for(severity, typ)): c.execute("INSERT INTO approval_steps(action_id,step,role) VALUES(?,?,?)", (aid, i + 1, r))
def chains(ids):
    """{action_id: [{step, role, status, by}]} for the ticket list (creates the default chain for tickets that have none yet)."""
    out = {}
    if not ids: return out
    with _DB_LOCK, conn() as c:
        _steps_ddl(c)
        for aid, sev, typ in c.execute("SELECT action_id, severity, type FROM agent_actions WHERE action_id IN (%s) AND (status='proposed' OR type='quote_approval')" % ",".join("?" * len(ids)), list(ids)).fetchall(): _ensure_chain(c, aid, sev, typ)
        for r in c.execute("SELECT action_id, step, role, status, by FROM approval_steps WHERE action_id IN (%s) ORDER BY action_id, step" % ",".join("?" * len(ids)), list(ids)).fetchall(): out.setdefault(r[0], []).append({"step": r[1], "role": r[2], "status": r[3], "by": r[4] or ""})
    return out
def next_role(chain):
    for s in chain or []:
        if s["status"] == "pending": return s["role"]
    return None
def advance(aid, actor, role, approve=True, note=""):
    """Record one decision. Returns ('final'|'partial'|'rejected'|'denied'|'missing', message). Does not execute anything."""
    with _DB_LOCK, conn() as c:
        r = c.execute("SELECT severity, type, note FROM agent_actions WHERE action_id=? AND (status='proposed' OR type='quote_approval')", (aid,)).fetchone()
        if not r: return "missing", "nothing to approve on this ticket"
        _ensure_chain(c, aid, r[0], r[1]); steps = c.execute("SELECT step, role, status, by FROM approval_steps WHERE action_id=? ORDER BY step", (aid,)).fetchall()
        cur = next((s for s in steps if s[2] == "pending"), None)
        if not cur: return "missing", "this ticket has no pending approval step"
        if not _role_ok(role, cur[1]): return "denied", f"step {cur[0]} needs a {cur[1]} (you are {role})"
        if approve:
            if actor in [s[3] for s in steps if s[3]]: return "denied", "four-eyes rule: you already approved an earlier step of this ticket"
            if f"requested by {actor}" in (r[2] or ""): return "denied", "four-eyes rule: you cannot approve your own request"
        c.execute("UPDATE approval_steps SET status=?, by=?, ts=?, note=? WHERE action_id=? AND step=?", ("approved" if approve else "rejected", actor, now(), note, aid, cur[0]))
        left = [s for s in steps if s[2] == "pending" and s[0] != cur[0]]
        if not approve: return "rejected", f"rejected at step {cur[0]} ({cur[1]})"
        if left:
            c.execute("UPDATE agent_actions SET note=COALESCE(note,'')||? WHERE action_id=?", (f" step {cur[0]}/{len(steps)} approved by {actor};", aid)); audit(actor, "approve_step", aid, f"step {cur[0]}/{len(steps)} {note}".strip())
            return "partial", f"step {cur[0]} of {len(steps)} approved; waiting for {left[0][1]}"
    return "final", "all steps approved"
def request_approval(dom, typ, target, detail, severity, requester, levels=None):
    """Anyone with access can ask for a decision: creates a proposed ticket with its own approval chain."""
    a = {"type": "manual_request", "target": target, "detail": detail, "request": typ}
    with _DB_LOCK, conn() as c:
        cur = c.execute("INSERT INTO agent_actions(ts,type,target,detail,severity,owner,status,note,approval) VALUES(?,?,?,?,?,?,'proposed',?,?)", (now(), "manual_request", target, f"{typ}: {detail}", severity, requester, f"requested by {requester};", json.dumps(a)))
        aid = cur.lastrowid; _steps_ddl(c)
        for i, r in enumerate(chain_for(severity, "manual_request", levels)): c.execute("INSERT INTO approval_steps(action_id,step,role) VALUES(?,?,?)", (aid, i + 1, r))
    audit(requester, "request_approval", f"{typ}:{target}", detail[:120]); return aid
def approve_action(dom, aid, actor="user", approve=True, note="", role="Admin"):
    """Human-in-the-loop: runs the approval chain; the action executes only when the last step is approved. Returns (state, message)."""
    st, msg = advance(aid, actor, role, approve, note)
    if st in ("denied", "missing", "partial"): return st, msg
    with _DB_LOCK, conn() as c:
        r = c.execute("SELECT type,target,detail,severity,approval FROM agent_actions WHERE action_id=?", (aid,)).fetchone()
        if st == "final":
            a = json.loads(r[4] or "{}") or {"type": r[0], "target": r[1], "detail": r[2]}
            try: res = dom.apply(a, c) or ""
            except Exception as ex: res = f"apply failed: {ex}"
            if r[0] == "manual_request": c.execute("UPDATE agent_actions SET status='resolved', resolved_ts=?, note=COALESCE(note,'')||?, approval='approved' WHERE action_id=?", (now(), f" approved by {actor}; request granted", aid))
            else: c.execute("UPDATE agent_actions SET status='open', note=COALESCE(note,'')||?, approval=? WHERE action_id=?", (f" approved by {actor}; {res}", "approved", aid))
        else:
            c.execute("UPDATE agent_actions SET status='rejected', resolved_ts=?, note=COALESCE(note,'')||?, approval='rejected' WHERE action_id=?", (now(), f" rejected by {actor} {note}", aid))
    audit(actor, "approve" if approve else "reject", f"{r[0]}:{r[1]}", note); return st, msg
def assign_action(aid, assignee, actor="user"):
    with _DB_LOCK, conn() as c: c.execute("UPDATE agent_actions SET assignee=? WHERE action_id=?", (assignee, aid))
    audit(actor, "assign", aid, assignee)
def comment_action(aid, author, body):
    with _DB_LOCK, conn() as c: c.execute("INSERT INTO ticket_comments(action_id,ts,author,body) VALUES(?,?,?,?)", (now(), author, body) if False else (aid, now(), author, body))
    audit(author, "comment", aid, body[:80])
def act(dom, decision, cid, results):
    raised = set(); sent = 0; extra = 0; pol = policy(dom)
    for a in decision.get("actions", []):
        key = (a["type"], str(a["target"]), _nk(a["detail"])); raised.add(key)
        sev = a.get("severity", "Warning")
        due = (datetime.datetime.now() + datetime.timedelta(hours=a.get("sla_h", SLA_H.get(sev, 72)))).isoformat(timespec="seconds")
        with _DB_LOCK, conn() as c:
            hit = next((r[0] for r in c.execute("SELECT action_id, detail FROM agent_actions WHERE type=? AND target=? AND status IN ('open','proposed')", key[:2]).fetchall() if _nk(r[1].replace("OVERDUE: ", "")) == key[2]), None)
            if hit:
                c.execute("UPDATE agent_actions SET detail=CASE WHEN detail LIKE 'OVERDUE:%' THEN 'OVERDUE: '||? ELSE ? END WHERE action_id=?", (a["detail"], a["detail"], hit)); continue
            note = ""; status = "open"; appr = None
            if pol.get(a["type"]) == "approval": status = "proposed"; note = "awaiting human approval"; appr = json.dumps(a, default=str)
            else:
                try: note = dom.apply(a, c) or ""
                except Exception as ex: note = f"apply failed: {ex}"
            c.execute("INSERT INTO agent_actions(ts,type,target,detail,severity,owner,due,source_cycle,note,status,approval) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (now(), a["type"], str(a["target"]), a["detail"], sev, a.get("owner") or dom.OWNER.get(a["type"], "Operations"), due, cid, note, status, appr))
        if sev == "Critical":
            if sent < 8: notify(dom, a["target"], "Critical", a["type"], a["detail"]); sent += 1
            else: extra += 1
    if extra: notify(dom, "MULTIPLE", "Critical", "Summary", f"{extra} more critical actions raised this cycle; see Command Center")
    with _DB_LOCK, conn() as c:      # auto-close: the owning agent re-ran and no longer raises it
        for aid, t, tg, d in c.execute("SELECT action_id,type,target,detail FROM agent_actions WHERE status IN ('open','proposed')").fetchall():
            if dom.ACTION_AGENT.get(t) in results and (t, tg, _nk(d.replace("OVERDUE: ", ""))) not in raised:
                c.execute("UPDATE agent_actions SET status='auto-closed', resolved_ts=? WHERE action_id=?", (now(), aid))

def escalate_overdue(dom):
    n = 0
    with _DB_LOCK, conn() as c:
        rows = c.execute("SELECT action_id,target,detail,type FROM agent_actions WHERE status='open' AND due<? AND detail NOT LIKE 'OVERDUE:%'", (now(),)).fetchall()
        for aid, tg, d, t in rows:
            nd = (datetime.datetime.now() + datetime.timedelta(hours=24)).isoformat(timespec="seconds")
            c.execute("UPDATE agent_actions SET severity='Critical', owner=?, detail=?, due=? WHERE action_id=?", (dom.ESCALATE_TO, "OVERDUE: " + d, nd, aid)); n += 1
    for aid, tg, d, t in rows: notify(dom, tg, "Critical", "Escalation", "OVERDUE: " + d)
    return n

def resolve_action(aid, status="resolved", note="", actor="user"):
    audit(actor, status, aid, note)
    with _DB_LOCK, conn() as c:
        c.execute("UPDATE agent_actions SET status=?, resolved_ts=?, note=COALESCE(note,'')||? WHERE action_id=?", (status, now(), (" " + note) if note else "", aid))

# ---------------- orchestration (LangGraph when installed, plain loop otherwise) ----------------
def _log_run(cid, trig, res, ms):
    with _DB_LOCK, conn() as c:
        c.execute("INSERT INTO agent_runs(ts,cycle_id,trigger_src,agent,risk,score,latency_ms,summary,output) VALUES(?,?,?,?,?,?,?,?,?)",
                  (now(), cid, trig, res.agent, res.risk, res.score, ms, res.summary, json.dumps(res.findings, default=str)[:30000]))

def make_nodes(dom):
    def planner(s): return {"queue": dom.plan(s["request"]), "results": {}}
    def agent(s):
        name = s["queue"][0]; t = time.time()
        try: res = dom.AGENTS[name](s)
        except Exception as e: res = AgentResult(name, 50.0, "Medium", f"agent error: {e}")
        _log_run(s["cycle_id"], s["trigger"], res, int((time.time() - t) * 1000))
        new = [n for n in dom.REPLAN.get(name, lambda r: [])(res) if n not in s["results"] and n not in s["queue"]]
        if new: _log_run(s["cycle_id"], s["trigger"], AgentResult("re-plan", 100, "Low", f"{name} risk {res.risk}: adding {', '.join(new)}"), 0)
        return {"results": {**s["results"], name: res}, "queue": s["queue"][1:] + new}
    def engine(s):
        d = dom.engine(s)
        with _DB_LOCK, conn() as c:
            c.execute("INSERT INTO decisions(ts,cycle_id,trigger_src,score,risk,narrative,evidence) VALUES(?,?,?,?,?,?,?)",
                      (now(), s["cycle_id"], s["trigger"], d["score"], d["risk"], d["narrative"], json.dumps({k: v for k, v in d.items() if k not in ("narrative", "actions")}, default=str)))
        return {"decision": d}
    def act_node(s): act(dom, s["decision"], s["cycle_id"], s["results"]); return {}
    return planner, agent, engine, act_node

def _compile(dom):
    from typing import TypedDict
    from langgraph.graph import StateGraph, END
    class S(TypedDict, total=False):
        cycle_id: str; trigger: str; request: str; queue: list; results: dict; decision: dict
    planner, agent, engine, act_node = make_nodes(dom)
    g = StateGraph(S)
    for n, f in (("planner", planner), ("agent", agent), ("engine", engine), ("act", act_node)): g.add_node(n, f)
    g.set_entry_point("planner"); g.add_edge("planner", "agent")
    g.add_conditional_edges("agent", lambda s: "agent" if s["queue"] else "engine")
    g.add_edge("engine", "act"); g.add_edge("act", END)
    return g.compile()

_GRAPHS = {}
def run_cycle(dom, trigger="manual", request=""):
    init_live_tables()
    cid = datetime.datetime.now().strftime("%m%d-%H%M%S") + "-" + trigger[:4]
    s = {"cycle_id": cid, "trigger": trigger, "request": request, "queue": [], "results": {}, "decision": {}}
    try:
        if dom.NAME not in _GRAPHS: _GRAPHS[dom.NAME] = _compile(dom)
        out = _GRAPHS[dom.NAME].invoke(s)
    except ImportError:
        planner, agent, engine, act_node = make_nodes(dom)
        s.update(planner(s))
        while s["queue"]: s.update(agent(s))
        s.update(engine(s)); act_node(s); out = s
    return out["decision"]

# ---------------- background runtime ----------------
class Runtime:
    def __init__(self, dom, tick=5, cycle=60, min_gap=12):
        self.dom, self.tick, self.cycle, self.min_gap = dom, tick, cycle, min_gap
        self.stop = threading.Event(); self.ticks = 0; self.cycles = 0; self.last_cycle = 0; self.last_err = ""
        self.th = threading.Thread(target=self._loop, daemon=True); self.th.start()
        if hasattr(dom, "feed"): self.fth = threading.Thread(target=self._feed_loop, daemon=True); self.fth.start()
    def _feed_loop(self):          # network polling lives here so slow/offline APIs never stall the tick
        while not self.stop.is_set():
            try: self.dom.feed()
            except Exception as e: self.last_err = f"feed: {e}"
            self.stop.wait(int(os.environ.get("FEED_SEC", 60)))
    def _loop(self):
        init_live_tables(); set_state("boot", {"stage": "bootstrap", "ts": now()})
        try: self.dom.bootstrap()
        except Exception as e: self.last_err = f"bootstrap: {e}"
        set_state("boot", {"stage": "first_cycle", "ts": now()})
        while not self.stop.is_set():
            try:
                reasons = self.dom.tick() or []; self.ticks += 1
                if self.ticks % 120 == 0: maintenance()
                reasons = reasons + (self.dom.process() or [])
                due = time.time() - self.last_cycle
                if (reasons and due >= self.min_gap) or due >= self.cycle:
                    run_cycle(self.dom, "event" if reasons else "sched", ""); escalate_overdue(self.dom)
                    self.cycles += 1; self.last_cycle = time.time()
                    set_state("runtime", {"ticks": self.ticks, "cycles": self.cycles, "last_cycle": now(), "reasons": reasons[:3], "err": self.last_err})
                    if self.cycles == 1: set_state("boot", {"stage": "ready", "ts": now()})
                elif self.ticks % 6 == 0: set_state("runtime", {**(get_state("runtime", {}) or {}), "ticks": self.ticks})
            except Exception as e: self.last_err = str(e)
            self.stop.wait(self.tick)

_RT = None; _RT_LOCK = threading.Lock()
def start_runtime(dom):
    global _RT
    with _RT_LOCK:
        if _RT is None:
            _RT = Runtime(dom, int(os.environ.get("LIVE_TICK_SEC", 5)), int(os.environ.get("LIVE_CYCLE_SEC", 60)))
    return _RT
