from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
import os

BASE_DIR = Path(__file__).parents[2].resolve()

class Settings(BaseSettings):
    s3_endpoint: str
    aws_access_key_id: str
    aws_secret_access_key: str
    olist_data: str
    upload_bucket: str

    model_config = SettingsConfigDict(
        extra="ignore"
    )


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()

