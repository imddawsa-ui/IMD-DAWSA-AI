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

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield


app = FastAPI(title=settings.app_name, version="0.5.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Token", "Authorization"],
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Lightweight per-process abuse controls. Use a shared gateway limiter for multi-worker production.
_rate_buckets = defaultdict(deque)
_RATE_POLICIES = {
    "/api/auth/login": (10, 60),
    "/api/auth/register": (5, 60),
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
    return {"status": "ok", "app": settings.app_name, "version": "0.5.0"}


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
    return {"user": user, "access_token": issue_access_token(user["id"]), "token_type": "bearer"}


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    require_auth_configuration()
    user_record = get_user_by_email(request.email)
    if not user_record or not verify_password(request.password, user_record["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user = get_user(user_record["id"])
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
        if not db.execute("SELECT 1 FROM posts WHERE id = ?", (post_id,)).fetchone():
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
        reply = await generate_reply(message)
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
