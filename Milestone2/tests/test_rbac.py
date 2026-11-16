"""RBAC tests: every role against every page and action, with an allowed and a denied (403) case.
The expected tables below are copied from the Milestone 2 instructions (page access matrix), NOT imported from rbac.py,
so the tests check the implementation against the specification."""
import json, re
import pytest

OUT = re.compile(r"OUT-\d+")
ROLES = ["Admin", "Franchise Owner", "Store Manager", "Staff", "Auditor"]
PAGES = ["copilot", "workforce", "outlets", "inventory", "marketing", "sentiment", "audit"]
Y, N = True, False
# role -> access to: copilot, workforce, outlets, inventory, marketing, sentiment, audit
MATRIX = {
    "Admin":           [Y, Y, Y, Y, Y, Y, Y],
    "Franchise Owner": [Y, Y, Y, Y, Y, Y, Y],
    "Store Manager":   [Y, Y, Y, Y, N, Y, Y],
    "Staff":           [Y, N, N, N, N, N, N],
    "Auditor":         [Y, Y, Y, Y, Y, Y, Y],
}
RUN_AGENTS = {"Admin": Y, "Franchise Owner": Y, "Store Manager": N, "Staff": N, "Auditor": N}
USERS_PAGE = {"Admin": Y, "Franchise Owner": N, "Store Manager": N, "Staff": N, "Auditor": N}
MINE, OTHER = "OUT-010", "OUT-011"
SCOPED = {"Store Manager", "Staff"}

def who(role): return (role, MINE if role in SCOPED else None)

# ------------------------------------------------------------------ pages: server-side 403, hiding the menu is not enough
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("page", PAGES)
def test_page_access_matrix(login, role, page):
    c = login(*who(role)); r = c.get(f"/api/page/{page}")
    assert r.status_code == (200 if MATRIX[role][PAGES.index(page)] else 403), (role, page, r.text[:200])

@pytest.mark.parametrize("role", ROLES)
def test_admin_page_only_for_admin(login, role):
    c = login(*who(role)); r = c.get("/api/page/admin")
    if not USERS_PAGE[role]: assert r.status_code == 403
    else: assert r.status_code in (200, 404)            # 404 until the admin dashboard page is merged; never 403 for the Admin

def test_unknown_page_is_404_for_everyone(login):
    assert login("Admin").get("/api/page/nope").status_code == 404
    assert login("Staff", MINE).get("/api/page/nope").status_code == 404

@pytest.mark.parametrize("role", ROLES)
def test_menu_matches_matrix(login, role):
    me = login(*who(role)).get("/api/me").json()
    ids = [m["id"] for m in me["menu"]]
    assert set(ids) == {p for p, ok in zip(PAGES, MATRIX[role]) if ok} | {"profile"} | ({"admin"} if USERS_PAGE[role] else set())
    assert me["user"]["role"] == role and "password_hash" not in me["user"]
    assert me["scope"] == (MINE if role in SCOPED else None)
    assert ("run" in me["caps"]) == RUN_AGENTS[role] and ("users" in me["caps"]) == USERS_PAGE[role]

def test_permission_table_matches_the_specification(server):
    import rbac
    for row in rbac.permission_table():
        flags = [row[p.capitalize()] == "✓" for p in PAGES]
        assert flags == MATRIX[row["Role"]], row["Role"]
        assert (row["Run agents"] == "✓") == RUN_AGENTS[row["Role"]] and (row["Users"] == "✓") == USERS_PAGE[row["Role"]]

# ------------------------------------------------------------------ actions
@pytest.mark.parametrize("role", ROLES)
def test_run_all_agents(login, role):
    r = login(*who(role)).post("/api/run_cycle")
    assert r.status_code == (200 if RUN_AGENTS[role] else 403), r.text

@pytest.mark.parametrize("role", ROLES)
def test_run_one_agent(login, role):
    r = login(*who(role)).post("/api/run_agent", json={"agent": "outlet"})
    assert r.status_code == (200 if RUN_AGENTS[role] else 403), r.text

