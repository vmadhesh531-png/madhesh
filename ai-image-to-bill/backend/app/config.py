"""Application configuration using Pydantic Settings."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App Info
    app_name: str = "AI Image-to-Bill"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, alias="DEBUG")

    # API Keys
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash-preview-05-20", alias="GEMINI_MODEL")

    # File Handling
    max_upload_size: int = Field(default=20 * 1024 * 1024, alias="MAX_UPLOAD_SIZE")  # 20MB
    upload_dir: Path = Field(default=Path("uploads"), alias="UPLOAD_DIR")
    output_dir: Path = Field(default=Path("outputs"), alias="OUTPUT_DIR")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=1, alias="WORKERS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Allowed MIME types
    allowed_mime_types: set[str] = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "application/pdf"
    }

    @property
    def upload_path(self) -> Path:
        """Ensure upload directory exists."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        return self.upload_dir

    @property
    def output_path(self) -> Path:
        """Ensure output directory exists."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir


# Global settings instance
settings = Settings()
