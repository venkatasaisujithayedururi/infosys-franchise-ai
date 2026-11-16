"""Exact-answer engine for the Copilot. Turns a plain-English question into a read-only, parameterised SQL query over the live tables
(counts, top/bottom N, averages, totals, group-by, filters, ID lookups) and returns the real rows. The LLM only explains afterwards;
it never has to guess a number. Table and column names come from a fixed whitelist, values are always bound parameters."""
import re
from blocks import Q

TABLES = {
    "Franchise": {
        "outlets": (["outlet", "store", "branch", "franchise"], "outlet_id", ["outlet_id", "outlet_name", "location", "tier", "revenue", "customer_satisfaction", "staff_headcount"], "revenue"),
        "staff": (["staff", "employee", "worker", "workforce", "people"], "staff_id", ["staff_id", "name", "role", "outlet_id", "salary", "overtime_hrs", "predicted_attrition_prob"], "predicted_attrition_prob"),
        "inventory": (["inventory", "sku", "item", "product", "stock level"], "record_id", ["outlet_id", "sku_name", "category", "current_stock", "reorder_threshold", "stockout_risk_prob"], "stockout_risk_prob"),
        "marketing": (["campaign", "marketing", "promotion", "advert"], "campaign_id", ["campaign_id", "campaign_name", "outlet_id", "channel", "budget", "actual_roi", "conversions"], "actual_roi"),
        "feedback": (["feedback", "review", "complaint", "comment"], "feedback_id", ["feedback_id", "outlet_id", "rating", "sentiment_score", "date", "comment"], "rating"),
        "audits": (["audit", "inspection", "compliance"], "audit_id", ["audit_id", "outlet_id", "audit_date", "score", "violations", "category", "status"], "score"),
        "sales": (["sale", "transaction", "takings"], "sale_id", ["outlet_id", "ts", "amount", "tx_count", "source"], "amount"),
        "purchase_orders": (["purchase order", "reorder order", "po"], "po_id", ["po_id", "outlet_id", "sku_name", "qty", "eta_ts", "status"], "qty"),
        "attendance": (["attendance", "absent", "absence", "present"], "att_id", ["staff_id", "outlet_id", "ts", "status"], None),
        "agent_actions": (["ticket", "action", "task", "approval", "alert"], "action_id", ["action_id", "type", "target", "severity", "status", "assignee", "detail"], None),
    },
    "Freight": {
        "shipments": (["shipment", "cargo", "container", "consignment"], "shipment_id", ["shipment_id", "origin_port", "dest_port", "carrier", "status", "eta", "weight_kg", "predicted_delay_risk"], "predicted_delay_risk"),
        "freight_quotes": (["quote", "quotation", "price", "pricing"], "quote_id", ["quote_id", "shipment_id", "customer_id", "carrier", "final_price", "margin_pct", "status"], "final_price"),
        "ports": (["port", "terminal", "harbour", "harbor"], "port_id", ["port_name", "country", "region", "congestion_index", "avg_dwell_days"], "congestion_index"),
        "carriers": (["carrier", "shipping line", "liner", "line"], "carrier_id", ["name", "rating", "on_time_pct", "avg_cost_index", "risk_level"], "on_time_pct"),
        "customers": (["customer", "client", "shipper"], "customer_id", ["customer_id", "name", "industry", "priority_tier", "credit_risk"], "credit_risk"),
        "weather_risks": (["weather", "storm", "wave", "wind", "forecast"], "port_name", ["port_name", "current_severity", "forecast", "wind_speed", "wave_height"], "wave_height"),
        "vessels": (["vessel", "ship ", "ais", "voyage"], "shipment_id", ["shipment_id", "route_name", "lat", "lon", "progress", "speed_kn"], "progress"),
        "quote_requests": (["request", "enquiry", "enquiries", "inquiry"], "req_id", ["req_id", "ts", "origin", "dest", "cargo", "weight_t", "status", "quote_id"], None),
        "customs_rules": (["customs", "duty", "hs code", "tariff"], "chapter", ["chapter", "goods", "duty_pct", "docs", "restricted"], "duty_pct"),
        "agent_actions": (["ticket", "action", "task", "approval", "alert"], "action_id", ["action_id", "type", "target", "severity", "status", "assignee", "detail"], None),
    },
}
CSYN = {"revenue": ["revenue", "turnover"], "customer_satisfaction": ["satisfaction", "csat"], "staff_headcount": ["headcount"], "salary": ["salary", "pay", "wage"], "overtime_hrs": ["overtime"],
        "job_satisfaction": ["job satisfaction"], "tenure_years": ["tenure"], "predicted_attrition_prob": ["attrition", "churn", "likely to leave", "quit"], "current_stock": ["current stock", "units in stock"],
        "reorder_threshold": ["reorder level", "threshold"], "weekly_demand": ["demand"], "lead_time_days": ["lead time"], "stockout_risk_prob": ["stockout", "stock-out", "stock out", "shortage", "run out"],
        "actual_roi": ["roi", "return on"], "sentiment_score": ["sentiment"], "score": ["audit score", "score"], "violations": ["violation"], "amount": ["amount", "sales value"], "qty": ["quantity", "qty"],
        "congestion_index": ["congestion", "congested", "crowded"], "avg_dwell_days": ["dwell"], "on_time_pct": ["on-time", "on time", "punctual", "punctuality", "reliab"], "avg_cost_index": ["cost index"],
        "predicted_delay_risk": ["delay risk", "delay", "delayed"], "weight_kg": ["weight"], "final_price": ["final price", "price", "quote value", "worth"], "margin_pct": ["margin"], "base_cost": ["base cost"],
        "insurance": ["insurance"], "customs_fee": ["customs fee"], "fuel_surcharge": ["fuel"], "credit_risk": ["credit risk", "credit"], "duty_pct": ["duty"], "wave_height": ["wave"], "wind_speed": ["wind"],
        "speed_kn": ["speed"], "progress": ["progress", "completed"], "operating_costs": ["operating cost", "costs"], "rating": ["rating", "rated", "stars"], "budget": ["budget", "spend"], "reach": ["reach"], "conversions": ["conversion"]}
