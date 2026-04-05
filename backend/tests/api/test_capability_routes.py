from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_capability_routes_are_registered():
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200

    paths = response.json()["paths"]
    assert "/api/v1/quick-cleaning/capabilities" in paths
    assert "/api/v1/chart-calculations/capabilities" in paths
    assert "/api/v1/theme-palettes/capabilities" in paths
    assert "/api/v1/quick-reports/capabilities" in paths
