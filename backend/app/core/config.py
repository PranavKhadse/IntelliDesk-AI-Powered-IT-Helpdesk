import os
from pathlib import Path
from typing import List, Union, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base backend directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    APP_NAME: str = "IntelliDesk"
    DEBUG: bool = True
    
    # Security - Loaded from backend/.env (no hardcoded fallback)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database - Loaded from backend/.env (PostgreSQL required)
    DATABASE_URL: str
    
    # CORS Configuration
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    
    # Standalone ML / FAISS Artifact Paths (Separated - loaded only when present)
    ML_MODEL_PATH: str = "app/ml/artifacts/triage_classifier.joblib"
    FAISS_INDEX_PATH: str = "app/rag/artifacts/faiss_index.bin"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # AI Service Settings. The API key is backend-only and must never be sent to clients.
    AI_PROVIDER: str = "none"
    AI_API_KEY: str = ""
    AI_MODEL: str = ""
    AI_API_BASE_URL: str = ""
    AI_TIMEOUT_SECONDS: float = 10.0

    # Environment variable aliases for provider flexibility
    LLM_PROVIDER: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    @property
    def effective_ai_provider(self) -> str:
        if self.AI_PROVIDER and self.AI_PROVIDER.strip().lower() != "none":
            return self.AI_PROVIDER.strip().lower()
        if self.LLM_PROVIDER and self.LLM_PROVIDER.strip().lower() != "none":
            return self.LLM_PROVIDER.strip().lower()
        if self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip():
            return "gemini"
        if self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip():
            return "openai"
        return "none"

    @property
    def effective_ai_api_key(self) -> str:
        if self.AI_API_KEY and self.AI_API_KEY.strip() and self.AI_API_KEY != "your_ai_provider_api_key_here":
            return self.AI_API_KEY.strip()
        if self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip():
            return self.GEMINI_API_KEY.strip()
        if self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip():
            return self.OPENAI_API_KEY.strip()
        return ""
    
    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return self.CORS_ORIGINS

    model_config = SettingsConfigDict(
        env_file=(str(ENV_PATH), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
