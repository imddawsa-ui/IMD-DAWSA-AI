import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .config import settings
from .database import initialize, connect
from .llm import generate_reply, ModelUnavailable

BASE_DIR = Path(__file__).resolve().parent.parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield

app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

class ChatRequest(BaseModel):
    message: str = Field(min_length=1)

def check_access(token: str | None):
    if settings.api_access_token and not secrets.compare_digest(token or "", settings.api_access_token):
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/")
async def home():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "version": "0.1.0"}

@app.get("/api/readiness")
async def readiness():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.ollama_url}/api/tags")
            r.raise_for_status()
        return {"ready": True, "model": settings.ollama_model}
    except httpx.HTTPError:
        return {"ready": False, "model": settings.ollama_model, "detail": "Ollama is not reachable"}

@app.post("/api/chat")
async def chat(request: ChatRequest, x_api_token: str | None = Header(default=None)):
    check_access(x_api_token)
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message cannot be blank")
    if len(message) > settings.max_message_chars:
        raise HTTPException(status_code=413, detail="Message is too long")
    try:
        reply = await generate_reply(message)
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    with connect() as db:
        db.execute("INSERT INTO conversations (user_message, assistant_message) VALUES (?, ?)", (message, reply))
    return {"reply": reply, "model": settings.ollama_model}
