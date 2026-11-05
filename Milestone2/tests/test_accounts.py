"""Real accounts, no simulated users: signup, login, lockout, password recovery, profile and the admin dashboard,
checked against the rules in the Milestone 2 instructions (Steps 3, 4, 5 and 6)."""
import re, itertools
import pytest

OUT = re.compile(r"OUT-\d+")
PW = "Passw0rd!x"
QUESTION, ANSWER = "What was the name of your first school?", "Greenwood Primary"
_n = itertools.count(1)

@pytest.fixture
def call(server):
    def _call(method, path, token=None, **kw):
        server.client.cookies.clear()               # the test client keeps the login cookie; send only what the test means to send
        h = {"Authorization": f"Bearer {token}"} if token else {}
        return server.client.request(method, path, headers=h, **kw)
    return _call

@pytest.fixture
def make(call):
    """make(role, outlet=None) -> (token, user) of a brand-new account created through the public signup route."""
    def _make(role, outlet=None, password=PW):
        k = next(_n); name = f"user{k}_{role.split()[0].lower()}"
        body = {"email": f"{name}@test.org", "username": name, "password": password, "confirm_password": password, "role": role, "outlet": outlet, "security_question": QUESTION, "security_answer": ANSWER}
        r = call("POST", "/api/auth/signup", json=body); assert r.status_code == 200, r.text
        r = call("POST", "/api/auth/login", json={"identity": body["email"], "password": password}); assert r.status_code == 200, r.text
        return r.json()["token"], {**r.json()["user"], "email": body["email"], "username": name, "password": password, "answer": ANSWER}
    return _make

@pytest.fixture
def admin(call):
    import config
    r = call("POST", "/api/auth/login", json={"identity": config.ADMIN_EMAIL_ID, "password": config.ADMIN_PASSWORD}); assert r.status_code == 200, r.text
    return r.json()["token"], r.json()["user"]

# ------------------------------------------------------------------ signup (Step 3 validation rules + RBAC at signup)
def signup(call, **over):
    k = next(_n); body = {"email": f"s{k}@test.org", "username": f"su{k}", "password": PW, "confirm_password": PW, "role": "Staff", "outlet": "OUT-010", "security_question": QUESTION, "security_answer": ANSWER, **over}
    return call("POST", "/api/auth/signup", json=body)

@pytest.mark.parametrize("over,needle", [
    ({"email": ""}, "empty"), ({"username": "  "}, "empty"), ({"password": "", "confirm_password": ""}, "empty"),
    ({"email": "a@bc.de"}, "2 characters before"), ({"email": "ab@c.de"}, "2 characters between"), ({"email": "ab@cd.e"}, "2 characters after"), ({"email": "no-at-sign.com"}, "@"),
    ({"password": "Sh0rt!a", "confirm_password": "Sh0rt!a"}, "8 characters"), ({"password": "alllower1!", "confirm_password": "alllower1!"}, "uppercase"),
    ({"password": "ALLUPPER1!", "confirm_password": "ALLUPPER1!"}, "lowercase"), ({"password": "NoDigits!!", "confirm_password": "NoDigits!!"}, "digit"),
    ({"password": "NoSpecial11", "confirm_password": "NoSpecial11"}, "special"), ({"confirm_password": "Different1!"}, "does not match"),
    ({"username": "a b"}, "letters, numbers"), ({"role": "Customer"}, "valid role"), ({"role": ""}, "empty"),
    ({"role": "Staff", "outlet": ""}, "outlet"), ({"role": "Store Manager", "outlet": "OUT-999"}, "does not exist"),
    ({"security_question": ""}, "empty"), ({"security_answer": "  "}, "empty"), ({"security_question": "What is your favourite colour?"}, "from the list"), ({"security_answer": "x"}, "2 characters"),
])
def test_signup_validation(call, over, needle):
    r = signup(call, **over); assert r.status_code == 400 and needle.lower() in r.json()["detail"].lower(), (over, r.text)

def test_nobody_can_sign_up_as_admin(call):
    for role in ("Admin", "admin", "ADMIN", "Administrator"):
        assert signup(call, role=role).status_code == 400, role

def test_signup_roles_and_outlet_rules(call):
    assert signup(call, role="Franchise Owner", outlet="").status_code == 200       # chain-wide roles need no outlet
    assert signup(call, role="Auditor", outlet="").status_code == 200
    assert signup(call, role="Store Manager", outlet="OUT-010").status_code == 200
    assert signup(call, role="Store Manager", outlet="").status_code == 400

