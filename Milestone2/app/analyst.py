"""Question understanding for the Copilot, ahead of the generic table query (qa.py). Each handler computes the answer from live data and returns
{"answer": lead text (markdown), "df": optional table, "sql": how it was computed, "extra": more markdown}. Nothing here asks the language model for a number."""
import re, json, datetime
import numpy as np, pandas as pd
from blocks import Q
import qa as QA, alts
CITY_STATE = {"Mumbai": "Maharashtra", "Pune": "Maharashtra", "Nashik": "Maharashtra", "Nagpur": "Maharashtra", "Delhi": "Delhi", "Bengaluru": "Karnataka", "Mysuru": "Karnataka", "Hyderabad": "Telangana", "Chennai": "Tamil Nadu", "Coimbatore": "Tamil Nadu", "Madurai": "Tamil Nadu",
              "Kolkata": "West Bengal", "Ahmedabad": "Gujarat", "Surat": "Gujarat", "Vadodara": "Gujarat", "Jaipur": "Rajasthan", "Lucknow": "Uttar Pradesh", "Kochi": "Kerala", "Thiruvananthapuram": "Kerala", "Chandigarh": "Chandigarh", "Bhopal": "Madhya Pradesh", "Indore": "Madhya Pradesh",
              "Patna": "Bihar", "Ranchi": "Jharkhand", "Raipur": "Chhattisgarh", "Bhubaneswar": "Odisha", "Guwahati": "Assam", "Goa": "Goa", "Visakhapatnam": "Andhra Pradesh", "Vijayawada": "Andhra Pradesh", "Kanpur": "Uttar Pradesh", "Dehradun": "Uttarakhand", "Amritsar": "Punjab", "Ludhiana": "Punjab"}
CHOKE = {"suez": ("Suez Canal", 30.5, 32.3), "panama": ("Panama Canal", 9.1, -79.7), "malacca": ("Strait of Malacca", 2.5, 101.5), "hormuz": ("Strait of Hormuz", 26.5, 56.5), "bosphorus": ("Bosphorus", 41.1, 29.0), "cape": ("Cape of Good Hope", -34.4, 18.5), "red sea": ("Red Sea", 18.0, 40.0)}
def _w(q, t): return re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", q) is not None
def _md(df, n=10): return QA.md(df.head(n)) if df is not None and len(df) else ""
def _health(dec): return (((dec or {}).get("ev") or {}).get("health")) or {}
def _agent_scores(e):
    import entities as EN; out = {}
    for a in ("outlet", "inventory", "staff", "marketing", "audit", "feedback"):
        v = EN.latest_out(a).get("per_outlet", {}).get(e)
        if v is not None: out[a] = round(float(v), 1)
    return out
NEXT = {"staffing_shortage": "add a cover shift or move staff from a nearby outlet", "health_alert": "review the lowest agent score below and fix that first", "reorder": "place the reorder or transfer stock from a nearby outlet", "stockout": "reorder now or transfer stock",
        "corrective_action": "complete the corrective plan before the re-audit", "anomaly_review": "check the POS feed and the day's sales for this outlet", "campaign_review": "pause or re-target the campaign", "retention": "talk to the staff at risk and review overtime"}
