"""Copilot question patterns (Step 7). Every pattern is an intent that runs ONE fixed, read-only, parameterised SQL query over the live tables;
the answer is built from the rows that query returns, so no number is ever made up. Table and column names are fixed in this file, values are bound parameters.

- Spelling mistakes and other wordings: normalize() maps synonyms (store/shop/branch -> outlet, employees/workers -> staff, csat -> satisfaction ...)
  and corrects near-misses against the vocabulary ("custmer", "revanue", "campain", "reoder", "audt" ...).
- RBAC: every query takes the caller's outlet scope (Store Manager and Staff only ever see their own outlet) and the PII mask (staff names are hidden from Staff and Auditor).
- Every answer carries the SQL that produced it and the number of rows it returned."""
import re, difflib
import pandas as pd
from blocks import Q

CANON = {  # synonym -> canonical word
    "outlets": "outlet", "store": "outlet", "stores": "outlet", "shop": "outlet", "shops": "outlet", "branch": "outlet", "branches": "outlet", "franchise": "outlet", "franchises": "outlet",
    "employee": "staff", "employees": "staff", "worker": "staff", "workers": "staff", "personnel": "staff", "workforce": "staff", "people": "staff", "staffs": "staff", "manpower": "staff",
    "csat": "satisfaction", "satisfied": "satisfaction", "turnover": "revenue", "income": "revenue", "earnings": "revenue", "takings": "revenue",
    "stock": "inventory", "stocks": "inventory", "sku": "inventory", "skus": "inventory", "item": "inventory", "items": "inventory", "product": "inventory", "products": "inventory", "ingredient": "inventory", "ingredients": "inventory",
    "campaigns": "campaign", "promotion": "campaign", "promotions": "campaign", "promo": "campaign", "promos": "campaign", "ads": "campaign",
    "reviews": "review", "feedback": "review", "feedbacks": "review", "comment": "review", "comments": "review", "complaint": "review", "complaints": "review",
    "audits": "audit", "inspection": "audit", "inspections": "audit", "compliance": "audit", "failing": "fail", "failed": "fail", "fails": "fail", "failures": "fail",
    "tickets": "ticket", "alerts": "ticket", "alert": "ticket", "violations": "violation", "ratings": "rating", "orders": "order", "costs": "cost", "expenses": "cost",
    "biggest": "highest", "largest": "highest", "greatest": "highest", "maximum": "highest", "max": "highest", "top": "highest", "most": "highest", "best": "best",
    "smallest": "lowest", "least": "lowest", "minimum": "lowest", "min": "lowest", "poorest": "lowest", "weakest": "lowest", "bottom": "lowest",
    "restock": "reorder", "restocking": "reorder", "reordering": "reorder", "replenish": "reorder", "reorders": "reorder", "overtime": "overtime", "mean": "average", "avg": "average",
}
VOCAB = set(CANON.values()) | set(CANON) | {w for w in """customer satisfaction revenue inventory reorder level threshold review negative positive audit violation rating average total count many number list show which what who how
 highest lowest best worst campaign roi return channel staff attrition risk likely leave quit employee outlet purchase order pending open critical urgent ticket sales week today last
 stockout shortage operating cost running attendance salary city live active fail score percent items need below under above more less than with for the of in at by per each all every has have does are is
 give tell find display top first""".split()}
STOP = {"works", "work", "working", "worked", "earns", "earn", "does", "the", "and", "for", "with", "that", "this", "are", "was", "were", "has", "have", "does", "did", "you", "your", "our", "can", "please", "could", "would", "tell", "give", "show", "list", "which", "what", "who", "how", "when", "where", "there"}

def normalize(q):
    """lower-case, fix near-miss spellings, map synonyms to one canonical word (outlet ids and numbers are kept as they are)."""
    out = []
    for tok in re.findall(r"out-\d+|[a-z]+|\d+(?:\.\d+)?|[<>=%]", q.lower()):
        if tok in CANON: tok = CANON[tok]
        elif tok.isalpha() and len(tok) >= 4 and tok not in VOCAB and tok not in STOP:
            m = difflib.get_close_matches(tok, VOCAB, n=1, cutoff=0.78)
            if m: tok = CANON.get(m[0], m[0])
        out.append(tok)
    return " ".join(out)