def test_signup_rejects_duplicates(call, make):
    _, u = make("Staff", "OUT-010")
    assert "email" in signup(call, email=u["email"].upper()).json()["detail"].lower()
    assert "username" in signup(call, username=u["username"].upper()).json()["detail"].lower()

def test_signup_options_are_public_and_exclude_admin(call):
    o = call("GET", "/api/auth/options").json(); assert "Admin" not in o["roles"] and set(o["roles"]) == {"Franchise Owner", "Store Manager", "Staff", "Auditor"} and "OUT-010" in o["outlets"]

def test_passwords_are_hashed(server, make):
    _, u = make("Staff", "OUT-010")
    import accounts
    with accounts.db() as c: h = c.execute("SELECT password_hash FROM users WHERE email=?", (u["email"],)).fetchone()[0]
    assert h.startswith("$2") and u["password"] not in h

# ------------------------------------------------------------------ login, JWT, lockout (Step 3)
def test_login_by_email_or_username_and_token_is_required(call, make):
    tok, u = make("Staff", "OUT-010")
    assert call("GET", "/api/me").status_code == 401                                   # no token
    assert call("GET", "/api/me", token="garbage").status_code == 401
    assert call("GET", "/api/me", token=tok).json()["user"]["role"] == "Staff"
    r = call("POST", "/api/auth/login", json={"identity": u["username"].upper(), "password": u["password"]}); assert r.status_code == 200
    assert "password" not in r.text and "hash" not in r.text

def test_unknown_user_and_wrong_password_give_the_same_error(call, make):
    _, u = make("Staff", "OUT-010")
    a = call("POST", "/api/auth/login", json={"identity": "nobody@nowhere.org", "password": "Whatever1!"})
    b = call("POST", "/api/auth/login", json={"identity": u["email"], "password": "Whatever1!"})
    assert a.status_code == b.status_code == 401 and a.json()["detail"] == b.json()["detail"]

def test_five_wrong_passwords_lock_the_account(call, make, admin):
    tok, u = make("Staff", "OUT-010")
    for i in range(4): assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": f"Wrong{i}pass!"}).status_code == 401
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": u["password"]}).status_code == 200     # still open after 4; success resets the counter
    for i in range(5): call("POST", "/api/auth/login", json={"identity": u["email"], "password": f"Wrong{i}pass!"})
    r = call("POST", "/api/auth/login", json={"identity": u["email"], "password": u["password"]}); assert r.status_code == 403 and "locked" in r.json()["detail"].lower()
    assert call("GET", "/api/me", token=tok).status_code == 401                         # the token from before the lock stops working at once
    users = call("GET", "/api/admin/overview", token=admin[0]).json()["users"]; assert next(x for x in users if x["email"] == u["email"])["locked"]

def test_locked_user_is_blocked_immediately_and_unlock_restores(call, make, admin):
    tok, u = make("Franchise Owner")
    assert call("GET", "/api/page/outlets", token=tok).status_code == 200
    assert call("POST", f"/api/admin/users/{u['id']}/lock", token=admin[0]).status_code == 200
    assert call("GET", "/api/page/outlets", token=tok).status_code == 401
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": u["password"]}).status_code == 403
    assert call("POST", f"/api/admin/users/{u['id']}/unlock", token=admin[0]).status_code == 200
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": u["password"]}).status_code == 200

# ------------------------------------------------------------------ RBAC with real accounts (Step 5: log in as each role, one allowed and one 403)
def test_each_real_role_gets_the_right_pages(call, make, admin):
    accounts = {"Admin": admin[0], "Franchise Owner": make("Franchise Owner")[0], "Store Manager": make("Store Manager", "OUT-010")[0], "Staff": make("Staff", "OUT-010")[0], "Auditor": make("Auditor")[0]}
    allowed = {"Admin": {"marketing", "audit"}, "Franchise Owner": {"marketing", "audit"}, "Store Manager": {"audit"}, "Staff": set(), "Auditor": {"marketing", "audit"}}
    for role, tok in accounts.items():
        for page in ("marketing", "audit"): assert call("GET", f"/api/page/{page}", token=tok).status_code == (200 if page in allowed[role] else 403), (role, page)
        assert call("GET", "/api/page/copilot", token=tok).status_code == 200
        assert call("POST", "/api/run_cycle", token=tok).status_code == (200 if role in ("Admin", "Franchise Owner") else 403), role
        assert call("GET", "/api/admin/overview", token=tok).status_code == (200 if role == "Admin" else 403), role
    sm = accounts["Store Manager"]; assert set(OUT.findall(call("GET", "/api/page/audit", token=sm).text)) <= {"OUT-010"}

