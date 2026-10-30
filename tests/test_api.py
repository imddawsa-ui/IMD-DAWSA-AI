import time

import pyotp
from fastapi.testclient import TestClient

from app.main import app
from app import main, account_security
from app.auth import hash_password, verify_password, issue_access_token, read_access_token


def configure_email(monkeypatch):
    main._rate_buckets.clear()
    monkeypatch.setattr(main.settings, "auth_secret_key", "test-secret-key-that-is-at-least-32-chars")
    monkeypatch.setattr(main.settings, "resend_api_key", "re_test_key")
    monkeypatch.setattr(main.settings, "email_from", "IMD DAWSA AI <verify@example.com>")
    monkeypatch.setattr(main.settings, "api_public_url", "https://api.example.com")
    sent_tokens = []

    async def fake_send(email, token):
        sent_tokens.append(token)
        return True

    monkeypatch.setattr(main, "send_verification_email", fake_send)
    monkeypatch.setattr(account_security, "send_verification_email", fake_send)
    return sent_tokens


def register_verified(client, sent_tokens, email, name):
    response = client.post("/api/auth/register", json={
        "email": email, "password": "A-strong-password-123", "display_name": name
    })
    assert response.status_code == 201, response.text
    user = response.json()["user"]
    token = sent_tokens.pop(0)
    # A mail scanner opening the GET link must not consume the one-time token.
    assert client.get("/api/auth/verify-email", params={"token": token}).status_code == 200
    verified = client.post("/api/auth/verify-email", json={"token": token})
    assert verified.status_code == 200
    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 400
    login = client.post("/api/auth/login", json={
        "email": email, "password": "A-strong-password-123"
    })
    assert login.status_code == 200
    return {"Authorization": "Bearer " + login.json()["access_token"]}, user


def test_cors_allows_social_profile_patch(monkeypatch):
    with TestClient(app) as client:
        response = client.options(
            "/api/social/profile",
            headers={
                "Origin": "http://localhost:8000",
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:8000"
        assert "PATCH" in response.headers["access-control-allow-methods"]


def test_health_and_history_endpoints():
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/conversations").status_code == 200
        assert client.delete("/api/conversations").json() == {"deleted": True}


def test_chat_saves_reply(monkeypatch):
    async def fake_reply(message, history=None):
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
        assert client.post("/api/chat", json={"message": "   "}).status_code == 422


def test_llm_context_preserves_recent_turn_order():
    from app.llm import _build_messages

    history = [
        {"user_message": "First question", "assistant_message": "First answer"},
        {"user_message": "Second question", "assistant_message": "Second answer"},
    ]
    messages = _build_messages("Third question", history)
    assert [item["role"] for item in messages] == ["system", "user", "assistant", "user", "assistant", "user"]
    assert messages[1]["content"] == "First question"
    assert messages[2]["content"] == "First answer"
    assert messages[-1]["content"] == "Third question"


def test_password_hashing():
    encoded = hash_password("A-strong-password-123")
    assert verify_password("A-strong-password-123", encoded)
    assert not verify_password("wrong-password", encoded)


def test_signed_tokens(monkeypatch):
    monkeypatch.setattr(main.settings, "auth_secret_key", "test-secret-key-that-is-at-least-32-chars")
    token = issue_access_token(42)
    assert read_access_token(token) == 42
    assert read_access_token(token + "x") is None


def test_register_requires_email_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "auth_secret_key", "test-secret-key-that-is-at-least-32-chars")
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "no-mail.sqlite3"))
    monkeypatch.setattr(main.settings, "resend_api_key", "")
    with TestClient(app) as client:
        response = client.post("/api/auth/register", json={
            "email": "person@example.com", "password": "A-strong-password-123", "display_name": "Person"
        })
        assert response.status_code == 503


