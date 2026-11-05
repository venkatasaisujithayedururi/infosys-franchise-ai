import re as _re_live
import pandas as pd
import re, math
from db import get_conn

def df_to_markdown_safe(df):
    """Safely converts a pandas DataFrame to Markdown format."""
    if df is None or df.empty:
        return ""
    try:
        return df.to_markdown(index=False)
    except Exception:
        headers = list(df.columns)
        lines = ["| " + " | ".join([str(h) for h in headers]) + " |"]
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for _, row in df.iterrows():
            vals = [str(v) if v is not None else "" for v in row.values]
            lines.append("| " + " | ".join(vals) + " |")
        return "\n".join(lines)

# Use meaningful phrases/whole words. Avoid tiny substrings such as
# "ad", "item", and "location" accidentally hijacking unrelated questions.
INTENT_MAP = {
    "staff": ["staff", "employee", "employees", "attrition", "salary", "workforce", "headcount", "hiring", "hire"],
    "outlet": ["outlet", "store", "branch", "revenue", "margin", "sales", "profit", "csat", "customer satisfaction"],
    "inventory": ["inventory", "stock", "stockout", "sku", "reorder", "demand", "supply", "safety stock"],
    "marketing": ["marketing", "campaign", "roi", "conversion", "promotion", "budget", "channel", "advertising", "advertisement", "ads"],
    "audit": ["audit", "compliance", "violation", "inspection", "policy", "standard", "fssai", "food safety"],
    "feedback": ["feedback", "review", "sentiment", "rating", "complaint", "customer review"],
}

