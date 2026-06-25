from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="GitHub Repo Analyzer", alias="APP_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    database_url: str = Field(default="sqlite+pysqlite:///./dev.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND")
    chroma_persist_dir: str = Field(default="./chroma", alias="CHROMA_PERSIST_DIR")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4.1-mini", alias="LLM_MODEL")
    llm_max_output_tokens: int = Field(default=1200, alias="LLM_MAX_OUTPUT_TOKENS")
    retrieval_top_k: int = Field(default=8, alias="RETRIEVAL_TOP_K")
    search_top_k: int = Field(default=10, alias="SEARCH_TOP_K")
    memory_window_messages: int = Field(default=8, alias="MEMORY_WINDOW_MESSAGES")
    prompt_max_context_chars: int = Field(default=24_000, alias="PROMPT_MAX_CONTEXT_CHARS")
    max_file_size_bytes: int = Field(default=1_048_576, alias="MAX_FILE_SIZE_BYTES")
    shallow_clone_default: bool = Field(default=True, alias="SHALLOW_CLONE_DEFAULT")
    jwt_algorithm: str = "HS256"

    @model_validator(mode="after")
    def validate_secret(self) -> "Settings":
        if not self.secret_key or self.secret_key == "change-me":
            raise ValueError("SECRET_KEY must be set to a non-default value")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
