import os
from typing import Annotated, List, Tuple

from pydantic import BaseModel, Field, PostgresDsn, field_validator, SecretStr
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
    api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Genai Token")
    models: list[str] = Field(
        default=[
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
        ],
        description="List of models to use",
    )
    request_delay: float = Field(
        default=4.0,
        ge=0.0,
        description="Delay between requests (to prevent 429 Too Many Requests error)",
    )
    max_tokens: int = Field(
        default=16384,
        gt=0,
        description="Max number of tokens allowed in each request",
    )
    chunk_size_limit: int = Field(
        default=12000,
        gt=100,
        description="Maximum length of each chunk",
    )
    daily_request_limit: int = Field(
        default=480,
        gt=0,
        description="Daily request limit",
    )
    max_attempts: int = Field(
        default=3,
        gt=0,
        description="Max number of attempts allowed in each answer",
    )
    timeout_seconds: int = Field(
        default=240_000,
        gt=0,
        description="Timeout for each request in seconds",
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: SecretStr) -> SecretStr:
        raw_key = v.get_secret_value().strip()
        if raw_key and len(raw_key) < 10:
            raise ValueError("API_KEY для переводчика должен быть валидной строкой")
        return v

    @field_validator("models")
    @classmethod
    def validate_models(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Список моделей не может быть пустым")
        return v

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
    bot: Annotated[BotConfig, Field()]
    parser: ParserConfig = Field(default_factory=ParserConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)


settings = Settings()
