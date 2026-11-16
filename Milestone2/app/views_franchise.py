"""FranchiseOps AI pages (server-driven blocks)."""
import json, datetime
import numpy as np, pandas as pd
import live_engine as LE, entities as EN
import domain_franchise as dom
import blocks as B
from blocks import Q, clean, L, TEAL, BLUE, AMBER, RED, VIOLET, GREEN, TONE
from views_core import can, latest, decision, ticket_block, tk_df, cross, hero, scoped

NAME = "FranchiseOps AI"
MENU = [('copilot', 'AI Copilot', 'bot'), ('workforce', 'Agent 1 · Workforce', 'users'), ('outlets', 'Agent 2 · Outlets', 'store'), ('inventory', 'Agent 3 · Inventory', 'boxes'), ('marketing', 'Agent 4 · Marketing', 'megaphone'), ('sentiment', 'Agent 5 · Sentiment', 'messages'), ('audit', 'Agent 6 · Audit', 'clipboard')]
def color_h(h): return RED if h < 60 else AMBER if h < 80 else TEAL
def _sc(c, col="outlet_id"): return (f" WHERE {col}=?", (c["scope"],)) if c.get("scope") else ("", ())
def model_card(name, keys):
    m = Q("SELECT metrics, trained_at FROM ml_models WHERE model_name=? ORDER BY model_id DESC LIMIT 1", (name,))
    if not len(m): return None
    try: d = json.loads(m.metrics[0])
    except Exception: d = {}
    return B.kpis(*[(k, d.get(k, "–")) for k in keys], ("trained", (m.trained_at[0] or "")[5:16]))

# ------------------------------------------------------------------ Command Center: Operations
def ops(c):
    d = decision(); health = (d or {}).get("ev", {}).get("health", {}) if d else {}
    g = Q("SELECT g.outlet_id, g.lat, g.lon, o.outlet_name, o.location FROM outlet_geo g JOIN outlets o USING(outlet_id)"); g = g[g.outlet_id == c["scope"]] if c.get("scope") else g
    tk = Q("SELECT target, COUNT(*) n FROM agent_actions WHERE status IN ('open','proposed') GROUP BY target").set_index("target").n; oa = tk_df(c, limit=500)
    pts = [{"id": r.outlet_id, "lat": r.lat, "lon": r.lon, "color": color_h(health.get(r.outlet_id, 70)), "r": 6 + min(10, int(tk.get(r.outlet_id, 0)) * 1.2), "tip": f"<b>{r.outlet_id}</b> {r.outlet_name}<br>{r.location}<br>health <b>{health.get(r.outlet_id, '–')}</b> · {int(tk.get(r.outlet_id, 0))} open tickets", "open": r.outlet_id} for r in g.itertuples() if r.outlet_id in health]
    mp = B.map_([{"type": "points", "id": "outlets", "pts": pts}], h=500, view={"bounds": [[7, 69], [34, 90]]}, key="ops_map", legend=[("Outlet health ≥ 80", TEAL), ("Health 60–79 (watch)", AMBER), ("Health < 60 (critical)", RED), ("Bigger dot = more open tickets", "#8b8d98")])
    hs = pd.Series(health).sort_values() if health else pd.Series(dtype=float); hs = hs[hs.index == c["scope"]] if c.get("scope") else hs
    need = pd.DataFrame({"outlet": hs.index[:10], "health": hs.values[:10]}); need["tickets"] = need.outlet.map(tk).fillna(0).astype(int)
    h = Q("SELECT substr(ts,12,8) t, score FROM decisions ORDER BY decision_id DESC LIMIT 80").iloc[::-1]; sales = Q("SELECT substr(ts,12,8) time, outlet_id, ROUND(amount) amount, source FROM sales ORDER BY sale_id DESC LIMIT 7")
    by_ag = oa.assign(agent=oa.type.map(lambda t: dom.ACTION_AGENT.get(t, "engine"))).groupby("agent").size().sort_values() if len(oa) else pd.Series(dtype=int); ex = dom.kpi_extra()
    bl = [B.kpis(("Franchise health", d["score"] if d else "…", (d or {}).get("risk", "") + " risk", "Critical" if d and d["risk"] == "High" else "Warning" if d and d["risk"] == "Medium" else "Low"), ("Open tickets", int((oa.status == "open").sum()) if len(oa) else 0), ("Critical", int(((oa.severity == "Critical") & (oa.status == "open")).sum()) if len(oa) else 0, None, "Critical"),
                  ("Awaiting approval", int((oa.status == "proposed").sum()) if len(oa) else 0, "agent proposals", "Warning"), (ex[0][0], ex[0][1]), (ex[1][0], ex[1][1]))]
    if d: bl.append({"t": "brief", "text": d["narrative"], "id": d["id"], "can_brief": True})
    bl.append(B.row(B.card("Outlet map · click an outlet", mp), B.col(B.card("Needs attention first", B.table(need, ["outlet", B.num_col("health", "health", "bar", 100), B.num_col("tickets", "tickets", "int")], h=250, open={"col": "outlet"}, key="need")),
                                                                B.card("Health trend", B.chart(B.line(h.t, h.score, ymin=0, ymax=100, colors=[TEAL]), h=150, key="trend"))), ratio=[3, 2]))
    bl.append(B.row(B.card("Live sales stream", B.table(sales, ["time", "outlet_id", B.num_col("amount", "amount", "money"), B.pill_col("source")], h=240, open={"col": "outlet_id"}, key="sales")), B.card("Open tickets by agent", B.chart(B.bar(by_ag.index, by_ag.values, horizontal=True, colors=[BLUE]), h=240, key="byag"))))
    return bl

