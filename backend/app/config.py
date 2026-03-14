from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List, Optional
import os
import secrets


class Settings(BaseSettings):
    PROJECT_NAME: str = "BA Toolkit API"
    VERSION: str = "0.1.0"

    # Database
    DATABASE_PATH: str = "data/app.db"
    VECTOR_DB_PATH: str = "data/vectors"
    UPLOAD_DIR: str = "data/uploads"

    # Azure OpenAI - Required
    AZURE_OPENAI_API_KEY: str = Field(..., min_length=1, description="Azure OpenAI API key")
    AZURE_OPENAI_ENDPOINT: str = Field(..., min_length=1, description="Azure OpenAI endpoint URL")
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"

    # OpenAI (for embeddings) - Required
    OPENAI_API_KEY: str = Field(..., min_length=1, description="OpenAI API key for embeddings")

    # JWT - Required, minimum 32 characters for security
    JWT_SECRET_KEY: str = Field(..., min_length=32, description="JWT secret key (min 32 chars)")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Docling Serve
    DOCLING_SERVE_URL: str = "https://docling-serve.nicemoss-edd0d815.eastus.azurecontainerapps.io"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Environment
    ENVIRONMENT: str = "development"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


# Create settings instance - will raise error if required vars are missing
settings = Settings()