# ------------------------------------------------------------------ forgot / reset by e-mail code
@pytest.fixture
def mails(monkeypatch):
    sent = []
    import mailer; monkeypatch.setattr(mailer, "send", lambda to, subject, body, *a, **k: (sent.append((to, body)) or (True, "ok")))
    return sent
def code_in(mails, to): return re.search(r"\b(\d{6})\b", [b for t, b in mails if t == to][-1]).group(1)

def expire_cooldown(email):
    import accounts
    with accounts.db() as c: c.execute("UPDATE users SET otp_sent=0 WHERE lower(email)=?", (email.lower(),))

def test_forgot_is_silent_about_unknown_emails(call, mails):
    r = call("POST", "/api/auth/forgot", json={"email": "ghost@nowhere.org"}); assert r.status_code == 200 and not mails
    assert call("POST", "/api/auth/forgot", json={}).status_code == 400
    assert call("POST", "/api/auth/forgot", json={"email": "not-an-account"}).status_code == 200 and not mails

def test_reset_flow_changes_the_password_and_ends_old_sessions(call, make, mails):
    tok, u = make("Staff", "OUT-010"); call("POST", "/api/auth/forgot", json={"email": u["email"]}); code = code_in(mails, u["email"])
    assert call("POST", "/api/auth/verify", json={"email": u["email"], "otp": "000000"}).status_code == 400
    assert call("POST", "/api/auth/verify", json={"email": u["email"], "otp": code}).status_code == 200
    assert call("POST", "/api/auth/reset", json={"email": u["email"], "otp": code, "password": "weak", "confirm_password": "weak"}).status_code == 400
    assert call("POST", "/api/auth/reset", json={"email": u["email"], "otp": code, "password": "NewPassw0rd!", "confirm_password": "Other0Passw!"}).status_code == 400
    assert call("POST", "/api/auth/reset", json={"email": u["email"], "otp": code, "password": "NewPassw0rd!", "confirm_password": "NewPassw0rd!"}).status_code == 200
    assert call("POST", "/api/auth/reset", json={"email": u["email"], "otp": code, "password": "NewPassw0rd!", "confirm_password": "NewPassw0rd!"}).status_code == 400   # the code works once
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": u["password"]}).status_code == 401
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": "NewPassw0rd!"}).status_code == 200
    assert call("GET", "/api/me", token=tok).status_code == 401

def test_three_wrong_codes_pause_recovery_for_fifteen_minutes(call, make, mails):
    _, u = make("Staff", "OUT-010"); call("POST", "/api/auth/forgot", json={"email": u["email"]}); code = code_in(mails, u["email"]); wrong = "111111" if code != "111111" else "222222"
    for _ in range(2): assert call("POST", "/api/auth/verify", json={"email": u["email"], "otp": wrong}).status_code == 400
    r = call("POST", "/api/auth/verify", json={"email": u["email"], "otp": wrong}); assert r.status_code == 429 and "paused" in r.json()["detail"]
    assert call("POST", "/api/auth/verify", json={"email": u["email"], "otp": code}).status_code == 429                              # even the right code waits
    assert call("POST", "/api/auth/forgot", json={"email": u["email"]}).status_code == 429                                           # and no new code is sent
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": u["password"]}).status_code == 200              # the account itself is not locked
    import accounts
    with accounts.db() as c: c.execute("UPDATE users SET otp_blocked_until=?, otp_sent=0 WHERE email=?", (__import__("time").time() - 1, u["email"]))
    mails.clear(); assert call("POST", "/api/auth/forgot", json={"email": u["email"]}).status_code == 200 and mails                    # the pause ends by itself

def test_a_code_cannot_be_used_after_the_account_is_locked(call, make, admin, mails):
    _, u = make("Staff", "OUT-010"); call("POST", "/api/auth/forgot", json={"email": u["email"]}); code = code_in(mails, u["email"])
    call("POST", f"/api/admin/users/{u['id']}/lock", token=admin[0])
    assert call("POST", "/api/auth/verify", json={"email": u["email"], "otp": code}).status_code == 403
    assert call("POST", "/api/auth/reset", json={"email": u["email"], "otp": code, "password": "NewPassw0rd!", "confirm_password": "NewPassw0rd!"}).status_code == 403