def test_register_verify_login_and_user_scoped_history(monkeypatch, tmp_path):
    sent = configure_email(monkeypatch)
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "auth-test.sqlite3"))

    async def fake_reply(message, history=None):
        return "Private answer"
    monkeypatch.setattr(main, "generate_reply", fake_reply)
    with TestClient(app) as client:
        unverified = client.post("/api/auth/register", json={
            "email": "person@example.com", "password": "A-strong-password-123", "display_name": "Person"
        })
        assert unverified.status_code == 201
        assert "access_token" not in unverified.json()
        assert client.post("/api/auth/login", json={
            "email": "person@example.com", "password": "A-strong-password-123"
        }).status_code == 403

        token = sent.pop(0)
        assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 200
        login = client.post("/api/auth/login", json={
            "email": "person@example.com", "password": "A-strong-password-123"
        })
        assert login.status_code == 200
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        assert client.get("/api/auth/me", headers=headers).status_code == 200
        assert client.post("/api/chat", json={"message": "secret"}, headers=headers).status_code == 200
        assert len(client.get("/api/conversations", headers=headers).json()["items"]) == 1
        assert client.get("/api/conversations").status_code == 401
        assert client.post("/api/auth/login", json={
            "email": "person@example.com", "password": "wrong-password"
        }).status_code == 401
        assert client.post("/api/auth/register", json={
            "email": "person@example.com", "password": "A-strong-password-123", "display_name": "Person"
        }).status_code == 409


def test_resend_verification_replaces_old_token(monkeypatch, tmp_path):
    sent = configure_email(monkeypatch)
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "resend-test.sqlite3"))
    with TestClient(app) as client:
        registered = client.post("/api/auth/register", json={
            "email": "resend@example.com", "password": "A-strong-password-123", "display_name": "Resend"
        })
        assert registered.status_code == 201
        original_token = sent[0]
        resent = client.post("/api/auth/resend-verification", params={"email": "resend@example.com"})
        assert resent.status_code == 200
        assert len(sent) == 2
        assert client.post("/api/auth/verify-email", json={"token": original_token}).status_code == 400
        assert client.post("/api/auth/verify-email", json={"token": sent[1]}).status_code == 200
        unknown = client.post("/api/auth/resend-verification", params={"email": "unknown@example.com"})
        assert unknown.status_code == 200
        assert len(sent) == 2


