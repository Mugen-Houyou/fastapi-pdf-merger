from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="PDF_MERGER_",
        env_file=".env",
        extra="ignore",
    )

    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("API_KEY", "PDF_MERGER_API_KEY"),
    )
    max_total_upload_mb: int = Field(
        default=200,
        validation_alias=AliasChoices("MAX_MB", "PDF_MERGER_MAX_TOTAL_UPLOAD_MB"),
    )

    pdf_merge_max_parallel: int | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "MERGE_MAX_PARALLEL",
            "PDF_MERGE_MAX_PARALLEL",
        ),
    )

    @field_validator("pdf_merge_max_parallel", mode="before")
    @classmethod
    def _coerce_pdf_merge_max_parallel(cls, value: object) -> int | None:
        if value in (None, ""):
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None


settings = Settings()
