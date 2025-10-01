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

    use_proxy_headers: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "USE_PROXY_HEADERS",
            "PDF_MERGER_USE_PROXY_HEADERS",
        ),
    )
    proxy_trusted_hosts: tuple[str, ...] = Field(
        default=("*",),
        validation_alias=AliasChoices(
            "PROXY_TRUSTED_HOSTS",
            "PDF_MERGER_PROXY_TRUSTED_HOSTS",
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

    @field_validator("proxy_trusted_hosts", mode="before")
    @classmethod
    def _coerce_proxy_trusted_hosts(
        cls, value: object
    ) -> tuple[str, ...]:  # pragma: no cover - simple parsing
        if value in (None, ""):
            return tuple()

        if isinstance(value, str):
            hosts = [host.strip() for host in value.split(",") if host.strip()]
            return tuple(hosts)

        if isinstance(value, (list, tuple, set)):
            return tuple(str(host).strip() for host in value if str(host).strip())

        return tuple()


settings = Settings()