def test_totp_setup_login_and_single_use_recovery_codes(monkeypatch, tmp_path):
    sent = configure_email(monkeypatch)
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "totp-test.sqlite3"))
    with TestClient(app) as client:
        headers, user = register_verified(client, sent, "mfa@example.com", "MFA User")

        setup = client.post("/api/auth/2fa/setup", headers=headers)
        assert setup.status_code == 200
        assert setup.json()["qr_code_png_base64"]
        secret = setup.json()["secret"]
        first_code = pyotp.TOTP(secret).now()
        enabled = client.post("/api/auth/2fa/enable", headers=headers, json={"code": first_code})
        assert enabled.status_code == 200
        recovery = enabled.json()["recovery_codes"]
        assert len(recovery) == 10

        login = client.post("/api/auth/login", json={
            "email": "mfa@example.com", "password": "A-strong-password-123"
        })
        assert login.status_code == 200
        assert login.json()["requires_2fa"] is True
        assert "access_token" not in login.json()

        # Use the next time-step code so it is not the same code used to activate MFA.
        next_code = pyotp.TOTP(secret).at((int(time.time()) // 30 + 1) * 30)
        wrong_code = str((int(next_code) + 1) % 1000000).zfill(6)
        rejected = client.post("/api/auth/2fa/login", json={
            "challenge_token": login.json()["challenge_token"], "code": wrong_code
        })
        assert rejected.status_code == 401
        # A typo must not burn the challenge; a valid code can still complete this sign-in.
        completed = client.post("/api/auth/2fa/login", json={
            "challenge_token": login.json()["challenge_token"], "code": next_code
        })
        assert completed.status_code == 200
        assert completed.json()["access_token"]
        replay = client.post("/api/auth/2fa/login", json={
            "challenge_token": login.json()["challenge_token"], "code": next_code
        })
        assert replay.status_code == 401

        second_login = client.post("/api/auth/login", json={
            "email": "mfa@example.com", "password": "A-strong-password-123"
        })
        recovery_login = client.post("/api/auth/2fa/login", json={
            "challenge_token": second_login.json()["challenge_token"], "code": recovery[0]
        })
        assert recovery_login.status_code == 200

        third_login = client.post("/api/auth/login", json={
            "email": "mfa@example.com", "password": "A-strong-password-123"
        })
        reused = client.post("/api/auth/2fa/login", json={
            "challenge_token": third_login.json()["challenge_token"], "code": recovery[0]
        })
        assert reused.status_code == 401

        disabled = client.post("/api/auth/2fa/disable", headers=headers, json={
            "password": "A-strong-password-123", "code": recovery[1]
        })
        assert disabled.status_code == 200
        normal_login = client.post("/api/auth/login", json={
            "email": "mfa@example.com", "password": "A-strong-password-123"
        })
        assert normal_login.status_code == 200
        assert not normal_login.json().get("requires_2fa", False)


def test_social_user_discovery_requires_query_and_returns_verified_profiles(monkeypatch, tmp_path):
    sent = configure_email(monkeypatch)
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "user-discovery-test.sqlite3"))
    with TestClient(app) as client:
        alice_headers, alice = register_verified(client, sent, "discover-alice@example.com", "Alice")
        bob_headers, bob = register_verified(client, sent, "discover-bob@example.com", "Bob Builder")
        unverified = client.post("/api/auth/register", json={
            "email": "discover-hidden@example.com",
            "password": "A-strong-password-123",
            "display_name": "Hidden Bob",
        })
        assert unverified.status_code == 201

        assert client.get("/api/social/users", params={"q": "B"}).status_code == 422
        results = client.get("/api/social/users", params={"q": "Bob"}, headers=alice_headers)
        assert results.status_code == 200
        items = results.json()["items"]
        assert [item["id"] for item in items] == [bob["id"]]
        assert items[0]["is_following"] is False

        assert client.post(f"/api/social/users/{bob['id']}/follow", headers=alice_headers).status_code == 200
        followed = client.get("/api/social/users", params={"q": "Bob"}, headers=alice_headers).json()["items"]
        assert followed[0]["is_following"] is True
        assert all(item["id"] != alice["id"] for item in followed)


def test_social_profile_posts_follow_likes_comments(monkeypatch, tmp_path):
    sent = configure_email(monkeypatch)
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "social-test.sqlite3"))
    with TestClient(app) as client:
        alice_headers, alice = register_verified(client, sent, "alice@example.com", "Alice")
        bob_headers, bob = register_verified(client, sent, "bob@example.com", "Bob")
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


def test_marketplace_listing_search_and_enquiries(monkeypatch, tmp_path):
    sent = configure_email(monkeypatch)
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "market-test.sqlite3"))
    with TestClient(app) as client:
        seller_headers, seller = register_verified(client, sent, "seller@example.com", "Seller")
        buyer_headers, buyer = register_verified(client, sent, "buyer@example.com", "Buyer")
        listing = client.post("/api/marketplace/listings", headers=seller_headers, json={
            "title": "Used laptop", "description": "Good condition", "category": "electronics",
            "price_amount": 250, "currency": "USD",
        })
        assert listing.status_code == 201
        listing_id = listing.json()["id"]
        search = client.get("/api/marketplace/listings", params={"q": "laptop", "category": "electronics"})
        assert search.status_code == 200
        assert search.json()["items"][0]["seller_id"] == seller["id"]
        enquiry = client.post(
            f"/api/marketplace/listings/{listing_id}/enquiries", headers=buyer_headers,
            json={"message": "Is this still available?"},
        )
        assert enquiry.status_code == 201
        assert client.get("/api/marketplace/my-enquiries", headers=buyer_headers).json()["items"][0]["listing_id"] == listing_id
        assert client.post(
            f"/api/marketplace/listings/{listing_id}/enquiries", headers=seller_headers,
            json={"message": "My own item"},
        ).status_code == 400
        assert client.post("/api/marketplace/listings", json={"title": "No auth"}).status_code == 401


