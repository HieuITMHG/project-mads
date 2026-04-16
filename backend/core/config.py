from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).parents[2].resolve()

class Settings(BaseSettings):
    env: str

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_port: int
    postgres_version: int

    s3_endpoint: str
    aws_access_key_id: str
    aws_secret_access_key: str
    bucket_name: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env.dev",
        env_file_encoding="utf-8",
    )


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()

