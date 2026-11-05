"""FranchiseOps AI live domain: simulator, 5 agents, intelligence engine, action handlers."""
import os, re, json, math, random, time, datetime, uuid
import numpy as np, pandas as pd, requests
from live_engine import AgentResult, risk_label, conn, now, _DB_LOCK, set_state, get_state, emit

KIND = "Franchise"; NAME = "FranchiseOps AI"; ENTITY_COL = "outlet_id"; SMS = True; ESCALATE_TO = "VP Operations"
OWNER = {"reorder": "Store Manager", "pause_promo": "Marketing Manager", "corrective_action": "Regional Manager", "retention_plan": "HR Lead",
         "outlet_review": "Regional Manager", "staffing_shortage": "Store Manager", "reallocate_budget": "Marketing Manager"}
ACTION_AGENT = {"reorder": "inventory", "pause_promo": "inventory", "corrective_action": "audit", "retention_plan": "staff",
                "outlet_review": "outlet", "staffing_shortage": "staff", "reallocate_budget": "marketing"}
SIM_DAY_SEC = 60          # one simulated day = 60 s of wall-clock (5 s ticks -> 12 ticks per day)
TICKS_PER_DAY = 12
def Q(sql, p=()):
    with _DB_LOCK, conn() as c: return pd.read_sql(sql, c, params=p)

