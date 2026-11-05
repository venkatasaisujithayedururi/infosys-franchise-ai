"""Shared page builders: helpers, Command Center (tickets, agents, anomalies), Knowledge Graph."""
import json, datetime
import numpy as np, pandas as pd
import live_engine as LE, entities as EN
import blocks as B
import rbac
from blocks import Q, clean, L, TEAL, BLUE, AMBER, RED, VIOLET, TONE

def can(c, cap): return cap in rbac.caps_of(c["role"])      # same table as need(): a button or form is only drawn for a role that may use it
def latest(agent):
    r = LE.conn().execute("SELECT ts,score,risk,latency_ms,summary,output,cycle_id FROM agent_runs WHERE agent=? ORDER BY run_id DESC LIMIT 1", (agent,)).fetchone()
    if not r: return None
    try: out = json.loads(r[5])
    except Exception: out = {}
    return {"ts": r[0], "score": r[1], "risk": r[2], "ms": r[3], "summary": r[4], "out": out, "cycle": r[6]}
def decision():
    d = Q("SELECT decision_id, ts, score, risk, narrative, evidence FROM decisions ORDER BY decision_id DESC LIMIT 1")
    if not len(d): return None
    try: ev = json.loads(d.evidence[0])
    except Exception: ev = {}
    return {"id": int(d.decision_id[0]), "ts": d.ts[0], "score": float(d.score[0]), "risk": d.risk[0], "narrative": d.narrative[0], "ev": ev}
def scoped(df, c, col="target"):
    return df[df[col].astype(str) == c["scope"]] if c.get("scope") and len(df) else df

# ------------------------------------------------------------------ tickets
def tk_df(c, agent=None, types=None, target=None, statuses=("open", "proposed"), limit=300):
    dom = c["dom"]; sql = "SELECT action_id id, severity, status, type, target, detail, owner, assignee, due, note, ts FROM agent_actions WHERE status IN (%s)" % ",".join("?" * len(statuses)); p = list(statuses)
    ts = types or ([t for t, a in dom.ACTION_AGENT.items() if a == agent] if agent else None)
    if ts: sql += f" AND type IN ({','.join('?' * len(ts))})"; p += list(ts)
    if target: sql += " AND target=?"; p.append(target)
    df = Q(sql + " ORDER BY CASE severity WHEN 'Critical' THEN 0 WHEN 'Warning' THEN 1 ELSE 2 END, action_id DESC LIMIT " + str(limit), p)
    return scoped(df, c)
def ticket_block(c, agent=None, types=None, title="Open tickets", target=None, key=None, limit=60):
    """Read-only list of what the agent has raised (type, target, severity, detail). There is no approval workflow in this version."""
    df = tk_df(c, agent, types, target, limit=limit)
    if not len(df): return B.callout("Nothing raised right now.", "info", title)
    return B.table(df, ["id", "ts", B.pill_col("severity"), "type", "target", "detail"], title=title, h=300, key=key or f"tk_{agent or target or 'all'}", open={"col": "target"} if False else None)
def ist_time(ts):
    """A server timestamp (naive = the server's local time) as a clock time in Indian Standard Time, e.g. 10:42:15 PM IST."""
    try: d = datetime.datetime.fromisoformat(str(ts))
    except Exception: return ts
    d = d.astimezone() if d.tzinfo is None else d
    return d.astimezone(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%I:%M:%S %p IST").lstrip("0")
def hero(c, agent, title, blurb):
    r = latest(agent)
    if r: r = {**r, "ts": ist_time(r["ts"])}
    if c.get("scope") and r: r = {**r, "score": None, "risk": "", "summary": "Showing your outlet only."}      # the agent's score and summary are chain-wide and name other outlets
    return B.hero(agent, title, blurb, r, can_run=can(c, "run"))
def cross(c, targets, own, title="Flagged by other agents for these entities"):
    t = [str(x) for x in list(dict.fromkeys(targets))][:60]
    if not t: return None
    df = Q("SELECT type, target, severity, detail FROM agent_actions WHERE status IN ('open','proposed') AND target IN (%s)" % ",".join("?" * len(t)), t)
    df["agent"] = df.type.map(lambda x: c["dom"].ACTION_AGENT.get(x, "engine")); df = df[df.agent != own].head(30)
    if not len(df): return None
    return B.table(df, ["target", "agent", "type", B.pill_col("severity"), "detail"], title=title, h=240, open={"col": "target"}, key="cross_" + own)

# ------------------------------------------------------------------ Command Center

# ------------------------------------------------------------------ Approvals inbox (human in the loop)
SOURCE = {"manual_request": "Approval request", "quote_approval": "Quote approval", "ml_review": "ML second opinion", "twin_mitigation": "Digital Twin"}





# ------------------------------------------------------------------ Knowledge graph
def entity_explorer(c):
    kind, dom = c["kind"], c["dom"]; e = (c.get("params") or {}).get("e")
    ents = Q("SELECT DISTINCT target FROM agent_actions WHERE status IN ('open','proposed') LIMIT 300").target.tolist()
    base = Q("SELECT outlet_id e FROM outlets ORDER BY outlet_id").e.tolist() if kind == "Franchise" else Q("SELECT port_name e FROM ports ORDER BY congestion_index DESC LIMIT 60").e.tolist()
    opts = list(dict.fromkeys(([c["scope"]] if c.get("scope") else ents + base))); e = e or opts[0]
    d = EN.describe(kind, dom, e); nodes = [{"id": e, "kind": "focus", "size": 34, "color": "#ffffff", "tip": "selected", "label": True}]; links = []
    for n, k, tip in d["rel"]: nodes.append({"id": n, "kind": k, "size": 16, "tip": tip, "label": True, "open": n if EN.kind_of(n) != "port" or kind == "Freight" else None}); links.append((e, n))
    for r in d["tickets"][d["tickets"].status.isin(["open", "proposed"])].itertuples():
        n = f"#{r.id} {r.type}"; ag = dom.ACTION_AGENT.get(r.type, "engine"); nodes += [{"id": n, "kind": "ticket", "size": 14, "color": TONE.get(r.severity), "tip": r.detail[:120], "label": True}, {"id": ag, "kind": "agent", "size": 26, "color": TEAL, "tip": "agent", "label": True}]; links += [(e, n), (n, ag)]
    seen = set(); nodes = [n for n in nodes if not (n["id"] in seen or seen.add(n["id"]))]
    sel = {"t": "form", "id": "kg_pick", "fields": [{"name": "e", "label": "Entity", "type": "select", "options": opts, "value": e}], "submit": "Explore", "url": "page:kg:explore", "title": None, "tone": "primary", "inline": True}
    info = B.table([{"field": k, "value": v} for k, v in d["info"].items()], ["field", "value"], title="What the platform knows", h=230, key="kg_info") if d["info"] else B.callout("No master record for this entity.", "info")
    tk = d["tickets"]
    return [sel, B.row(B.card("Facts", info, B.table(tk, ["id", B.pill_col("severity"), B.pill_col("status"), "type", "owner", "detail"], title="Why is it flagged", h=260, key="kg_tk")), B.card("Relations", B.chart(B.graph(nodes, links), h=470, open={"graph": True}, key="kg_ent")), ratio=[2, 3])]