# ------------------------------------------------------------------------------------------------ Franchise
def explain_outlet(e, dec):
    o = Q("SELECT * FROM outlets WHERE outlet_id=?", (e,))
    if not len(o): return None
    r = o.iloc[0]; h = _health(dec).get(e); sc = _agent_scores(e); tk = Q("SELECT action_id id, type, severity, status, detail FROM agent_actions WHERE target=? AND status IN ('open','proposed') ORDER BY CASE severity WHEN 'Critical' THEN 0 WHEN 'Warning' THEN 1 ELSE 2 END, action_id DESC LIMIT 8", (e,))
    avg = Q("SELECT AVG(revenue) rv, AVG(customer_satisfaction) cs FROM outlets").iloc[0]; low = Q("SELECT COUNT(*) n FROM inventory WHERE outlet_id=? AND current_stock<=reorder_threshold*1.5", (e,)).n[0]
    att = Q("SELECT AVG(predicted_attrition_prob) p, COUNT(*) n FROM staff WHERE outlet_id=?", (e,)).iloc[0]
    lines = []
    if h is not None: lines.append(f"Health score **{h:.1f}**/100 ({'Critical' if h < 60 else 'Needs attention' if h < 80 else 'Healthy'}).")
    if sc: worst = sorted(sc.items(), key=lambda kv: kv[1])[:2]; lines.append("Weakest areas: " + ", ".join(f"**{a}** {v}" for a, v in worst) + " (each agent scores 0-100, higher is better).")
    lines.append(f"Revenue {r.revenue:,.0f} ({(r.revenue / avg.rv - 1):+.0%} vs chain average), satisfaction {r.customer_satisfaction:.2f} (chain {avg.cs:.2f}), {int(att.n)} staff with average attrition risk {att.p:.0%}, {int(low)} SKUs at or near reorder level.")
    why = "\n".join(f"- {t.type} ({t.severity}): {t.detail}" + (f" → {NEXT[t.type]}" if t.type in NEXT else "") for t in tk.itertuples()) or "- no open tickets"
    return {"answer": (f"**{e}** ({r.outlet_name}, {r.location}) is flagged because:\n" if (h is None or h < 80 or len(tk)) else f"**{e}** ({r.outlet_name}, {r.location}) is not flagged right now; here is its status:\n") + "\n".join("- " + l for l in lines) + "\n\n**Open tickets:**\n" + why, "df": pd.DataFrame([{"agent": a, "score": v} for a, v in sc.items()]) if sc else None, "sql": f"decision health + agent per_outlet scores + agent_actions for {e}"}
def risk_rank(q, dec, scope, n=5):
    hl = _health(dec)
    if not hl: return None
    s = pd.Series(hl).astype(float); worst = bool(re.search(r"\b(highest risk|most at risk|worst|lowest|riskiest|critical|weakest|needs? attention|problem|bottom)\b", q)); best = bool(re.search(r"\b(best|top|highest health|strongest|healthiest)\b", q)) and not re.search(r"highest risk", q)
    both = re.search(r"best.*worst|worst.*best", q) is not None
    if scope: s = s[s.index == scope]
    o = Q("SELECT outlet_id, outlet_name, location, revenue, customer_satisfaction csat FROM outlets").set_index("outlet_id")
    def frame(ix):
        rows = []
        for e in ix:
            sc = _agent_scores(e); wk = min(sc, key=sc.get) if sc else "-"; ct = int(Q("SELECT COUNT(*) n FROM agent_actions WHERE target=? AND status IN ('open','proposed') AND severity='Critical'", (e,)).n[0])
            rows.append({"outlet": e, "name": o.name if False else (o.outlet_name.get(e, "") if e in o.index else ""), "location": o.location.get(e, ""), "health": round(float(s[e]), 1), "weakest_area": f"{wk} {sc.get(wk, '')}", "critical_tickets": ct, "revenue": o.revenue.get(e), "csat": o.csat.get(e)})
        return pd.DataFrame(rows)
    low = s.sort_values().head(n).index; hi = s.sort_values(ascending=False).head(n).index
    if both or (best and worst):
        a, b = frame(hi), frame(low); return {"answer": f"Best outlet: **{a.outlet[0]}** (health {a.health[0]}). Worst outlet: **{b.outlet[0]}** (health {b.health[0]}). Health combines outlet, inventory, staff, marketing, audit and feedback agent scores.", "df": None, "sql": "decision health per outlet", "extra": "**Top " + str(n) + " by health**\n" + QA.md(a) + "\n\n**Bottom " + str(n) + " by health**\n" + QA.md(b)}
    if best and not worst: d = frame(hi); return {"answer": f"Healthiest outlet: **{d.outlet[0]}** (health {d.health[0]}, {d.location[0]}). Top {n} below.", "df": d, "sql": "decision health per outlet, descending"}
    d = frame(low); crit = int((s < 60).sum()); return {"answer": f"Highest risk: **{d.outlet[0]}** (health {d.health[0]}, weakest area {d.weakest_area[0]}). {crit} outlets are below 60 (critical). Lowest {n} below; ask \"why is {d.outlet[0]} flagged\" for the reasons.", "df": d, "sql": "decision health per outlet, ascending"}