# ---------------------------------------------------------------- bootstrap / simulator
def bootstrap():
    from scale_data import scale_franchise; scale_franchise()
    with _DB_LOCK, conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS sales(sale_id INTEGER PRIMARY KEY AUTOINCREMENT, outlet_id TEXT, ts TEXT, amount REAL, tx_count INT, source TEXT);
        CREATE TABLE IF NOT EXISTS attendance(att_id INTEGER PRIMARY KEY AUTOINCREMENT, staff_id TEXT, outlet_id TEXT, ts TEXT, status TEXT);
        CREATE TABLE IF NOT EXISTS purchase_orders(po_id INTEGER PRIMARY KEY AUTOINCREMENT, outlet_id TEXT, sku_name TEXT, qty INT, ts TEXT, eta_ts TEXT, status TEXT);
        CREATE TABLE IF NOT EXISTS ml_models(model_id INTEGER PRIMARY KEY AUTOINCREMENT, model_name TEXT, metrics TEXT, trained_at TEXT, is_active INT);
        CREATE INDEX IF NOT EXISTS ix_sales ON sales(outlet_id, ts);
        """)
        if c.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0:       # 90 days of seeded history so baselines exist
            rng = np.random.default_rng(7); today = datetime.date.today()
            for oid, rev in c.execute("SELECT outlet_id, revenue FROM outlets").fetchall():
                base = (rev or 100000) / 30
                for d in range(90, 0, -1):
                    dt = today - datetime.timedelta(days=d)
                    c.execute("INSERT INTO sales(outlet_id,ts,amount,tx_count,source) VALUES(?,?,?,?,'seed')", (oid, dt.isoformat(), float(base * rng.normal(1, .07) * (1.15 if dt.weekday() >= 5 else 1)), int(base / 250)))
        active = c.execute("SELECT COUNT(*) FROM marketing WHERE end_date>=date('now')").fetchone()[0]
        if active == 0:                                                       # launch a live promo set (seed campaigns are all expired)
            ids = [r[0] for r in c.execute("SELECT campaign_id FROM marketing ORDER BY RANDOM() LIMIT 14").fetchall()]
            for i in ids: c.execute("UPDATE marketing SET start_date=date('now','-3 day'), end_date=date('now','+14 day') WHERE campaign_id=?", (i,))
        c.execute("UPDATE inventory SET weekly_demand=MAX(weekly_demand,1)")
        for rid, st_, wk, lead in c.execute("SELECT record_id, current_stock, weekly_demand, lead_time_days FROM inventory").fetchall():   # (re)start from a healthy, varied stock position
            if st_ / max(wk / 7, 1) < lead + 1.5: c.execute("UPDATE inventory SET current_stock=? WHERE record_id=?", (int(wk / 7 * (lead + random.uniform(1.5, 14))), rid))

_incident = {}; _tickn = [0]
def tick():
    reasons = []; _tickn[0] += 1; n = _tickn[0]; mult = get_state("demand_mult", 1.0) or 1.0
    ts = now()
    with _DB_LOCK, conn() as c:
        outlets = c.execute("SELECT outlet_id, revenue, operating_costs, customer_satisfaction FROM outlets").fetchall()
        real = set()
        for oid, rev, cost, csat in outlets:
            if oid in real: continue
            if oid not in _incident and random.random() < 0.002: _incident[oid] = random.randint(8, 14)
            f = 0.35 if oid in _incident else 1.0
            if oid in _incident:
                _incident[oid] -= 1
                if _incident[oid] <= 0: _incident.pop(oid)
            base = 3000000 / 30 / TICKS_PER_DAY if not rev else (rev / 30 / TICKS_PER_DAY)
            amt = float(base * random.uniform(.8, 1.2) * mult * f)
            c.execute("INSERT INTO sales(outlet_id,ts,amount,tx_count,source) VALUES(?,?,?,?,'sim')", (oid, ts, amt, max(1, int(amt / 250))))
            c.execute("UPDATE outlets SET revenue=revenue+?, operating_costs=operating_costs+? WHERE outlet_id=?", (amt, amt * (cost / rev if rev else .65), oid))
        # stock drawdown + deliveries
        for rid, oid, sku, stock, thr, wk, lead in c.execute("SELECT record_id,outlet_id,sku_name,current_stock,reorder_threshold,weekly_demand,lead_time_days FROM inventory").fetchall():
            use = max(0, int(round(wk / 7 / TICKS_PER_DAY * mult * random.uniform(.6, 1.6))))
            new = max(0, stock - use); cover = new / max(wk / 7, 1)
            risk = float(min(1, max(0, 1 - cover / (lead + 3))))
            c.execute("UPDATE inventory SET current_stock=?, stockout_risk_prob=? WHERE record_id=?", (new, round(risk, 2), rid))
            if stock / max(wk / 7, 1) >= lead + 2 > cover: reasons.append(f"stock-low:{oid}")
        for po, oid, sku, qty in c.execute("SELECT po_id,outlet_id,sku_name,qty FROM purchase_orders WHERE status='ordered' AND eta_ts<=?", (ts,)).fetchall():
            c.execute("UPDATE inventory SET current_stock=current_stock+? WHERE outlet_id=? AND sku_name=?", (qty, oid, sku))
            c.execute("UPDATE purchase_orders SET status='delivered' WHERE po_id=?", (po,)); emit("po_delivered", oid, {"sku": sku, "qty": qty})
        # staff: attendance, overtime drift, attrition recompute (same heuristic the app uses)
        for sid, oid, sal, sat, ot in c.execute("SELECT staff_id,outlet_id,salary,job_satisfaction,overtime_hrs FROM staff ORDER BY RANDOM() LIMIT 40").fetchall():
            st = random.choices(["Present", "Late", "Absent"], [.86, .09, .05 + (.25 if oid in _incident else 0)])[0]
            c.execute("INSERT INTO attendance(staff_id,outlet_id,ts,status) VALUES(?,?,?,?)", (sid, oid, ts, st))
            ot2 = float(min(45, max(0, ot + random.uniform(-1.5, 2) + (1.5 if st == "Absent" else 0))))
            c.execute("UPDATE staff SET overtime_hrs=? WHERE staff_id=?", (round(ot2, 1), sid))
        # feedback + csat moving average
        for oid, csat in random.sample([(o[0], o[3]) for o in outlets], 6):
            r = int(min(5, max(1, round(random.gauss(csat if csat else 4, .9) - (1.5 if oid in _incident else 0)))))
            c.execute("INSERT INTO feedback(feedback_id,outlet_id,rating,comment,date,sentiment_score) VALUES(?,?,?,?,?,?)",
                      ("FB-L"+uuid.uuid4().hex[:10], oid, r, "Live feedback", datetime.date.today().isoformat(), (r - 3) / 2))
            c.execute("UPDATE outlets SET customer_satisfaction=ROUND(0.95*customer_satisfaction+0.05*?,3) WHERE outlet_id=?", (r, oid))
        if random.random() < 0.05:
            oid = random.choice(outlets)[0]; sc = float(np.clip(random.gauss(84, 12), 40, 100))
            c.execute("INSERT INTO audits(audit_id,outlet_id,audit_date,score,violations,category,status,notes) VALUES(?,?,?,?,?,?,?,?)",
                      ("AUD-L"+uuid.uuid4().hex[:10], oid, datetime.date.today().isoformat(), sc, int((100 - sc) / 6), "Food Safety", "Pass" if sc >= 85 else "Conditional Pass" if sc >= 70 else "Fail", "Live inspection"))
            if sc < 70: reasons.append(f"audit-fail:{oid}")
    return list(dict.fromkeys(reasons))[:5]

def process(): pass
def feed(): _external()
DEFAULT_POLICY = {"pause_promo": "approval"}

def _external():
    """Real feeds: Open-Meteo weather (city list from the app), Nager.Date public holidays. Falls back silently when offline."""
    mult, feeds, rain = 1.0, {}, []
    try:
        from weather_context import CITY_COORDS
        for city, (la, lo) in list(CITY_COORDS.items())[:5]:
            r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={la}&longitude={lo}&current=temperature_2m,precipitation,wind_speed_10m", timeout=4).json()["current"]
            rain.append(r.get("precipitation", 0) or 0); feeds[city] = {"temp": r["temperature_2m"], "rain": r["precipitation"], "wind": r["wind_speed_10m"]}
        if np.mean(rain) > 1.5: mult *= .92
        feeds_ok = True
    except Exception: feeds_ok = False
    hol = False
    try:
        hol = requests.get("https://date.nager.at/api/v3/IsTodayPublicHoliday/IN", timeout=4).status_code == 200
        if hol: mult *= 1.15
    except Exception: pass
    set_state("demand_mult", round(mult, 3)); set_state("weather", feeds); set_state("feeds", {"weather": feeds_ok, "holiday": hol, "ts": now()})

def feed_status():
    f = get_state("feeds", {}) or {}
    return [("Open-Meteo weather", "Real · live" if f.get("weather") else "Offline · no demand adjustment"),
            ("Public holidays (Nager.Date)", "Real · today is a holiday" if f.get("holiday") else "Real · no holiday today" if f else "Waiting"),
            ("Outlet POS, stock, attendance, feedback", "Simulated feed (replace via Data Feed Center)")]

# ---------------------------------------------------------------- agents (PRS v3: 7 agents + Intelligence Engine)
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, silhouette_score
TIER_BASE = {"Excellent": 95, "Good": 80, "Needs Attention": 58, "Critical": 35}
def _reg_model(name, metrics, active=1):
    with _DB_LOCK, conn() as c:
        c.execute("UPDATE ml_models SET is_active=0 WHERE model_name=?", (name,))
        c.execute("INSERT INTO ml_models(model_name,metrics,trained_at,is_active) VALUES(?,?,?,?)", (name, json.dumps(metrics), now(), active))

def outlet_agent(s):
    """Agent 1: KMeans (k=4) on 30-day revenue/orders/customers, ranked into Excellent/Good/Needs Attention/Critical."""
    d = Q("SELECT outlet_id, source, AVG(amount) rev, AVG(tx_count) orders FROM sales GROUP BY outlet_id, source")
    d.loc[d.source == "sim", ["rev", "orders"]] *= TICKS_PER_DAY
    d = d.sort_values("source").drop_duplicates("outlet_id", keep="first")            # sim rows preferred once present ('sim' < 'seed')
    d["cust"] = d.orders * .8; X = StandardScaler().fit_transform(d[["rev", "orders", "cust"]])
    km = KMeans(4, n_init=10, random_state=42).fit(X); d["cl"] = km.labels_
    order = d.groupby("cl").rev.mean().sort_values(ascending=False).index.tolist(); tmap = dict(zip(order, ["Excellent", "Good", "Needs Attention", "Critical"]))
    d["tier"] = d.cl.map(tmap); dist = np.linalg.norm(X - km.cluster_centers_[km.labels_], axis=1); d["conf"] = (1 / (1 + dist)).round(2)
    d["score"] = d.tier.map(TIER_BASE) + d.groupby("tier").rev.rank(pct=True) * 8 - 4
    sil = float(silhouette_score(X, km.labels_)) if len(d) > 4 else 0
    _reg_model("kmeans_outlet_clusters", {"silhouette": round(sil, 3), "n": len(d)})
    crit = d[d.tier == "Critical"]
    return AgentResult("outlet", round(float(d.score.mean()), 1), risk_label(d.score.mean()), f"KMeans tiers: " + ", ".join(f"{t} {int((d.tier == t).sum())}" for t in TIER_BASE),
        {"per_outlet": d.set_index("outlet_id").score.round(1).to_dict(), "tiers": d.set_index("outlet_id").tier.to_dict(), "silhouette": round(sil, 3), "weak": crit.outlet_id.tolist()},
        [{"type": "outlet_review", "target": r.outlet_id, "detail": f"KMeans tier Critical (revenue {r.rev:,.0f}/day, confidence {r.conf})", "severity": "Warning"} for r in crit.itertuples()])

def forecast_series(outlet, horizon=14, method=None):
    """Demand forecast for one outlet. Prophet when installed and USE_PROPHET != 0 (daily + weekly seasonality), else linear trend x weekday-seasonal index."""
    h = Q("SELECT substr(ts,1,10) d, SUM(amount) a FROM sales WHERE outlet_id=? AND source='seed' GROUP BY d ORDER BY d", (outlet,))
    if len(h) < 21: return h.assign(kind="actual"), pd.DataFrame(), "insufficient history"
    h["d"] = pd.to_datetime(h.d); fut_d = pd.date_range(h.d.iloc[-1] + pd.Timedelta(days=1), periods=horizon)
    if (method or os.environ.get("USE_PROPHET", "1")) not in ("0", "trend"):
        try:
            from prophet import Prophet
            m = Prophet(weekly_seasonality=True, daily_seasonality=False, yearly_seasonality=False); m.fit(h.rename(columns={"d": "ds", "a": "y"}))
            f = m.predict(pd.DataFrame({"ds": fut_d})); return h, pd.DataFrame({"d": f.ds, "a": f.yhat, "lo": f.yhat_lower, "hi": f.yhat_upper}), "Prophet"
        except Exception: pass
    y = h.a.values; x = np.arange(len(y)); k, b = np.polyfit(x, y, 1); trend = k * x + b; ratio = pd.Series(y / np.maximum(trend, 1)).groupby(h.d.dt.weekday.values).mean()
    xf = np.arange(len(y), len(y) + horizon); fa = (k * xf + b) * pd.Series(fut_d.weekday).map(ratio).values; sd = float(np.std(y - trend * h.d.dt.weekday.map(ratio).values))
    return h, pd.DataFrame({"d": fut_d, "a": fa, "lo": fa - 1.28 * sd, "hi": fa + 1.28 * sd}), "trend x weekday seasonality"

def _forecast_ratio(outlet):
    """Agent 2 forecast: Prophet when installed (USE_PROPHET=1), otherwise weekday-seasonal linear trend. Returns next-7-day / last-7-day demand ratio."""
    h, f, _ = forecast_series(outlet, 7, method="trend")                 # the fleet-wide loop stays on the fast method; Prophet is used on the Inventory page per outlet
    if not len(f): return 1.0
    return float(np.clip(f.a.mean() / max(h.a.iloc[-7:].mean(), 1), .8, 1.3))

def inventory_agent(s):
    mult = get_state("demand_mult", 1.0) or 1.0
    d = Q("SELECT outlet_id, sku_name, current_stock, reorder_threshold mn, weekly_demand, lead_time_days lead FROM inventory")
    fr = get_state("forecast_ratio", {}) or {}
    if not fr or now()[:13] != (get_state("forecast_hour") or ""):
        fr = {o: _forecast_ratio(o) for o in d.outlet_id.unique()}; set_state("forecast_ratio", fr); set_state("forecast_hour", now()[:13])
    d["daily"] = d.weekly_demand.clip(lower=1) / 7 * mult * d.outlet_id.map(fr).fillna(1.0); d["cover"] = d.current_stock / d.daily
    po = Q("SELECT outlet_id, sku_name FROM purchase_orders WHERE status='ordered'"); open_po = set(zip(po.outlet_id, po.sku_name))
    d["short"] = (d.current_stock <= d.mn) | (d.cover < d.lead + 2)
    per = (100 - d.groupby("outlet_id").short.mean() * 200).clip(0, 100).round(1)
    acts = []
    for r in d[d.short].sort_values("cover").itertuples():
        if (r.outlet_id, r.sku_name) in open_po: continue
        qty = int(max(r.mn * 3, math.ceil(r.daily * (r.lead + 7)) - r.current_stock))               # PRS: reorder_qty = min_stock x 3 (or forecast need if larger)
        acts.append({"type": "reorder", "target": r.outlet_id, "detail": f"{r.sku_name}: {r.cover:.1f} days cover, order {qty} units", "severity": "Critical" if r.cover < r.lead else "Warning", "sku": r.sku_name, "qty": qty, "lead": int(r.lead)})
    n = int(d.short.sum())
    return AgentResult("inventory", round(float(per.mean()), 1), risk_label(per.mean()), f"{n} SKUs flagged of {len(d)}, demand x{mult}", {"per_outlet": per.to_dict(), "outlets": d[d.short].outlet_id.unique().tolist(), "demand_mult": mult, "forecast": "weekday-seasonal trend (Prophet optional)"}, acts[:40])

_LR = {}
def _attrition_model():
    """Agent 3 ML: LogisticRegression. Uses a fed HR dataset (table hr_training, e.g. IBM HR Analytics) when present; otherwise a bootstrap model on the staff table labelled by the rule score."""
    d = Q("SELECT st.staff_id, st.outlet_id, st.salary, st.overtime_hrs, st.job_satisfaction sat, st.tenure_years ten, st.work_life_balance wlb, st.age, st.predicted_attrition_prob p FROM staff st")
    att = Q("SELECT staff_id, AVG(status='Present') pres FROM attendance GROUP BY staff_id").set_index("staff_id").pres
    d["att"] = d.staff_id.map(att).fillna(.9) * 100; feats = ["salary", "overtime_hrs", "sat", "ten", "wlb", "age", "att"]
    src = "bootstrap (labels from rule score)"
    try:
        h = Q("SELECT * FROM hr_training")
        if len(h) >= 300 and "attrition" in h.columns:
            src = "fed HR dataset"; tr = h.rename(columns={"job_satisfaction": "sat", "tenure_years": "ten", "work_life_balance": "wlb", "monthly_income": "salary", "overtime_hrs": "overtime_hrs"})
            for f in feats:
                if f not in tr: tr[f] = d[f].median()
            X, y = tr[feats].fillna(0), tr.attrition.astype(int)
    except Exception: pass
    if src.startswith("boot"): X, y = d[feats], (d.p + np.random.default_rng(1).normal(0, .05, len(d)) > .5).astype(int)
    sc = StandardScaler().fit(X); Xtr, Xte, ytr, yte = train_test_split(sc.transform(X), y, test_size=.2, random_state=42, stratify=y if y.nunique() > 1 else None)
    lr = LogisticRegression(max_iter=500).fit(Xtr, ytr)
    m = {"accuracy": round(accuracy_score(yte, lr.predict(Xte)), 3), "auc": round(roc_auc_score(yte, lr.predict_proba(Xte)[:, 1]), 3) if yte.nunique() > 1 else None, "source": src}
    _reg_model("logreg_attrition", m); _LR.update(model=lr, sc=sc, feats=feats, metrics=m, trained=time.time()); return d

def _staff_frame():
    d = Q("SELECT st.staff_id, st.outlet_id, st.name, st.role, st.salary, st.overtime_hrs, st.job_satisfaction sat, st.tenure_years ten, st.work_life_balance wlb, st.age, st.predicted_attrition_prob p FROM staff st")
    att = Q("SELECT staff_id, AVG(status='Present') pres FROM attendance GROUP BY staff_id").set_index("staff_id").pres
    d["att"] = d.staff_id.map(att).fillna(.9) * 100; return d

def attrition_table(scope=None, n=25):
    """Per-staff attrition probability with the single biggest driver (coefficient x standardised value): what the Workforce page shows."""
    if not _LR: return pd.DataFrame()
    d = _staff_frame()
    if scope: d = d[d.outlet_id == scope]
    if not len(d): return d
    X = _LR["sc"].transform(d[_LR["feats"]]); d["prob"] = _LR["model"].predict_proba(X)[:, 1].round(3)
    contrib = X * _LR["model"].coef_[0]; d["driver"] = [_LR["feats"][i] for i in contrib.argmax(1)]
    return d.sort_values("prob", ascending=False).head(n)
def attrition_importance():
    if not _LR: return {}
    return dict(zip(_LR["feats"], _LR["model"].coef_[0].round(3).tolist()))

def staff_agent(s):
    if not _LR or time.time() - _LR["trained"] > 900: _attrition_model()
    d = _staff_frame()
    d["prob"] = _LR["model"].predict_proba(_LR["sc"].transform(d[_LR["feats"]]))[:, 1].round(3)
    with _DB_LOCK, conn() as c: c.executemany("UPDATE staff SET predicted_attrition_prob=? WHERE staff_id=?", list(zip(d.prob.tolist(), d.staff_id)))
    d["perf"] = d.sat * 20; hi = d[d.prob > .6]; low = d[(d.perf < 60) | (d.att < 75)]
    per = (100 - (d.groupby("outlet_id").prob.mean() * 100 * .6 + (100 - d.groupby("outlet_id").att.mean()) * .4)).clip(0, 100).round(1)
    a = [{"type": "retention_plan", "target": o, "detail": f"{n} staff above 60% predicted attrition (LogReg {_LR['metrics']['source']})", "severity": "Warning"} for o, n in hi.groupby("outlet_id").size().items() if n >= 4]
    a += [{"type": "staffing_shortage", "target": o, "detail": f"{n} staff below 75% attendance or performance 60", "severity": "Warning"} for o, n in low.groupby("outlet_id").size().items() if n >= 6]
    return AgentResult("staff", round(float(per.mean()), 1), risk_label(per.mean()), f"{len(hi)} high attrition risk, {len(low)} low performers or attendance (attrition model AUC {_LR['metrics'].get('auc', 0):.2f})", {"per_outlet": per.to_dict(), "short_staffed": [x["target"] for x in a if x["type"] == "staffing_shortage"], "model": _LR["metrics"]}, a[:25])

def marketing_agent(s):
    """Agent 4: ROI = (revenue-budget)/budget; KMeans (k=3) customer segments: High-Value, Frequent, Churned."""
    m = Q("SELECT outlet_id, campaign_name, channel, actual_roi, end_date FROM marketing"); m["roi_pct"] = (m.actual_roi - 1) * 100
    cu = Q("SELECT outlet_id, total_spend_90d sp, visit_freq vf, avg_order_value aov, days_since_last_visit dl FROM customers_fr")
    churn = {}; seg_counts = {}
    if len(cu) > 30:
        X = StandardScaler().fit_transform(cu[["sp", "vf", "aov", "dl"]]); km = KMeans(3, n_init=10, random_state=42).fit(X); cu["cl"] = km.labels_
        g = cu.groupby("cl").agg(sp=("sp", "mean"), dl=("dl", "mean")); names = {g.sp.idxmax(): "High-Value", g.dl.idxmax(): "Churned"}
        cu["seg"] = cu.cl.map(lambda k: names.get(k, "Frequent")); churn = cu.assign(ch=cu.seg == "Churned").groupby("outlet_id").ch.mean().to_dict(); seg_counts = cu.seg.value_counts().to_dict()
    per = (m.groupby("outlet_id").roi_pct.mean().clip(0, 300) / 3).round(1); best = m.groupby("channel").actual_roi.mean().idxmax()
    live = m[m.end_date >= datetime.date.today().isoformat()]; low = live[live.actual_roi < 2.0]
    acts = [{"type": "reallocate_budget", "target": r.outlet_id, "detail": f"{r.campaign_name}: ROI {r.roi_pct:.0f}% below 100%; shift budget to {best}", "severity": "Info"} for r in low.head(10).itertuples()]
    acts += [{"type": "win_back_campaign", "target": o, "detail": f"{v*100:.0f}% of customers in Churned segment", "severity": "Warning"} for o, v in churn.items() if v > .5][:10]
    return AgentResult("marketing", round(float(per.mean()), 1), risk_label(per.mean()), f"{len(live)} live campaigns, best channel {best}, {sum(v > .5 for v in churn.values())} outlets with high churn", {"per_outlet": per.to_dict(), "active_outlets": live.outlet_id.unique().tolist(), "best_channel": best, "segments": seg_counts, "churn_share": {k: round(v, 3) for k, v in churn.items()}}, acts)

def audit_agent(s):
    """Agent 5: latest audit per outlet. Pass >= 80, Warning >= 60, Fail < 60. SOP hint from the FAISS/keyword RAG when available."""
    d = Q("SELECT outlet_id, score, category FROM audits ORDER BY audit_date DESC, rowid DESC").drop_duplicates("outlet_id")
    per = d.set_index("outlet_id").score.clip(0, 100).round(1); fail = d[d.score < 60]; warn = d[(d.score >= 60) & (d.score < 80)]
    hint = ""
    try:
        from rag_engine import answer_with_citation
        ctx, _ = answer_with_citation("food safety corrective action procedure"); hint = (str(ctx)[:140] + "...") if ctx else ""
    except Exception: pass
    acts = [{"type": "corrective_action", "target": r.outlet_id, "detail": f"Audit FAIL {r.score:.0f} ({r.category}): corrective plan within 72 h. {hint}", "severity": "Critical", "sla_h": 72} for r in fail.itertuples()]
    acts += [{"type": "corrective_action", "target": r.outlet_id, "detail": f"Audit WARNING {r.score:.0f} ({r.category}): re-check in 14 days", "severity": "Warning", "sla_h": 336} for r in warn.itertuples()][:15]
    return AgentResult("audit", round(float(per.mean()), 1), risk_label(per.mean()), f"Pass {int((d.score >= 80).sum())}, Warning {len(warn)}, Fail {len(fail)}", {"per_outlet": per.to_dict(), "failed": fail.outlet_id.tolist()}, acts)

POS = {"great", "good", "clean", "tasty", "friendly", "fast", "love", "excellent", "value", "fresh"}; NEG = {"slow", "rude", "dirty", "cold", "bad", "long", "wait", "stale", "expensive", "late"}
ISSUES = {"food quality": ("cold", "stale", "taste", "food"), "staff behavior": ("rude", "staff"), "wait time": ("slow", "wait", "long", "late"), "hygiene": ("dirty", "clean", "hygiene"), "value": ("expensive", "value", "price")}
def feedback_agent(s):
    """Agent 7: VADER when installed, else lexicon + rating blend; keyword issue categorisation."""
    f = Q("SELECT outlet_id, rating, comment FROM feedback ORDER BY rowid DESC LIMIT 6000")
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer; v = SentimentIntensityAnalyzer(); f["sent"] = f.comment.map(lambda t: v.polarity_scores(str(t))["compound"]); method = "VADER"
    except Exception:
        f["sent"] = f.comment.map(lambda t: (sum(w in POS for w in str(t).lower().split()) - sum(w in NEG for w in str(t).lower().split())) / 2); method = "lexicon"
    f["sent"] = (.6 * (f.rating - 3) / 2 + .4 * f.sent.clip(-1, 1)); per = ((f.groupby("outlet_id").sent.mean() + 1) / 2 * 100).round(1)
    cat = {k: int(f.comment.str.lower().str.contains("|".join(v)).sum()) for k, v in ISSUES.items()}
    low = per[per < 45]
    return AgentResult("feedback", round(float(per.mean()), 1), risk_label(per.mean()), f"{len(low)} outlets with poor sentiment ({method}); top issue {max(cat, key=cat.get)}", {"per_outlet": per.to_dict(), "issues": cat},
        [{"type": "service_recovery", "target": o, "detail": f"Sentiment score {v:.0f}/100; main issue: {max(cat, key=cat.get)}", "severity": "Warning"} for o, v in low.items()][:15])

def digest_agent(s):
    """Agent 6: weekly digest + immediate alerts. Runs on the weekly trigger or on request; stores the digest and emails the owner when SMTP is set."""
    r = s["results"]; per = r.get("outlet").findings["per_outlet"] if "outlet" in r else {}
    top = sorted(per, key=per.get, reverse=True)[:3]; bot = sorted(per, key=per.get)[:3]
    txt = f"Weekly digest {now()[:10]}: top {top}, bottom {bot}. " + " ".join(f"{k}: {v.summary}." for k, v in r.items() if k != "digest")
    with _DB_LOCK, conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS digests(digest_id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, body TEXT)"); c.execute("INSERT INTO digests(ts,body) VALUES(?,?)", (now(), txt))
    return AgentResult("digest", 100, "Low", "weekly digest generated", {"digest": txt}, [{"type": "digest_sent", "target": "OWNER", "detail": txt[:300], "severity": "Info"}])


def anomaly_agent(s):
    """Live anomaly detection: IsolationForest over each outlet's recent sales-vs-baseline ratio, volatility and feedback sentiment."""
    from sklearn.ensemble import IsolationForest
    sl = Q("SELECT outlet_id, amount FROM sales WHERE source='sim' ORDER BY sale_id DESC LIMIT 4000")
    if len(sl) < 600: return AgentResult("anomaly", 100, "Low", "collecting live data (needs a few minutes of ticks)", {"flagged": []})
    base = Q("SELECT outlet_id, AVG(amount)/? b FROM sales WHERE source='seed' GROUP BY outlet_id", (TICKS_PER_DAY,)).set_index("outlet_id").b
    g = sl.groupby("outlet_id").amount; d = pd.DataFrame({"ratio": g.agg(lambda x: x.iloc[:5].mean()) / base, "vol": g.std() / g.mean()}).dropna()
    if len(d) < 10: return AgentResult("anomaly", 100, "Low", "waiting for enough outlets with both live and baseline sales", {"flagged": []})
    fb = Q("SELECT outlet_id, AVG(sentiment_score) s FROM (SELECT * FROM feedback ORDER BY rowid DESC LIMIT 1500) GROUP BY outlet_id").set_index("outlet_id").s
    d["sent"] = fb.reindex(d.index).fillna(0); iso = IsolationForest(contamination=.05, random_state=42).fit(d); d["flag"] = iso.predict(d) == -1
    bad = d[d.flag | (d.ratio < .6)]; sc = 100 - len(bad) / max(len(d), 1) * 300
    return AgentResult("anomaly", round(max(sc, 0), 1), risk_label(sc), f"{len(bad)} outlets with anomalous sales/feedback pattern (IsolationForest)", {"flagged": bad.index.tolist(), "detail": bad.round(2).reset_index().to_dict("records")[:30], "all": d.round(3).reset_index().to_dict("records")},
        [{"type": "anomaly_review", "target": o, "detail": f"Unusual pattern: sales at {r.ratio*100:.0f}% of baseline, volatility {r.vol:.2f}, sentiment {r.sent:.2f}", "severity": "Critical" if r.ratio < .6 else "Warning"} for o, r in bad.iterrows()][:20])

