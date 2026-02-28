from pydantic_settings import BaseSettings
from typing import List


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
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v1:0"

    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "focusfeed-uploads"
    S3_REGION: str = "us-east-1"

    GOOGLE_CLIENT_ID: str = ""
    ABELIAN_SERVICE_URL: str = "http://localhost:8001"

    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:8081", "http://localhost:8082", "http://localhost:19006"]

    class Config:
        env_file = "../.env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
