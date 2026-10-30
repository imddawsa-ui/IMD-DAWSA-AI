from fastapi.testclient import TestClient
from app.main import app
from app import main

def test_health_and_history_endpoints():
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/conversations").status_code == 200
        assert client.delete("/api/conversations").json() == {"deleted": True}

def test_chat_saves_reply(monkeypatch):
    async def fake_reply(message):
        return "Test response"
    monkeypatch.setattr(main, "generate_reply", fake_reply)
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "Hello"})
        assert response.status_code == 200
        assert response.json()["reply"] == "Test response"
        items = client.get("/api/conversations").json()["items"]
        assert any(item["user_message"] == "Hello" for item in items)
        client.delete("/api/conversations")

def test_blank_chat_is_rejected():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "   "})
        assert response.status_code == 422
