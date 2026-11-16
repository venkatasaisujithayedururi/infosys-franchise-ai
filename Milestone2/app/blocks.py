"""Server-driven UI blocks. Pages are Python functions returning JSON blocks; the single-page front end renders them and live-updates only what changed.
Charts are ECharts option dicts built here with one consistent palette."""
import math, json, datetime
import numpy as np, pandas as pd
import live_engine as LE

TEAL, BLUE, AMBER, RED, VIOLET, GREEN, PINK, GREY = "#0d9488", "#2563eb", "#f59e0b", "#e5484d", "#7c3aed", "#16a34a", "#db2777", "#64748b"
PRI = "#0f766e"
PAL = [PRI, BLUE, AMBER, VIOLET, RED, GREEN, PINK, TEAL, GREY]
TONE = {"Critical": RED, "High": RED, "Warning": AMBER, "Medium": AMBER, "Info": BLUE, "Low": TEAL, "Pass": TEAL, "Fail": RED}

def Q(sql, p=()):
    with LE._DB_LOCK:
        return pd.read_sql(sql, LE.conn(), params=p)

def clean(v):
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating, float)): return None if (v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) or (isinstance(v, np.floating) and (np.isnan(v) or np.isinf(v)))) else round(float(v), 4)
    if isinstance(v, (np.bool_,)): return bool(v)
    if isinstance(v, (pd.Timestamp, datetime.datetime, datetime.date)): return str(v)
    if isinstance(v, (list, tuple)): return [clean(x) for x in v]
    if isinstance(v, dict): return {str(k): clean(x) for k, x in v.items()}
    if v is pd.NA or v is pd.NaT: return None
    return v
def L(x): return [clean(v) for v in (x.tolist() if hasattr(x, "tolist") else list(x))]

# ------------------------------------------------------------------ charts (ECharts options)
def _base(extra=None, legend=False, grid=None):
    o = {"animation": True, "animationDuration": 350, "color": PAL, "tooltip": {"trigger": "axis", "confine": True}, "grid": grid or {"left": 8, "right": 14, "top": 28 if legend else 14, "bottom": 6, "containLabel": True}}
    if legend: o["legend"] = {"top": 0, "type": "scroll"}
    if extra: o.update(extra)
    return o
def bar(cats, series, horizontal=False, stack=False, colors=None, fmt=None, max_=None, pct=False, itemcolors=None, sort=False):
    """series: {name: values} or a list of values."""
    series = {"": series} if not isinstance(series, dict) else series; cats = L(cats)
    if sort and len(series) == 1:
        v = L(list(series.values())[0]); order = sorted(range(len(v)), key=lambda i: (v[i] is None, v[i] or 0)); cats = [cats[i] for i in order]; series = {k: [L(x)[i] for i in order] for k, x in series.items()}
    ser = []
    for i, (n, v) in enumerate(series.items()):
        d = L(v); s = {"type": "bar", "name": n, "data": d, "barMaxWidth": 22, "itemStyle": {"borderRadius": [0, 4, 4, 0] if horizontal else [4, 4, 0, 0], "color": (colors or PAL)[i % len(colors or PAL)]}, "emphasis": {"focus": "series"}}
        if itemcolors and i == 0: s["data"] = [{"value": x, "itemStyle": {"color": c}} for x, c in zip(d, itemcolors)]
        if stack: s["stack"] = "s"
        ser.append(s)
    cat = {"type": "category", "data": cats, "axisLabel": {"hideOverlap": True}}; val = {"type": "value", "splitLine": {"lineStyle": {"color": "#eceef6"}}}
    if max_: val["max"] = max_
    if pct: val["axisLabel"] = {"formatter": "{value}%"}
    o = _base(legend=len(series) > 1 and any(series)); o.update({"xAxis": val if horizontal else cat, "yAxis": cat if horizontal else val, "series": ser})
    return o
