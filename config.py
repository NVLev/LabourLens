import os
from typing import Annotated, List, Tuple

from pydantic import BaseModel, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RunConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class DatabaseConfig(BaseModel):
    url: PostgresDsn
    echo: bool = False
    echo_pool: bool = False
    pool_size: int = 10
    max_overflow: int = 20


class BotConfig(BaseModel):
    token: str = Field(default="", description="Telegram Bot Token")

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        if not v or len(v) < 10:
            raise ValueError("BOT_TOKEN must be valid")
        return v


class ParserConfig(BaseModel):
    request_delay_seconds: float = 1.5
    check_interval_minutes: int = 1440
    finlex_base_url: str = "https://www.finlex.fi"
    tyosuojelu_base_url: str = "https://www.tyosuojelu.fi"
    playwright_timeout_ms: int = 30000

class TranslationConfig(BaseModel):
    deepl_api_key: str = ""

class PaginationConfig(BaseModel):
    page_size: int = 10
    bot_page_size: int = 5


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    run: RunConfig = Field(default_factory=RunConfig)
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    # bot: Annotated[BotConfig, Field()]
    parser: ParserConfig = Field(default_factory=ParserConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)


settings = Settings()

