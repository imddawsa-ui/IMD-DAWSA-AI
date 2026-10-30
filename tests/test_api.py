from fastapi.testclient import TestClient
from app.main import app
from app import main
from app.auth import hash_password, verify_password, issue_access_token, read_access_token


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


def test_password_hashing():
    encoded = hash_password("A-strong-password-123")
    assert verify_password("A-strong-password-123", encoded)
    assert not verify_password("wrong-password", encoded)


def test_signed_tokens(monkeypatch):
    monkeypatch.setattr(main.settings, "auth_secret_key", "test-secret-key-that-is-at-least-32-chars")
    token = issue_access_token(42)
    assert read_access_token(token) == 42
    assert read_access_token(token + "x") is None


def test_register_login_and_user_scoped_history(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "auth_secret_key", "test-secret-key-that-is-at-least-32-chars")
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "auth-test.sqlite3"))
    async def fake_reply(message):
        return "Private answer"
    monkeypatch.setattr(main, "generate_reply", fake_reply)
    with TestClient(app) as client:
        registered = client.post("/api/auth/register", json={
            "email": "person@example.com", "password": "A-strong-password-123", "display_name": "Person"
        })
        assert registered.status_code == 201
        token = registered.json()["access_token"]
        headers = {"Authorization": "Bearer " + token}
        assert client.get("/api/auth/me", headers=headers).status_code == 200
        assert client.post("/api/chat", json={"message": "secret"}, headers=headers).status_code == 200
        assert len(client.get("/api/conversations", headers=headers).json()["items"]) == 1
        assert client.get("/api/conversations").json()["items"] == []
        assert client.post("/api/auth/login", json={
            "email": "person@example.com", "password": "A-strong-password-123"
        }).status_code == 200
        assert client.post("/api/auth/login", json={
            "email": "person@example.com", "password": "wrong-password"
        }).status_code == 401
        assert client.post("/api/auth/register", json={
            "email": "person@example.com", "password": "A-strong-password-123", "display_name": "Person"
        }).status_code == 409



def test_social_profile_posts_follow_likes_comments(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "auth_secret_key", "test-secret-key-that-is-at-least-32-chars")
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "social-test.sqlite3"))
    with TestClient(app) as client:
        def register(email, name):
            response = client.post("/api/auth/register", json={
                "email": email, "password": "A-strong-password-123", "display_name": name
            })
            assert response.status_code == 201
            return {"Authorization": "Bearer " + response.json()["access_token"]}, response.json()["user"]
        alice_headers, alice = register("alice@example.com", "Alice")
        bob_headers, bob = register("bob@example.com", "Bob")
        profile = client.patch("/api/social/profile", headers=alice_headers, json={
            "handle": "alice", "bio": "Hello community"
        })
        assert profile.status_code == 200
        post = client.post("/api/social/posts", headers=alice_headers, json={
            "content": "My first post", "visibility": "public"
        })
        assert post.status_code == 201
        post_id = post.json()["id"]
        assert any(item["id"] == post_id for item in client.get("/api/social/feed").json()["items"])
        assert client.post(f"/api/social/users/{alice['id']}/follow", headers=bob_headers).status_code == 200
        assert client.post(f"/api/social/posts/{post_id}/like", headers=bob_headers).json()["liked"] is True
        comment = client.post(f"/api/social/posts/{post_id}/comments", headers=bob_headers, json={
            "content": "Welcome!"
        })
        assert comment.status_code == 201
        assert len(client.get(f"/api/social/posts/{post_id}/comments").json()["items"]) == 1
        assert client.get(f"/api/social/users/{alice['id']}").json()["user"]["follower_count"] == 1