def inventory_status(scope):
    w = " WHERE outlet_id=?" if scope else ""; p = (scope,) if scope else ()
    d = Q("SELECT outlet_id, sku_name, category, current_stock st, reorder_threshold thr, weekly_demand wk, lead_time_days lead, stockout_risk_prob p FROM inventory" + w, p)
    if not len(d): return None
    d["cover_d"] = d.st / (d.wk / 7).replace(0, np.nan); below = d[d.st <= d.thr]; wk1 = d[d.cover_d < 7]; lt = d[d.cover_d < d.lead]
    po = Q("SELECT status, COUNT(*) n FROM purchase_orders" + w + " GROUP BY status", p); cat = d.groupby("category").agg(skus=("sku_name", "count"), below_reorder=("st", lambda s: int((d.loc[s.index, "st"] <= d.loc[s.index, "thr"]).sum())), avg_cover_days=("cover_d", "mean"), avg_risk=("p", "mean")).reset_index().sort_values("avg_risk", ascending=False)
    worst = d.sort_values("cover_d").head(8)[["outlet_id", "sku_name", "st", "cover_d", "lead", "p"]].rename(columns={"st": "stock", "cover_d": "days_of_cover", "lead": "lead_days", "p": "stockout_risk"})
    return {"answer": f"Inventory: **{len(d):,}** SKU records; **{len(below):,}** at or below reorder level, **{len(wk1):,}** have under 7 days of cover, **{len(lt):,}** will run out before a new order can arrive (cover shorter than lead time). Average stock-out risk {d.p.mean():.0%}." + (" Open purchase orders: " + ", ".join(f"{r.status} {r.n}" for r in po.itertuples()) + "." if len(po) else ""), "df": worst, "sql": "inventory: stock vs reorder threshold, cover = stock ÷ daily demand", "extra": "**By category**\n" + QA.md(cat.round(2))}
def sales_trend(scope):
    w = " AND outlet_id=?" if scope else ""; p = (scope,) if scope else ()
    d = Q(f"SELECT substr(ts,1,10) day, SUM(amount) amount, SUM(tx_count) tx FROM sales WHERE ts IS NOT NULL{w} GROUP BY day ORDER BY day DESC LIMIT 14", p)
    if len(d) < 2: return None
    d = d.iloc[::-1].reset_index(drop=True); last7, prev7 = d.tail(7).amount.sum(), d.iloc[:-7].tail(7).amount.sum() if len(d) > 7 else np.nan
    ch = f" ({(last7 / prev7 - 1):+.1%} vs the 7 days before)" if prev7 == prev7 and prev7 else ""
    return {"answer": f"Sales over the last 7 recorded days: **{last7:,.0f}**{ch}. Best day {d.loc[d.amount.idxmax(), 'day']} ({d.amount.max():,.0f}), weakest {d.loc[d.amount.idxmin(), 'day']} ({d.amount.min():,.0f}).", "df": d.tail(10), "sql": "sales grouped by day"}

def _place(ql):
    """Find a state or city named in the question. Returns ("state"|"city", name) or None."""
    flat = re.sub(r"[^a-z]", "", ql); cities = Q("SELECT DISTINCT location FROM outlets").location.dropna().tolist()
    for st in sorted(set(CITY_STATE.values()), key=len, reverse=True):
        if re.sub(r"[^a-z]", "", st.lower()) in flat: return "state", st
    for ct in sorted(cities, key=len, reverse=True):
        if re.search(r"\b" + re.escape(ct.lower()) + r"\b", ql): return "city", ct
    return None
