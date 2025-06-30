from fastapi.testclient import TestClient
from main import app

c = TestClient(app)

def test_health():
    r = c.get("/")
    assert r.status_code == 200 and r.json() == {"status": "ok"}

def test_validate_ok():
    assert c.get("/validate", params={"expr": "*/5 * * * *"}).json()["valid"] is True

def test_validate_bad():
    assert c.get("/validate", params={"expr": "bad cron"}).json()["valid"] is False

def test_next_default():
    r = c.get("/next", params={"expr": "*/10 * * * *"})
    assert r.status_code == 200
    assert len(r.json()["next"]) == 5