AGENTS = {"outlet": outlet_agent, "inventory": inventory_agent, "staff": staff_agent, "marketing": marketing_agent, "audit": audit_agent, "feedback": feedback_agent, "anomaly": anomaly_agent, "digest": digest_agent}
REPLAN = {"inventory": lambda r: ["marketing"] if r.risk != "Low" else [], "audit": lambda r: ["staff", "feedback"] if r.risk == "High" else [], "outlet": lambda r: ["inventory", "staff"] if r.risk != "Low" else []}
KW = {"outlet": ["outlet", "store", "revenue", "sales", "performance", "health"], "inventory": ["stock", "inventory", "reorder", "demand"], "staff": ["staff", "attrition", "workforce", "attendance", "employee"],
      "marketing": ["campaign", "roi", "marketing", "promo", "customer"], "audit": ["audit", "compliance", "violation", "sop"], "feedback": ["feedback", "sentiment", "review", "complaint"], "digest": ["digest", "weekly report"], "anomaly": ["anomal", "unusual", "spike", "fraud", "outlier"]}
ACTION_AGENT.update({"digest_sent": "digest", "anomaly_review": "anomaly", "win_back_campaign": "marketing", "service_recovery": "feedback", "health_alert": "outlet"}); OWNER.update({"anomaly_review": "Regional Manager", "win_back_campaign": "Marketing Manager", "service_recovery": "Store Manager", "health_alert": "Regional Manager", "digest_sent": "Franchise Owner"})
W = {"outlet": .30, "inventory": .20, "staff": .20, "marketing": .15, "audit": .15}     # PRS v3 weighted health score
def plan(req):
    q = (req or "").lower(); picked = [a for a, ks in KW.items() if any(re.search(r"\b" + k, q) for k in ks)]
    base = [a for a in AGENTS if a != "digest"]
    return (picked + (["digest"] if "digest" in picked and len(picked) == 1 else [])) if picked else base