def outlets_in_place(ql, scope=None):
    pl = _place(ql)
    if not pl: return None
    kind, name = pl; o = Q("SELECT outlet_id, outlet_name name, location, tier, revenue, customer_satisfaction csat, staff_headcount staff FROM outlets")
    o["state"] = o.location.map(CITY_STATE).fillna("Other"); d = o[o.state == name] if kind == "state" else o[o.location == name]
    if scope: d = d[d.outlet_id == scope]           # RBAC: a scoped role only sees its own outlet
    if not len(d): return {"answer": f"No outlets found in {name}.", "df": None, "sql": "outlets filtered by place"}
    by = d.groupby("location").size().sort_values(ascending=False); txt = ", ".join(f"{k} {v}" for k, v in by.items())
    return {"answer": f"**{len(d)}** outlets in {name}" + (f": {txt}." if kind == "state" else "."), "df": d.drop(columns=["state"]).sort_values(["location", "outlet_id"]), "sql": f"outlets where {'state (from city)' if kind == 'state' else 'location'} = {name}"}
def staff_by_place(ql, scope=None):
    s = Q("SELECT s.staff_id, s.outlet_id, o.location FROM staff s LEFT JOIN outlets o USING(outlet_id)")
    if not len(s): return None
    if scope: s = s[s.outlet_id == scope]           # RBAC: a scoped role only sees its own outlet
    s["state"] = s.location.map(CITY_STATE).fillna("Other"); pl = _place(ql)
    if pl:
        kind, name = pl; d = s[s.state == name] if kind == "state" else s[s.location == name]; g = d.groupby("location").size().sort_values(ascending=False).reset_index(name="employees")
        return {"answer": f"**{len(d):,}** employees in {name}" + (f"; most in **{g.location.iloc[0]}** ({int(g.employees.iloc[0]):,})." if len(g) else "."), "df": g, "sql": f"staff joined to outlets, place = {name}"}
    by_state = bool(re.search(r"\bstates?\b", ql)); by_out = bool(re.search(r"\boutlets?\b", ql)); col = "outlet_id" if by_out else ("state" if by_state else "location")
    g = s.groupby(col).size().sort_values(ascending=False).head(15).reset_index(name="employees"); low = bool(re.search(r"\b(fewest|least|lowest|less|low number)\b", ql)); r = (s.groupby(col).size().sort_values().reset_index(name="employees").iloc[0] if low else g.iloc[0])
    return {"answer": f"**{r[col]}** has the {'fewest' if low else 'most'} employees: **{int(r.employees):,}** (of {len(s):,} in total, by {'outlet' if by_out else 'state' if by_state else 'city'}).", "df": g, "sql": f"staff joined to outlets, grouped by {col}"}
def by_state(q):
    o = Q("SELECT outlet_id, location, revenue FROM outlets"); o["state"] = o.location.map(CITY_STATE).fillna("Other"); g = o.groupby("state").agg(outlets=("outlet_id", "count"), revenue=("revenue", "sum")).reset_index().sort_values("outlets", ascending=False)
    low = bool(re.search(r"\b(fewest|least|lowest)\b", q)); r = g.iloc[-1] if low else g.iloc[0]
    return {"answer": f"**{r.state}** has the {'fewest' if low else 'most'} outlets: **{int(r.outlets)}**. Your outlets table stores the city, so states are derived from the city name.", "df": g, "sql": "outlets grouped by state (city → state mapping)"}
def staff_status(scope):
    w = " WHERE outlet_id=?" if scope else ""; p = (scope,) if scope else ()
    s = Q("SELECT outlet_id, role, overtime_hrs ot, predicted_attrition_prob pr FROM staff" + w, p); at = Q("SELECT status, COUNT(*) n FROM attendance" + (" WHERE outlet_id=?" if scope else "") + " GROUP BY status", p)
    if not len(s): return None
    hi = s[s.pr > .6]; g = s.groupby("outlet_id").pr.mean().sort_values(ascending=False).head(8).reset_index().rename(columns={"pr": "avg_attrition_risk"})
    return {"answer": f"Workforce: **{len(s):,}** staff, **{len(hi):,}** at high attrition risk (>60%), average overtime {s.ot.mean():.1f} h" + (". Attendance: " + ", ".join(f"{r.status} {r.n:,}" for r in at.itertuples()) if len(at) else "") + ".", "df": g, "sql": "staff + attendance", }