# ------------------------------------------------------------------ detail drawer
def detail(c, e):
    k = EN.kind_of(e)
    if k != "outlet": return {"title": e, "blocks": [B.callout("No detail view for this entity.", "info")]}
    d = decision(); health = (d or {}).get("ev", {}).get("health", {}); o = Q("SELECT outlet_name, location, revenue, customer_satisfaction csat, staff_headcount hc FROM outlets WHERE outlet_id=?", (e,))
    if not len(o): return {"title": e, "blocks": [B.callout("Unknown outlet.", "warn")]}
    r = o.iloc[0]; bd = {}
    for a in ("outlet", "inventory", "staff", "marketing", "audit", "feedback"):
        v = EN.latest_out(a).get("per_outlet", {}).get(e)
        if v is not None: bd[a] = round(v, 1)
    s = Q("SELECT substr(ts,12,8) t, amount FROM sales WHERE outlet_id=? ORDER BY sale_id DESC LIMIT 50", (e,)).iloc[::-1]
    lo = Q("SELECT sku_name, current_stock stock, weekly_demand wk, lead_time_days lead FROM inventory WHERE outlet_id=? ORDER BY current_stock*1.0/MAX(weekly_demand,1) LIMIT 5", (e,))
    h = health.get(e); bl = [B.kpis(("Health", h if h is not None else "–", None, "Critical" if h is not None and h < 60 else "Warning" if h is not None and h < 80 else "Low"), ("Satisfaction", f"{r.csat:.2f}"), ("Headcount", int(r.hc)), ("Revenue", f"{r.revenue:,.0f}"))]
    if bd: bl.append(B.card("Why: score from each agent", B.chart(B.bar(list(bd), list(bd.values()), horizontal=True, max_=100, itemcolors=[color_h(v) for v in bd.values()]), h=200, key="d_bd"), sub="weights: outlet 30% · inventory 20% · staff 20% · marketing 15% · audit 15%"))
    if len(s): bl.append(B.card("Live sales stream", B.chart(B.line(s.t, s.amount, colors=[TEAL]), h=170, key="d_s")))
    bl.append(B.table(lo, ["sku_name", "stock", "wk", "lead"], title="Lowest-cover SKUs", h=190, key="d_lo"))
    if c.get("scope"): bl.append(B.callout("Stock-transfer suggestions compare you with other outlets, so they are only shown to roles that see the whole chain.", "info"))
    else:
        try:
            import alts; bl += alts.outlet_alternatives(e)
        except Exception as ex: bl.append(B.callout(f"Transfer suggestions unavailable: {ex}", "info"))
    bl.append(ticket_block(c, target=e, title=f"Tickets for {e}", key="d_tk"))
    if can(c, "run"): bl.append(B.button("rerun", "Re-run all agents now", "/api/run_cycle", "ghost"))
    return {"title": f"{e} · {r.outlet_name}", "sub": r.location, "blocks": bl}

