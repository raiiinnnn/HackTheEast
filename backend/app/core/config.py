import json
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List

# Project root .env (backend/app/core -> backend -> project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/focusfeed"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/focusfeed"

    JWT_SECRET_KEY: str = "change-me-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    MINIMAX_API_KEY: str = ""
    MINIMAX_GROUP_ID: str = ""

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "us-east-1"
    # Default: Amazon Nova Pro (broader geographic availability than Anthropic Claude)
    BEDROCK_MODEL_ID: str = "amazon.nova-pro-v1:0"

    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "focusfeed-uploads"
    S3_REGION: str = "us-east-1"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_IOS_CLIENT_ID: str = ""
    ABELIAN_SERVICE_URL: str = "http://localhost:8001"

    # Env BACKEND_CORS_ORIGINS: comma-separated or JSON array string (read as string to avoid JSON parse errors)
    cors_origins_raw: str = Field(
        default="http://localhost:8081,http://localhost:8082,http://localhost:19006",
        validation_alias="BACKEND_CORS_ORIGINS",
    )

    @property
    def BACKEND_CORS_ORIGINS(self) -> List[str]:
        raw = self.cors_origins_raw.strip()
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(o).strip() for o in parsed if o]
            except json.JSONDecodeError:
                pass
            # Fallback: split by comma and strip brackets/quotes from each part
        parts = [o.strip().strip("[]\"'") for o in raw.split(",") if o.strip()]
        return [p for p in parts if p]

    class Config:
        env_file = str(_ENV_FILE) if _ENV_FILE.exists() else None
        case_sensitive = True
        extra = "ignore"
        # So that BACKEND_CORS_ORIGINS (env) populates _cors_origins_raw
        populate_by_name = True


settings = Settings()
