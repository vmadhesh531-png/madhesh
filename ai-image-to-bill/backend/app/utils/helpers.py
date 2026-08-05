"""Utility helper functions."""

import hashlib
import secrets
import uuid
from datetime import datetime
from typing import Optional
from pathlib import Path


def generate_id() -> str:
    """Generate a unique identifier for bill extraction jobs."""
    return str(uuid.uuid4())


def generate_file_hash(file_content: bytes) -> str:
    """Generate SHA-256 hash of file content for deduplication."""
    return hashlib.sha256(file_content).hexdigest()


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    safe_name = Path(filename).name
    # Remove any potentially dangerous characters
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
    if not safe_name:
        safe_name = "unnamed_file"
    return safe_name


def format_datetime(dt: Optional[datetime] = None) -> str:
    """Format datetime to ISO format."""
    if dt is None:
        dt = datetime.utcnow()
    return dt.isoformat() + "Z"


def safe_float_conversion(value: Optional[str], default: Optional[float] = None) -> Optional[float]:
    """Safely convert string to float, handling currency symbols and commas."""
    if value is None or value == "":
        return default

    # Remove currency symbols, commas, and whitespace
    cleaned = value.strip().replace(",", "").replace("$", "").replace("₹", "").replace("€", "").replace("£", "")

    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return default