# ------------------------------------------------------------------ agent pages
def workforce(c, tab=None):
    w, p = _sc(c); s = Q("SELECT staff_id, outlet_id, name, role, salary, overtime_hrs, job_satisfaction sat, predicted_attrition_prob p FROM staff" + w, p)
    bl = [hero(c, "staff", "Workforce agent", "Attrition risk (LogisticRegression), attendance and overtime for every employee. Feeds 20% of the outlet health score."),
          B.kpis(("Employees", f"{len(s):,}"), ("Avg attrition risk", f"{s.p.mean():.0%}"), ("High risk (>60%)", int((s.p > .6).sum()), None, "Warning"), ("Avg overtime h", round(s.overtime_hrs.mean(), 1)))]
    g = s.groupby("outlet_id").p.mean().sort_values(ascending=False).head(12); at = Q("SELECT status, COUNT(*) n FROM attendance" + w + " GROUP BY status", p)
    bl.append(B.row(B.card("Attrition probability distribution", B.chart(B.hist(s.p, 24, TEAL, pct=True), h=270, key="wf_h")), B.card("Outlets with highest average attrition risk (click)", B.chart(B.bar(g.index, (g.values * 100).round(1), horizontal=True, colors=[AMBER], pct=True), h=270, open={"bar": "y"}, key="wf_b"))))
    t = dom.attrition_table(c.get("scope"), 15); imp = dom.attrition_importance()
    bl.append(B.row(B.card("Live attendance (all recorded shifts)", B.chart(B.pie(at.set_index("status").n.to_dict(), colors={"Present": TEAL, "Late": AMBER, "Absent": RED}), h=270, key="wf_a")),
                    B.card("Highest-risk employees and their main driver", B.table(t[["staff_id", "outlet_id", "name", "role", "prob", "driver"]] if len(t) else pd.DataFrame(), ["staff_id", "outlet_id", "name", "role", B.num_col("prob", "attrition", "pct"), "driver"], h=270, open={"col": "outlet_id"}, key="wf_t"))))
    if imp: ip = pd.Series(imp).sort_values(); bl.append(B.card("What pushes attrition up (positive) or down (negative)", B.chart(B.bar(ip.index, ip.values.round(3), horizontal=True, colors=[VIOLET]), h=240, key="wf_i")))
    mc = model_card("logreg_attrition", ["accuracy", "auc", "source"]); bl += [mc] if mc else []
    x = cross(c, s.groupby("outlet_id").p.mean().sort_values(ascending=False).head(15).index, "staff"); bl += [x] if x else []
    bl.append(ticket_block(c, "staff", title="Open tickets from this agent", key="tk_staff")); return B.page("Workforce", "Agent 1 · attrition, attendance, overtime", bl, live=12)

