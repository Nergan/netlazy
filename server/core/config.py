from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    mongodb_uri: str = Field(..., validation_alias='MONGODB_URI')
    database_name: str = "netlazy"
    mongodb_tls_allow_invalid: bool = False

    # Ограничения
    max_pending_requests_size_mb: int = 15          # Максимальный размер очереди запросов в МБ
    rate_limit_per_minute: int = 10                 # Максимум запросов в минуту с одного IP
    rate_limit_window_seconds: int = 60             # Окно для rate limiting
    rate_limit_cache_size: int = 10000              # Максимум IP в кэше rate limit
    nonce_cache_max_size: int = 10000               # Максимум записей nonce в кэше

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

Settings.model_rebuild()
settings = Settings()