# ------------------------------------------------------------------------------------------------ Freight
STOP = {"long", "port", "new", "fort", "saint", "south", "north", "east", "west", "city", "bay", "cape", "grand", "great", "royal", "santa", "puerto", "king", "bandar"}
def _ports_in(q):
    p = Q("SELECT port_name FROM ports").port_name.tolist(); spans = []; first = {}
    for name in p:
        core = [w for w in re.sub(r"\(.*?\)", "", name).lower().split() if w not in QA.GENERIC]
        if core and len(core[0]) >= 4 and core[0] not in STOP: first.setdefault(core[0], []).append(name)
    for name in p:
        als = set(QA._alias(name)); core = [w for w in re.sub(r"\(.*?\)", "", name).lower().split() if w not in QA.GENERIC]
        if core and core[0] not in STOP and len(first.get(core[0], [])) == 1 and len(core[0]) >= 4: als.add(core[0])
        for al in sorted(als, key=len, reverse=True):
            m = re.search(r"(?<![a-z0-9])" + re.escape(al) + r"(?![a-z0-9])", q)
            if m: spans.append((m.start(), m.end(), len(al), name)); break
    spans.sort(key=lambda x: (-x[2], x[0])); kept = []
    for s_ in spans:
        if not any(s_[0] < k[1] and k[0] < s_[1] for k in kept): kept.append(s_)
    kept.sort(); return [k[3] for k in kept], kept
def plan_lane(q, dom):
    ps, hits = _ports_in(re.sub(r"how long", "how_long", q.lower()))
    if len(ps) < 2: return None
    pre = q.lower(); o, d = ps[0], ps[1]; m = re.search(r"from\s+(.+?)\s+to\s+", pre)
    cargo = next((k for k in dom.CARGO if k.lower() in pre or k.lower().rstrip("s") in pre), "General"); wm = re.search(r"(\d+(?:\.\d+)?)\s*(t|tons?|tonnes?|mt|kg|kgs)\b", pre); wt = 20.0
    if wm: wt = float(wm.group(1)) / (1000 if wm.group(2).startswith("kg") else 1)
    po, pd_ = dom.port_xy(o), dom.port_xy(d)
    if not po or not pd_: return None
    cust = Q("SELECT customer_id FROM customers LIMIT 1").customer_id[0]; req = {"origin": o, "dest": d, "cargo": cargo, "weight_t": wt, "hs_code": "HS-8501", "customer_id": cust, "docs_provided": None}
    pq = dom.preview_quote(req); opts = alts.route_alternatives(dom, (po[0], po[1]), (pd_[0], pd_[1]), tonnes=wt, interp=dom.interp, dwell=(po[3] + pd_[3]) * .5)
    if not pq and not opts: return None
    rows = [{"option": f"{i + 1}. {x['label']}", "route": x["name"], "nm": x["nm"], "days": round(x["days"], 1), "freight_cost": round(x["freight"]), "time_cost": round(x["delay_cost"]), "total": round(x["total"]), "tag": x["tag"]} for i, x in enumerate(opts)]
    head = f"**{o} → {d}**, {wt:g} t of {cargo}: "
    if pq: head += f"recommended route **{pq['route']}**, about **{pq['days']} days** at sea and in port, quoted price **${pq['price']:,.0f}** (margin {pq['margin_pct']}%), weather risk {pq['weather']}, decision: {pq['decision']}."
    elif opts: head += f"best route **{opts[0]['name']}**, about **{opts[0]['days']} days**."
    ex = (pq["narrative"] if pq and pq.get("narrative") else "") + ("\n\nOnly one sea route exists for this lane in the routing model (it does not pass a closable canal or strait), so the alternatives are commercial: another carrier, or diverting to a nearby less-congested port (open the port in the map to see candidates)." if len(opts) == 1 else "")
    return {"answer": head, "df": pd.DataFrame(rows) if rows else None, "sql": "dom.preview_quote (route, weather, ML price, customs, margin) + sea-route alternatives; nothing was saved", "extra": ex, "map": opts}