BAD = {"predicted_attrition_prob", "stockout_risk_prob", "violations", "congestion_index", "avg_dwell_days", "predicted_delay_risk", "credit_risk", "operating_costs", "overtime_hrs", "lead_time_days", "avg_cost_index", "wave_height", "wind_speed"}
PROB = {"predicted_attrition_prob", "stockout_risk_prob", "predicted_delay_risk", "credit_risk", "progress", "sentiment_score"}
LABEL = {"outlets": "outlet_name", "staff": "name", "carriers": "name", "customers": "name", "ports": "port_name", "inventory": "sku_name", "marketing": "campaign_name"}
GENERIC = {"port", "line", "terminal", "cargo", "ocean", "shipping", "the", "of"}

def _w(q, term): return re.search(r"(?<![a-z0-9])" + re.escape(term.strip()) + r"(?:s|es)?(?![a-z0-9])", q) is not None
def _num(s, unit):
    v = float(s.replace(",", "")); u = (unit or "").lower()
    return v * {"k": 1e3, "m": 1e6, "lakh": 1e5, "lakhs": 1e5, "cr": 1e7, "crore": 1e7, "crores": 1e7}.get(u, 1)
_NUM = {}
def _cols(t):
    df = Q(f"SELECT * FROM {t} LIMIT 20"); _NUM[t] = {c for c in df.columns if str(df[c].dtype)[:3] in ("flo", "int") }
    return list(df.columns)
PL = {"inventory": "inventory records", "staff": "staff", "marketing": "campaigns", "feedback": "feedback entries", "audits": "audits", "sales": "sales records", "attendance": "attendance records", "freight_quotes": "quotes", "ports": "ports", "carriers": "carriers", "customs_rules": "customs rules", "weather_risks": "port weather entries", "agent_actions": "tickets", "purchase_orders": "purchase orders", "quote_requests": "quote requests", "outlets": "outlets", "shipments": "shipments", "customers": "customers", "vessels": "vessels"}
def pct(df, cols):
    df = df.copy()
    for c in cols:
        if c in df.columns and c in PROB: df[c] = df[c].map(lambda x: f"{x:.0%}" if isinstance(x, (int, float)) and abs(x) <= 1 else x)
    return df