def test_marketplace_seller_dashboard_is_scoped_to_own_listings(monkeypatch, tmp_path):
    sent = configure_email(monkeypatch)
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "seller-dashboard-test.sqlite3"))
    with TestClient(app) as client:
        seller_headers, seller = register_verified(client, sent, "dashboard-seller@example.com", "Seller")
        other_seller_headers, _ = register_verified(client, sent, "dashboard-other@example.com", "Other Seller")
        buyer_headers, buyer = register_verified(client, sent, "dashboard-buyer@example.com", "Buyer")

        own_listing = client.post("/api/marketplace/listings", headers=seller_headers, json={
            "title": "Seller camera", "description": "Camera", "category": "electronics"
        }).json()
        other_listing = client.post("/api/marketplace/listings", headers=other_seller_headers, json={
            "title": "Other camera", "description": "Camera", "category": "electronics"
        }).json()
        enquiry = client.post(
            f"/api/marketplace/listings/{own_listing['id']}/enquiries",
            headers=buyer_headers, json={"message": "Can I collect it today?"},
        )
        assert enquiry.status_code == 201

        own_items = client.get("/api/marketplace/my-listings", headers=seller_headers).json()["items"]
        assert [item["id"] for item in own_items] == [own_listing["id"]]
        assert own_items[0]["enquiry_count"] == 1

        inbox = client.get("/api/marketplace/seller-enquiries", headers=seller_headers).json()["items"]
        assert len(inbox) == 1
        assert inbox[0]["listing_id"] == own_listing["id"]
        assert inbox[0]["buyer_id"] == buyer["id"]
        assert inbox[0]["listing_title"] == "Seller camera"

        assert client.get("/api/marketplace/my-listings", headers=buyer_headers).json()["items"] == []
        assert client.get("/api/marketplace/seller-enquiries", headers=buyer_headers).json()["items"] == []
        assert client.get("/api/marketplace/my-listings").status_code == 401
        assert client.get("/api/marketplace/seller-enquiries").status_code == 401


def test_notifications_cover_social_marketplace_and_enforce_owner_scope(monkeypatch, tmp_path):
    sent = configure_email(monkeypatch)
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "notifications-test.sqlite3"))
    with TestClient(app) as client:
        alice_headers, alice = register_verified(client, sent, "notify-alice@example.com", "Alice")
        bob_headers, bob = register_verified(client, sent, "notify-bob@example.com", "Bob")
        stranger_headers, _ = register_verified(client, sent, "notify-stranger@example.com", "Stranger")

        post = client.post("/api/social/posts", headers=bob_headers, json={
            "content": "A public update", "visibility": "public"
        }).json()
        assert client.post(f"/api/social/users/{bob['id']}/follow", headers=alice_headers).status_code == 200
        assert client.post(f"/api/social/posts/{post['id']}/like", headers=alice_headers).json()["liked"] is True
        assert client.post(f"/api/social/posts/{post['id']}/comments", headers=alice_headers, json={
            "content": "Nice update"
        }).status_code == 201
        assert client.post(f"/api/social/messages/{bob['id']}", headers=alice_headers, json={
            "content": "Hello Bob"
        }).status_code == 201

        listing = client.post("/api/marketplace/listings", headers=bob_headers, json={
            "title": "Bob's service", "description": "Available now", "category": "services"
        }).json()
        assert client.post(f"/api/marketplace/listings/{listing['id']}/enquiries", headers=alice_headers, json={
            "message": "Please share more details"
        }).status_code == 201

        notifications = client.get("/api/notifications", headers=bob_headers)
        assert notifications.status_code == 200
        items = notifications.json()["items"]
        assert {item["kind"] for item in items} == {
            "follow", "like", "comment", "message", "marketplace_enquiry"
        }
        first_id = items[0]["id"]
        assert client.post(f"/api/notifications/{first_id}/read", headers=stranger_headers).status_code == 404
        assert client.post(f"/api/notifications/{first_id}/read", headers=bob_headers).json()["updated"] is True
        refreshed = client.get("/api/notifications", headers=bob_headers).json()["items"]
        assert next(item for item in refreshed if item["id"] == first_id)["read_at"] is not None
        assert client.post("/api/notifications/read-all", headers=bob_headers).status_code == 200
        assert all(item["read_at"] is not None for item in client.get("/api/notifications", headers=bob_headers).json()["items"])
        assert client.get("/api/notifications", headers=alice_headers).json()["items"] == []
        assert client.get("/api/notifications").status_code == 401