def outlets(c, tab=None):
    r = latest("outlet"); out = (r or {}).get("out", {}); tiers = pd.Series(out.get("tiers", {})); d = decision(); health = (d or {}).get("ev", {}).get("health", {})
    o = Q("SELECT o.outlet_id, o.outlet_name, o.location, o.revenue, o.customer_satisfaction csat, o.staff_headcount hc, g.lat, g.lon FROM outlets o LEFT JOIN outlet_geo g USING(outlet_id)"); o["tier"] = o.outlet_id.map(tiers); o["health"] = o.outlet_id.map(health); o = o[o.outlet_id == c["scope"]] if c.get("scope") else o
    order = ["Excellent", "Good", "Needs Attention", "Critical"]; col = {"Excellent": TEAL, "Good": BLUE, "Needs Attention": AMBER, "Critical": RED}; tc = o.tier.value_counts().reindex(order).fillna(0)
    bl = [hero(c, "outlet", "Outlet performance agent", "KMeans (k=4) over revenue, orders and customers ranks every outlet. Drives 30% of the health score."),
          B.kpis(("Outlets", len(o)), ("Avg health", f"{o.health.mean():.1f}" if o.health.notna().any() else "…"), ("Critical tier", int((o.tier == "Critical").sum()), None, "Critical"), ("Silhouette", out.get("silhouette", "n/a")))]
    sc = {t: [{"x": a.revenue, "y": a.csat, "label": a.outlet_id, "size": 6 + a.hc / 4} for a in o[o.tier == t].itertuples()] for t in order if (o.tier == t).any()}
    bl.append(B.row(B.card("Outlets per KMeans tier", B.chart(B.bar(order, tc.values.astype(int).tolist(), itemcolors=[col[t] for t in order]), h=290, key="ou_t")), B.card("Revenue vs satisfaction (size = headcount · click a dot)", B.chart(B.scatter(sc, "revenue", "satisfaction", colors=col, sized=True), h=290, open={"scatter": True}, key="ou_s"))))
    bl.append(B.table(o.sort_values("health")[["outlet_id", "outlet_name", "location", "tier", "health", "csat", "hc"]], ["outlet_id", "outlet_name", "location", B.pill_col("tier"), B.num_col("health", "health", "bar", 100), B.num_col("csat", "csat", "num"), B.num_col("hc", "staff", "int")], title="All outlets · click a row for the drill-down", h=360, open={"col": "outlet_id"}, key="ou_tb", search=True))
    x = cross(c, o.sort_values("health").head(15).outlet_id, "outlet"); bl += [x] if x else []
    allo = o.sort_values("outlet_id").outlet_id.tolist(); picks = [p for p in ((c.get("params") or {}).get("cmp") or []) if p in allo][:5] or o.sort_values("health", ascending=False).outlet_id.tolist()[:2] + o.sort_values("health").outlet_id.tolist()[:1]
    names = ["outlet", "inventory", "staff", "marketing", "audit", "feedback"]; ser = {}; rows = []
    for p in picks:
        vals = [round(float(EN.latest_out(a).get("per_outlet", {}).get(p, 0) or 0), 1) for a in names]; ser[p] = vals; rr = o[o.outlet_id == p].iloc[0]; rows.append({"outlet": p, "location": rr.location, "health": health.get(p), "revenue": rr.revenue, "csat": rr.csat, "hc": rr.hc, **dict(zip(names, vals))})
    bl.append({"t": "form", "id": "cmp", "fields": [{"name": "cmp", "label": "Benchmark up to 5 outlets", "type": "multi", "options": allo, "value": picks}], "submit": "Compare", "url": "page:outlets", "title": None, "tone": "ghost", "inline": True})
    bl.append(B.row(B.card("Outlet benchmarking: score from each agent", B.chart(B.radar(names, ser), h=330, key="cmp_r")), B.card("Side by side", B.table(rows, ["outlet", "location", B.num_col("health", "health", "bar", 100)] + [B.num_col(a, a, "num") for a in names] + [B.num_col("revenue", "revenue", "money")], h=330, open={"col": "outlet"}, key="cmp_t")), ratio=[2, 3]))
    bl.append(ticket_block(c, "outlet", ["outlet_review", "health_alert"], title="Open tickets from this agent", key="tk_out")); return B.page("Outlets", "Agent 2 · KMeans tiers and the live health score", bl, live=12)

