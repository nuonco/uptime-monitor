from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_livez():
    response = client.get("/livez")
    assert response.status_code == 200
    assert response.text == "ok"
