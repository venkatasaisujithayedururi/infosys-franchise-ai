"""Role-based access control (Step 5). One place that says who may open which page, which capability each role has and
which outlet a role is limited to. Everything here is enforced on the server; hiding a menu item in the front end is only a convenience.

The user object that user_of(request) returns must contain: email, username, role and (for Store Manager / Staff) outlet.
An unknown role gets nothing, and a scoped role without an outlet is refused: every check fails closed."""
import re
from fastapi import HTTPException

ROLES = ["Admin", "Franchise Owner", "Store Manager", "Staff", "Auditor"]

# page ids (the menu entries of server.py plus the profile and admin pages)
AGENT_PAGES = {"workforce", "outlets", "inventory", "marketing", "sentiment", "audit"}
ALL_PAGES = {"copilot", "profile", "admin"} | AGENT_PAGES
EXTRA_MENU = [("profile", "My Profile", "user"), ("admin", "Admin Dashboard", "shield")]      # appended to V.MENU; the front end draws these two pages itself

# page access matrix (Copilot, Workforce, Outlets, Inventory, Marketing, Sentiment, Audit; Profile for everyone; Users = the admin page)
ROLE_MENU = {
    "Admin":           {"copilot", "workforce", "outlets", "inventory", "marketing", "sentiment", "audit", "profile", "admin"},
    "Franchise Owner": {"copilot", "workforce", "outlets", "inventory", "marketing", "sentiment", "audit", "profile"},
    "Store Manager":   {"copilot", "workforce", "outlets", "inventory", "sentiment", "audit", "profile"},
    "Staff":           {"copilot", "profile"},
    "Auditor":         {"copilot", "workforce", "outlets", "inventory", "marketing", "sentiment", "audit", "profile"},
}

# capabilities: what a role may DO (need(ctx, capability) is called by every action route)
#   copilot  use the AI Copilot and its saved chats      view     read the agent pages and open the outlet detail drawer
#   run      run the agents                              resolve  log an inspection (Audit page)
#   review   add a customer review (Sentiment page)      users    open the admin dashboard and manage users and roles
#   profile  see and edit your own profile               quote, approve, admin: Freight-edition actions, Admin only
ALL_CAPS = {"copilot", "view", "run", "resolve", "review", "users", "profile", "quote", "approve", "admin"}
ROLE_CAPS = {
    "Admin":           set(ALL_CAPS),
    "Franchise Owner": {"copilot", "view", "run", "resolve", "review", "profile"},
    "Store Manager":   {"copilot", "view", "resolve", "review", "profile"},
    "Staff":           {"copilot", "profile"},
    "Auditor":         {"copilot", "view", "profile"},
}

SCOPED_ROLES = {"Store Manager", "Staff"}       # limited to ONE outlet (user["outlet"]); the other roles see every outlet
MASKED_ROLES = {"Staff", "Auditor"}             # the Copilot hides salary and personal details from these roles
OUTLET_RE = re.compile(r"OUT-\d+", re.I)

def role_of(user):
    role = (user or {}).get("role")
    if role not in ROLE_MENU: raise HTTPException(403, "Your account has no valid role. Ask an Admin to assign one.")
    return role

def scope_for(user):
    """None = every outlet. A scoped role returns its outlet id, or is refused when no outlet is assigned."""
    role = role_of(user)
    if role not in SCOPED_ROLES: return None
    outlet = str((user or {}).get("outlet") or "").strip().upper()
    if not OUTLET_RE.fullmatch(outlet): raise HTTPException(403, f"No outlet is assigned to this {role} account. Ask an Admin to assign one.")
    return outlet

def permission_table():
    """The page access matrix as rows ({"Role": ..., "Copilot": "✓", ...}) for the Admin dashboard and the README, so both always match ROLE_MENU / ROLE_CAPS."""
    cols = [("copilot", "Copilot"), ("workforce", "Workforce"), ("outlets", "Outlets"), ("inventory", "Inventory"), ("marketing", "Marketing"), ("sentiment", "Sentiment"), ("audit", "Audit")]
    yes = lambda b: "✓" if b else "✗"
    return [{"Role": r, **{label: yes(pid in ROLE_MENU[r]) for pid, label in cols}, "Run agents": yes("run" in ROLE_CAPS[r]), "Users": yes("users" in ROLE_CAPS[r])} for r in ROLES]

def caps_of(role): return set(ROLE_CAPS.get(role, ()))
def pages_of(role): return set(ROLE_MENU.get(role, ()))
def masked(role): return role in MASKED_ROLES

def menu_for(role, catalog):
    """The menu entries (id, label, icon) this role may open, in the catalog's order."""
    allowed = pages_of(role)
    return [m for m in catalog if m[0] in allowed]

def need(c, cap):
    """Raise 403 when the role lacks the capability."""
    if cap not in ROLE_CAPS.get(c["role"], ()): raise HTTPException(403, f"Forbidden: the {c['role']} role is not allowed to do this ({cap}).")

def need_page(c, pid):
    if pid not in ALL_PAGES: raise HTTPException(404, "unknown page")
    if pid not in ROLE_MENU.get(c["role"], ()): raise HTTPException(403, f"Forbidden: the {c['role']} role cannot open the {pid} page.")

def guard_outlets(c, *texts):
    """A scoped user may not mention another outlet in a request (page parameters, tab, detail id, question)."""
    s = c.get("scope")
    if not s: return
    for t in texts:
        for m in OUTLET_RE.findall(str(t)):
            if m.upper() != s: raise HTTPException(403, f"Forbidden: {m.upper()} is outside your outlet ({s}).")

def own_outlet(c, outlet):
    """Writes (reviews, inspections): a scoped user may only write for their own outlet."""
    s = c.get("scope")
    if s and str(outlet or "").strip().upper() != s: raise HTTPException(403, f"Forbidden: you can only act on your own outlet ({s}).")