def inventory(c, tab=None):
    w, p = _sc(c); d = Q("SELECT outlet_id, sku_name, category, current_stock, reorder_threshold mn, weekly_demand wd, lead_time_days lead, stockout_risk_prob risk FROM inventory" + w, p)
    mult = LE.get_state("demand_mult", 1.0) or 1.0; d["cover_days"] = (d.current_stock / (d.wd.clip(lower=1) / 7 * mult)).round(1); d["short"] = d.cover_days < d.lead + 2
    po = Q("SELECT po_id, outlet_id, sku_name, qty, ts, eta_ts, status FROM purchase_orders" + w + " ORDER BY po_id DESC LIMIT 300", p)
    bl = [hero(c, "inventory", "Inventory agent", "Cover days = stock ÷ (forecast demand × live demand multiplier). Below lead time + 2 days raises a reorder and creates a purchase order."),
          B.kpis(("SKUs tracked", f"{len(d):,}"), ("Flagged short", int(d.short.sum()), None, "Warning"), ("POs in transit", int((po.status == "ordered").sum())), ("POs delivered", int((po.status == "delivered").sum())), ("Demand multiplier", f"x{mult}", "weather + holiday feed"))]
    cat = d.groupby("category").short.mean().mul(100).round(1)
    bl.append(B.row(B.card("Stock cover (days)", B.chart(B.hist(d.cover_days, 28, BLUE), h=270, key="iv_h")), B.card("% of SKUs short, by category", B.chart(B.bar(cat.index, cat.values, colors=[AMBER], pct=True), h=270, key="iv_c"))))
    bl.append(B.row(B.card("Most urgent SKUs", B.table(d[d.short].sort_values("cover_days").head(15)[["outlet_id", "sku_name", "current_stock", "cover_days", "lead", "risk"]], ["outlet_id", "sku_name", "current_stock", B.num_col("cover_days", "cover days", "num"), "lead", B.num_col("risk", "stock-out risk", "pct")], h=290, open={"col": "outlet_id"}, key="iv_u")),
                    B.card("Purchase orders created by this agent (they deliver into stock, closing the loop)", B.table(po.head(20), ["po_id", "outlet_id", "sku_name", "qty", B.pill_col("status"), "eta_ts"], h=290, open={"col": "outlet_id"}, key="iv_p"))))
    outs = sorted(d.outlet_id.unique()); sel = (c.get("params") or {}).get("o") or (outs[0] if outs else None); sel = sel if sel in outs else (outs[0] if outs else None); meth = (c.get("params") or {}).get("m") or "Prophet (if installed)"
    bl.append({"t": "form", "id": "inv_fc", "fields": [{"name": "o", "label": "Demand forecast for outlet", "type": "select", "options": outs, "value": sel}, {"name": "m", "label": "Method", "type": "select", "options": ["Prophet (if installed)", "Trend x weekday"], "value": meth}], "submit": "Forecast", "url": "page:inventory", "title": None, "tone": "ghost", "inline": True})
    if sel:
        h, f, how = dom.forecast_series(sel, 14, "trend" if meth.startswith("Trend") else None)
        if len(f): x = list(h.d.astype(str)) + list(f.d.astype(str)); bl.append(B.card(f"{sel}: daily sales and 14-day forecast ({how})", B.chart(B.line(x, {"actual": list(h.a) + [None] * len(f), "forecast": [None] * (len(h) - 1) + [h.a.iloc[-1]] + list(f.a)}, colors=[TEAL, AMBER], dashed=("forecast",), band=([None] * len(h) + list(f.lo), [None] * len(h) + list(f.hi))), h=290, key="iv_f")))
    x = cross(c, d[d.short].outlet_id.unique(), "inventory"); bl += [x] if x else []
    bl.append(ticket_block(c, "inventory", title="Open tickets from this agent", key="tk_inv")); return B.page("Inventory", "Agent 3 · cover days, reorders, forecast", bl, live=10)