def choke_ports(q):
    k = next((k for k in CHOKE if _w(q, k)), None)
    if not k: return None
    name, la, lo = CHOKE[k]; p = Q("SELECT port_name, country, congestion_index ci, avg_dwell_days dw, lat, lon FROM ports"); p["km"] = alts.hav(la, lo, p.lat.values, p.lon.values); near = p[p.km <= 1800].sort_values("ci", ascending=False)
    v = Q("SELECT COUNT(*) n FROM vessels WHERE route_name LIKE ?", (f"%{name.split()[0]}%",)).n[0]; sh = Q("SELECT COUNT(*) n FROM shipments s JOIN vessels v USING(shipment_id) WHERE v.route_name LIKE ? AND s.status LIKE '%Delay%'", (f"%{name.split()[0]}%",)).n[0]
    if not len(near): return None
    return {"answer": f"Ports within 1,800 km of the **{name}**: **{len(near)}**; **{int((near.ci >= 4).sum())}** are congested (index ≥ 4). Most congested: **{near.port_name.iloc[0]}** ({near.ci.iloc[0]:.1f}, dwell {near.dw.iloc[0]:.1f} days). {int(v)} tracked vessels are routed via this passage, {int(sh)} of them delayed.", "df": near[["port_name", "country", "ci", "dw", "km"]].rename(columns={"ci": "congestion", "dw": "dwell_days", "km": "km_from_passage"}), "sql": f"ports within 1,800 km of {name}"}
def freight_summary(q):
    if re.search(r"\bcustoms\b", q) and re.search(r"\b(hold|held|status|summary|how many|why|docs?|documents?)\b", q):
        d = Q("SELECT dest_port, COUNT(*) n FROM shipments WHERE status='Customs Hold' GROUP BY dest_port ORDER BY n DESC LIMIT 8"); t = int(Q("SELECT COUNT(*) n FROM shipments WHERE status='Customs Hold'").n[0]); tk = Q("SELECT detail FROM agent_actions WHERE type='customs_docs' AND status IN ('open','proposed') LIMIT 400")
        miss = pd.Series([x for dd in tk.detail for x in re.findall(r"missing ([^:]+?)(?:\.|$)", dd)[0].split(", ")] if len(tk) and all("missing" in x for x in tk.detail) else []).value_counts().head(6)
        return {"answer": f"**{t}** shipments are on customs hold. Most held at **{d.dest_port.iloc[0] if len(d) else '-'}**." + (" Most often missing: " + ", ".join(f"{k} ({v})" for k, v in miss.items()) + "." if len(miss) else ""), "df": d.rename(columns={"n": "held"}), "sql": "shipments with status Customs Hold; customs_docs tickets"}
    return None
def greeting(q, kind):
    ql = re.sub(r"[^a-z0-9 ?']", " ", q.lower()).strip()
    hi = re.match(r"^(hi+|hello+|hey+|hola|namaste|good (morning|afternoon|evening)|greetings|yo|sup|howdy)\b( there| team| copilot| buddy)?$", ql)
    thanks = re.match(r"^(thanks?|thank you|thx|ok(ay)?|cool|great|nice|got it|awesome)( a lot| so much)?$", ql)
    who = re.search(r"\b(who are you|what are you|what can you do|what do you do|help me|how can you help|your capabilities|what is this)\b", ql) or ql in ("help", "?")
    how = re.match(r"^how are you", ql)
    if not (hi or thanks or who or how): return None
    ex = (["Which stock needs immediate refill?", "Which outlets are at highest risk and why?", "Top 5 outlets by revenue", "Why is OUT-007 flagged?", "Which state has the most outlets?"] if kind == "Franchise" else
          ["Mumbai to Singapore 50 t electronics: days, cost and best route", "Which ports are most congested?", "How many shipments are on customs hold?", "Which quotes have the lowest margin?"])
    what = ("outlets, stock, staff, marketing, audits, customer feedback and anomalies" if kind == "Franchise" else "routes, ports, weather, customs, quotes and carriers")
    if thanks: return {"answer": "You're welcome. Ask me anything else about " + what + ".", "df": None, "sql": ""}
    head = "Hello! " if hi else ("I'm doing well, thank you. " if how else "")
    return {"answer": head + f"I'm your operations copilot. I answer from your live data on {what}, and I can explain *why* something is flagged, suggest actions and send them to the approval queue. I understand 37 languages.\n\nTry one of these:\n" + "\n".join(f"- {e}" for e in ex), "df": None, "sql": ""}

