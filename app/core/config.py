from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="PDF_MERGER_", extra="ignore")

    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("API_KEY", "PDF_MERGER_API_KEY"),
    )
    max_total_upload_mb: int = Field(
        default=200,
        validation_alias=AliasChoices("MAX_MB", "PDF_MERGER_MAX_TOTAL_UPLOAD_MB"),
    )


settings = Settings()