def engine(s):
    r = s["results"]; used = [k for k in W if k in r and "per_outlet" in r[k].findings]
    outlets = set().union(*[set(r[k].findings.get("per_outlet", {})) for k in used]) if used else set()
    health = {o: round(sum(W[k] * r[k].findings["per_outlet"].get(o, r[k].score) for k in used) / sum(W[k] for k in used), 1) for o in outlets}
    score = float(np.mean(list(health.values()))) if health else 0.0
    actions = [a for res in r.values() for a in res.actions]
    for o, h in health.items():
        if h < 60: actions.append({"type": "health_alert", "target": o, "detail": f"Outlet health score {h} below 60 (perf, stock, staff, ROI, audit)", "severity": "Critical"})
    if "inventory" in r and "marketing" in r:
        for o in set(r["inventory"].findings.get("outlets", [])) & set(r["marketing"].findings.get("active_outlets", [])):
            actions.append({"type": "pause_promo", "target": o, "detail": "Stock shortage during active campaign: promo paused", "severity": "Critical"})
    if "staff" in r and "inventory" in r:
        for o in set(r["staff"].findings.get("short_staffed", [])) & set(r["inventory"].findings.get("outlets", [])):
            actions.append({"type": "staffing_shortage", "target": o, "detail": "Short-staffed while stock is low: add cover shift", "severity": "Critical"})
    order = {"Critical": 0, "Warning": 1, "Info": 2}; actions.sort(key=lambda a: order.get(a.get("severity"), 3))
    ev = {"franchise_health": round(score, 1), "outlets": len(health), "outlets_below_60": sum(h < 60 for h in health.values()), "agents": {k: {"score": v.score, "risk": v.risk, "summary": v.summary} for k, v in r.items()},
          "critical": sum(a.get("severity") == "Critical" for a in actions), "total_actions": len(actions)}
    return {"score": round(score, 1), "risk": risk_label(score), "narrative": _narrate(ev, actions), "actions": actions, "agents": ev["agents"], "health": health, "evidence": ev}