# ------------------------------------------------------------------ helpers
def _n(q, default):
    m = re.search(r"\b(?:highest|lowest|best|worst|first|top|bottom)\s+(\d{1,2})\b|\b(\d{1,2})\s+(?:outlet|staff|inventory|campaign|review|audit|ticket|order)", q)
    return min(25, int(next(g for g in m.groups() if g))) if m else default
def _scope(scope, col="outlet_id", pre=" WHERE "):
    return (f"{pre}{col}=?", [scope]) if scope else ("", [])
def _sql_shown(sql, params):
    s = sql
    for p in params: s = s.replace("?", repr(p) if isinstance(p, str) else str(p), 1)
    return s
def _run(sql, params):
    return Q(sql, tuple(params))
def _out(intent, answer, df, sql, params):
    return {"intent": intent, "answer": answer, "df": df if df is not None and len(df) else None, "sql": _sql_shown(sql, params), "rows": 0 if df is None else int(len(df)), "params": list(params), "complete": True}
def _none(intent, what, sql, params, scope):
    return _out(intent, f"No {what} found" + (f" for {scope}." if scope else "."), None, sql, params)
def _tail(q): return re.search(r"out-(\d+)", q)
def _oid(q, scope):
    m = _tail(q); return scope or (f"OUT-{int(m.group(1)):03d}" if m else None)
def _pct(x): return f"{float(x):.0%}"
def _money(x): return f"{float(x):,.0f}"

# ------------------------------------------------------------------ intents: (id, example question, regex on the normalized question, handler(q, scope, mask))
def csat(q, scope, mask, low):
    w, p = _scope(scope); n = _n(q, 5); sql = f"SELECT outlet_id, outlet_name, location, customer_satisfaction FROM outlets{w} ORDER BY customer_satisfaction {'ASC' if low else 'DESC'} LIMIT ?"; p += [n]
    d = _run(sql, p)
    if not len(d): return _none("lowest_csat" if low else "highest_csat", "outlets", sql, p, scope)
    r = d.iloc[0]; return _out("lowest_csat" if low else "highest_csat", f"**{r.outlet_id}** ({r.outlet_name}, {r.location}) has the {'lowest' if low else 'highest'} customer satisfaction: **{r.customer_satisfaction:.2f}** out of 5.", d, sql, p)

def revenue(q, scope, mask, low):
    w, p = _scope(scope); n = _n(q, 5); sql = f"SELECT outlet_id, outlet_name, location, revenue FROM outlets{w} ORDER BY revenue {'ASC' if low else 'DESC'} LIMIT ?"; p += [n]; d = _run(sql, p)
    if not len(d): return _none("lowest_revenue" if low else "highest_revenue", "outlets", sql, p, scope)
    r = d.iloc[0]; return _out("lowest_revenue" if low else "highest_revenue", f"**{r.outlet_id}** ({r.outlet_name}) has the {'lowest' if low else 'highest'} revenue: **{_money(r.revenue)}**.", d, sql, p)

def staff_count(q, scope, mask):
    o = _oid(q, scope); w, p = (" WHERE outlet_id=?", [o]) if o else ("", []); sql = f"SELECT COUNT(*) AS staff FROM staff{w}"; d = _run(sql, p); n = int(d.staff[0])
    return _out("staff_count", f"**{o}** has **{n:,}** staff members." if o else f"There are **{n:,}** staff members in total.", d, sql, p)

def most_staff(q, scope, mask):
    w, p = _scope(scope); n = _n(q, 5); sql = f"SELECT outlet_id, COUNT(*) AS staff FROM staff{w} GROUP BY outlet_id ORDER BY staff DESC, outlet_id LIMIT ?"; p += [n]; d = _run(sql, p)
    if not len(d): return _none("highest_staff_count", "staff", sql, p, scope)
    r = d.iloc[0]; return _out("highest_staff_count", f"**{r.outlet_id}** has the most staff: **{int(r.staff)}**.", d, sql, p)

def attrition(q, scope, mask):
    w, p = _scope(scope, pre=" AND "); n = _n(q, 10); cols = "staff_id, role, outlet_id, predicted_attrition_prob" if mask else "staff_id, name, role, outlet_id, predicted_attrition_prob"
    sql = f"SELECT {cols} FROM staff WHERE predicted_attrition_prob>=0.6{w} ORDER BY predicted_attrition_prob DESC LIMIT ?"; p += [n]; d = _run(sql, p)
    cs, cp = f"SELECT COUNT(*) AS n FROM staff WHERE predicted_attrition_prob>=0.6{w}", ([scope] if scope else []); tot = int(_run(cs, cp).n[0])
    if not tot: return _none("high_attrition", "employees with a high attrition risk (60% or more)", sql, p, scope)
    d = d.assign(predicted_attrition_prob=d.predicted_attrition_prob.map(_pct)); return _out("high_attrition", f"**{tot:,}** employees have a high attrition risk (60% or more){' at ' + scope if scope else ''}. The {len(d)} highest are below." + (" Names are hidden for your role." if mask else ""), d, sql, p)