def test_auditor_is_read_only_everywhere(login):
    c = login("Auditor")
    assert c.post("/api/run_cycle").status_code == 403
    assert c.post("/api/franchise/review", json={"outlet": MINE, "rating": 4, "comment": "fine"}).status_code == 403
    assert c.post("/api/franchise/audit", json={"outlet": MINE, "score": 80, "category": "Hygiene"}).status_code == 403

def test_staff_cannot_write_or_read_agents(login):
    c = login("Staff", MINE)
    assert c.post("/api/franchise/review", json={"outlet": MINE, "rating": 4, "comment": "fine"}).status_code == 403
    assert c.post("/api/franchise/audit", json={"outlet": MINE, "score": 80, "category": "Hygiene"}).status_code == 403
    assert c.get(f"/api/detail/{MINE}").status_code == 403

def test_store_manager_writes_only_for_own_outlet(login):
    c = login("Store Manager", MINE)
    ok = c.post("/api/franchise/review", json={"outlet": MINE, "rating": 4, "comment": "great food"}); assert ok.status_code == 200, ok.text
    assert c.post("/api/franchise/review", json={"outlet": OTHER, "rating": 1, "comment": "bad"}).status_code == 403
    ok = c.post("/api/franchise/audit", json={"outlet": MINE, "score": 85, "category": "Hygiene", "notes": "ok"}); assert ok.status_code == 200, ok.text
    assert c.post("/api/franchise/audit", json={"outlet": OTHER, "score": 10, "category": "Hygiene"}).status_code == 403

@pytest.mark.parametrize("role", ["Admin", "Franchise Owner"])
def test_owner_and_admin_write_for_any_outlet(login, role):
    c = login(role)
    assert c.post("/api/franchise/review", json={"outlet": OTHER, "rating": 5, "comment": "lovely"}).status_code == 200
    assert c.post("/api/franchise/audit", json={"outlet": OTHER, "score": 90, "category": "Hygiene"}).status_code == 200

@pytest.mark.parametrize("role", ["Franchise Owner", "Store Manager", "Staff", "Auditor"])
def test_freight_actions_are_admin_only(login, role):
    c = login(*who(role))
    assert c.post("/api/freight/quote", json={}).status_code == 403
    assert c.post("/api/freight/attach", json={}).status_code == 403

# ------------------------------------------------------------------ outlet scope (Store Manager and Staff)
def test_detail_drawer_is_scoped(login):
    c = login("Store Manager", MINE)
    assert c.get(f"/api/detail/{MINE}").status_code == 200
    assert c.get(f"/api/detail/{OTHER}").status_code == 403
    assert login("Admin").get(f"/api/detail/{OTHER}").status_code == 200
    assert login("Auditor").get(f"/api/detail/{OTHER}").status_code == 200

def test_page_parameters_cannot_name_another_outlet(login):
    c = login("Store Manager", MINE)
    assert c.get("/api/page/inventory", params={"p": json.dumps({"o": OTHER})}).status_code == 403
    assert c.get("/api/page/outlets", params={"p": json.dumps({"cmp": [MINE, OTHER]})}).status_code == 403
    assert c.get("/api/page/audit", params={"tab": OTHER}).status_code == 403
    assert c.get("/api/page/inventory", params={"p": json.dumps({"o": MINE})}).status_code == 200
    assert login("Admin").get("/api/page/inventory", params={"p": json.dumps({"o": OTHER})}).status_code == 200

@pytest.mark.parametrize("page", ["workforce", "outlets", "inventory", "sentiment", "audit"])
def test_store_manager_pages_contain_only_own_outlet(login, page):
    r = login("Store Manager", MINE).get(f"/api/page/{page}"); assert r.status_code == 200
    assert set(OUT.findall(r.text)) <= {MINE}, (page, sorted(set(OUT.findall(r.text)) - {MINE})[:5])
    if page != "sentiment": assert MINE in r.text, f"{page} shows nothing for the manager's own outlet"

def test_store_manager_detail_has_no_other_outlets(login):
    r = login("Store Manager", MINE).get(f"/api/detail/{MINE}"); assert r.status_code == 200
    assert set(OUT.findall(r.text)) <= {MINE}

