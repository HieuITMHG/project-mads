from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
import os

BASE_DIR = Path(__file__).parents[2].resolve()

class Settings(BaseSettings):
    env: str

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_port: int
    postgres_host: str
    postgres_version: int

    s3_endpoint: str
    aws_access_key_id: str
    aws_secret_access_key: str
    olist_data: str
    upload_bucket: str
    
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    
    redis_url: str
    celery_result_backend: str

    temp_dir: str

    max_upload_size_mb: int = 10

    qdrant_endpoint: str
    qdrant_key: str
    upload_collection:str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / f".env.{os.getenv('ENV_STATE', 'dev')}",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()