def line(x, series, area=True, band=None, colors=None, dashed=(), ymin=None, ymax=None, step=False, markers=False):
    series = {"": series} if not isinstance(series, dict) else series; ser = []
    for i, (n, v) in enumerate(series.items()):
        c = (colors or PAL)[i % len(colors or PAL)]; s = {"type": "line", "name": n, "data": L(v), "smooth": not step, "showSymbol": markers, "symbolSize": 5, "lineStyle": {"width": 2, "color": c, "type": "dashed" if n in dashed else "solid"}, "itemStyle": {"color": c}}
        if step: s["step"] = "end"
        if area and i == 0 and len(series) <= 2: s["areaStyle"] = {"color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1, "colorStops": [{"offset": 0, "color": c + "55"}, {"offset": 1, "color": c + "00"}]}}
        ser.append(s)
    if band:
        lo, hi = L(band[0]), L(band[1]); ser += [{"type": "line", "data": lo, "stack": "b", "lineStyle": {"opacity": 0}, "showSymbol": False, "silent": True, "tooltip": {"show": False}}, {"type": "line", "data": [None if (a is None or b is None) else b - a for a, b in zip(lo, hi)], "stack": "b", "lineStyle": {"opacity": 0}, "areaStyle": {"color": "rgba(251,191,36,.16)"}, "showSymbol": False, "silent": True, "tooltip": {"show": False}}]
    y = {"type": "value", "scale": True, "splitLine": {"lineStyle": {"color": "#eceef6"}}}
    if ymin is not None: y["min"] = ymin
    if ymax is not None: y["max"] = ymax
    o = _base(legend=len([s for s in series if s]) > 1); o.update({"xAxis": {"type": "category", "data": L(x), "boundaryGap": False, "axisLabel": {"hideOverlap": True}}, "yAxis": y, "series": ser}); return o
def pie(items, donut=True, colors=None):
    """items: {name: value} or list of (name, value, color?)"""
    its = list(items.items()) if isinstance(items, dict) else items; data = []
    for i, it in enumerate(its):
        d = {"name": str(it[0]), "value": clean(it[1])}
        if (colors and str(it[0]) in colors) or len(it) > 2: d["itemStyle"] = {"color": (colors or {}).get(str(it[0])) or it[2]}
        data.append(d)
    return {"animation": True, "color": PAL, "tooltip": {"trigger": "item", "confine": True}, "legend": {"bottom": 0, "type": "scroll"}, "series": [{"type": "pie", "radius": ["52%", "78%"] if donut else "75%", "center": ["50%", "44%"], "avoidLabelOverlap": True, "label": {"show": False}, "itemStyle": {"borderColor": "#ffffff", "borderWidth": 2, "borderRadius": 4}, "data": data}]}
def scatter(groups, xname="", yname="", colors=None, sized=False):
    """groups: {name: [ {x,y,label,size?} ]}. Points are [x, y, label, size]; the client resolves the {"__fn": ...} formatters."""
    ser = []
    for i, (n, pts) in enumerate(groups.items()):
        ser.append({"type": "scatter", "name": n, "symbolSize": {"__fn": "size3"} if sized else 10, "data": [[clean(p["x"]), clean(p["y"]), p.get("label", ""), clean(p.get("size", 10))] for p in pts],
                    "itemStyle": {"color": (colors or {}).get(n, PAL[i % len(PAL)]), "opacity": .85}, "emphasis": {"focus": "series"}})
    o = _base(legend=len(groups) > 1); o["tooltip"] = {"trigger": "item", "confine": True, "formatter": {"__fn": "scatterTip"}}
    ax = lambda n: {"type": "value", "name": n, "scale": True, "nameTextStyle": {"color": "#6b7080"}, "splitLine": {"lineStyle": {"color": "#eceef6"}}}
    o.update({"xAxis": ax(xname), "yAxis": ax(yname), "series": ser}); return o
def hist(values, bins=24, color=TEAL, pct=False):
    v = np.asarray([x for x in values if x is not None and not (isinstance(x, float) and math.isnan(x))], dtype=float)
    if not len(v): return bar([], [])
    h, e = np.histogram(v, bins=bins); labels = [f"{(e[i] * (100 if pct else 1)):.{0 if pct else 1}f}" + ("%" if pct else "") for i in range(len(h))]
    return bar(labels, [int(x) for x in h], colors=[color])
def waterfall(labels, deltas, total_label="Total"):
    base, run, up = [], 0.0, []
    for d in deltas: base.append(run if d >= 0 else run + d); up.append(abs(d)); run += d
    cats = list(labels) + [total_label]; base.append(0); up.append(run)
    o = _base(); o.update({"xAxis": {"type": "category", "data": cats}, "yAxis": {"type": "value", "splitLine": {"lineStyle": {"color": "#eceef6"}}},
                           "series": [{"type": "bar", "stack": "w", "data": [clean(x) for x in base], "itemStyle": {"color": "transparent"}, "tooltip": {"show": False}}, {"type": "bar", "stack": "w", "data": [{"value": clean(u), "itemStyle": {"color": TEAL if i == len(up) - 1 else (BLUE if deltas[i] >= 0 else RED)}} for i, u in enumerate(up)], "barMaxWidth": 34, "itemStyle": {"borderRadius": 4}}]}); return o
def radar(names, series, mx=100):
    o = {"animation": True, "color": PAL, "tooltip": {"confine": True}, "legend": {"bottom": 0}, "radar": {"indicator": [{"name": n, "max": mx} for n in names], "splitArea": {"show": False}, "axisName": {"color": "#6b7080"}}, "series": [{"type": "radar", "data": [{"name": k, "value": L(v), "areaStyle": {"opacity": .18}} for k, v in series.items()]}]}; return o
def gauge(value, name="", mx=100):
    c = RED if value < 60 else AMBER if value < 80 else TEAL
    return {"series": [{"type": "gauge", "startAngle": 210, "endAngle": -30, "min": 0, "max": mx, "progress": {"show": True, "width": 14, "itemStyle": {"color": c}}, "axisLine": {"lineStyle": {"width": 14, "color": [[1, "rgba(148,163,184,.15)"]]}}, "axisTick": {"show": False}, "splitLine": {"show": False}, "axisLabel": {"show": False}, "pointer": {"show": False}, "anchor": {"show": False},
                         "detail": {"valueAnimation": True, "fontSize": 30, "fontWeight": 700, "offsetCenter": [0, "8%"], "color": "#1c2024", "formatter": "{value}"}, "title": {"offsetCenter": [0, "62%"], "color": "#6b7080", "fontSize": 12}, "data": [{"value": clean(round(value, 1)), "name": name}]}]}
def graph(nodes, links, h=520):
    """nodes: [{id,name,kind,size,color,tip}] ; links: [(a,b)]"""
    cat = sorted({n.get("kind", "x") for n in nodes}); return {"animation": True, "tooltip": {"confine": True, "formatter": {"__fn": "nodeTip"}}, "legend": {"data": cat, "bottom": 0, "textStyle": {"color": "#6b7080"}}, "color": PAL,
        "series": [{"type": "graph", "layout": "force", "roam": True, "draggable": True, "force": {"repulsion": 260, "edgeLength": [40, 120], "gravity": .08}, "label": {"show": True, "position": "right", "color": "#454a58", "fontSize": 10, "formatter": {"__fn": "nodeLabel"}},
                    "categories": [{"name": c} for c in cat], "lineStyle": {"color": "#cfd3e3", "width": 1}, "emphasis": {"focus": "adjacency", "lineStyle": {"width": 2}},
                    "data": [{"id": n["id"], "name": n["id"], "category": cat.index(n.get("kind", "x")), "symbolSize": n.get("size", 12), "itemStyle": {"color": n.get("color")} if n.get("color") else {}, "tip": n.get("tip", ""), "showLabel": n.get("label", False), "open": n.get("open")} for n in nodes],
                    "links": [{"source": a, "target": b} for a, b in links]}]}

# ------------------------------------------------------------------ blocks
def kpis(*items):
    out = []
    for it in items:
        d = {"label": it[0], "value": clean(it[1])}
        if len(it) > 2 and it[2] is not None: d["sub"] = str(it[2])
        if len(it) > 3 and it[3]: d["tone"] = it[3]
        out.append(d)
    return {"t": "kpis", "items": out}
def chart(opt, title=None, h=290, open=None, sub=None, key=None): return {"t": "chart", "opt": opt, "title": title, "h": h, "open": open, "sub": sub, "key": key or title}
def table(df, cols=None, title=None, h=None, open=None, key=None, sub=None, search=False, page=None):
    """cols: list of names or dicts {k,label,type: text|num|int|pct|pill|bar|money|time|id, max}. open = {"kind":"outlet","col":"outlet_id"} makes rows clickable."""
    if isinstance(df, list): df = pd.DataFrame(df)
    cols = cols or list(df.columns); cs = [{"k": c, "label": c.replace("_", " ")} if isinstance(c, str) else c for c in cols]
    rows = [{c["k"]: clean(r.get(c["k"])) for c in cs} for r in df.to_dict("records")] if len(df) else []
    return {"t": "table", "cols": cs, "rows": rows, "title": title, "h": h, "open": open, "key": key or title, "sub": sub, "search": search}
def callout(text, tone="info", title=None): return {"t": "callout", "text": text, "tone": tone, "title": title}
def md(text): return {"t": "md", "text": text}
def row(*cols, ratio=None): return {"t": "row", "cols": list(cols), "ratio": ratio}
def col(*blocks): return {"t": "col", "blocks": list(blocks)}
def card(title, *blocks, sub=None): return {"t": "card", "title": title, "sub": sub, "blocks": list(blocks)}
def form(id, fields, submit="Submit", url=None, title=None, tone="primary", result=True, sub=None):
    """fields: {name,label,type: select|number|text|textarea|range|checks|multi|file|date, options, value, min,max,step}"""
    return {"t": "form", "id": id, "fields": fields, "submit": submit, "url": url, "title": title, "tone": tone, "sub": sub}
def button(id, label, url, tone="primary", confirm=None, payload=None): return {"t": "button", "id": id, "label": label, "url": url, "tone": tone, "confirm": confirm, "payload": payload or {}}
def map_(layers, h=470, view=None, open=None, key="map", legend=None, live=None): return {"t": "map", "layers": layers, "h": h, "view": view, "open": open, "key": key, "legend": legend, "live": live}
def tickets(items, key="tickets", title=None, sub=None): return {"t": "tickets", "items": items, "key": key, "title": title, "sub": sub}
def hero(agent, title, blurb, r, can_run=True):
    return {"t": "hero", "agent": agent, "title": title, "blurb": blurb, "can_run": can_run, "score": None if not r else clean(r["score"]), "risk": None if not r else r["risk"], "summary": None if not r else r["summary"], "ts": None if not r else r["ts"], "ms": None if not r else r["ms"]}
def tabs(items): return {"t": "tabs", "tabs": items}
def page(title, sub, blocks, tabs=None, live=8, actions=None): return {"title": title, "sub": sub, "blocks": blocks, "tabs": tabs, "live": live, "actions": actions or []}
def pill_col(k, label=None): return {"k": k, "label": label or k.replace("_", " "), "type": "pill"}
def num_col(k, label=None, fmt="num", mx=None): return {"k": k, "label": label or k.replace("_", " "), "type": fmt, "max": mx}
