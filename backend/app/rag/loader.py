"""Reading documents from disk: front matter, cleaning, PDF text, the corpus."""

from __future__ import annotations

import hashlib
import io
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)

SEED_FOLDERS = {"companies": "company", "interviews": "interview", "guides": "guide"}
TEXT_SUFFIXES = {".md", ".txt"}
ALLOWED_SUFFIXES = TEXT_SUFFIXES | {".pdf"}
DOC_TYPES = {"policy", "company", "interview", "guide", "upload"}


@dataclass
class SourceDoc:
    doc_key: str
    title: str
    doc_type: str
    text: str  # cleaned, sanitised body (no front matter)
    source: str  # seed | upload
    filename: str
    path: str
    checksum: str
    size_bytes: int
    company_id: str | None = None
    removed_lines: list[str] = field(default_factory=list)


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown file into (metadata, body).

    Files without a YAML block return an empty dict and the whole text.
    A malformed block is treated as no front matter, never as an error,
    because uploaded files are untrusted.
    """
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}, text
    if not isinstance(meta, dict):
        return {}, text
    return meta, text[match.end():]


def clean_text(text: str) -> str:
    """Normalise unicode and whitespace and remove control characters."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_RE.sub("", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_text(data: bytes) -> str:
    """Text of every page of a PDF. Raises ValueError if it cannot be read."""
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("The PDF is password protected.")
        pages = [page.extract_text() or "" for page in reader.pages]
    except PyPdfError as exc:
        raise ValueError("The PDF could not be read.") from exc
    except ValueError:
        raise
    except Exception as exc:  # pypdf raises assorted errors on corrupt files
        raise ValueError("The PDF could not be read.") from exc
    return "\n\n".join(pages)


def decode_bytes(data: bytes, suffix: str) -> str:
    """Bytes of an allowed file type to text."""
    if suffix == ".pdf":
        return extract_pdf_text(data)
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The file is not valid UTF-8 text.") from exc


def slugify(value: str, max_length: int = 80) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:max_length].strip("-") or "document"


def _title_from(meta: dict[str, Any], body: str, fallback: str) -> str:
    if meta.get("title"):
        return str(meta["title"]).strip()[:200]
    if meta.get("name") and meta.get("role"):
        return f"{meta['name']} - {meta['role']}"[:200]
    heading = _HEADING_RE.search(body)
    if heading:
        return heading.group(1).strip()[:200]
    return fallback[:200]


def build_source_doc(
    raw_text: str,
    *,
    filename: str,
    path: str,
    source: str,
    size_bytes: int,
    checksum: str,
    default_type: str = "upload",
    doc_key: str | None = None,
) -> SourceDoc:
    """Turn raw file text into a cleaned, sanitised document."""
    from app.security.injection import sanitize_document_text

    meta, body = parse_front_matter(raw_text)
    body = clean_text(body)
    body, removed = sanitize_document_text(body)

    doc_type = str(meta.get("doc_type") or default_type)
    if doc_type not in DOC_TYPES:
        doc_type = default_type

    stem = Path(filename).stem
    key = doc_key or (str(meta["id"]) if meta.get("id") else slugify(stem))
    company_id = meta.get("company_id") or (meta.get("id") if doc_type == "company" else None)

    return SourceDoc(
        doc_key=slugify(key),
        title=_title_from(meta, body, stem.replace("_", " ").replace("-", " ").title()),
        doc_type=doc_type,
        text=body,
        source=source,
        filename=filename,
        path=path,
        checksum=checksum,
        size_bytes=size_bytes,
        company_id=str(company_id).lower() if company_id else None,
        removed_lines=removed,
    )


def load_file(path: Path, *, source: str, default_type: str = "upload", doc_key: str | None = None) -> SourceDoc:
    data = path.read_bytes()
    raw_text = decode_bytes(data, path.suffix.lower())
    return build_source_doc(
        raw_text,
        filename=path.name,
        path=str(path),
        source=source,
        size_bytes=len(data),
        checksum=hashlib.sha256(data).hexdigest(),
        default_type=default_type,
        doc_key=doc_key,
    )


def load_seed_documents(data_dir: Path) -> list[SourceDoc]:
    """The committed sample corpus: policy, companies, interviews, guides."""
    docs: list[SourceDoc] = []
    policy = data_dir / "placement_policy.md"
    if policy.exists():
        docs.append(load_file(policy, source="seed", default_type="policy"))
    for folder, doc_type in SEED_FOLDERS.items():
        for path in sorted((data_dir / folder).glob("*.md")):
            docs.append(load_file(path, source="seed", default_type=doc_type))
    return docs


def load_corpus(data_dir: Path, uploads: list[tuple[str, Path]]) -> list[SourceDoc]:
    """Seed documents plus uploaded ones. `uploads` is (doc_key, path) pairs."""
    docs = load_seed_documents(data_dir)
    seen = {doc.doc_key for doc in docs}
    for doc_key, path in uploads:
        if not path.exists() or doc_key in seen:
            continue
        try:
            docs.append(load_file(path, source="upload", doc_key=doc_key))
            seen.add(doc_key)
        except ValueError:
            continue
    return docs
