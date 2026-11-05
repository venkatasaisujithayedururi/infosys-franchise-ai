"""Step 7: the Copilot answers only from SQL, understands spelling mistakes and other wordings, shows the SQL and the row count,
replies politely (with three valid questions) outside the data, and respects the user's role."""
import json, re
import pytest

OUT = re.compile(r"OUT-\d+")
MINE = "OUT-010"

@pytest.fixture(scope="module")
def I(server):
    import intents; return intents
@pytest.fixture(scope="module")
def Qr(server):
    import blocks; return blocks.Q

def test_at_least_15_new_question_patterns(I):
    assert len(I.INTENTS) >= 15 and len({i for i, *_ in I.INTENTS}) == len(I.INTENTS)

# ------------------------------------------------------------------ every pattern: its own intent, real SQL, a row count, no invented numbers
def pytest_generate_tests(metafunc):
    if "iid" in metafunc.fixturenames and "example" in metafunc.fixturenames:             # one test per question pattern
        import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))
        os.environ.setdefault("APP_KIND", "Franchise")
        import intents
        metafunc.parametrize("iid,example", [(i, e) for i, e, _, _ in intents.INTENTS], ids=[i for i, *_ in intents.INTENTS])

def test_every_intent_answers_its_example(I, iid, example):
    r = I.answer(example)
    assert r and r["intent"] == iid, (iid, r and r["intent"])
    assert r["answer"].strip() and r["sql"].lstrip().upper().startswith("SELECT") and "?" not in r["sql"]
    assert isinstance(r["rows"], int) and r["rows"] >= 0 and r["rows"] == (0 if r["df"] is None else len(r["df"]))

def test_answers_match_independent_queries(I, Qr):
    n = lambda sql, p=(): int(Qr(sql, p).iloc[0, 0])
    assert I.answer("How many outlets are there?")["df"].iloc[0, 0] == n("SELECT COUNT(*) FROM outlets")
    assert I.answer("How many inventory items need reordering?")["df"].iloc[0, 0] == n("SELECT COUNT(*) FROM inventory WHERE current_stock<=reorder_threshold")
    assert I.answer("How many staff does OUT-010 have?")["df"].iloc[0, 0] == n("SELECT COUNT(*) FROM staff WHERE outlet_id='OUT-010'")
    assert I.answer("How many staff are there in total")["df"].iloc[0, 0] == n("SELECT COUNT(*) FROM staff")
    low = Qr("SELECT outlet_id FROM outlets ORDER BY customer_satisfaction ASC LIMIT 1").outlet_id[0]; assert low in I.answer("Which outlet has the lowest customer satisfaction?")["answer"]
    top = Qr("SELECT outlet_id FROM outlets ORDER BY revenue DESC LIMIT 1").outlet_id[0]; assert top in I.answer("Which outlet has the highest revenue?")["answer"]
    best = Qr("SELECT campaign_id FROM marketing ORDER BY actual_roi DESC LIMIT 1").campaign_id[0]; assert best in I.answer("Which campaign has the best ROI?")["answer"]
    assert I.answer("Show failed audits")["df"] is None or all(I.answer("Show failed audits")["df"].score < 60)
    avg = round(float(Qr("SELECT AVG(rating) v FROM feedback").v[0]), 2); assert f"{avg:.2f}" in I.answer("What is the average customer rating?")["answer"]

def test_top_n_is_honoured(I):
    assert I.answer("top 3 outlets by revenue")["rows"] == 3 and I.answer("show the 7 outlets with the lowest satisfaction")["rows"] == 7

# ------------------------------------------------------------------ spelling mistakes and different wordings
@pytest.mark.parametrize("question,intent", [
    ("Which outlet has the lowest custmer satisfation?", "lowest_csat"), ("which stores have the worst csat", "lowest_csat"), ("Which outlet has the highest revanue?", "highest_revenue"), ("which shop earns the most revenue", "highest_revenue"), ("biggest turnover branch", "highest_revenue"),
    ("How many employes are in outlet OUT-001?", "staff_count"), ("how many workers does out-10 have", "staff_count"), ("staff count for OUT-020", "staff_count"),
    ("Which campain has the best ROI?", "best_campaign_roi"), ("best performing promotion by roi", "best_campaign_roi"), ("worst campaign roi", "worst_campaign_roi"),
    ("How many inventry items need reoder?", "reorder_count"), ("how many skus must be restocked", "reorder_count"), ("list items below reorder level", "below_reorder"), ("show low stock items", "below_reorder"),
    ("show negative feeback this week", "negative_reviews"), ("which outlet has the most complaints that are negative", "most_negative_reviews"),
    ("show failing audt results", "failed_audits"), ("which inspection failed", "failed_audits"), ("which shop has the most violatons", "highest_violations"),
    ("avg customer ratings", "average_rating"), ("which people are likely to quit", "high_attrition"), ("emplyees with high attrtion risk", "high_attrition"),
    ("who works the most overtime", "highest_overtime"), ("outstanding purchase orders", "pending_purchase_orders"), ("total sales this week", "sales_last_7_days"),
    ("how many stores do we have", "total_outlets"), ("show urgent alerts", "open_critical_tickets"), ("which outlet costs the most to run - operating cost", "highest_operating_cost"),
])
def test_spelling_and_alternate_wording(I, question, intent):
    r = I.answer(question)
    assert r and r["intent"] == intent, (question, r and r["intent"], I.normalize(question))