def test_recovery_works_with_the_username_too(call, make, mails):
    _, u = make("Staff", "OUT-010"); call("POST", "/api/auth/forgot", json={"identity": u["username"].upper()}); code = code_in(mails, u["email"])          # the code goes to the e-mail on file
    assert call("POST", "/api/auth/reset", json={"identity": u["username"], "otp": code, "password": "NewPassw0rd!", "confirm_password": "NewPassw0rd!"}).status_code == 200
    assert ask_q(call, u["username"]).json()["question"] == QUESTION
    assert reset_a(call, u["username"], ANSWER, "Another0Pass!").status_code == 200

def test_a_locked_account_is_told_so_and_gets_no_code_or_question(call, make, admin, mails):
    _, u = make("Staff", "OUT-010"); call("POST", f"/api/admin/users/{u['id']}/lock", token=admin[0])
    for body in ({"email": u["email"]}, {"identity": u["username"]}):
        r = call("POST", "/api/auth/forgot", json=body); assert r.status_code == 403 and "locked" in r.json()["detail"].lower()
        r = call("POST", "/api/auth/security-question", json=body); assert r.status_code == 403
    assert not [m for m in mails if m[0] == u["email"]]
    call("POST", f"/api/admin/users/{u['id']}/unlock", token=admin[0])
    assert call("POST", "/api/auth/forgot", json={"email": u["email"]}).status_code == 200 and [m for m in mails if m[0] == u["email"]]          # after an unlock it works again

def test_the_verification_email_is_formatted(call, make, monkeypatch):
    sent = {}
    import mailer; monkeypatch.setattr(mailer, "send", lambda to, subject, body, *a, **k: (sent.update(to=to, subject=subject, body=body, html=k.get("html")) or (True, "ok")))
    _, u = make("Staff", "OUT-010"); call("POST", "/api/auth/forgot", json={"email": u["email"]})
    code = re.search(r"code is (\d{6})", sent["body"]).group(1)
    assert sent["to"] == u["email"] and "verification code" in sent["subject"].lower() and "5 minutes" in sent["body"]
    h = sent["html"]; assert h.startswith("<!doctype html>") and "FranchiseOps" in h and "5 minutes" in h and "Did not ask for this?" in h and u["username"] in h
    assert all(f">{d}</span>" in h for d in code)                                                                                  # each digit in its own box
    assert "<script" not in h.lower()

def test_reset_does_not_unlock_a_locked_account(call, make, admin, mails):
    _, u = make("Staff", "OUT-010"); call("POST", f"/api/admin/users/{u['id']}/lock", token=admin[0])
    call("POST", "/api/auth/forgot", json={"email": u["email"]}); assert not [m for m in mails if m[0] == u["email"]]       # no code for a locked account
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": u["password"]}).status_code == 403

# ------------------------------------------------------------------ profile (Step 4)
def test_profile_shows_account_and_never_the_hash(call, make):
    tok, u = make("Store Manager", "OUT-010"); p = call("GET", "/api/profile", token=tok).json()["profile"]
    assert p["email"] == u["email"] and p["role"] == "Store Manager" and p["outlet"] == "OUT-010" and p["created_at"] and p["last_login"] and "hash" not in str(p).lower()

def test_profile_username_change(call, make):
    tok, u = make("Staff", "OUT-010"); _, other = make("Staff", "OUT-011")
    assert call("POST", "/api/profile/username", token=tok, json={"username": other["username"]}).status_code == 400
    assert call("POST", "/api/profile/username", token=tok, json={"username": "x"}).status_code == 400
    assert call("POST", "/api/profile/username", token=tok, json={"username": "renamed_user"}).status_code == 200
    assert call("GET", "/api/profile", token=tok).json()["profile"]["username"] == "renamed_user"

def test_profile_password_change_needs_current_password_and_rules(call, make):
    tok, u = make("Staff", "OUT-010"); body = lambda **o: {"current_password": u["password"], "new_password": "Brand0New!pw", "confirm_password": "Brand0New!pw", **o}
    assert call("POST", "/api/profile/password", token=tok, json=body(current_password="Wrong0pass!")).status_code == 400
    assert call("POST", "/api/profile/password", token=tok, json=body(new_password="weak", confirm_password="weak")).status_code == 400
    assert call("POST", "/api/profile/password", token=tok, json=body(confirm_password="Mismatch0!pw")).status_code == 400
    r = call("POST", "/api/profile/password", token=tok, json=body()); assert r.status_code == 200
    assert call("GET", "/api/me", token=tok).status_code == 401 and call("GET", "/api/me", token=r.json()["token"]).status_code == 200
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": "Brand0New!pw"}).status_code == 200