def below_reorder(q, scope, mask):
    w, p = _scope(scope, pre=" AND "); n = _n(q, 15); sql = f"SELECT outlet_id, sku_name, current_stock, reorder_threshold FROM inventory WHERE current_stock<=reorder_threshold{w} ORDER BY current_stock*1.0/MAX(reorder_threshold,1) LIMIT ?"; p += [n]; d = _run(sql, p)
    tot = int(_run(f"SELECT COUNT(*) n FROM inventory WHERE current_stock<=reorder_threshold{w}", [scope] if scope else []).n[0])
    if not tot: return _none("below_reorder", "inventory items at or below their reorder level", sql, p, scope)
    return _out("below_reorder", f"**{tot:,}** inventory items are at or below their reorder level{' at ' + scope if scope else ''}. The {len(d)} most urgent are below.", d, sql, p)

def reorder_count(q, scope, mask):
    w, p = _scope(scope, pre=" AND "); sql = f"SELECT COUNT(*) AS items_to_reorder FROM inventory WHERE current_stock<=reorder_threshold{w}"; d = _run(sql, p)
    return _out("reorder_count", f"**{int(d.items_to_reorder[0]):,}** inventory items need reordering (stock at or below the reorder level){' at ' + scope if scope else ''}.", d, sql, p)

def stockout(q, scope, mask):
    w, p = _scope(scope); n = _n(q, 10); sql = f"SELECT outlet_id, sku_name, current_stock, weekly_demand, stockout_risk_prob FROM inventory{w} ORDER BY stockout_risk_prob DESC LIMIT ?"; p += [n]; d = _run(sql, p)
    if not len(d): return _none("stockout_risk", "inventory items", sql, p, scope)
    r = d.iloc[0]; d = d.assign(stockout_risk_prob=d.stockout_risk_prob.map(_pct)); return _out("stockout_risk", f"Highest stock-out risk: **{r.sku_name}** at **{r.outlet_id}** ({_pct(r.stockout_risk_prob)}). Top {len(d)} below.", d, sql, p)

def roi(q, scope, mask, low):
    w, p = _scope(scope); n = _n(q, 5); sql = f"SELECT campaign_id, campaign_name, outlet_id, channel, budget, actual_roi FROM marketing{w} ORDER BY actual_roi {'ASC' if low else 'DESC'} LIMIT ?"; p += [n]; d = _run(sql, p)
    if not len(d): return _none("worst_campaign_roi" if low else "best_campaign_roi", "campaigns", sql, p, scope)
    r = d.iloc[0]; return _out("worst_campaign_roi" if low else "best_campaign_roi", f"The campaign with the {'lowest' if low else 'best'} ROI is **{r.campaign_name}** ({r.campaign_id}, {r.channel}, {r.outlet_id}): ROI **{r.actual_roi:.2f}**x.", d, sql, p)

def avg_roi(q, scope, mask):
    w, p = _scope(scope); sql = f"SELECT channel, ROUND(AVG(actual_roi),2) AS avg_roi, COUNT(*) AS campaigns FROM marketing{w} GROUP BY channel ORDER BY avg_roi DESC"; d = _run(sql, p)
    if not len(d): return _none("average_campaign_roi", "campaigns", sql, p, scope)
    sql2 = f"SELECT ROUND(AVG(actual_roi),2) AS v FROM marketing{w}"; v = float(_run(sql2, p).v[0])
    return _out("average_campaign_roi", f"The average campaign ROI is **{v:.2f}**x across {int(d.campaigns.sum()):,} campaigns. Best channel: **{d.channel[0]}** ({d.avg_roi[0]:.2f}x).", d, sql, p)

