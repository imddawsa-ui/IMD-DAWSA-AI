import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "IMD DAWSA AI")
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    ollama_timeout_seconds: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))
    ai_provider: str = os.getenv("AI_PROVIDER", "ollama").lower()
    cloud_base_url: str = os.getenv("CLOUD_BASE_URL", "https://api.openai.com/v1")
    cloud_model: str = os.getenv("CLOUD_MODEL", "gpt-4o-mini")
    cloud_api_key: str = os.getenv("CLOUD_API_KEY", "")
    database_path: str = os.getenv("DATABASE_PATH", "./data/imd_dawsa.sqlite3")
    api_access_token: str = os.getenv("API_ACCESS_TOKEN", "")
    auth_secret_key: str = os.getenv("AUTH_SECRET_KEY", "")
    auth_token_ttl_seconds: int = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "86400"))
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    email_from: str = os.getenv("EMAIL_FROM", "")
    api_public_url: str = os.getenv("API_PUBLIC_URL", "http://127.0.0.1:8000")
    email_verification_ttl_seconds: int = int(os.getenv("EMAIL_VERIFICATION_TTL_SECONDS", "900"))
    max_message_chars: int = int(os.getenv("MAX_MESSAGE_CHARS", "12000"))
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:8000,http://127.0.0.1:8000",
        ).split(",")
        if origin.strip()
    )


settings = Settings()