def _narrate(ev, actions):
    tmpl = f"Franchise health {ev['franchise_health']}/100 across {ev['outlets']} outlets, {ev['outlets_below_60']} below 60. " + " ".join(f"{k.title()}: {v['summary']}." for k, v in ev["agents"].items()) + f" {ev['critical']} critical of {ev['total_actions']} actions."
    try:
        from llm_engine import is_llm_loaded, generate_text
        if not is_llm_loaded(): return tmpl
        txt = generate_text([{"role": "system", "content": "Write a 3-line executive recommendation for a franchise owner. Use only numbers present in the JSON."}, {"role": "user", "content": json.dumps(ev)}], max_new_tokens=160, temperature=0.1)
        ok = all(n in json.dumps(ev) for n in re.findall(r"\d+(?:\.\d+)?", txt or ""))
        return txt.strip() if txt and ok else tmpl
    except Exception: return tmpl

def apply(a, c):
    if a["type"] == "reorder":
        eta = (datetime.datetime.now() + datetime.timedelta(seconds=SIM_DAY_SEC * a.get("lead", 3))).isoformat(timespec="seconds")
        cur = c.execute("INSERT INTO purchase_orders(outlet_id,sku_name,qty,ts,eta_ts,status) VALUES(?,?,?,?,?,'ordered')", (a["target"], a["sku"], a["qty"], now(), eta))
        return f"PO-{cur.lastrowid} created, ETA {eta[11:19]}"
    if a["type"] == "pause_promo":
        n = c.execute("UPDATE marketing SET end_date=date('now','-1 day') WHERE outlet_id=? AND end_date>=date('now')", (a["target"],)).rowcount
        return f"{n} campaign(s) paused"
    return ""

# ---------------------------------------------------------------- UI hooks
def kpi_extra():
    s = Q("SELECT COALESCE(SUM(amount),0) v FROM sales WHERE source='sim'").v[0]; po = Q("SELECT COUNT(*) n FROM purchase_orders WHERE status='ordered'").n[0]
    return [("Live sales since start", f"Rs {s:,.0f}"), ("Purchase orders in transit", int(po))]
