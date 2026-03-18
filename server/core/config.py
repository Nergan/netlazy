from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional  # добавьте этот импорт

class Settings(BaseSettings):
    mongodb_uri: str = Field(..., validation_alias='MONGODB_URI')
    database_name: str = "netlazy"
    redis_url: str | None = Field(None, validation_alias='REDIS_URL')

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

Settings.model_rebuild()
settings = Settings()