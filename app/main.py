import re
import secrets
import sqlite3
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


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=2, max_length=60)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


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


@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    x_api_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    check_access(x_api_token)
    user = current_user(authorization)
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
    return {"items": list_conversations(max(1, min(limit, 100)), user["id"] if user else None)}


@app.delete("/api/conversations")
async def delete_conversations(
    x_api_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    check_access(x_api_token)
    user = current_user(authorization)
    clear_conversations(user["id"] if user else None)
    return {"deleted": True}