# ------------------------------------------------------------------ admin dashboard (Step 6)
def test_admin_overview_has_users_kpis_activity_and_no_hashes(call, admin, make):
    make("Staff", "OUT-010"); d = call("GET", "/api/admin/overview", token=admin[0]).json()
    assert d["kpis"]["total"] == len(d["users"]) and d["kpis"]["per_role"]["Admin"] >= 1 and "locked" in d["kpis"]
    assert {"email", "username", "role", "locked", "created_at", "last_login"} <= set(d["users"][0]) and "hash" not in str(d).lower() and "otp" not in str(d["users"]).lower()
    assert len(d["activity"]) <= 50 and d["activity"] and {"ts", "actor", "event"} <= set(d["activity"][0]) and d["matrix"][0]["Role"] == "Admin"

def test_admin_add_user_applies_the_validation_rules(call, admin):
    ok = {"email": "new.hire@test.org", "username": "new_hire", "password": "Temp0rary!pw", "role": "Auditor"}
    assert call("POST", "/api/admin/users", token=admin[0], json={**ok, "password": "weak"}).status_code == 400
    assert call("POST", "/api/admin/users", token=admin[0], json={**ok, "email": "a@b.c"}).status_code == 400
    assert call("POST", "/api/admin/users", token=admin[0], json={**ok, "role": "Store Manager"}).status_code == 400            # needs an outlet
    assert call("POST", "/api/admin/users", token=admin[0], json=ok).status_code == 200
    assert call("POST", "/api/admin/users", token=admin[0], json=ok).status_code == 400                                         # duplicate
    assert call("POST", "/api/auth/login", json={"identity": ok["email"], "password": ok["password"]}).status_code == 200
    assert call("POST", "/api/admin/users", token=admin[0], json={**ok, "email": "boss@test.org", "username": "boss_two", "role": "Admin"}).status_code == 200   # an Admin may create an Admin

def test_promote_and_demote_take_effect_immediately(call, admin, make):
    tok, u = make("Staff", "OUT-010")
    assert call("GET", "/api/page/workforce", token=tok).status_code == 403
    assert call("POST", f"/api/admin/users/{u['id']}/role", token=admin[0], json={"role": "Franchise Owner"}).status_code == 200
    assert call("GET", "/api/page/workforce", token=tok).status_code == 200 and call("POST", "/api/run_cycle", token=tok).status_code == 200      # same token, new privileges
    assert call("POST", f"/api/admin/users/{u['id']}/role", token=admin[0], json={"role": "Auditor"}).status_code == 200
    assert call("POST", "/api/run_cycle", token=tok).status_code == 403 and call("GET", "/api/page/workforce", token=tok).status_code == 200
    assert call("POST", f"/api/admin/users/{u['id']}/role", token=admin[0], json={"role": "Store Manager"}).status_code == 200            # the outlet from signup was kept while they held an all-outlets role
    assert call("GET", "/api/me", token=tok).json()["scope"] == "OUT-010"
    assert call("POST", f"/api/admin/users/{u['id']}/role", token=admin[0], json={"role": "Store Manager", "outlet": "OUT-020"}).status_code == 200
    assert call("GET", "/api/me", token=tok).json()["scope"] == "OUT-020"
    _, nobody = make("Franchise Owner")                                                                                                   # never had an outlet: a scoped role needs one
    assert call("POST", f"/api/admin/users/{nobody['id']}/role", token=admin[0], json={"role": "Store Manager"}).status_code == 400
    assert call("POST", f"/api/admin/users/{nobody['id']}/role", token=admin[0], json={"role": "Staff", "outlet": "OUT-999"}).status_code == 400
    assert call("POST", f"/api/admin/users/{u['id']}/role", token=admin[0], json={"role": "Wizard"}).status_code == 400

def test_non_admins_cannot_touch_users(call, make, admin):
    tok, u = make("Franchise Owner"); _, victim = make("Staff", "OUT-010")
    for method, path, body in [("GET", "/api/admin/overview", None), ("POST", "/api/admin/users", {}), ("POST", f"/api/admin/users/{victim['id']}/role", {"role": "Admin"}),
                               ("POST", f"/api/admin/users/{victim['id']}/lock", {}), ("POST", f"/api/admin/users/{victim['id']}/delete", {"confirm": True})]:
        assert call(method, path, token=tok, json=body).status_code == 403, path
    assert call("GET", "/api/admin/overview").status_code == 401