def negative_reviews(q, scope, mask):
    week = bool(re.search(r"\bweek\b|\brecent\b|\blatest\b", q)); w, p = _scope(scope, pre=" AND "); n = _n(q, 10)
    recent = " AND date>=date((SELECT MAX(date) FROM feedback),'-7 day')" if week else ""
    sql = f"SELECT feedback_id, outlet_id, rating, date, comment FROM feedback WHERE rating<=2{recent}{w} ORDER BY date DESC, rating LIMIT ?"; p += [n]; d = _run(sql, p)
    tot = int(_run(f"SELECT COUNT(*) n FROM feedback WHERE rating<=2{recent}{w}", [scope] if scope else []).n[0])
    if not tot: return _none("negative_reviews", "negative reviews" + (" in the last week of data" if week else ""), sql, p, scope)
    return _out("negative_reviews", f"**{tot:,}** negative reviews (rating 1-2){' in the last week of data' if week else ''}{' at ' + scope if scope else ''}. The latest {len(d)} are below.", d, sql, p)

def most_negative(q, scope, mask):
    w, p = _scope(scope, pre=" AND "); n = _n(q, 5); sql = f"SELECT outlet_id, COUNT(*) AS negative_reviews FROM feedback WHERE rating<=2{w} GROUP BY outlet_id ORDER BY negative_reviews DESC, outlet_id LIMIT ?"; p += [n]; d = _run(sql, p)
    if not len(d): return _none("most_negative_reviews", "negative reviews", sql, p, scope)
    r = d.iloc[0]; return _out("most_negative_reviews", f"**{r.outlet_id}** has the most negative reviews: **{int(r.negative_reviews)}**.", d, sql, p)

def avg_rating(q, scope, mask):
    w, p = _scope(scope); sql = f"SELECT ROUND(AVG(rating),2) AS average_rating, COUNT(*) AS reviews FROM feedback{w}"; d = _run(sql, p)
    if not int(d.reviews[0]): return _none("average_rating", "reviews", sql, p, scope)
    return _out("average_rating", f"The average customer rating is **{d.average_rating[0]:.2f}** out of 5, from {int(d.reviews[0]):,} reviews{' at ' + scope if scope else ''}.", d, sql, p)

def failed_audits(q, scope, mask):
    w, p = _scope(scope, pre=" AND "); n = _n(q, 10); sql = f"SELECT audit_id, outlet_id, audit_date, score, violations, category, status FROM audits WHERE score<60{w} ORDER BY audit_date DESC, score LIMIT ?"; p += [n]; d = _run(sql, p)
    tot = int(_run(f"SELECT COUNT(*) n FROM audits WHERE score<60{w}", [scope] if scope else []).n[0])
    if not tot: return _none("failed_audits", "failed audits (score below 60)", sql, p, scope)
    return _out("failed_audits", f"**{tot:,}** audits failed (score below 60){' at ' + scope if scope else ''}. The latest {len(d)} are below.", d, sql, p)

def violations(q, scope, mask):
    w, p = _scope(scope); n = _n(q, 5); sql = f"SELECT outlet_id, SUM(violations) AS violations, COUNT(*) AS audits FROM audits{w} GROUP BY outlet_id ORDER BY violations DESC, outlet_id LIMIT ?"; p += [n]; d = _run(sql, p)
    if not len(d): return _none("highest_violations", "audits", sql, p, scope)
    r = d.iloc[0]; return _out("highest_violations", f"**{r.outlet_id}** has the most audit violations: **{int(r.violations)}** across {int(r.audits)} audits.", d, sql, p)

def total_outlets(q, scope, mask):
    w, p = _scope(scope); sql = f"SELECT COUNT(*) AS outlets FROM outlets{w}"; d = _run(sql, p); n = int(d.outlets[0])
    return _out("total_outlets", f"You can see **{n:,}** outlet{'s' if n != 1 else ''}" + (f" ({scope})." if scope else " in the franchise."), d, sql, p)

def op_cost(q, scope, mask):
    w, p = _scope(scope); n = _n(q, 5); sql = f"SELECT outlet_id, outlet_name, location, operating_costs, revenue FROM outlets{w} ORDER BY operating_costs DESC LIMIT ?"; p += [n]; d = _run(sql, p)
    if not len(d): return _none("highest_operating_cost", "outlets", sql, p, scope)
    r = d.iloc[0]; return _out("highest_operating_cost", f"**{r.outlet_id}** ({r.outlet_name}) has the highest operating costs: **{_money(r.operating_costs)}**.", d, sql, p)

