"""File storage backend.

`LocalStorage` writes to a directory on disk. The interface (save / full_path /
delete) is deliberately small so an S3-compatible backend can be dropped in
without touching callers — swap the `storage` instance below.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import settings


class LocalStorage:
    def __init__(self, base_dir: str) -> None:
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def new_key(self, filename: str) -> str:
        """A collision-free storage key that preserves the extension."""
        suffix = Path(filename).suffix[:20]
        return f"{uuid.uuid4().hex}{suffix}"

    def full_path(self, key: str) -> Path:
        # Guard against path traversal: keys are basenames only.
        return self.base / Path(key).name

    def save(self, key: str, data: bytes) -> None:
        self.full_path(key).write_bytes(data)

    def delete(self, key: str) -> None:
        self.full_path(key).unlink(missing_ok=True)


storage = LocalStorage(settings.storage_dir)
