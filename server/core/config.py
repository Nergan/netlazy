from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    mongodb_uri: str = Field(..., validation_alias='MONGODB_URI')
    database_name: str = "netlazy"
    mongodb_tls_allow_invalid: bool = False

    # Ограничения
    max_pending_requests_size_mb: int = 15
    rate_limit_per_minute: int = 10
    rate_limit_window_seconds: int = 60
    rate_limit_cache_size: int = 10000
    nonce_cache_max_size: int = 10000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()