def tickets(q, scope, mask):
    w, p = _scope(scope, col="target", pre=" AND "); n = _n(q, 10); crit = " AND severity='Critical'" if re.search(r"critical|urgent", q) else ""
    sql = f"SELECT action_id, severity, type, target, detail FROM agent_actions WHERE status IN ('open','proposed'){crit}{w} ORDER BY CASE severity WHEN 'Critical' THEN 0 WHEN 'Warning' THEN 1 ELSE 2 END, action_id DESC LIMIT ?"; p += [n]; d = _run(sql, p)
    tot = int(_run(f"SELECT COUNT(*) n FROM agent_actions WHERE status IN ('open','proposed'){crit}{w}", [scope] if scope else []).n[0])
    if not tot: return _none("open_tickets", ("critical " if crit else "") + "open tickets", sql, p, scope)
    return _out("open_critical_tickets" if crit else "open_tickets", f"**{tot:,}** {'critical ' if crit else ''}tickets are open{' for ' + scope if scope else ''}. The {len(d)} most severe are below.", d, sql, p)

def overtime(q, scope, mask):
    w, p = _scope(scope); n = _n(q, 10); cols = "staff_id, role, outlet_id, overtime_hrs" if mask else "staff_id, name, role, outlet_id, overtime_hrs"
    sql = f"SELECT {cols} FROM staff{w} ORDER BY overtime_hrs DESC LIMIT ?"; p += [n]; d = _run(sql, p)
    if not len(d): return _none("highest_overtime", "staff", sql, p, scope)
    return _out("highest_overtime", f"The highest overtime is **{d.overtime_hrs[0]:.1f} hours** (staff {d.staff_id[0]}, {d.outlet_id[0]}). Top {len(d)} below." + (" Names are hidden for your role." if mask else ""), d, sql, p)

def pending_po(q, scope, mask):
    w, p = _scope(scope, pre=" AND "); n = _n(q, 10); sql = f"SELECT po_id, outlet_id, sku_name, qty, eta_ts, status FROM purchase_orders WHERE LOWER(status) NOT IN ('delivered','received','closed'){w} ORDER BY eta_ts LIMIT ?"; p += [n]; d = _run(sql, p)
    tot = int(_run(f"SELECT COUNT(*) n FROM purchase_orders WHERE LOWER(status) NOT IN ('delivered','received','closed'){w}", [scope] if scope else []).n[0])
    if not tot: return _none("pending_purchase_orders", "pending purchase orders", sql, p, scope)
    return _out("pending_purchase_orders", f"**{tot:,}** purchase orders are still on their way{' for ' + scope if scope else ''}. The {len(d)} arriving first are below.", d, sql, p)

def sales_week(q, scope, mask):
    w, p = _scope(scope, pre=" AND "); sql = f"SELECT SUBSTR(ts,1,10) AS day, ROUND(SUM(amount)) AS sales FROM sales WHERE ts>=date((SELECT MAX(ts) FROM sales),'-6 day'){w} GROUP BY day ORDER BY day DESC"; d = _run(sql, p)
    if not len(d): return _none("sales_last_7_days", "sales", sql, p, scope)
    return _out("sales_last_7_days", f"Sales over the last 7 days of data: **{_money(d.sales.sum())}**{' at ' + scope if scope else ''}. Best day {d.loc[d.sales.idxmax(), 'day']} ({_money(d.sales.max())}).", d, sql, p)