def test_delete_needs_confirmation(call, admin, make):
    _, u = make("Staff", "OUT-010")
    assert call("POST", f"/api/admin/users/{u['id']}/delete", token=admin[0], json={}).status_code == 400
    assert call("POST", f"/api/admin/users/{u['id']}/delete", token=admin[0], json={"confirm": "yes"}).status_code == 400
    assert call("POST", f"/api/admin/users/{u['id']}/delete", token=admin[0], json={"confirm": True}).status_code == 200
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": u["password"]}).status_code == 401
    assert call("POST", f"/api/admin/users/{u['id']}/delete", token=admin[0], json={"confirm": True}).status_code == 404

def test_an_admin_cannot_delete_lock_or_demote_themselves(call, admin):
    tok, me = admin
    assert call("POST", f"/api/admin/users/{me['id']}/delete", token=tok, json={"confirm": True}).status_code == 400
    assert call("POST", f"/api/admin/users/{me['id']}/lock", token=tok).status_code == 400
    assert call("POST", f"/api/admin/users/{me['id']}/role", token=tok, json={"role": "Staff", "outlet": "OUT-010"}).status_code == 400

def test_the_last_admin_is_protected(call, admin):
    """A locked Admin cannot act and an Admin cannot touch their own account, so the last active Admin can never be removed, locked or demoted."""
    tok, me = admin
    r = call("POST", "/api/admin/users", token=tok, json={"email": "extra.admin@test.org", "username": "extra_admin", "password": "Extra0Admin!", "role": "Admin"}); assert r.status_code == 200
    extra = r.json()["id"]; t2 = call("POST", "/api/auth/login", json={"identity": "extra.admin@test.org", "password": "Extra0Admin!"}).json()["token"]
    assert call("POST", f"/api/admin/users/{me['id']}/lock", token=t2).status_code == 200            # two Admins: one may lock the other
    assert call("GET", "/api/admin/overview", token=tok).status_code == 401                          # ...and the locked Admin is out at once, so it cannot hit back
    assert call("POST", f"/api/admin/users/{extra}/delete", token=t2, json={"confirm": True}).status_code == 400   # the remaining Admin cannot delete itself
    assert call("POST", f"/api/admin/users/{extra}/lock", token=t2).status_code == 400
    assert call("POST", f"/api/admin/users/{extra}/role", token=t2, json={"role": "Staff", "outlet": "OUT-010"}).status_code == 400
    assert call("POST", f"/api/admin/users/{me['id']}/unlock", token=t2).status_code == 200            # put things back
    assert call("POST", f"/api/admin/users/{extra}/delete", token=call("POST", "/api/auth/login", json={"identity": me["email"], "password": __import__("config").ADMIN_PASSWORD}).json()["token"], json={"confirm": True}).status_code == 200

def test_admin_actions_are_logged_with_who_what_when(call, admin, make):
    _, u = make("Staff", "OUT-010"); call("POST", f"/api/admin/users/{u['id']}/role", token=admin[0], json={"role": "Auditor"}); call("POST", f"/api/admin/users/{u['id']}/lock", token=admin[0])
    log = call("GET", "/api/admin/overview", token=admin[0]).json()["activity"]
    ev = {(x["event"], x["target"]) for x in log}; assert ("role_changed", u["email"]) in ev and ("user_locked", u["email"]) in ev
    assert all(x["actor"] and x["ts"] for x in log)

def test_five_wrong_passwords_never_lock_the_last_active_admin(call):
    import accounts, config
    with accounts.db() as c: c.execute("DELETE FROM users WHERE role='Admin' AND lower(email)<>lower(?)", (config.ADMIN_EMAIL_ID,)); c.execute("UPDATE users SET locked=0, failed_attempts=0 WHERE lower(email)=lower(?)", (config.ADMIN_EMAIL_ID,))
    for i in range(8): call("POST", "/api/auth/login", json={"identity": config.ADMIN_EMAIL_ID, "password": f"Wrong{i}pass!"})
    assert call("POST", "/api/auth/login", json={"identity": config.ADMIN_EMAIL_ID, "password": config.ADMIN_PASSWORD}).status_code == 200

# ------------------------------------------------------------------ recovery by security question (the second recovery route from Milestone 1)
def ask_q(call, email): return call("POST", "/api/auth/security-question", json={"email": email})
def reset_a(call, email, answer, pw="NewPassw0rd!"): return call("POST", "/api/auth/reset-with-answer", json={"email": email, "answer": answer, "password": pw, "confirm_password": pw})

def test_options_list_the_five_questions_and_the_answer_is_stored_hashed(call, make):
    qs = call("GET", "/api/auth/options").json()["questions"]; assert len(qs) == 5 and QUESTION in qs
    _, u = make("Staff", "OUT-010")
    import accounts
    with accounts.db() as c: q, h = c.execute("SELECT security_question, security_answer FROM users WHERE email=?", (u["email"],)).fetchone()
    assert q == QUESTION and h.startswith("$2") and ANSWER.lower() not in h.lower()

