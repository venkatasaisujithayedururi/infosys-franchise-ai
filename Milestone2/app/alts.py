"""Alternatives shown in the detail panels: other sea routes for a shipment, nearby lower-congestion ports for a port, nearby outlets that can transfer stock to an outlet."""
import json, numpy as np, pandas as pd
import blocks as B
from blocks import Q, TEAL, BLUE, AMBER, RED, VIOLET
COLORS = [TEAL, BLUE, AMBER, VIOLET, "#d6409f", "#8b8d98"]
def hav(la1, lo1, la2, lo2, R=6371.0):
    p = np.pi / 180; a = np.sin((np.asarray(la2) - la1) * p / 2) ** 2 + np.cos(la1 * p) * np.cos(np.asarray(la2) * p) * np.sin((np.asarray(lo2) - lo1) * p / 2) ** 2; return 2 * R * np.arcsin(np.sqrt(a))
def usd(x): return "${:,.0f}".format(x)
VARIANTS = [((), "Default"), (("suez",), "Avoid Suez"), (("panama",), "Avoid Panama"), (("malacca",), "Avoid Malacca"), (("hormuz",), "Avoid Hormuz"), (("storm",), "Avoid storms")]
def route_alternatives(dom, o_xy, d_xy, tonnes=20.0, interp=None, rate=0.012, day_cost=120.0, dwell=0.0):
    """-> list of options sorted by total cost; each {label, name, nm, days, freight, delay_cost, total, wind, chain, avoid, flags}"""
    seen, out = {}, []
    for av, lab in VARIANTS:
        try: opts = dom.route_options(o_xy, d_xy, avoid=av)
        except Exception: continue
        if not opts: continue
        o = opts[0]; key = o["name"]
        if key in seen: continue
        seen[key] = 1; ch = o["chain"]; wind = 0.0
        if interp:
            try: wind = max(dom.weather_at(*interp(ch, f), allow_live=False)["wind"] for f in (.15, .35, .55, .75, .95))
            except Exception: pass
        days = o["nm"] / (14 * 24) + dwell; fr = o["nm"] * tonnes * rate; dl = days * day_cost; risk_cost = max(0, wind - 15) * 0.02 * days * day_cost * 3
        out.append({"label": lab, "name": o["name"], "nm": o["nm"], "days": round(days, 1), "freight": fr, "delay_cost": dl + risk_cost, "total": fr + dl + risk_cost, "wind": round(wind, 1), "chain": ch, "avoid": list(av)})
    if not out: return out
    out.sort(key=lambda r: r["total"]); fast = min(out, key=lambda r: r["days"]); short = min(out, key=lambda r: r["nm"])
    for r in out: r["tag"] = ", ".join(t for t, c in (("Recommended", r is out[0]), ("Fastest", r is fast), ("Shortest", r is short)) if c)
    return out
def route_blocks(opts, sid=None, title="Route alternatives", cur=None):
    if not opts: return [B.callout("No alternative sea route found for this lane.", "info")]
    lines = [{"pts": r["chain"], "color": COLORS[i % len(COLORS)], "w": 4 if i == 0 else 2.5, "dash": None if i == 0 else "6 6"} for i, r in enumerate(opts)]
    rows = [{"option": f"{i + 1}. {r['label']}", "route": r["name"], "nm": r["nm"], "days": r["days"], "freight": r["freight"], "delay": r["delay_cost"], "total": r["total"], "wind": r["wind"], "tag": r["tag"]} for i, r in enumerate(opts)]
    best, worst = opts[0], opts[-1]; pts = [p for r in opts for p in r["chain"]]; la = [p[0] for p in pts]; lo = [p[1] for p in pts]
    view = {"bounds": [[min(la) - 4, min(lo) - 6], [max(la) + 4, max(lo) + 6]]}
    ends = [{"id": "o", "lat": opts[0]["chain"][0][0], "lon": opts[0]["chain"][0][1], "color": "#1f2430", "r": 6, "tip": "start"}, {"id": "d", "lat": opts[0]["chain"][-1][0], "lon": opts[0]["chain"][-1][1], "color": RED, "r": 6, "tip": "destination"}]
    bl = [B.card(title, B.map_([{"type": "lines", "lines": lines}, {"type": "points", "id": "alt_ends", "pts": ends}], h=300, view=view, key="alt_map", legend=[(str(rows[i]["option"]) + (" (solid = recommended)" if i == 0 else " (dashed)"), COLORS[i % len(COLORS)]) for i in range(min(len(rows), len(COLORS)))] + [("Start", "#1f2430"), ("Destination", RED)]), B.table(rows, ["option", "route", B.num_col("nm", "nm", "int"), B.num_col("days", "days", "num"), B.num_col("freight", "freight cost", "money"), B.num_col("delay", "time + weather cost", "money"), B.num_col("total", "total", "money"), B.num_col("wind", "max wind m/s", "num"), "tag"], h=min(60 + 40 * len(rows), 330), key="alt_t"),
                       sub=f"Best: {best['label']} ({best['name']}), {best['days']} days, {usd(best['total'])}. Worst: {usd(worst['total'])}. Cost = $0.012 per tonne-nm + $120 per day + weather penalty above 15 m/s.")]
    return bl
