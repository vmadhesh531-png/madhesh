"""Request schemas for API endpoints."""

from typing import Optional
from pydantic import BaseModel, Field


class ImageUploadResponse(BaseModel):
    """Response schema for image upload."""

    id: str = Field(..., description="Unique job ID")
    filename: str = Field(..., description="Original filename")
    file_hash: str = Field(..., description="SHA-256 hash of file")
    status: str = Field(default="uploaded", description="Current status")
    message: str = Field(default="Image uploaded successfully", description="Status message")


class ExtractBillRequest(BaseModel):
    """Request schema for bill extraction."""

    id: str = Field(..., description="Job ID from upload")
    preprocess: bool = Field(default=True, description="Whether to preprocess image")
    language_hint: Optional[str] = Field(default=None, description="Language hint for OCR (e.g., 'en', 'hi')")


class ValidateRequest(BaseModel):
    """Request schema for manual validation trigger."""

    id: str = Field(..., description="Job ID to validate")