def test_the_account_question_is_shown_and_never_the_answer(call, make):
    tok, u = make("Staff", "OUT-010")
    assert ask_q(call, u["email"]).json()["question"] == QUESTION and ANSWER.lower() not in ask_q(call, u["email"]).text.lower()
    p = call("GET", "/api/profile", token=tok).json()["profile"]; assert p["security_question"] == QUESTION and ANSWER.lower() not in str(p).lower()
    assert ask_q(call, "").status_code == 400

def test_unknown_and_locked_accounts_get_a_stable_believable_question(call, make, admin):
    qs = call("GET", "/api/auth/options").json()["questions"]
    a, b = ask_q(call, "ghost@nowhere.org").json()["question"], ask_q(call, "ghost@nowhere.org").json()["question"]; assert a == b and a in qs
    _, u = make("Staff", "OUT-010"); call("POST", f"/api/admin/users/{u['id']}/lock", token=admin[0])
    assert ask_q(call, u["email"]).status_code == 403                                                    # a locked account is told so, and gets no question

def test_reset_with_the_right_answer_changes_the_password_and_ends_old_sessions(call, make):
    tok, u = make("Staff", "OUT-010")
    assert reset_a(call, u["email"], "not my school").status_code == 400
    assert reset_a(call, u["email"], "  GREENWOOD   primary ").status_code == 200                      # capital letters and extra spaces do not matter
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": u["password"]}).status_code == 401
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": "NewPassw0rd!"}).status_code == 200
    assert call("GET", "/api/me", token=tok).status_code == 401

def test_reset_by_answer_applies_the_password_rules(call, make):
    _, u = make("Staff", "OUT-010")
    assert reset_a(call, u["email"], ANSWER, "weak").status_code == 400
    assert call("POST", "/api/auth/reset-with-answer", json={"email": u["email"], "answer": ANSWER, "password": "NewPassw0rd!", "confirm_password": "Different0Pass!"}).status_code == 400
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": u["password"]}).status_code == 200            # nothing changed

def test_three_wrong_answers_pause_recovery_for_fifteen_minutes(call, make):
    _, u = make("Staff", "OUT-010")
    for i in range(2): assert reset_a(call, u["email"], f"nope{i}").status_code == 400
    r = reset_a(call, u["email"], "nope3"); assert r.status_code == 400 and "paused" in r.json()["detail"]
    r = reset_a(call, u["email"], ANSWER); assert r.status_code == 429 and "paused" in r.json()["detail"]                       # even the right answer waits
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": u["password"]}).status_code == 200            # the account itself is not locked
    import accounts
    with accounts.db() as c: c.execute("UPDATE users SET sq_blocked_until=? WHERE email=?", (__import__("time").time() - 1, u["email"]))
    assert reset_a(call, u["email"], ANSWER).status_code == 200                                                                   # the pause ends by itself

def test_wrong_answers_for_an_unknown_email_look_the_same_and_block_nothing(call, make):
    _, u = make("Staff", "OUT-010")
    a = reset_a(call, "ghost@nowhere.org", "anything"); b = reset_a(call, u["email"], "anything")
    assert a.status_code == b.status_code == 400 and a.json()["detail"] == b.json()["detail"] == "That answer is wrong."

def test_a_locked_account_cannot_recover_itself_by_answer(call, make, admin):
    _, u = make("Staff", "OUT-010"); call("POST", f"/api/admin/users/{u['id']}/lock", token=admin[0])
    assert reset_a(call, u["email"], ANSWER).status_code == 403
    assert call("POST", "/api/auth/login", json={"identity": u["email"], "password": u["password"]}).status_code == 403

def test_an_account_without_a_question_must_set_one_in_the_profile_first(call, admin):
    ok = {"email": "noquestion@test.org", "username": "no_question", "password": "Temp0rary!pw", "role": "Auditor"}
    assert call("POST", "/api/admin/users", token=admin[0], json=ok).status_code == 200                                           # created by an Admin: no question yet
    assert reset_a(call, ok["email"], "anything").status_code == 400
    tok = call("POST", "/api/auth/login", json={"identity": ok["email"], "password": ok["password"]}).json()["token"]
    assert call("GET", "/api/profile", token=tok).json()["profile"]["security_question"] is None
    body = lambda **o: {"current_password": ok["password"], "security_question": QUESTION, "security_answer": "Blue Door", **o}
    assert call("POST", "/api/profile/security", token=tok, json=body(current_password="Wrong0pass!")).status_code == 400
    assert call("POST", "/api/profile/security", token=tok, json=body(security_question="What is your favourite colour?")).status_code == 400
    assert call("POST", "/api/profile/security", token=tok, json=body(security_answer="x")).status_code == 400
    assert call("POST", "/api/profile/security", token=tok, json=body()).status_code == 200
    assert call("GET", "/api/profile", token=tok).json()["profile"]["security_question"] == QUESTION
    assert reset_a(call, ok["email"], "blue door").status_code == 200