def test_normalize_corrects_misspellings(I):
    n = I.normalize("custmer satisfation revanue employes campain reoder inventry feeback audt")
    assert n == "customer satisfaction revenue staff campaign reorder inventory review audit"

# ------------------------------------------------------------------ through the real endpoint: SQL + row count shown, polite fallback with three suggestions
def ask(c, q):
    r = c.post("/api/copilot", json={"q": q}); assert r.status_code == 200, r.text
    return [json.loads(x[6:]) for x in r.text.split("\n\n") if x.startswith("data: ")]

def test_endpoint_shows_sql_and_row_count(login):
    ev = ask(login("Admin"), "Which employees have a high attrition risk?")
    exact = next(e for e in ev if e["ev"] == "exact"); final = next(e for e in ev if e["ev"] == "final")
    assert exact["sql"].startswith("SELECT") and isinstance(exact["rows"], int) and exact["rows"] > 0
    assert final["sql"] == exact["sql"] and "row" in final["text"] and "SELECT" not in final["text"]

def test_greeting_and_thanks(login):
    c = login("Admin")
    assert "Hello" in next(e for e in ask(c, "hello") if e["ev"] == "final")["text"] and "welcome" in next(e for e in ask(c, "thanks") if e["ev"] == "final")["text"].lower()

@pytest.mark.parametrize("q", ["What is the weather in Paris?", "write me a poem", "who won the world cup", "asdf qwer zxcv"])
def test_polite_reply_with_three_valid_questions_outside_the_data(login, I, q):
    t = next(e for e in ask(login("Admin"), q) if e["ev"] == "final")["text"]
    bullets = [l[2:] for l in t.splitlines() if l.startswith("- ")]
    assert t.startswith("Sorry") and "franchise database" in t and len(bullets) == 3
    for b in bullets: assert I.answer(b) is not None, b              # every suggestion really is answerable

def test_every_suggestion_for_a_scoped_role_is_answerable(login, I):
    for s in I.suggestions(MINE, "x") + I.suggestions(MINE, "y") + I.suggestions(None, "z"):
        assert I.answer(s, MINE) is not None, s

# ------------------------------------------------------------------ RBAC: only data this role may see
def test_scoped_answers_contain_only_the_own_outlet(I):
    for _id, example, _rx, _fn in I.INTENTS:
        r = I.answer(example, MINE)
        assert r is not None, example
        text = r["answer"] + (r["df"].to_string() if r["df"] is not None else "") + r["sql"]
        assert set(OUT.findall(text)) <= {MINE}, (example, sorted(set(OUT.findall(text)) - {MINE}))

def test_a_scoped_role_is_told_when_a_ranking_shows_only_its_outlet(I):
    r = I.answer("Which outlet has the lowest customer satisfaction?", MINE)
    assert r["answer"].startswith("Rankings compare outlets") and MINE in r["answer"] and r["rows"] == 1
    assert not I.answer("Which outlet has the lowest customer satisfaction?")["answer"].startswith("Rankings")      # the whole chain: a real ranking

def test_scoped_role_through_the_endpoint(login, I):
    for role in ("Store Manager", "Staff"):
        c = login(role, MINE)
        for _id, example, _rx, _fn in I.INTENTS:
            text = " ".join(e.get("text", "") for e in ask(c, example) if e["ev"] == "final")
            assert set(OUT.findall(text)) <= {MINE}, (role, example)

def test_staff_names_are_hidden_from_staff_and_auditor(login, I):
    unmasked = I.answer("Which employees have a high attrition risk?", None, False)["df"]; assert "name" in unmasked.columns
    for mask in (True,):
        r = I.answer("Which employees have a high attrition risk?", None, mask); assert "name" not in r["df"].columns and "name" not in r["sql"].split("FROM")[0]
        r = I.answer("who works the most overtime", None, mask); assert "name" not in r["df"].columns
    for role in ("Staff", "Auditor"):
        t = next(e for e in ask(login(role, MINE if role == "Staff" else None), "Which employees have a high attrition risk?") if e["ev"] == "final")["text"]
        assert "| name |" not in t.lower()

def test_scoped_questions_about_another_outlet_are_refused(login):
    t = next(e for e in ask(login("Store Manager", MINE), "How many staff does OUT-011 have?") if e["ev"] == "final")["text"]
    assert "outside your outlet scope" in t

def test_queries_are_read_only_and_parameterised(I):
    import inspect
    src = inspect.getsource(I)
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b", re.sub(r"'[^']*'", "", " ".join(l for l in src.splitlines() if "sql" in l.lower() and "SELECT" in l)))
    r = I.answer("How many staff does OUT-010'; DROP TABLE staff;-- have?")
    assert r is not None and "DROP" not in r["sql"]
