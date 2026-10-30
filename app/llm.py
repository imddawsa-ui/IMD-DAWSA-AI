import httpx
from .config import settings

class ModelUnavailable(RuntimeError):
    pass

async def generate_reply(message: str) -> str:
    if settings.ai_provider == "openai_compatible":
        url = settings.cloud_base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {settings.cloud_api_key}"} if settings.cloud_api_key else {}
        payload = {
            "model": settings.cloud_model,
            "messages": [
                {"role": "system", "content": "You are IMD DAWSA AI, a helpful, honest and privacy-conscious assistant. Reply in the user's language. Never claim an action was completed unless it actually was."},
                {"role": "user", "content": message},
            ],
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise ModelUnavailable("The configured cloud AI service is unavailable. Check provider settings and network access.") from exc

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
            return response.json()["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise ModelUnavailable("The local Ollama model is unavailable. Start Ollama and download the configured model.") from exc
