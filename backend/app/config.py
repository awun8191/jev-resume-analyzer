from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    typesafe_api_key: SecretStr = SecretStr("")
    typesafe_model: Literal["jev-latest"] = "jev-latest"
    typesafe_timeout_seconds: float = Field(default=90, gt=0, le=110)
    max_upload_bytes: int = Field(default=4000000, gt=0, le=4000000)
    max_document_pages: int = Field(default=40, gt=0, le=100)
    max_extracted_chars: int = Field(default=60000, gt=0, le=100000)
    max_analysis_chars: int = Field(default=40000, gt=0, le=60000)
    max_docx_uncompressed_bytes: int = Field(default=20971520, gt=0)
    parser_timeout_seconds: float = Field(default=15, gt=0, le=30)