def refill(scope, n=10):
    w = " WHERE outlet_id=?" if scope else ""; p = (scope,) if scope else ()
    d = Q("SELECT outlet_id, sku_name sku, category, current_stock stock, reorder_threshold thr, weekly_demand wk, lead_time_days lead FROM inventory" + w, p)
    if not len(d): return None
    d["daily"] = d.wk / 7.0; d["cover"] = d.stock / d.daily.replace(0, np.nan); d["cover"] = d.cover.fillna(999)
    d["order_qty"] = np.maximum(d.thr * 3, np.ceil(d.daily * (d.lead + 7)) - d.stock).astype(int)
    d["gap"] = d.cover - d.lead
    d["urgency"] = np.where(d.cover < d.lead, "Critical: runs out before delivery", np.where(d.stock <= d.thr, "High: below reorder level", np.where(d.cover < 7, "Medium: under 7 days", "OK")))
    d["rank"] = d.urgency.str[:4].map({"Crit": 0, "High": 1, "Medi": 2}).fillna(3); need = d[d.urgency != "OK"].sort_values(["rank", "gap", "cover"])
    if not len(need): return {"answer": "No SKU needs an urgent refill right now: all have stock above the reorder level and cover longer than the supplier lead time.", "df": None, "sql": "inventory: cover = stock / daily demand vs lead time"}
    crit = need[need.urgency.str.startswith("Critical")]; po = Q("SELECT outlet_id, sku_name FROM purchase_orders WHERE status IN ('open','ordered','pending','Pending','Ordered','Open')" + (" AND outlet_id=?" if scope else ""), p) if "purchase_orders" in [r[0] for r in Q("SELECT name FROM sqlite_master WHERE type='table'").values] else None
    top = need.head(n)[["outlet_id", "sku", "stock", "thr", "cover", "lead", "order_qty", "urgency"]].rename(columns={"thr": "reorder_level", "cover": "days_of_cover", "lead": "lead_days"}); top["days_of_cover"] = top.days_of_cover.round(1)
    pool = crit if len(crit) else need[need.urgency.str.startswith("High")] if (need.urgency.str.startswith("High")).any() else need; by = pool.groupby("outlet_id").size().sort_values(ascending=False).head(5)
    outs = ", ".join(f"{k} ({v} SKUs)" for k, v in by.items()) if len(by) else "none"
    return {"answer": f"**{len(crit):,}** SKU records will run out *before a new order can arrive* (days of cover < supplier lead time) and **{len(need) - len(crit):,}** more are low. Most urgent outlets: {outs}. The table lists the {len(top)} most urgent SKUs, with the quantity to order.",
            "df": top, "sql": "inventory: days_of_cover = stock / (weekly_demand/7); urgent when cover < lead_time_days; order_qty = max(3 x reorder level, daily demand x (lead + 7 days) - stock)",
            "extra": "**How to read it:** *days_of_cover* is how long current stock lasts at current demand; *lead_days* is how long the supplier takes. When cover is shorter than lead time, stock-out is certain unless you order now (or transfer stock from a nearby outlet). The matching *reorder* tickets are raised by the agent."}

# ------------------------------------------------------------------------------------------------ router
def answer(kind, q, scope=None, dec=None, dom=None, mask=False):
    if kind == "Franchise":
        import intents                                   # the 23 SQL question patterns (spelling tolerant, scope and mask aware)
        r = intents.answer(q, scope, mask)
        if r: return r
    r = _answer(kind, q, scope, dec, dom)
    if r: r["complete"] = True
    return r
