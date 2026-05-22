"""Small shared helpers used across apps."""
from __future__ import annotations

import hashlib
from typing import BinaryIO


def sha256_of_file(fileobj: BinaryIO, chunk_size: int = 8192) -> str:
    """Stream-hash a file for dedup / content-addressing without loading it all."""
    digest = hashlib.sha256()
    fileobj.seek(0)
    for chunk in iter(lambda: fileobj.read(chunk_size), b""):
        digest.update(chunk)
    fileobj.seek(0)
    return digest.hexdigest()


def truncate(text: str, limit: int = 280) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def human_filesize(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
