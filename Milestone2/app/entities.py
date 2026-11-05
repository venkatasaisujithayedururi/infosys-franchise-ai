"""One description of any entity (outlet, staff, quote, shipment, vessel, port): master data, relations, and everything flagged on it. Feeds the drawer, the knowledge graph and the Copilot."""
import json
from blocks import Q, clean

def _tickets(e, n=30):
    return Q("SELECT action_id id, type, severity, status, detail, owner, assignee, due FROM agent_actions WHERE target=? ORDER BY action_id DESC LIMIT ?", (e, n))
def latest_out(agent):
    r = Q("SELECT output FROM agent_runs WHERE agent=? ORDER BY run_id DESC LIMIT 1", (agent,))
    try: return json.loads(r.output[0]) if len(r) else {}
    except Exception: return {}
def kind_of(e):
    e = str(e)
    if e.startswith("OUT-"): return "outlet"
    if e.startswith("QTE"): return "quote"
    if e.startswith("SHP"): return "shipment"
    if e.startswith("EMP") or e.startswith("STF"): return "staff"
    return "port"

def describe(kind, dom, e):
    """-> {"kind","info":{label:value},"rel":[(name,kind,tip)], "tickets": DataFrame}"""
    k = kind_of(e); info, rel = {}, []
    if kind == "Franchise" and k == "outlet":
        o = Q("SELECT * FROM outlets WHERE outlet_id=?", (e,))
        if len(o):
            r = o.iloc[0]; info = {"Outlet": r.outlet_name, "Location": r.location, "Revenue": f"{r.revenue:,.0f}", "Customer satisfaction": round(float(r.customer_satisfaction), 2), "Headcount": int(r.staff_headcount)}
            for a in ("outlet", "inventory", "staff", "marketing", "audit", "feedback"):
                v = latest_out(a).get("per_outlet", {}).get(e)
                if v is not None: rel.append((f"{a} agent: {v:.0f}", "agent", f"{a} score for {e}"))
            for s in Q("SELECT staff_id, predicted_attrition_prob p FROM staff WHERE outlet_id=? ORDER BY p DESC LIMIT 4", (e,)).itertuples(): rel.append((s.staff_id, "staff", f"attrition {s.p:.0%}"))
            for s in Q("SELECT sku_name, stockout_risk_prob p FROM inventory WHERE outlet_id=? ORDER BY p DESC LIMIT 4", (e,)).itertuples(): rel.append((s.sku_name, "sku", f"stock-out risk {s.p:.0%}"))
            for s in Q("SELECT campaign_name, channel FROM marketing WHERE outlet_id=? AND end_date>=date('now')", (e,)).itertuples(): rel.append((s.campaign_name, "campaign", f"live via {s.channel}"))
    elif kind == "Freight" and k == "quote":
        q = Q("SELECT * FROM freight_quotes WHERE quote_id=?", (e,))
        if len(q):
            r = q.iloc[0]; info = {"Quote": e, "Price": f"${r.final_price:,.0f}", "Margin": f"{r.margin_pct}%", "Status": r.status}
            for n, tip in ((r.shipment_id, "shipment"), (r.customer_id, "customer"), (r.carrier, "carrier")): rel.append((n, tip, tip))
    elif kind == "Freight" and k == "shipment":
        s = Q("SELECT * FROM shipments WHERE shipment_id=?", (e,))
        if len(s):
            r = s.iloc[0]; info = {"Shipment": e, "Route": f"{r.origin_port} to {r.dest_port}", "Carrier": r.carrier, "Status": r.status, "Delay risk": r.predicted_delay_risk}
            for n, tip in ((r.origin_port, "port"), (r.dest_port, "port"), (r.carrier, "carrier")): rel.append((n, tip, tip))
            v = Q("SELECT lat, lon, route_name, progress FROM vessels WHERE shipment_id=?", (e,))
            if len(v): info["Vessel"] = f"{v.lat[0]:.1f}, {v.lon[0]:.1f} · {v.route_name[0]} · {v.progress[0]:.0%}"
    elif kind == "Freight":
        p = Q("SELECT * FROM ports WHERE port_name=?", (e,))
        if len(p):
            r = p.iloc[0]; info = {"Port": e, "Country": r.country, "Congestion index": round(float(r.congestion_index), 2), "Dwell days": r.avg_dwell_days}
            for s in Q("SELECT shipment_id FROM shipments WHERE origin_port=? OR dest_port=? LIMIT 6", (e, e)).itertuples(): rel.append((s.shipment_id, "shipment", "via port"))
    return {"kind": k, "info": {a: clean(b) for a, b in info.items()}, "rel": rel, "tickets": _tickets(e)}

def facts(kind, dom, text):
    import re
    out = []
    for e in dict.fromkeys(m.upper() for m in re.findall(r"\b(OUT-\d+|QTE-L\d+|SHP-[A-Z0-9-]+)\b", text, re.I)):
        d = describe(kind, dom, e); t = d["tickets"]; t = t[t.status.isin(["open", "proposed"])].head(8)
        if d["info"] or len(t): out.append(f"{e}: " + "; ".join(f"{k}={v}" for k, v in d["info"].items()) + (f". Related: {', '.join(n for n, _, _ in d['rel'][:8])}." if d["rel"] else "") + (" Open tickets: " + " | ".join(f"{r.type} ({r.severity}): {r.detail}" for r in t.itertuples()) if len(t) else " No open tickets."))
    return out
