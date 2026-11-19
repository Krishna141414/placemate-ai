"""Upload validation: type, size, content and filename.

Checked in this order, and each failure has its own error code so the UI can
say exactly what was wrong:

    empty_file            the file has no bytes
    file_too_large        bigger than MAX_UPLOAD_MB          (413)
    unsupported_file_type extension is not .md, .txt or .pdf (415)
    content_mismatch      bytes do not match the extension    (415)
    no_text               no readable text after extraction   (422)
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

from fastapi import UploadFile

from app.config import get_settings
from app.errors import AppError
from app.rag.loader import ALLOWED_SUFFIXES, clean_text, decode_bytes

MIN_TEXT_CHARS = 40
READ_CHUNK = 64 * 1024
# Magic numbers of formats that must never be accepted as text.
_BINARY_SIGNATURES = (b"%PDF-", b"MZ", b"PK\x03\x04", b"\x7fELF", b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"\xd0\xcf\x11\xe0")


@dataclass
class ValidatedUpload:
    original_name: str
    safe_name: str  # sanitised, no directory parts
    stored_name: str  # safe_name with a unique prefix
    suffix: str
    data: bytes
    text: str


def sanitize_filename(name: str) -> str:
    """Basename only, ASCII, lowercase, `[a-z0-9._-]`, no leading dots."""
    name = name or ""
    # Strip directory parts written with either separator ("..\\..\\x", "/etc/x").
    name = PureWindowsPath(PurePosixPath(name.replace("\\", "/")).name).name
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    name = re.sub(r"[^a-z0-9._-]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-.")
    stem, dot, suffix = name.rpartition(".")
    if not dot:
        stem, suffix = name, ""
    stem = stem.replace(".", "-")[:60].strip("-") or "document"
    return f"{stem}.{suffix}" if suffix else stem


async def read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    """Read at most max_bytes + 1, so an oversized upload is never fully buffered."""
    data = bytearray()
    while True:
        chunk = await upload.read(READ_CHUNK)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > max_bytes:
            raise AppError(
                413, "file_too_large", f"The file is larger than the {max_bytes // (1024 * 1024)} MB limit."
            )
    return bytes(data)


def validate_bytes(filename: str, data: bytes, *, max_bytes: int | None = None) -> ValidatedUpload:
    settings = get_settings()
    max_bytes = max_bytes or settings.max_upload_mb * 1024 * 1024

    if not data:
        raise AppError(400, "empty_file", "The file is empty.")
    if len(data) > max_bytes:
        raise AppError(413, "file_too_large", f"The file is larger than the {max_bytes // (1024 * 1024)} MB limit.")

    safe = sanitize_filename(filename)
    suffix = "." + safe.rpartition(".")[2] if "." in safe else ""
    if suffix not in ALLOWED_SUFFIXES:
        raise AppError(415, "unsupported_file_type", "Only .md, .txt and .pdf files can be uploaded.")

    if suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise AppError(415, "content_mismatch", "The file is named .pdf but is not a PDF.")
    else:
        if data.startswith(_BINARY_SIGNATURES) or b"\x00" in data[:4096]:
            raise AppError(415, "content_mismatch", f"The file is named {suffix} but contains binary data.")

    try:
        text = clean_text(decode_bytes(data, suffix))
    except ValueError as exc:
        raise AppError(415, "content_mismatch", str(exc)) from exc
    if len(text) < MIN_TEXT_CHARS:
        raise AppError(422, "no_text", "No readable text was found in the file.")

    stored = f"{uuid.uuid4().hex[:8]}-{safe}"
    return ValidatedUpload(original_name=filename, safe_name=safe, stored_name=stored, suffix=suffix, data=data, text=text)