def test_chain_wide_roles_do_see_every_outlet(login):
    for role in ("Admin", "Franchise Owner", "Auditor"):
        r = login(role).get("/api/page/outlets"); assert len(set(OUT.findall(r.text))) > 20, role

def test_scoped_role_without_outlet_is_refused_everywhere(login):
    c = login("Store Manager", None)
    for path in ("/api/me", "/api/page/audit", "/api/pulse", f"/api/detail/{MINE}"): assert c.get(path).status_code == 403, path
    assert login("Staff", "").post("/api/copilot", json={"q": "hello"}).status_code == 403

def test_unknown_role_gets_nothing(login):
    c = login("Intern", MINE)
    for path in ("/api/me", "/api/page/copilot", "/api/pulse"): assert c.get(path).status_code == 403, path
    assert c.post("/api/copilot", json={"q": "hello"}).status_code == 403

def test_live_pulse_is_scoped(login):
    chain = login("Admin").get("/api/pulse").json(); mine = login("Store Manager", MINE).get("/api/pulse").json()
    assert mine["open"] <= 1 + 6 and mine["open"] < chain["open"]
    assert mine["critical"] <= chain["critical"]

# ------------------------------------------------------------------ AI Copilot
def ask(c, q):
    r = c.post("/api/copilot", json={"q": q}); assert r.status_code == 200, r.text
    ev = [json.loads(x[6:]) for x in r.text.split("\n\n") if x.startswith("data: ")]
    return " ".join(e.get("text", "") for e in ev if e.get("ev") == "final")

@pytest.mark.parametrize("role", ROLES)
def test_every_role_may_use_the_copilot(login, role):
    assert "Hello" in ask(login(*who(role)), "hello")

def test_copilot_refuses_another_outlet(login):
    c = login("Store Manager", MINE)
    for q in (f"Why is {OTHER} flagged?", f"show staff at {OTHER}", f"tell me about {OTHER}"):
        t = ask(c, q); assert "outside your outlet scope" in t and OTHER in t, (q, t[:200])
    assert "outside" not in ask(login("Admin"), f"Why is {OTHER} flagged?")

SCOPED_QUESTIONS = ["Which outlets are at highest risk?", "Top 5 outlets by revenue", "Which stores have the lowest customer satisfaction?", "How is inventory holding up?",
                    "How many staff are in Mumbai?", "list all outlets", "average salary by outlet", "which state has the most outlets", "show open tickets",
                    "how many employees are there in total", "best performing outlet", "outlets in Delhi", "how are sales trending", "which campaign has the best ROI",
                    "show negative reviews this week", "low stock items per outlet"]
@pytest.mark.parametrize("role", ["Store Manager", "Staff"])
@pytest.mark.parametrize("q", SCOPED_QUESTIONS)
def test_copilot_never_reveals_other_outlets(login, role, q):
    t = ask(login(role, MINE), q)
    assert set(OUT.findall(t)) <= {MINE}, (q, sorted(set(OUT.findall(t)) - {MINE})[:5])

def test_copilot_hides_salary_from_staff_and_auditor(login):
    for role in ("Staff", "Auditor"):
        t = ask(login(*who(role)), "what is the average salary of staff"); assert "salary" not in t.lower() or "visible" in t.lower() or "not available" in t.lower(), (role, t[:200])

def test_scoped_copilot_examples_name_own_outlet(login):
    ex = login("Store Manager", MINE).get("/api/page/copilot").json()["blocks"][0]["examples"]
    assert all(set(OUT.findall(e)) <= {MINE} for e in ex)

@pytest.mark.parametrize("role", ROLES)
def test_chats_need_copilot_capability(login, role):
    assert login(*who(role)).get("/api/chats").status_code == 200       # every role has the copilot capability

# ------------------------------------------------------------------ the other places identity enters
@pytest.mark.parametrize("role,code", [("Admin", 200), ("Franchise Owner", 403), ("Store Manager", 403), ("Staff", 403), ("Auditor", 403)])
def test_metrics_is_admin_only(login, role, code):
    assert login(*who(role)).get("/api/metrics").status_code == code

def test_public_endpoints_stay_public(server):
    assert server.client.get("/api/health").status_code == 200
    assert server.client.get("/api/public").status_code == 200