# (intent id, example question, regex on the NORMALIZED question, handler). First match wins, so the specific patterns come before the general ones.
INTENTS = [
    ("lowest_csat",             "Which outlet has the lowest customer satisfaction?",   r"lowest.*satisfaction|satisfaction.*lowest|worst.*satisfaction",             lambda q, s, m: csat(q, s, m, True)),
    ("highest_csat",            "Which outlet has the best customer satisfaction?",     r"(highest|best).*satisfaction|satisfaction.*(highest|best)",                 lambda q, s, m: csat(q, s, m, False)),
    ("lowest_revenue",          "Which outlet has the lowest revenue?",                 r"(lowest|worst).*revenue",                                                   lambda q, s, m: revenue(q, s, m, True)),
    ("highest_revenue",         "Which outlet has the highest revenue?",                r"(highest|best).*revenue|revenue.*(highest|best)",                           lambda q, s, m: revenue(q, s, m, False)),
    ("highest_overtime",        "Who works the most overtime?",                         r"overtime",                                                                   overtime),
    ("highest_staff_count",     "Which outlet has the most staff?",                     r"(highest|most).*(staff|outlet).*(staff|headcount)|(highest|most) staff|staff.*(highest|most)", most_staff),
    ("staff_count",             "How many staff does OUT-010 have?",                    r"how many staff|staff count|number of staff|count.*staff",                   staff_count),
    ("high_attrition",          "Which employees have a high attrition risk?",          r"attrition|likely (to )?(leave|quit)|leave soon|churn|resign",                       attrition),
    ("reorder_count",           "How many inventory items need reordering?",            r"how many.*reorder|number.*reorder|count.*reorder|reorder.*how many",         reorder_count),
    ("below_reorder",           "List inventory items below reorder level",             r"reorder|below.*level|inventory.*(low|short)|(low|short).*inventory",                                below_reorder),
    ("stockout_risk",           "Which inventory items have the highest stockout risk?", r"stockout|inventory out|run out|shortage",                                       stockout),
    ("worst_campaign_roi",      "Which campaign has the worst ROI?",                    r"(lowest|worst).*(roi|return)",                                               lambda q, s, m: roi(q, s, m, True)),
    ("average_campaign_roi",    "What is the average campaign ROI?",                    r"average.*(roi|return)|(roi|return).*average",                                avg_roi),
    ("best_campaign_roi",       "Which campaign has the best ROI?",                     r"(highest|best).*(roi|return)|(roi|return).*(highest|best)|campaign.*roi",   lambda q, s, m: roi(q, s, m, False)),
    ("most_negative_reviews",   "Which outlet has the most negative reviews?",          r"(highest|most).*negative|negative.*(highest|most)",                          most_negative),
    ("negative_reviews",        "Show negative reviews this week",                      r"negative|bad review|poor review|unhappy|low rating",                         negative_reviews),
    ("average_rating",          "What is the average customer rating?",                 r"average.*rating|rating.*average",                                            avg_rating),
    ("failed_audits",           "Show failed audits",                                   r"fail.*audit|audit.*fail",                                                    failed_audits),
    ("highest_violations",      "Which outlet has the most audit violations?",          r"violation",                                                                  violations),
    ("highest_operating_cost",  "Which outlet has the highest operating costs?",        r"(highest|most).*(operating|running)? ?cost|cost.*(highest|most)|operating cost", op_cost),
    ("open_critical_tickets",   "Show critical open tickets",                           r"ticket",                                                                     tickets),
    ("pending_purchase_orders", "Which purchase orders are still pending?",             r"(pending|open|outstanding|undelivered|transit).*order|order.*(pending|outstanding)", pending_po),
    ("sales_last_7_days",       "What were the total sales in the last 7 days?",        r"(total|how much).*sales|sales.*(week|7 day|last)",                           sales_week),
    ("total_outlets",           "How many outlets are there?",                          r"how many outlet|number of outlet|count.*outlet|total outlet",                total_outlets),
]
EXAMPLES = [e for _, e, _, _ in INTENTS]
RANKING = {"lowest_csat", "highest_csat", "lowest_revenue", "highest_revenue", "highest_staff_count", "most_negative_reviews", "highest_violations", "highest_operating_cost", "best_campaign_roi", "worst_campaign_roi"}

def answer(q, scope=None, mask=False):
    """-> dict(intent, answer, df, sql, rows) for a recognised question, else None."""
    nq = normalize(q)
    for iid, _ex, rx, fn in INTENTS:
        if re.search(rx, nq):
            r = fn(nq, scope, mask)
            if scope and r and iid in RANKING and r.get("df") is not None:       # one visible outlet is not a ranking: say so instead of calling it "the highest"
                r["answer"] = f"Rankings compare outlets across the chain, so for your role this shows {scope} only. " + r["answer"]
            return r
    return None

def suggestions(scope=None, seed=""):
    """Three valid questions for the polite fallback (own-outlet wording for a scoped role)."""
    import random
    pool = ["Which outlet has the lowest customer satisfaction?", "How many inventory items need reordering?", "Which campaign has the best ROI?", "Show negative reviews this week", "Show failed audits",
            "Which employees have a high attrition risk?", "What is the average customer rating?", "Show critical open tickets"]
    if scope: pool = ["How many staff does " + scope + " have?", "Show inventory items below reorder level", "Show negative reviews this week", "Show failed audits", "What is the average customer rating?", "Show critical open tickets"]
    return random.Random(seed).sample(pool, 3)