def _answer(kind, q, scope=None, dec=None, dom=None):
    g = greeting(q, kind)
    if g: return g
    ql = q.lower().strip(); ids = re.findall(r"\b(OUT-\d+|STF-\d+|SHP-[A-Z0-9-]+|QTE-[A-Z0-9-]+)\b", q, re.I)
    try:
        if kind == "Franchise":
            if ids and ids[0].upper().startswith("OUT") and re.search(r"\b(why|reason|flag\w*|wrong|problem|issue|explain|risk)\b", ql):
                if scope and ids[0].upper() != scope: return {"answer": f"{ids[0].upper()} is outside your outlet scope ({scope}).", "df": None, "sql": ""}
                return explain_outlet(ids[0].upper(), dec)
            _pl = (bool(re.search(r"\b(where|which|list|all|show|located|locations?|states?|cities|city|how many|number)\b", ql)) or bool(_place(ql))) and not re.search(r"\b(risk\w*|health\w*|revenue|sales|csat|satisfaction|inventory|stock|attrition|salary|overtime|best|worst|weakest|critical)\b", ql)
            if _pl and re.search(r"\b(employees?|staff|workers?|people|headcount|manpower|workforce)\b", ql) and (_place(ql) or re.search(r"\b(where|which|most|highest|more|largest|big|fewest|least|lowest|number)\b", ql)): return staff_by_place(ql, scope)
            if _pl and re.search(r"\b(outlets?|stores?|branch\w*|franchises?)\b", ql) and _place(ql): return outlets_in_place(ql, scope)
            if re.search(r"\b(state|states)\b", ql) and re.search(r"\b(outlets?|stores?|branch\w*)\b", ql): return by_state(ql) if not scope else {"answer": "State-wise comparisons cover the whole chain and are not available for your outlet role.", "df": None, "sql": ""}
            if re.search(r"\b(outlets?|stores?|branch\w*)\b", ql) and re.search(r"\b(risk\w*|health\w*|best|worst|weakest|strongest|critical|attention|problem\w*|performing|performance)\b", ql) and not re.search(r"\b(revenue|sales|csat|satisfaction|headcount)\b", ql): return risk_rank(ql, dec, scope)
            if re.search(r"\b(inventory|stock|stocks|stocked|sku|skus|items?|products?|ingredients?)\b", ql) and re.search(r"\b(refill\w*|restock\w*|re-?order\w*|replenish\w*|immediate\w*|urgent\w*|attention|run(ning)? (out|low)|shortage\w*|low|critical|need\w*|order now)\b", ql) and not re.search(r"\b(how many|count|average|total)\b", ql): return refill(scope)
            if re.search(r"\b(inventory|stock)\b", ql) and re.search(r"\b(how|status|holding|summary|overview|situation|look|doing|week|today|health)\b", ql) and not re.search(r"\b(how many|count|average|total|top|lowest|highest|which)\b", ql): return inventory_status(scope)
            if re.search(r"\b(sales|revenue|takings)\b", ql) and re.search(r"\b(trend|this week|last week|today|yesterday|last 7|past week|recent|how (is|are|did))\b", ql): return sales_trend(scope)
            if re.search(r"\b(staff|workforce|employees?|team)\b", ql) and re.search(r"\b(how|status|summary|overview|situation|doing|look)\b", ql) and not re.search(r"\b(how many|count|average|total|top|lowest|highest|which)\b", ql): return staff_status(scope)
        else:
            if dom is not None and re.search(r"\b(days?|time|transit|cost|price|quote|route|how long|how much|eta)\b", ql):
                r = plan_lane(q, dom)
                if r: return r
            if re.search(r"\b(congest\w*|delay\w*|busy|ports?)\b", ql) and any(_w(ql, k) for k in CHOKE): return choke_ports(ql)
            r = freight_summary(ql)
            if r: return r
    except Exception as e:
        import sys; print("analyst failed:", repr(e), file=sys.stderr)
    return None
