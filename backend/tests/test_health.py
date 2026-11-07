from fastapi.testclient import TestClient

from app.main import app


def test_health():
    assert TestClient(app).get("/health").json() == {"status": "ok"}


def test_me_requires_token():
    assert TestClient(app).get("/api/v1/me").status_code == 401


def test_business_routes_require_authentication():
    c = TestClient(app)
    for path in ("/api/v1/ingredients", "/api/v1/inventory/summary", "/api/v1/dishes", "/api/v1/shortages",
                 "/api/v1/reports/summary", "/api/v1/replenishment-suggestions"):
        assert c.get(path).status_code == 401, path
    assert c.post("/api/v1/assistant/messages", json={"message": "hi"}).status_code == 401