def _contains_term(q, term):
    return bool(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", q))

def classify_intent(query):
    """Score meaningful whole-word/phrase matches and return one primary domain."""
    q = query.lower().strip()
    scores = {}
    for intent, keywords in INTENT_MAP.items():
        score = 0
        for kw in keywords:
            if _contains_term(q, kw):
                score += 2 if " " in kw else 1
        scores[intent] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"

def handle_franchise_intent(query):
    """Return only data for the most relevant franchise domain."""
    q_low = query.lower()
    intent = classify_intent(query)

    try:
        with get_conn() as conn:
            if intent == "outlet":
                total = conn.execute("SELECT COUNT(*) FROM outlets;").fetchone()[0]
                revenue = conn.execute("SELECT SUM(revenue) FROM outlets;").fetchone()[0] or 0
                csat = conn.execute("SELECT AVG(customer_satisfaction) FROM outlets;").fetchone()[0] or 0

                if any(_contains_term(q_low, k) for k in ["margin", "profit"]):
                    sql = """SELECT outlet_id, outlet_name, location, tier,
                             ROUND(revenue, 0) AS revenue_rs,
                             ROUND(operating_costs, 0) AS costs_rs,
                             ROUND(((revenue - operating_costs)/NULLIF(revenue,0))*100, 2) AS net_margin_pct,
                             customer_satisfaction
                             FROM outlets ORDER BY net_margin_pct DESC LIMIT 10;"""
                else:
                    sql = """SELECT outlet_id, outlet_name, location, tier,
                             ROUND(revenue, 0) AS revenue_rs,
                             ROUND(((revenue - operating_costs)/NULLIF(revenue,0))*100, 2) AS net_margin_pct,
                             customer_satisfaction
                             FROM outlets ORDER BY revenue_rs DESC LIMIT 10;"""
                df = pd.read_sql(sql, conn)
                return f"### Franchise Outlet Data\nActive outlets: **{total}** | Total revenue: **Rs. {revenue:,.0f}** | Average CSAT: **{csat:.2f}/5**\n\n{df_to_markdown_safe(df)}", "Outlets DB"

            if intent == "staff":
                total = conn.execute("SELECT COUNT(*) FROM staff;").fetchone()[0]
                high_risk = conn.execute("SELECT COUNT(*) FROM staff WHERE predicted_attrition_prob > 0.6;").fetchone()[0]
                df = pd.read_sql("""SELECT outlet_id, role, COUNT(*) AS staff_count,
                                    ROUND(AVG(salary), 0) AS avg_salary_rs,
                                    ROUND(AVG(predicted_attrition_prob), 2) AS avg_attrition_risk
                                    FROM staff GROUP BY outlet_id, role
                                    ORDER BY avg_attrition_risk DESC LIMIT 10;""", conn)
                return f"### Workforce Data\nTotal staff: **{total}** | High attrition risk (>60%): **{high_risk}**\n\n{df_to_markdown_safe(df)}", "Staff DB"

            if intent == "inventory":
                total_skus = conn.execute("SELECT COUNT(*) FROM inventory;").fetchone()[0]
                risk_items = conn.execute("SELECT COUNT(*) FROM inventory WHERE stockout_risk_prob > 0.7;").fetchone()[0]
                df = pd.read_sql("""SELECT outlet_id, sku_name, category, current_stock,
                                    reorder_threshold, stockout_risk_prob
                                    FROM inventory ORDER BY stockout_risk_prob DESC LIMIT 12;""", conn)
                return f"### Inventory Data\nTracked SKUs: **{total_skus}** | SKUs above 70% stockout risk: **{risk_items}**\n\n{df_to_markdown_safe(df)}", "Inventory DB"

            if intent == "marketing":
                avg_roi = conn.execute("SELECT AVG(actual_roi) FROM marketing;").fetchone()[0] or 0
                df = pd.read_sql("""SELECT channel, COUNT(*) AS campaigns,
                                    ROUND(AVG(actual_roi), 2) AS avg_roi,
                                    SUM(conversions) AS conversions
                                    FROM marketing GROUP BY channel ORDER BY avg_roi DESC;""", conn)
                return f"### Marketing Data\nAverage campaign ROI: **{avg_roi:.2f}x**\n\n{df_to_markdown_safe(df)}", "Marketing DB"

            if intent == "feedback":
                avg_rating = conn.execute("SELECT AVG(rating) FROM feedback;").fetchone()[0] or 0
                df = pd.read_sql("""SELECT outlet_id, rating, comment, sentiment_score, date
                                    FROM feedback ORDER BY sentiment_score ASC LIMIT 10;""", conn)
                return f"### Customer Feedback Data\nAverage rating: **{avg_rating:.2f}/5**\n\n{df_to_markdown_safe(df)}", "Feedback DB"

            if intent == "audit":
                avg_score = conn.execute("SELECT AVG(score) FROM audits;").fetchone()[0] or 0
                open_items = conn.execute("SELECT COUNT(*) FROM audits WHERE status != 'Pass';").fetchone()[0]
                df = pd.read_sql("""SELECT outlet_id, audit_date, score, violations, category, status
                                    FROM audits ORDER BY score ASC LIMIT 10;""", conn)
                return f"### Audit & Compliance Data\nAverage score: **{avg_score:.1f}/100** | Non-pass audits: **{open_items}**\n\n{df_to_markdown_safe(df)}", "Audits DB"

    except Exception:
        return None

    return None

def handle_port_intent(query):
    try:
        with get_conn() as conn:
            tot_ports = conn.execute("SELECT COUNT(*) FROM ports;").fetchone()[0]
            df_ports = pd.read_sql("""SELECT port_name AS 'Port Name', country AS 'Country',
                                      region AS 'Region',
                                      congestion_index AS 'Congestion (1-5)',
                                      avg_dwell_days AS 'Avg Dwell Days'
                                      FROM ports ORDER BY congestion_index ASC LIMIT 10;""", conn)
        return f"### Global Ports Data ({tot_ports} monitored)\n\n{df_to_markdown_safe(df_ports)}", f"Ports Ledger DB ({tot_ports} Hubs)"
    except Exception:
        return None, None


_AGENTIC_Q = _re_live.compile(r"(need[s]? attention|what should i do|action plan|prioriti[sz]e|overall (status|health)|run (the )?agents?|full analysis|full status|why is .{0,40}(low|down|failing|underperform|risky)|what is going wrong)")
def _agentic_query(query):
    """Open-ended 'what should I do / what needs attention' questions run the whole agent graph instead of a single table lookup."""
    if not _AGENTIC_Q.search(query.lower()): return None
    try:
        from live_engine import run_cycle
        import domain_franchise as _dom
        dec = run_cycle(_dom, "copilot", query)
        top = "\n".join(f"- **{a['severity']}** · {a['type']} · {a['target']}: {a['detail']}" for a in dec["actions"][:8])
        return f"### Agent orchestration result\n\n{dec['narrative']}\n\n**Top actions**\n{top}", "Agent Orchestrator (live)"
    except Exception:
        return None

def _run_centralized_orig(query):
    """Retrieve one relevant evidence set. Do not mix unrelated data sources."""
    q_low = query.lower()

    franchise = handle_franchise_intent(query)
    if franchise:
        return franchise

    if any(_contains_term(q_low, k) for k in ["port", "ports", "harbor", "terminal", "congestion"]):
        return handle_port_intent(query)

    if any(_contains_term(q_low, k) for k in ["shipment", "shipments", "carrier"]):
        try:
            with get_conn() as conn:
                tot_shipments = conn.execute("SELECT COUNT(*) FROM shipments;").fetchone()[0]
                df_ship = pd.read_sql("""SELECT shipment_id, origin_port, dest_port, carrier,
                                         status, predicted_delay_risk
                                         FROM shipments ORDER BY predicted_delay_risk DESC LIMIT 10;""", conn)
            return f"### Active Shipments ({tot_shipments})\n\n{df_to_markdown_safe(df_ship)}", "Shipments Ledger DB"
        except Exception:
            pass

    # Only invoke RAG for questions that clearly look like document/SOP/policy questions.
    rag_terms = ["sop", "document", "manual", "policy", "procedure", "fssai", "hygiene", "food safety", "guideline"]
    if any(_contains_term(q_low, k) for k in rag_terms):
        try:
            from rag_engine import answer_with_citation
            ctx, src = answer_with_citation(query)
            if ctx and str(ctx).strip():
                return ctx, src
        except Exception:
            pass

    return None, None

def run_grounded_query(query):
    return run_centralized_brain_query(query)

def text_to_sql(query):
    return run_centralized_brain_query(query)

def run_centralized_brain_query(query):
    _ag = _agentic_query(query)
    return _ag if _ag else _run_centralized_orig(query)