def _alias(v):
    v = str(v); out = {v.lower()}; base = re.sub(r"\(.*?\)", "", v).strip().lower(); out.add(base)
    out.update(m.lower() for m in re.findall(r"\((.*?)\)", v))
    core = " ".join(w for w in base.split() if w not in GENERIC)
    if len(core) >= 3: out.add(core)
    return {a for a in out if len(a) >= 3}
def _fmt(v):
    if isinstance(v, float): return f"{v:,.2f}" if abs(v) < 1000 else f"{v:,.0f}"
    if isinstance(v, int): return f"{v:,}" if abs(v) >= 10000 else str(v)
    return str(v)
def md(df):
    if df is None or not len(df): return ""
    h = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    return h + "\n".join("| " + " | ".join(_fmt(x).replace("|", "/").replace("\n", " ")[:90] for x in r) + " |" for r in df.itertuples(index=False))

def lookup(kind, q, scope=None):
    """ID in the question -> the exact row(s) plus its open tickets."""
    ids = list(dict.fromkeys(re.findall(r"\b(OUT-\d+|STF-\d+|EMP-\d+|SHP-[A-Z0-9-]+|QTE-[A-Z0-9-]+|PORT-\d+|CAR-\d+|CUST-\d+|CAMP-\d+|AUD-\d+|FB-\d+)\b", q, re.I)))
    ids = [i.upper() for i in ids]
    if not ids: return None
    parts, sqls = [], []
    for e in ids[:4]:
        if scope and e != scope and not e.startswith("PORT") and not e.startswith("CAR"): parts.append(f"{e} is outside your outlet scope ({scope})."); continue
        for t, (_, idc, cols, _m) in TABLES[kind].items():
            if t == "agent_actions": continue
            try: df = Q(f"SELECT * FROM {t} WHERE {idc}=?", (e,))
            except Exception: continue
            if len(df):
                r = df.iloc[0]; parts.append(f"**{e}** ({t}): " + "; ".join(f"{c}={_fmt(r[c])}" for c in df.columns if str(r[c]) not in ("None", "nan"))); sqls.append(f"SELECT * FROM {t} WHERE {idc}='{e}'"); break
        tk = Q("SELECT action_id, type, severity, status, detail FROM agent_actions WHERE target=? AND status IN ('open','proposed') ORDER BY action_id DESC LIMIT 5", (e,))
        if len(tk): parts.append(f"Open tickets on {e}:\n" + md(tk)); sqls.append(f"SELECT … FROM agent_actions WHERE target='{e}' AND status IN ('open','proposed')")
    return {"answer": "\n\n".join(parts), "df": None, "sql": "; ".join(sqls)} if parts else None

