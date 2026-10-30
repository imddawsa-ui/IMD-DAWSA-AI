import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .auth import hash_password, verify_password, issue_access_token, read_access_token
from .config import settings
from .database import (
    initialize, connect, list_conversations, clear_conversations,
    create_user, get_user, get_user_by_email, save_conversation,
)
from .llm import generate_reply, ModelUnavailable
from .account_security import (
    router as account_security_router,
    create_verification_token,
    send_verification_email,
    _new_challenge,
)

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield


app = FastAPI(title=settings.app_name, version="0.6.0", lifespan=lifespan)
app.include_router(account_security_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Token", "Authorization"],
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Lightweight per-process abuse controls. Use a shared gateway limiter for multi-worker production.
_rate_buckets = defaultdict(deque)
_RATE_POLICIES = {
    "/api/auth/login": (10, 60),
    "/api/auth/register": (5, 60),
    "/api/auth/resend-verification": (3, 300),
    "/api/auth/2fa/login": (8, 300),
    "/api/chat": (30, 60),
}


@app.middleware("http")
async def security_middleware(request, call_next):
    path = request.url.path
    policy = _RATE_POLICIES.get(path) if request.method == "POST" else None
    if policy:
        limit, window = policy
        client_ip = request.client.host if request.client else "unknown"
        key = (client_ip, path)
        now = time.monotonic()
        bucket = _rate_buckets[key]
        while bucket and now - bucket[0] >= window:
            bucket.popleft()
        if len(bucket) >= limit:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again later."},
                                headers={"Retry-After": str(window)})
        bucket.append(now)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def create_notification(user_id: int, actor_id: int | None, kind: str,
                        object_type: str | None, object_id: int | None, message: str):
    if actor_id is not None and int(actor_id) == int(user_id):
        return
    with connect() as db:
        db.execute(
            "INSERT INTO notifications (user_id, actor_id, kind, object_type, object_id, message) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, actor_id, kind, object_type, object_id, message),
        )


def can_view_post(db, post, viewer_id):
    if not post:
        return False
    if post["visibility"] == "public":
        return True
    if viewer_id is None:
        return False
    if post["user_id"] == viewer_id:
        return True
    if post["visibility"] == "followers":
        return bool(db.execute(
            "SELECT 1 FROM follows WHERE follower_id = ? AND following_id = ?",
            (viewer_id, post["user_id"]),
        ).fetchone())
    return False


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=2, max_length=60)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=60)
    handle: str | None = Field(default=None, min_length=3, max_length=30)
    bio: str | None = Field(default=None, max_length=280)


class PostCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    visibility: str = Field(default="public", pattern="^(public|followers|private)$")


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

class DirectMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

class ListingCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=4000)
    category: str = Field(default="general", min_length=2, max_length=50)
    price_amount: float | None = Field(default=None, gt=0, le=1000000000)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")


class MarketplaceEnquiryCreate(BaseModel):
    message: str = Field(min_length=5, max_length=2000)


def check_access(token: str | None):
    if settings.api_access_token and not secrets.compare_digest(token or "", settings.api_access_token):
        raise HTTPException(status_code=401, detail="Unauthorized")


def current_user(authorization: str | None):
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    user_id = read_access_token(token)
    user = get_user(user_id) if user_id else None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


def require_auth_configuration():
    if len(settings.auth_secret_key) < 32:
        raise HTTPException(status_code=503, detail="Account authentication is disabled. Configure AUTH_SECRET_KEY with a unique random value of at least 32 characters.")


@app.get("/")
async def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "version": "0.6.0"}


@app.get("/api/readiness")
async def readiness():
    if settings.ai_provider == "openai_compatible":
        configured = bool(settings.cloud_api_key.strip())
        return {
            "ready": configured,
            "provider": settings.ai_provider,
            "model": settings.cloud_model,
            "accounts_enabled": len(settings.auth_secret_key) >= 32,
            **({} if configured else {"detail": "Cloud API key is not configured"}),
        }
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            response.raise_for_status()
        return {
            "ready": True, "provider": "ollama", "model": settings.ollama_model,
            "accounts_enabled": len(settings.auth_secret_key) >= 32,
        }
    except httpx.HTTPError:
        return {
            "ready": False, "provider": "ollama", "model": settings.ollama_model,
            "accounts_enabled": len(settings.auth_secret_key) >= 32,
            "detail": "Ollama is not reachable",
        }


