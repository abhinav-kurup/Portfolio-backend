# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # app
    APP_ENV: str = "development"
    DEBUG: bool = True

    # database
    DB_PATH: str = "data/portfolio.db"

    # llm
    PRIMARY_LLM_PROVIDER: str = "groq"          # anthropic / openai
    PRIMARY_LLM_MODEL: str = "llama-3.3-70b-versatile"
    PRIMARY_LLM_MAX_TOKENS: int = 1000
    PRIMARY_LLM_API_KEY: str = "None"

    FALLBACK_LLM_PROVIDER: str = "google"
    FALLBACK_LLM_MODEL: str = "gemini-2.5-flash"
    FALLBACK_LLM_MAX_TOKENS: int = 1000
    FALLBACK_LLM_API_KEY: str = "None"

    # embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # local, no API cost
    EMBEDDING_DIMENSIONS: int = 384

    # faq
    FAQ_SIMILARITY_THRESHOLD: float = 0.85    # above this = FAQ hit

    # retrieval
    MAX_CHUNKS_RETRIEVED: int = 3

    # security
    ADMIN_API_KEY: str                         # required, no default

    # cors
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Allow extra fields in .env without crashing
    )

settings = Settings()