def marketing(c, tab=None):
    w, p = _sc(c); m = Q("SELECT outlet_id, campaign_name, channel, budget, actual_roi, reach, conversions, start_date, end_date FROM marketing" + w, p); today = datetime.date.today().isoformat()
    m["status"] = np.where(m.end_date >= today, "live", "ended / paused"); m["roi_pct"] = ((m.actual_roi - 1) * 100).round(0); r = (latest("marketing") or {}).get("out", {})
    bl = [hero(c, "marketing", "Marketing agent", "Campaign ROI = (revenue − budget) ÷ budget, plus KMeans (k=3) customer segments. Campaigns are paused when Inventory reports a shortage."),
          B.kpis(("Campaigns", len(m)), ("Live now", int((m.status == "live").sum())), ("Avg ROI", f"{m.roi_pct.mean():.0f}%"), ("Best channel", r.get("best_channel", "…")))]
    ch = m.groupby("channel").actual_roi.mean().sub(1).mul(100).round(0).sort_values(); seg = r.get("segments", {})
    bl.append(B.row(B.card("Average ROI % by channel", B.chart(B.bar(ch.index, ch.values, horizontal=True, colors=[TEAL], pct=True), h=270, key="mk_c")), B.card("Customer segments (KMeans k=3)", B.chart(B.pie(seg), h=270, key="mk_s")) if seg else B.callout("Segments appear after the first agent run.", "info")))
    bl.append(B.table(m[m.status == "live"].sort_values("roi_pct")[["outlet_id", "campaign_name", "channel", "budget", "roi_pct", "end_date"]].head(30), ["outlet_id", "campaign_name", "channel", B.num_col("budget", "budget", "money"), B.num_col("roi_pct", "ROI %", "num"), "end_date"], title="Live campaigns (lowest ROI first)", h=300, open={"col": "outlet_id"}, key="mk_l"))
    paused = scoped(Q("SELECT target, detail, ts FROM agent_actions WHERE type='pause_promo' ORDER BY action_id DESC LIMIT 8"), c)
    if len(paused): bl.append(B.table(paused, ["target", "detail", "ts"], title="Promotions paused by the cross-agent rule (stock shortage + live campaign)", h=220, open={"col": "target"}, key="mk_p"))
    x = cross(c, m[m.status == "live"].outlet_id.unique(), "marketing"); bl += [x] if x else []
    bl.append(ticket_block(c, "marketing", title="Open tickets from this agent", key="tk_mk")); return B.page("Marketing", "Agent 4 · ROI, segments, campaign control", bl, live=12)

def sentiment(c, tab=None):
    w, p = _sc(c); f = Q("SELECT outlet_id, rating, comment, date, sentiment_score s FROM feedback" + w + " ORDER BY rowid DESC LIMIT 4000", p); r = (latest("feedback") or {}).get("out", {})
    bl = [hero(c, "feedback", "Sentiment agent", "VADER + star rating on every review, with issue categories. A review submitted here is analysed at once and picked up by the next agent cycle."),
          B.kpis(("Reviews analysed", len(f)), ("Avg rating", f"{f.rating.mean():.2f}" if len(f) else "n/a"), ("Outlets scoring < 45", sum(v < 45 for k, v in r.get("per_outlet", {}).items() if not c.get("scope") or k == c["scope"]), None, "Warning"))]
    iss = pd.Series(r.get("issues", {})).sort_values(); rd = f.rating.value_counts().sort_index()
    bl.append(B.row(B.callout("Issue categories are counted across the whole chain, so they are not shown for an outlet role.", "info") if c.get("scope") else B.card("Issue categories in reviews", B.chart(B.bar(iss.index, iss.values, horizontal=True, colors=[AMBER]), h=270, key="se_i")) if len(iss) else B.callout("Issue categories appear after the first run.", "info"), B.card("Rating distribution", B.chart(B.bar(rd.index.astype(int).astype(str), rd.values.astype(int), colors=[TEAL]), h=270, key="se_r"))))
    per = pd.Series(r.get("per_outlet", {})); per = per[per.index == c["scope"]] if c.get("scope") else per.sort_values().head(10)
    if len(per): bl.append(B.table(per.rename("score").reset_index().rename(columns={"index": "outlet"}), ["outlet", B.num_col("score", "score", "bar", 100)], title="Lowest sentiment scores (0-100)", h=250, open={"col": "outlet"}, key="se_l"))
    bl.append(B.table(f.head(14)[["outlet_id", "rating", "comment", "date"]], ["outlet_id", "rating", "comment", "date"], title="Latest reviews", h=300, open={"col": "outlet_id"}, key="se_t"))
    outs = [c["scope"]] if c.get("scope") else Q("SELECT outlet_id FROM outlets ORDER BY outlet_id").outlet_id.tolist()
    bl.append(B.form("review", [{"name": "outlet", "label": "Outlet", "type": "select", "options": outs, "value": outs[0]}, {"name": "rating", "label": "Rating", "type": "range", "min": 1, "max": 5, "value": 4}, {"name": "comment", "label": "Comment (any language, translated by NLLB)", "type": "textarea"}], "Submit review", "/api/franchise/review", title="Add a review", sub="Stored and analysed immediately; the agent includes it in its next cycle."))
    if can(c, "view"): bl.append(ticket_block(c, "feedback", title="Open tickets from this agent", key="tk_fb"))
    return B.page("Sentiment", "Agent 5 · reviews, VADER, issue categories", bl, live=15)

