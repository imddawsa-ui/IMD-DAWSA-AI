import httpx
from .config import settings

class ModelUnavailable(RuntimeError):
    pass

async def generate_reply(message: str) -> str:
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": "You are IMD DAWSA AI, a helpful, honest and privacy-conscious assistant. Reply in the user's language. Never claim an action was completed unless it actually was."},
            {"role": "user", "content": message},
        ],
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
            response = await client.post(f"{settings.ollama_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise ModelUnavailable("The local Ollama model is unavailable. Start Ollama and download the configured model.") from exc