def test_a_new_security_answer_replaces_the_old_one(call, make):
    tok, u = make("Staff", "OUT-010")
    assert call("POST", "/api/profile/security", token=tok, json={"current_password": u["password"], "security_question": "What is your mother's maiden name?", "security_answer": "Sharma"}).status_code == 200
    assert ask_q(call, u["email"]).json()["question"] == "What is your mother's maiden name?"
    assert reset_a(call, u["email"], ANSWER).status_code == 400 and reset_a(call, u["email"], "sharma").status_code == 200

# ------------------------------------------------------------------ profile picture, IST timestamps (Milestone 2 polish)
import base64 as _b64
PNG = "data:image/png;base64," + _b64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 200).decode()
JPG = "data:image/jpeg;base64," + _b64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 200).decode()

def test_a_user_can_set_and_remove_a_profile_photo(call, make):
    tok, u = make("Staff", "OUT-010")
    assert call("GET", "/api/profile", token=tok).json()["profile"]["picture"] is None
    r = call("POST", "/api/profile/picture", token=tok, json={"image": JPG}); assert r.status_code == 200
    assert call("GET", "/api/profile", token=tok).json()["profile"]["picture"] == JPG
    assert call("GET", "/api/me", token=tok).json()["user"]["picture"] == JPG                      # the sidebar uses it
    assert call("POST", "/api/profile/picture", token=tok, json={"image": PNG}).status_code == 200
    assert call("POST", "/api/profile/picture", token=tok, json={"remove": True}).status_code == 200
    assert call("GET", "/api/profile", token=tok).json()["profile"]["picture"] is None

def test_bad_profile_photos_are_refused(call, make):
    tok, _ = make("Staff", "OUT-010"); post = lambda img: call("POST", "/api/profile/picture", token=tok, json={"image": img}).status_code
    assert post("") == 400 and post("hello") == 400 and post("data:text/html;base64,PHNjcmlwdD4=") == 400 and post("data:image/svg+xml;base64,PHN2Zz4=") == 400
    assert post("data:image/png;base64,@@@@") == 400
    assert post("data:image/png;base64," + _b64.b64encode(b"not really a png" * 20).decode()) == 400                       # the bytes must be a real PNG
    assert post("data:image/jpeg;base64," + _b64.b64encode(b"\xff\xd8\xff" + b"0" * 160_000).decode()) == 400                # too large
    assert call("POST", "/api/profile/picture", json={"image": JPG}).status_code == 401

def test_every_role_has_a_photo_and_the_admin_sees_them(call, make, admin):
    tok, u = make("Auditor"); call("POST", "/api/profile/picture", token=tok, json={"image": PNG})
    atok = admin[0]; assert call("POST", "/api/profile/picture", token=atok, json={"image": JPG}).status_code == 200                  # the Admin too
    users = call("GET", "/api/admin/overview", token=atok).json()["users"]
    assert next(x for x in users if x["email"] == u["email"])["picture"] == PNG and next(x for x in users if x["role"] == "Admin")["picture"] == JPG

def test_times_carry_a_time_zone_so_the_browser_can_show_them_in_ist(call, make, admin):
    tok, u = make("Staff", "OUT-010")
    p = call("GET", "/api/profile", token=tok).json()["profile"]
    tz = re.compile(r"(Z|[+-]\d\d:\d\d)$")
    assert tz.search(p["created_at"]) and tz.search(p["last_login"])
    d = call("GET", "/api/admin/overview", token=admin[0]).json()
    assert all(tz.search(x["ts"]) for x in d["activity"]) and all(tz.search(x["created_at"]) for x in d["users"])

def test_agent_run_time_is_shown_in_ist(server):
    import views_core
    assert views_core.ist_time("2026-11-03T12:00:00+00:00") == "5:30:00 PM IST"
    assert views_core.ist_time("2026-11-03T18:45:10+00:00").endswith("AM IST") and views_core.ist_time("not a time") == "not a time"