def audit(c, tab=None):
    w, p = _sc(c); a = Q("SELECT outlet_id, audit_date, score, violations, category, status, notes FROM audits" + w + " ORDER BY audit_date DESC, rowid DESC", p); last = a.drop_duplicates("outlet_id")
    bl = [hero(c, "audit", "Audit & compliance agent", "Latest inspection per outlet. Pass ≥ 80, Warning 60–79, Fail < 60. A fail opens a 72-hour corrective-action ticket and re-plans the Staff and Sentiment agents."),
          B.kpis(("Outlets audited", len(last)), ("Pass", int((last.score >= 80).sum()), None, "Low"), ("Warning", int(((last.score >= 60) & (last.score < 80)).sum()), None, "Warning"), ("Fail", int((last.score < 60).sum()), None, "Critical"))]
    cg = a.groupby("category").score.mean().round(1)
    bl.append(B.row(B.card("Latest audit scores", B.chart(B.hist(last.score, 20, TEAL), h=270, key="au_h")), B.card("Average score by category", B.chart(B.bar(cg.index, cg.values, colors=[BLUE]), h=270, key="au_c"))))
    bl.append(B.table(last.sort_values("score").head(15), ["outlet_id", "audit_date", B.num_col("score", "score", "bar", 100), "violations", "category", B.pill_col("status"), "notes"], title="Lowest-scoring outlets", h=320, open={"col": "outlet_id"}, key="au_l"))
    if can(c, "resolve"):
        outs = [c["scope"]] if c.get("scope") else Q("SELECT outlet_id FROM outlets ORDER BY outlet_id").outlet_id.tolist()
        bl.append(B.form("audit_log", [{"name": "outlet", "label": "Outlet", "type": "select", "options": outs, "value": outs[0]}, {"name": "score", "label": "Score", "type": "range", "min": 0, "max": 100, "value": 82}, {"name": "category", "label": "Category", "type": "select", "options": ["Food Safety", "Hygiene", "Documentation", "Equipment", "Staff Training"], "value": "Food Safety"}, {"name": "notes", "label": "Notes", "type": "text"}], "Save inspection", "/api/franchise/audit", title="Log an inspection", sub="Runs the Audit agent straight away; a fail opens a corrective-action ticket."))
    x = cross(c, last[last.score < 80].outlet_id, "audit"); bl += [x] if x else []
    bl.append(ticket_block(c, "audit", title="Open tickets from this agent", key="tk_au")); return B.page("Audit", "Agent 6 · inspections and compliance", bl, live=15)

PAGES = {"workforce": workforce, "outlets": outlets, "inventory": inventory, "marketing": marketing, "sentiment": sentiment, "audit": audit}