def answer(kind, q, scope=None, mask=False):
    """-> dict(answer, sql, df, table) when the question maps to the data, else None."""
    ql = q.lower().strip()
    if not ql: return None
    d = lookup(kind, q, scope)
    if d: return d
    T = TABLES[kind]; sc = {}
    for t, (syn, _, _, _) in T.items(): sc[t] = sum(3 for s in syn if _w(ql, s))
    cols_of = {}
    for t in T:
        try: cols_of[t] = _cols(t)
        except Exception: cols_of[t] = []
    hits = {c: any(_w(ql, s) for s in (CSYN.get(c, []) + [c.replace("_", " ")])) for c in {c for v in cols_of.values() for c in v}}
    for t, cs in cols_of.items(): sc[t] += sum(2 for c in cs if hits.get(c) and c not in ("status", "type", "date", "name"))
    if not sc or max(sc.values()) <= 0: return None
    order = list(T); t = max(order, key=lambda x: (sc[x], -order.index(x)))
    syn, idc, show, dmetric = T[t]; cs = cols_of[t]
    # aggregation
    agg = "list"
    if re.search(r"\b(how many|number of|count)\b", ql): agg = "count"
    elif re.search(r"\b(average|avg|mean)\b", ql): agg = "avg"
    elif re.search(r"\b(total|sum|overall|combined)\b", ql): agg = "sum"
    elif re.search(r"\b(highest|most|top|best|largest|biggest|maximum|max|greatest|riskiest|worst|lowest|least|smallest|minimum|min|bottom|weakest|cheapest|fewest|poorest)\b", ql): agg = "rank"
    # metric
    mc = [c for c in cs if hits.get(c) and c in _NUM.get(t, ()) and c not in ("lat", "lon")]
    metric = mc[0] if mc else dmetric
    if metric and metric not in cs: metric = None
    # filters
    where, params, desc = [], [], []
    def val_filter(tab, col, sub=False):
        try: vals = Q(f"SELECT DISTINCT {col} v FROM {tab} WHERE {col} IS NOT NULL LIMIT 600").v.tolist()
        except Exception: return
        found = []
        for v in vals:
            if isinstance(v, (int, float)): continue
            for a in _alias(v):
                if _w(ql, a): found.append((len(a), str(v), a)); break
        found.sort(reverse=True); used, taken = [], ql
        for _, v, a in found:
            if a in taken and not any(a in u or u in a for u in used):
                used.append(a)
                if sub: where.append(f"outlet_id IN (SELECT outlet_id FROM {tab} WHERE {col}=?)")
                else:
                    where.append(f"{col}=?")
                params.append(v); desc.append(f"{col} = {v}")
    for c in cs:
        if c in ("status", "category", "channel", "role", "tier", "severity", "type", "location", "origin_port", "dest_port", "carrier", "region", "country", "risk_level", "industry", "priority_tier", "source", "sku_name", "name", "port_name", "customer_id", "forecast", "route_name", "origin", "dest", "cargo"):
            if c in ("origin_port", "dest_port", "origin", "dest"): continue
            val_filter(t, c)
    if t in ("shipments", "quote_requests"):
        oc, dc = ("origin_port", "dest_port") if t == "shipments" else ("origin", "dest")
        try: pv = Q("SELECT DISTINCT port_name v FROM ports").v.tolist()
        except Exception: pv = []
        for pn in pv:
            for a_ in sorted(_alias(pn), key=len, reverse=True):
                mm = re.search(r"(?<![a-z0-9])" + re.escape(a_) + r"(?![a-z0-9])", ql)
                if not mm: continue
                pre = ql[max(0, mm.start() - 22):mm.start()].strip()
                frm = re.search(r"(from|origin|out of|leaving|departing|ex)$", pre); to = re.search(r"(to|towards|into|destination|dest|bound for|arriving at|arriving in|reaching)$", pre)
                if t == "quote_requests": pn_ = a_.split(" (")[0]; pat = pn_
                else: pat = pn
                if frm: where.append(f"{oc}=?"); params.append(pat); desc.append(f"{oc} = {pn}")
                elif to: where.append(f"{dc}=?"); params.append(pat); desc.append(f"{dc} = {pn}")
                else: where.append(f"({oc}=? OR {dc}=?)"); params += [pat, pat]; desc.append(f"{pn} is origin or destination")
                break
    if "outlet_id" in cs and t != "outlets":
        try: val_filter("outlets", "location", sub=True); val_filter("outlets", "tier", sub=True)
        except Exception: pass
    m = re.search(r"\b(outlet|store|branch)\s*(?:no\.?|number|#)?\s*(\d{1,3})\b", ql)
    if m and "outlet_id" in cs: where.append("outlet_id=?"); params.append(f"OUT-{int(m.group(2)):03d}"); desc.append(f"outlet_id = OUT-{int(m.group(2)):03d}")
    for pat, op in ((r"(?:below|under|less than|lower than|smaller than|<)", "<"), (r"(?:above|over|more than|greater than|higher than|exceed\w*|>)", ">"), (r"(?:at least|minimum of|>=)", ">="), (r"(?:at most|no more than|<=)", "<=")):
        mm = re.search(pat + r"\s*(?:rs\.?|₹|\$|inr|usd)?\s*([\d,]*\.?\d+)\s*(%|k|m|lakhs?|cr(?:ores?)?)?", ql)
        if mm and metric:
            v = _num(mm.group(1), mm.group(2) if mm.group(2) != "%" else "");
            if metric in PROB and v > 1: v /= 100
            where.append(f"{metric}{op}?"); params.append(v); desc.append(f"{metric} {op} {v:g}"); break
    if re.search(r"\b(open|pending|unresolved)\b", ql) and "status" in cs and not any("status" in x for x in desc) and t in ("agent_actions", "purchase_orders"):
        where.append("status IN ('open','proposed')" if t == "agent_actions" else "status NOT IN ('delivered','received','closed')"); desc.append("status = open")
    if re.search(r"\b(critical|high severity|urgent)\b", ql) and "severity" in cs and not any("severity" in x for x in desc): where.append("severity IN ('critical','high')"); desc.append("severity = critical/high")
    if re.search(r"\b(delayed|late)\b", ql) and t == "shipments" and not any("status" in x for x in desc): where.append("(status LIKE '%delay%' OR predicted_delay_risk>=0.5)"); desc.append("delayed or delay risk ≥ 0.5")
    if re.search(r"\b(low stock|running low|below reorder|need reorder|reorder)\b", ql) and t == "inventory": where.append("current_stock<=reorder_threshold"); desc.append("stock ≤ reorder threshold")
    if re.search(r"\b(high risk|at risk)\b", ql) and metric in PROB and not any(metric in x for x in desc): where.append(f"{metric}>=0.5"); desc.append(f"{metric} ≥ 0.5")
    if scope and t != "agent_actions":
        if "outlet_id" in cs: where.append("outlet_id=?"); params.append(scope); desc.append(f"outlet_id = {scope}")
        else: return {"answer": "That data is not available for your outlet role.", "sql": "", "df": None}
    elif scope: return {"answer": "Ticket lists are limited to your outlet; open the Actions page.", "sql": "", "df": None}
    # an unfiltered, unaggregated, unranked question is too vague to answer exactly
    if agg == "list" and not where and not re.search(r"\b(show|list|which|what|who|give)\b", ql): return None
    W = (" WHERE " + " AND ".join(where)) if where else ""
    nm = re.search(r"\b(?:top|bottom|first|best|worst|lowest|highest)\s+(\d{1,2})\b", ql); n = int(nm.group(1)) if nm else (5 if agg == "rank" else 10)
    tdesc = PL.get(t, syn[0] + "s"); fdesc = (" where " + ", ".join(desc)) if desc else ""
    grp = re.search(r"\b(?:by|per|for each|across|grouped by|each)\s+(location|city|tier|role|category|channel|carrier|region|country|status|type|severity|industry|outlet|port|origin|destination|sku|customer)\b", ql)
    gcol = {"city": "location", "outlet": "outlet_id", "port": "port_name" if "port_name" in cs else "origin_port", "origin": "origin_port", "destination": "dest_port", "sku": "sku_name", "customer": "customer_id"}.get(grp.group(1), grp.group(1)) if grp else None
    if gcol and gcol not in cs and "outlet_id" in cs and gcol in ("location", "tier"):
        j = f" JOIN outlets o ON o.outlet_id={t}.outlet_id"; gq = f"o.{gcol}"
    elif gcol in cs: j, gq = "", gcol
    else: j, gq = "", None
    if mask and t == "staff" and (metric in ("salary", "age") or re.search(r"\b(salary|salaries|pay|wage|age)\b", ql)): return {"answer": "Salary and personal details are visible to the Admin, Franchise Owner and Store Manager roles only.", "sql": "", "df": None}     # RBAC: checked before every aggregation, not only for lists
    if gq:
        fn = {"count": "COUNT(*)", "avg": f"AVG({metric})", "sum": f"SUM({metric})"}.get(agg, f"AVG({metric})" if metric else "COUNT(*)")
        if agg == "rank" and re.search(r"\b(lowest|least|smallest|minimum|min|bottom|worst|fewest|weakest|poorest|cheapest)\b", ql) and not re.search(r"\b(worst|riskiest)\b", ql) or (re.search(r"\b(worst)\b", ql) and metric not in BAD): order_dir = "ASC"
        else: order_dir = "DESC"
        if re.search(r"\bhow many|number of|count\b", ql): fn = "COUNT(*)"
        sql = f"SELECT {gq} AS grp, {fn} AS value, COUNT(*) AS rows_n FROM {t}{j}{W} GROUP BY {gq} ORDER BY value {order_dir} LIMIT 25"
        df = Q(sql, tuple(params))
        if not len(df): return {"answer": f"No {tdesc}{fdesc} found.", "sql": sql, "df": None}
        lab = {"COUNT(*)": "count"}.get(fn, fn.lower().replace("(", " of ").replace(")", ""))
        top = df.iloc[0]; df = df.rename(columns={"grp": gcol, "value": lab});
        return {"answer": f"{lab.capitalize()} of {tdesc} by {gcol}{fdesc}. Highest: **{top.iloc[0]}** ({_fmt(top.iloc[1])}); lowest: **{df.iloc[-1, 0]}** ({_fmt(df.iloc[-1, 1])}).", "sql": sql, "df": df}
    if agg == "count":
        sql = f"SELECT COUNT(*) AS n FROM {t}{W}"; n_ = int(Q(sql, tuple(params)).n[0])
        return {"answer": f"**{n_:,}** {tdesc}{fdesc}.", "sql": sql, "df": None}
    if agg in ("avg", "sum") and metric:
        fn = "AVG" if agg == "avg" else "SUM"; sql = f"SELECT {fn}({metric}) AS v, COUNT(*) AS n, MIN({metric}) AS lo, MAX({metric}) AS hi FROM {t}{W}"; r = Q(sql, tuple(params)).iloc[0]
        if not r.n: return {"answer": f"No {tdesc}{fdesc} found.", "sql": sql, "df": None}
        pv = f"{r.v:.1%}" if metric in PROB and abs(r.v) <= 1 else _fmt(float(r.v))
        return {"answer": f"{'Average' if agg == 'avg' else 'Total'} {metric.replace('_', ' ')} of {tdesc}{fdesc}: **{pv}** across {int(r.n):,} rows (min {_fmt(float(r.lo))}, max {_fmt(float(r.hi))}).", "sql": sql, "df": None}
    if mask and t == "staff" and (metric in ("salary", "age") or re.search(r"\b(salary|salaries|pay|wage|age)\b", ql)): return {"answer": "Salary and personal details are visible to Admin, Owner and Operations roles only.", "sql": "", "df": None}
    sel = list(dict.fromkeys([c for c in show if c in cs] + ([metric] if metric else [])))
    if mask: sel = [c for c in sel if not (t == "staff" and c in ("name", "salary", "age"))]
    if t == "inventory" and "outlet_id" in cs and "sku_name" not in sel: sel.append("sku_name")
    if agg == "rank" and metric:
        low = re.search(r"\b(lowest|least|smallest|minimum|min|bottom|fewest|weakest|poorest|cheapest)\b", ql) is not None; worst = re.search(r"\b(worst|riskiest)\b", ql) is not None
        asc = (low and not worst) or (worst and metric not in BAD) or (re.search(r"\b(best)\b", ql) is not None and metric in BAD)
        sql = f"SELECT {', '.join(sel)} FROM {t}{W} ORDER BY {metric} {'ASC' if asc else 'DESC'} LIMIT {n}"; df = Q(sql, tuple(params))
        if not len(df): return {"answer": f"No {tdesc}{fdesc} found.", "sql": sql, "df": None}
        r0 = df.iloc[0]; lab = r0[LABEL[t]] if t in LABEL and LABEL[t] in df.columns else r0[idc] if idc in df.columns else r0.iloc[0]; pv = f"{r0[metric]:.1%}" if metric in PROB and abs(r0[metric]) <= 1 else _fmt(r0[metric])
        return {"answer": f"{'Lowest' if asc else 'Highest'} {metric.replace('_', ' ')} among {tdesc}{fdesc}: **{lab}** at **{pv}**. Top {len(df)} below.", "sql": sql, "df": pct(df, sel)}
    sql = f"SELECT {', '.join(sel)} FROM {t}{W}" + (f" ORDER BY {metric} {'ASC' if metric in BAD and False else 'DESC'}" if metric else "") + f" LIMIT {max(n, 10) if not nm else n}"
    tot = int(Q(f"SELECT COUNT(*) n FROM {t}{W}", tuple(params)).n[0]); df = Q(sql, tuple(params))
    if not len(df): return {"answer": f"No {tdesc}{fdesc} found.", "sql": sql, "df": None}
    return {"answer": f"**{tot:,}** {tdesc}{fdesc}; showing {len(df)}" + (f", sorted by {metric.replace('_', ' ')}" if metric else "") + ".", "sql": sql, "df": pct(df, sel)}
