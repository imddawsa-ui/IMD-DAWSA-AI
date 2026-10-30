import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "IMD DAWSA AI")
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    ollama_timeout_seconds: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))
    database_path: str = os.getenv("DATABASE_PATH", "./data/imd_dawsa.sqlite3")
    api_access_token: str = os.getenv("API_ACCESS_TOKEN", "")
    max_message_chars: int = int(os.getenv("MAX_MESSAGE_CHARS", "12000"))

settings = Settings()
