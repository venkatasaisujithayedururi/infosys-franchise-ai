"""Test setup for the FranchiseOps server: a throw-away database, no background worker, seeded data and one agent cycle.
Requires the Milestone 2 packages (pip install fastapi pandas numpy scikit-learn scipy vaderSentiment httpx python-multipart pytest)."""
import os, sys, tempfile
import pytest

os.environ.update(APP_KIND="Franchise", NO_WORKER="1", RATE_LIMIT_OFF="1", PERSIST_DIR=tempfile.mkdtemp(prefix="m2_rbac_"))
APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
sys.path.insert(0, os.path.abspath(APP))

@pytest.fixture(scope="session")
def server():
    from fastapi.testclient import TestClient
    import server as S, live_engine as LE
    with TestClient(S.app) as client:
        S.dom.bootstrap(); LE.run_cycle(S.dom, "manual", "")
        S.client = client
        yield S

@pytest.fixture
def login(server, monkeypatch):
    """login(role, outlet=None) makes server.user_of return that account for the next requests, and returns the test client."""
    def _login(role, outlet=None, email=None):
        user = {"id": 1, "email": email or f"{role.lower().replace(' ', '_')}@test.local", "username": role.replace(" ", "_"), "role": role, "outlet": outlet}
        monkeypatch.setattr(server, "user_of", lambda request: user)
        return server.client
    return _login