def port_alternatives(port, k=6):
    p = Q("SELECT port_name, country, region, lat, lon, congestion_index ci, avg_dwell_days dw FROM ports"); me = p[p.port_name == port]
    if not len(me): return []
    me = me.iloc[0]; p["km"] = hav(me.lat, me.lon, p.lat.values, p.lon.values); c = p[(p.port_name != port) & (p.km < 1800)].copy()
    c["better"] = (me.ci - c.ci); c["score"] = c.ci * 12 + c.dw * 4 + c.km / 100; c = c[c.ci < me.ci].sort_values("score").head(k)
    rows = [{"port": r.port_name, "country": r.country, "km": r.km, "ci": r.ci, "dwell": r.dw, "days_saved": max(0, me.dw - r.dw), "haul_days": r.km / 600 / 1 if r.country == me.country else r.km / 450} for r in c.itertuples()]
    if not rows: return [B.callout(f"No less-congested port within 1,800 km of {port}.", "info")]
    return [B.card("Alternative ports nearby", B.table(rows, ["port", "country", B.num_col("km", "km away", "int"), B.num_col("ci", "congestion", "num"), B.num_col("dwell", "dwell days", "num"), B.num_col("days_saved", "dwell saved", "num"), B.num_col("haul_days", "extra haul days (approx.)", "num")], h=min(70 + 40 * len(rows), 340), open={"kind": "port", "col": "port"}, key="alt_p"),
                    sub="Cargo for the port could be diverted here; haul by road/rail is estimated at 600 km/day domestic, 450 km/day cross-border. Check customs and carrier agreements before diverting.")]
def outlet_alternatives(oid, max_km=400):
    g = Q("SELECT outlet_id, lat, lon FROM outlet_geo"); me = g[g.outlet_id == oid]
    if not len(me): return []
    me = me.iloc[0]; g["km"] = hav(me.lat, me.lon, g.lat.values, g.lon.values); near = g[(g.outlet_id != oid) & (g.km <= max_km)].sort_values("km").head(12)
    need = Q("SELECT sku_name, current_stock st, reorder_threshold thr, weekly_demand wk, lead_time_days lead FROM inventory WHERE outlet_id=? AND current_stock<=reorder_threshold*1.5 ORDER BY current_stock*1.0/MAX(weekly_demand,1) LIMIT 6", (oid,))
    if not len(need): return [B.callout("This outlet has no SKUs at or near the reorder level (within 150%), so no transfers are suggested.", "info")]
    if not len(near): return [B.callout(f"No outlet within {max_km} km to transfer stock from.", "info")]
    inv = Q(f"SELECT outlet_id, sku_name, current_stock st, reorder_threshold thr, weekly_demand wk FROM inventory WHERE outlet_id IN ({','.join('?' * len(near))}) AND sku_name IN ({','.join('?' * len(need))})", tuple(near.outlet_id) + tuple(need.sku_name))
    inv["spare"] = inv.st - (inv.thr + inv.wk); inv = inv[inv.spare > 0].merge(near[["outlet_id", "km"]], on="outlet_id"); rows = []
    for r in need.itertuples():
        want = max(1, int(r.thr + r.wk - r.st)); c = inv[inv.sku_name == r.sku_name].sort_values("km")
        if len(c):
            s = c.iloc[0]; q = int(min(want, s.spare)); days = max(.5, s.km * 1.3 / 320); rows.append({"sku": r.sku_name, "short_by": want, "from": s.outlet_id, "km": s.km, "units": q, "days": days, "vs_supplier": r.lead - days, "cost": s.km * 1.3 * 14})
        else: rows.append({"sku": r.sku_name, "short_by": want, "from": "none nearby has spare", "km": None, "units": 0, "days": None, "vs_supplier": None, "cost": None})
    d = pd.DataFrame(rows); mp = [{"type": "lines", "lines": [{"pts": [[float(me.lat), float(me.lon)], [float(g[g.outlet_id == r["from"]].lat.iloc[0]), float(g[g.outlet_id == r["from"]].lon.iloc[0])]], "color": COLORS[i % 6], "w": 3} for i, r in enumerate(rows) if r["units"]]},
                                {"type": "points", "id": "alt_o", "pts": [{"id": oid, "lat": float(me.lat), "lon": float(me.lon), "color": "#1f2430", "r": 8, "tip": oid}] + [{"id": r["from"], "lat": float(g[g.outlet_id == r["from"]].lat.iloc[0]), "lon": float(g[g.outlet_id == r["from"]].lon.iloc[0]), "color": TEAL, "r": 6, "tip": r["from"]} for r in rows if r["units"]]}]
    return [B.card("Suggested stock transfers from nearby outlets", B.map_(mp, h=240, key="alt_om", legend=[("This outlet (needs stock)", "#1f2430"), ("Outlet that can send stock", TEAL), ("Transfer line (colour per supplier outlet)", BLUE)]) if any(r["units"] for r in rows) else B.md("No nearby outlet has spare stock for these SKUs."), B.table(d, ["sku", B.num_col("short_by", "short by", "int"), "from", B.num_col("km", "km (straight line)", "int"), B.num_col("units", "transfer units", "int"), B.num_col("days", "transfer days (approx.)", "num"), B.num_col("vs_supplier", "days faster than supplier", "num"), B.num_col("cost", "est. cost ₹", "money")], h=min(80 + 40 * len(d), 330), open={"kind": "outlet", "col": "from"}, key="alt_ot"),
                    sub="Spare = stock above reorder level plus one week of demand. Distance is straight-line; road distance ≈ 1.3×. Cost ₹14 per road km. Compare with the supplier lead time before moving stock.")]
