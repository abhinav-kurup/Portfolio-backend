from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # app
    DB_PATH: str = "data/portfolio.db"

    # llm
    PRIMARY_LLM_PROVIDER: str = "groq"         
    PRIMARY_LLM_MODEL: str = "llama-3.3-70b-versatile"
    PRIMARY_LLM_MAX_TOKENS: int = 1000
    PRIMARY_LLM_API_KEY: str = "None"

    FALLBACK_LLM_PROVIDER: str = "google"
    FALLBACK_LLM_MODEL: str = "gemini-2.5-flash"
    FALLBACK_LLM_MAX_TOKENS: int = 1000
    FALLBACK_LLM_API_KEY: str = "None"

    # embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  
    EMBEDDING_DIMENSIONS: int = 384

    # faq
    FAQ_SIMILARITY_THRESHOLD: float = 0.85    
    # retrieval
    MAX_CHUNKS_RETRIEVED: int = 3

    # security
    # ADMIN_API_KEY: str = "default_admin_key"

    # cors
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "https://huggingface.co/spaces/abhinavkurup/portfolio-backend/","https://abhinav-kurup.vercel.app/"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore" 
    )

settings = Settings()