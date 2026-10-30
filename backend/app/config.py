from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    typesafe_api_key: SecretStr = SecretStr("")
    typesafe_model: Literal["jev-latest"] = "jev-latest"
    typesafe_timeout_seconds: float = Field(default=90, gt=0, le=110)
    max_upload_bytes: int = Field(default=10485760, gt=0, le=10485760)
    max_document_pages: int = Field(default=40, gt=0, le=100)
    max_extracted_chars: int = Field(default=60000, gt=0, le=100000)
    max_analysis_chars: int = Field(default=40000, gt=0, le=60000)
    max_docx_uncompressed_bytes: int = Field(default=20971520, gt=0)
    parser_timeout_seconds: float = Field(default=15, gt=0, le=30)
    rate_limit_enabled: bool = True
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: SecretStr = SecretStr("")
    rate_limit_salt: str = ""
    rate_limit_analyses_per_hour: int = Field(default=10, gt=0)
    rate_limit_extracts_per_hour: int = Field(default=30, gt=0)
    rate_limit_requests_per_minute: int = Field(default=120, gt=0)
    rate_limit_global_analyses_per_day: int = Field(default=300, gt=0)

    @model_validator(mode="after")
    def require_rest_token_with_url(self):
        if self.upstash_redis_rest_url and not self.upstash_redis_rest_token.get_secret_value():
            raise ValueError(
                "UPSTASH_REDIS_REST_TOKEN is required when UPSTASH_REDIS_REST_URL is set."
            )
        return self