def test_private_direct_messages_are_scoped_to_participants(monkeypatch, tmp_path):
    sent = configure_email(monkeypatch)
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "messages-test.sqlite3"))
    with TestClient(app) as client:
        alice_headers, alice = register_verified(client, sent, "dm-alice@example.com", "Alice")
        bob_headers, bob = register_verified(client, sent, "dm-bob@example.com", "Bob")
        stranger_headers, _ = register_verified(client, sent, "dm-stranger@example.com", "Stranger")
        sent_message = client.post(
            f"/api/social/messages/{bob['id']}", headers=alice_headers,
            json={"content": "A private hello"},
        )
        assert sent_message.status_code == 201
        thread = client.get(f"/api/social/messages/{alice['id']}", headers=bob_headers)
        assert thread.status_code == 200
        assert thread.json()["items"][0]["content"] == "A private hello"
        assert client.get(f"/api/social/messages/{alice['id']}", headers=stranger_headers).json()["items"] == []
        assert client.post(
            f"/api/social/messages/{alice['id']}", headers=alice_headers,
            json={"content": "self"},
        ).status_code == 400
        assert client.get(f"/api/social/messages/{alice['id']}").status_code == 401


def test_security_headers_and_authenticated_chat_requirement(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "auth_secret_key", "test-secret-key-that-is-at-least-32-chars")
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "security-test.sqlite3"))
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.headers["x-content-type-options"] == "nosniff"
        assert health.headers["x-frame-options"] == "DENY"
        assert client.post("/api/chat", json={"message": "private"}).status_code == 401
        assert client.get("/api/conversations").status_code == 401


def test_private_post_comments_are_not_visible_to_other_users(monkeypatch, tmp_path):
    sent = configure_email(monkeypatch)
    monkeypatch.setattr(main.settings, "database_path", str(tmp_path / "privacy-test.sqlite3"))
    with TestClient(app) as client:
        owner, _ = register_verified(client, sent, "owner@example.com", "Owner")
        stranger, _ = register_verified(client, sent, "stranger@example.com", "Stranger")
        post = client.post("/api/social/posts", headers=owner, json={
            "content": "Private note", "visibility": "private"
        }).json()
        post_id = post["id"]
        assert client.get(f"/api/social/posts/{post_id}/comments", headers=stranger).status_code == 404
        assert client.post(f"/api/social/posts/{post_id}/comments", headers=stranger, json={
            "content": "Can I see this?"
        }).status_code == 404
        assert client.get(f"/api/social/posts/{post_id}/comments", headers=owner).status_code == 200


def test_translation_endpoints_are_explicitly_disabled_without_provider(monkeypatch):
    monkeypatch.setattr(main.settings, "translation_api_url", "")
    with TestClient(app) as client:
        catalog = client.get("/api/i18n/languages")
        assert catalog.status_code == 200
        assert catalog.json() == {"enabled": False, "provider": None, "languages": []}
        response = client.post("/api/i18n/translate", json={
            "text": "Hello world", "source": "auto", "target": "ar"
        })
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()


def test_translation_request_validates_language_codes():
    with TestClient(app) as client:
        response = client.post("/api/i18n/translate", json={
            "text": "Hello", "source": "auto", "target": "not a language!"
        })
        assert response.status_code == 422
