"""In-memory storage for extraction jobs (replace with Redis/DB in production)."""

import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta

from app.schemas.bill import BillExtractionResult
from app.utils.helpers import format_datetime


class JobStorage:
    """Thread-safe in-memory storage for bill extraction jobs."""

    def __init__(self, ttl_hours: int = 24):
        self._storage: Dict[str, BillExtractionResult] = {}
        self._lock = asyncio.Lock()
        self._ttl = timedelta(hours=ttl_hours)
        self._created_at: Dict[str, datetime] = {}

    async def create(self, job_id: str) -> BillExtractionResult:
        """Create a new job entry."""
        async with self._lock:
            result = BillExtractionResult(
                id=job_id,
                status="pending",
                created_at=format_datetime()
            )
            self._storage[job_id] = result
            self._created_at[job_id] = datetime.utcnow()
            return result

    async def get(self, job_id: str) -> Optional[BillExtractionResult]:
        """Get job by ID."""
        async with self._lock:
            if job_id in self._created_at:
                if datetime.utcnow() - self._created_at[job_id] > self._ttl:
                    self._storage.pop(job_id, None)
                    self._created_at.pop(job_id, None)
                    return None
            return self._storage.get(job_id)

    async def update(self, job_id: str, result: BillExtractionResult) -> None:
        """Update job result."""
        async with self._lock:
            if job_id in self._storage:
                self._storage[job_id] = result

    async def delete(self, job_id: str) -> bool:
        """Delete job by ID."""
        async with self._lock:
            if job_id in self._storage:
                del self._storage[job_id]
                del self._created_at[job_id]
                return True
            return False

    async def cleanup_expired(self) -> int:
        """Remove expired jobs. Returns count of removed jobs."""
        async with self._lock:
            now = datetime.utcnow()
            expired = [
                jid for jid, created in self._created_at.items()
                if now - created > self._ttl
            ]
            for jid in expired:
                self._storage.pop(jid, None)
                self._created_at.pop(jid, None)
            return len(expired)


# Global storage instance
job_storage = JobStorage()