@app.post("/api/auth/register", status_code=201)
async def register(request: RegisterRequest):
    require_auth_configuration()
    if not settings.resend_api_key or not settings.email_from or not settings.api_public_url.startswith("https://"):
        raise HTTPException(status_code=503, detail="Email verification is not configured. Set RESEND_API_KEY, EMAIL_FROM and HTTPS API_PUBLIC_URL.")
    email = request.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if len(request.password) < 10:
        raise HTTPException(status_code=422, detail="Password must contain at least 10 characters")
    if not request.display_name.strip():
        raise HTTPException(status_code=422, detail="Display name cannot be blank")
    try:
        user = create_user(email, hash_password(request.password), request.display_name)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists") from exc
    token = create_verification_token(user["id"])
    try:
        sent = await send_verification_email(email, token)
    except httpx.HTTPError:
        sent = False
    if not sent:
        raise HTTPException(status_code=503, detail="Account created, but verification email delivery failed. Use resend-verification after fixing email settings.")
    return {"user": user, "email_verification_required": True, "message": "Check your inbox and verify your email before signing in."}


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    require_auth_configuration()
    user_record = get_user_by_email(request.email)
    if not user_record or not verify_password(request.password, user_record["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user = get_user(user_record["id"])
    if not user or not user.get("email_verified"):
        raise HTTPException(status_code=403, detail="Verify your email address before signing in")
    if user.get("totp_enabled"):
        return {"requires_2fa": True, "challenge_token": _new_challenge(user["id"]), "token_type": "2fa"}
    return {"user": user, "access_token": issue_access_token(user["id"]), "token_type": "bearer"}


@app.get("/api/auth/me")
async def me(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"user": user}


@app.get("/api/social/feed")
async def social_feed(
    limit: int = 30,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    user_id = user["id"] if user else -1
    with connect() as db:
        rows = db.execute("""
            SELECT p.id, p.content, p.visibility, p.created_at, u.id AS author_id,
                   u.display_name, u.handle,
                   (SELECT COUNT(*) FROM post_likes l WHERE l.post_id = p.id) AS like_count,
                   (SELECT COUNT(*) FROM post_comments c WHERE c.post_id = p.id) AS comment_count,
                   EXISTS(SELECT 1 FROM post_likes l WHERE l.post_id = p.id AND l.user_id = ?) AS liked_by_me
            FROM posts p JOIN users u ON u.id = p.user_id
            WHERE p.visibility = 'public'
               OR (p.visibility = 'followers' AND EXISTS(
                    SELECT 1 FROM follows f WHERE f.follower_id = ? AND f.following_id = p.user_id
               ))
               OR (p.user_id = ?)
            ORDER BY p.id DESC LIMIT ?
        """, (user_id, user_id, user_id, max(1, min(limit, 100)))).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/social/users")
async def search_social_users(
    q: str = "",
    limit: int = 20,
    authorization: str | None = Header(default=None),
):
    query_text = q.strip()
    if len(query_text) < 2:
        raise HTTPException(status_code=422, detail="Search query must contain at least 2 characters")
    user = current_user(authorization)
    viewer_id = user["id"] if user else None
    pattern = "%" + query_text.replace("%", "\\%").replace("_", "\\_") + "%"
    with connect() as db:
        rows = db.execute("""
            SELECT u.id, u.display_name, u.handle, u.bio,
                   (SELECT COUNT(*) FROM follows f WHERE f.following_id = u.id) AS follower_count,
                   EXISTS(SELECT 1 FROM follows f WHERE f.follower_id = ? AND f.following_id = u.id) AS is_following
            FROM users u
            WHERE u.email_verified = 1
              AND u.id IS NOT ?
              AND (u.display_name LIKE ? ESCAPE '\\' OR u.handle LIKE ? ESCAPE '\\')
            ORDER BY follower_count DESC, u.id DESC
            LIMIT ?
        """, (viewer_id, viewer_id, pattern, pattern, max(1, min(limit, 30)))).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["is_following"] = bool(item["is_following"])
        items.append(item)
    return {"items": items}


@app.get("/api/social/users/{user_id}")
async def social_profile(user_id: int):
    with connect() as db:
        row = db.execute("""
            SELECT u.id, u.display_name, u.handle, u.bio, u.created_at,
                   (SELECT COUNT(*) FROM follows f WHERE f.following_id = u.id) AS follower_count,
                   (SELECT COUNT(*) FROM follows f WHERE f.follower_id = u.id) AS following_count,
                   (SELECT COUNT(*) FROM posts p WHERE p.user_id = u.id AND p.visibility = 'public') AS post_count
            FROM users u WHERE u.id = ?
        """, (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": dict(row)}


@app.patch("/api/social/profile")
async def update_social_profile(
    request: ProfileUpdate,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        return {"user": get_user(user["id"])}
    if "handle" in updates:
        handle = updates["handle"].strip().lower()
        if not re.fullmatch(r"[a-z0-9_]{3,30}", handle):
            raise HTTPException(status_code=422, detail="Handle must use 3-30 letters, numbers or underscores")
        updates["handle"] = handle
    if "display_name" in updates and updates["display_name"]:
        updates["display_name"] = updates["display_name"].strip()
    if "bio" in updates and updates["bio"] is not None:
        updates["bio"] = updates["bio"].strip()
    try:
        with connect() as db:
            for field, value in updates.items():
                db.execute("UPDATE users SET " + field + " = ? WHERE id = ?", (value, user["id"]))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="That handle is already in use") from exc
    return {"user": get_user(user["id"])}


@app.post("/api/social/posts", status_code=201)
async def create_social_post(
    request: PostCreate,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Post cannot be blank")
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO posts (user_id, content, visibility) VALUES (?, ?, ?)",
            (user["id"], content, request.visibility),
        )
        post_id = cursor.lastrowid
    return {"id": post_id, "content": content, "visibility": request.visibility, "author_id": user["id"]}


@app.post("/api/social/users/{user_id}/follow")
async def follow_social_user(user_id: int, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")
    with connect() as db:
        if not db.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        cursor = db.execute(
            "INSERT OR IGNORE INTO follows (follower_id, following_id) VALUES (?, ?)",
            (user["id"], user_id),
        )
    if cursor.rowcount == 1:
        create_notification(user_id, user["id"], "follow", "user", user["id"], "بدأ بمتابعتك")
    return {"following": True, "created": cursor.rowcount == 1}


@app.delete("/api/social/users/{user_id}/follow")
async def unfollow_social_user(user_id: int, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    with connect() as db:
        db.execute("DELETE FROM follows WHERE follower_id = ? AND following_id = ?", (user["id"], user_id))
    return {"following": False}


@app.post("/api/social/posts/{post_id}/like")
async def toggle_post_like(post_id: int, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    with connect() as db:
        post = db.execute("SELECT id, user_id, visibility FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not post or not can_view_post(db, post, user["id"]):
            raise HTTPException(status_code=404, detail="Post not found")
        existing = db.execute(
            "SELECT 1 FROM post_likes WHERE user_id = ? AND post_id = ?", (user["id"], post_id)
        ).fetchone()
        if existing:
            db.execute("DELETE FROM post_likes WHERE user_id = ? AND post_id = ?", (user["id"], post_id))
            liked = False
        else:
            db.execute("INSERT INTO post_likes (user_id, post_id) VALUES (?, ?)", (user["id"], post_id))
            liked = True
        count = db.execute("SELECT COUNT(*) FROM post_likes WHERE post_id = ?", (post_id,)).fetchone()[0]
        owner_id = int(post["user_id"])
    if liked:
        create_notification(owner_id, user["id"], "like", "post", post_id, "أعجب بمنشورك")
    return {"liked": liked, "like_count": count}


@app.post("/api/social/posts/{post_id}/comments", status_code=201)
async def add_post_comment(
    post_id: int,
    request: CommentCreate,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Comment cannot be blank")
    with connect() as db:
        post = db.execute("SELECT id, user_id, visibility FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        if not can_view_post(db, post, user["id"]):
            raise HTTPException(status_code=404, detail="Post not found")
        cursor = db.execute(
            "INSERT INTO post_comments (post_id, user_id, content) VALUES (?, ?, ?)",
            (post_id, user["id"], content),
        )
        comment_id = cursor.lastrowid
        owner_id = int(post["user_id"])
    create_notification(owner_id, user["id"], "comment", "post", post_id, "علّق على منشورك")
    return {"id": comment_id, "post_id": post_id, "user_id": user["id"], "content": content}


@app.get("/api/social/posts/{post_id}/comments")
async def list_post_comments(
    post_id: int, limit: int = 50, authorization: str | None = Header(default=None)
):
    user = current_user(authorization)
    with connect() as db:
        post = db.execute("SELECT id, user_id, visibility FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not post or not can_view_post(db, post, user["id"] if user else None):
            raise HTTPException(status_code=404, detail="Post not found")
        rows = db.execute("""
            SELECT c.id, c.content, c.created_at, u.id AS author_id, u.display_name, u.handle
            FROM post_comments c JOIN users u ON u.id = c.user_id
            WHERE c.post_id = ? ORDER BY c.id ASC LIMIT ?
        """, (post_id, max(1, min(limit, 100)))).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/notifications")
async def list_notifications(
    limit: int = 50,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    with connect() as db:
        rows = db.execute("""
            SELECT n.id, n.kind, n.object_type, n.object_id, n.message, n.read_at, n.created_at,
                   n.actor_id, u.display_name AS actor_name, u.handle AS actor_handle
            FROM notifications n
            LEFT JOIN users u ON u.id = n.actor_id
            WHERE n.user_id = ?
            ORDER BY n.id DESC LIMIT ?
        """, (user["id"], max(1, min(limit, 100)))).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    with connect() as db:
        cursor = db.execute(
            "UPDATE notifications SET read_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ? AND read_at IS NULL",
            (notification_id, user["id"]),
        )
        exists = db.execute(
            "SELECT 1 FROM notifications WHERE id = ? AND user_id = ?",
            (notification_id, user["id"]),
        ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"read": True, "updated": cursor.rowcount == 1}


@app.post("/api/notifications/read-all")
async def mark_all_notifications_read(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    with connect() as db:
        cursor = db.execute(
            "UPDATE notifications SET read_at = CURRENT_TIMESTAMP WHERE user_id = ? AND read_at IS NULL",
            (user["id"],),
        )
    return {"read": True, "updated": cursor.rowcount}


@app.get("/api/marketplace/listings")
async def marketplace_listings(
    q: str = "",
    category: str = "",
    limit: int = 30,
):
    query = "%" + q.strip().replace("%", "\\%").replace("_", "\\_") + "%"
    with connect() as db:
        rows = db.execute("""
            SELECT l.id, l.title, l.description, l.category, l.price_amount, l.currency,
                   l.created_at, u.id AS seller_id, u.display_name AS seller_name, u.handle AS seller_handle
            FROM marketplace_listings l JOIN users u ON u.id = l.seller_id
            WHERE l.status = 'active' AND u.email_verified = 1
              AND (? = '' OR l.title LIKE ? ESCAPE '\\' OR l.description LIKE ? ESCAPE '\\')
              AND (? = '' OR l.category = ?)
            ORDER BY l.id DESC LIMIT ?
        """, (q.strip(), query, query, category.strip().lower(), category.strip().lower(), max(1, min(limit, 100)))).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/marketplace/listings", status_code=201)
async def create_marketplace_listing(
    request: ListingCreate,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    with connect() as db:
        cursor = db.execute("""
            INSERT INTO marketplace_listings
                (seller_id, title, description, category, price_amount, currency)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user["id"], request.title.strip(), request.description.strip(),
              request.category.strip().lower(), request.price_amount, request.currency))
        listing_id = cursor.lastrowid
    return {"id": listing_id, "title": request.title.strip(), "status": "active"}


@app.get("/api/marketplace/listings/{listing_id}")
async def marketplace_listing(listing_id: int):
    with connect() as db:
        row = db.execute("""
            SELECT l.id, l.title, l.description, l.category, l.price_amount, l.currency,
                   l.created_at, u.id AS seller_id, u.display_name AS seller_name, u.handle AS seller_handle
            FROM marketplace_listings l JOIN users u ON u.id = l.seller_id
            WHERE l.id = ? AND l.status = 'active' AND u.email_verified = 1
        """, (listing_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"listing": dict(row)}


@app.post("/api/marketplace/listings/{listing_id}/enquiries", status_code=201)
async def create_marketplace_enquiry(
    listing_id: int,
    request: MarketplaceEnquiryCreate,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    with connect() as db:
        listing = db.execute(
            "SELECT seller_id FROM marketplace_listings WHERE id = ? AND status = 'active'",
            (listing_id,),
        ).fetchone()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        if int(listing["seller_id"]) == int(user["id"]):
            raise HTTPException(status_code=400, detail="You cannot enquire about your own listing")
        cursor = db.execute(
            "INSERT INTO marketplace_enquiries (listing_id, buyer_id, message) VALUES (?, ?, ?)",
            (listing_id, user["id"], request.message.strip()),
        )
        seller_id = int(listing["seller_id"])
    create_notification(seller_id, user["id"], "marketplace_enquiry", "listing", listing_id, "أرسل مشتري استفساراً عن عرضك")
    return {"id": cursor.lastrowid, "listing_id": listing_id, "created": True}


@app.get("/api/marketplace/my-enquiries")
async def my_marketplace_enquiries(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    with connect() as db:
        rows = db.execute("""
            SELECT e.id, e.listing_id, e.message, e.created_at, l.title,
                   l.seller_id, s.display_name AS seller_name
            FROM marketplace_enquiries e
            JOIN marketplace_listings l ON l.id = e.listing_id
            JOIN users s ON s.id = l.seller_id
            WHERE e.buyer_id = ? ORDER BY e.id DESC LIMIT 100
        """, (user["id"],)).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/marketplace/my-listings")
async def my_marketplace_listings(
    limit: int = 50,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    with connect() as db:
        rows = db.execute("""
            SELECT l.id, l.title, l.description, l.category, l.price_amount, l.currency,
                   l.status, l.created_at,
                   (SELECT COUNT(*) FROM marketplace_enquiries e WHERE e.listing_id = l.id) AS enquiry_count
            FROM marketplace_listings l
            WHERE l.seller_id = ?
            ORDER BY l.id DESC LIMIT ?
        """, (user["id"], max(1, min(limit, 100)))).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/marketplace/seller-enquiries")
async def seller_marketplace_enquiries(
    limit: int = 50,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    with connect() as db:
        rows = db.execute("""
            SELECT e.id, e.listing_id, e.buyer_id, e.message, e.created_at,
                   l.title AS listing_title, b.display_name AS buyer_name, b.handle AS buyer_handle
            FROM marketplace_enquiries e
            JOIN marketplace_listings l ON l.id = e.listing_id
            JOIN users b ON b.id = e.buyer_id
            WHERE l.seller_id = ?
            ORDER BY e.id DESC LIMIT ?
        """, (user["id"], max(1, min(limit, 100)))).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.post("/api/social/messages/{other_user_id}", status_code=201)
async def send_direct_message(
    other_user_id: int,
    request: DirectMessageCreate,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message cannot be blank")
    if other_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="You cannot message yourself")
    with connect() as db:
        recipient = db.execute(
            "SELECT id FROM users WHERE id = ? AND email_verified = 1", (other_user_id,)
        ).fetchone()
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")
        cursor = db.execute(
            "INSERT INTO direct_messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
            (user["id"], other_user_id, content),
        )
        message_id = cursor.lastrowid
    create_notification(other_user_id, user["id"], "message", "conversation", user["id"], "أرسل إليك رسالة جديدة")
    return {"id": message_id, "sender_id": user["id"], "receiver_id": other_user_id, "content": content}


@app.get("/api/social/messages/{other_user_id}")
async def list_direct_messages(
    other_user_id: int,
    limit: int = 50,
    authorization: str | None = Header(default=None),
):
    user = current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if other_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Invalid conversation")
    with connect() as db:
        recipient = db.execute(
            "SELECT id FROM users WHERE id = ? AND email_verified = 1", (other_user_id,)
        ).fetchone()
        if not recipient:
            raise HTTPException(status_code=404, detail="Conversation not found")
        rows = db.execute("""
            SELECT id, sender_id, receiver_id, content, created_at
            FROM direct_messages
            WHERE (sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY id DESC LIMIT ?
        """, (user["id"], other_user_id, other_user_id, user["id"], max(1, min(limit, 100)))).fetchall()
    return {"items": [dict(row) for row in reversed(rows)]}


@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    x_api_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    check_access(x_api_token)
    user = current_user(authorization)
    if len(settings.auth_secret_key) >= 32 and not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be blank")
    if len(message) > settings.max_message_chars:
        raise HTTPException(status_code=413, detail="Message is too long")
    try:
        history = list_conversations(limit=8, user_id=user["id"] if user else None)
        reply = await generate_reply(message, history=list(reversed(history)))
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    save_conversation(message, reply, user["id"] if user else None)
    return {
        "reply": reply,
        "provider": settings.ai_provider,
        "model": settings.cloud_model if settings.ai_provider == "openai_compatible" else settings.ollama_model,
    }


@app.get("/api/conversations")
async def conversations(
    limit: int = 50,
    x_api_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    check_access(x_api_token)
    user = current_user(authorization)
    if len(settings.auth_secret_key) >= 32 and not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"items": list_conversations(max(1, min(limit, 100)), user["id"] if user else None)}


@app.delete("/api/conversations")
async def delete_conversations(
    x_api_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    check_access(x_api_token)
    user = current_user(authorization)
    if len(settings.auth_secret_key) >= 32 and not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    clear_conversations(user["id"] if user else None)
    return {"deleted": True}
