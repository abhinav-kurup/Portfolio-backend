from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # app
    APP_ENV: str = "development"
    DEBUG: bool = True

    # database
    DB_PATH: str = "data/portfolio.db"

    # llm
    PRIMARY_LLM_PROVIDER: str = "groq"         
    PRIMARY_LLM_MODEL: str = "llama-3.3-70b-versatile"
    PRIMARY_LLM_MAX_TOKENS: int = 1000
    GROK_API_KEY: str = "None"

    FALLBACK_LLM_PROVIDER: str = "google"
    FALLBACK_LLM_MODEL: str = "gemini-3.1-flash-lite"
    FALLBACK_LLM_MAX_TOKENS: int = 1000
    GEMINI_API_KEY: str = "None"

    # OPENROUTER_API_KEY: str = "None"
    # CONTEXT_LLM_PROVIDER: str = "openrouter"
    # CONTEXT_LLM_MODEL: str = "deepseek/deepseek-v3.1"
    # CONTEXT_LLM_MAX_TOKENS: int = 1000

    # embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  
    EMBEDDING_DIMENSIONS: int = 384

    # faq
    FAQ_SIMILARITY_THRESHOLD: float = 0.85    
    # retrieval
    MAX_CHUNKS_RETRIEVED: int = 3

    # security
    ADMIN_API_KEY: str = "default_admin_key"

    # cors
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "https://huggingface.co/spaces/abhinavkurup/portfolio-backend/","https://abhinav-kurup.vercel.app/"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore" 
    )

settings = Settings()