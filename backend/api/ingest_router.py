"""Public upload ingestion endpoint.

Security and behavior notes:
- Allowed extensions: .pdf, .png, .jpg, .jpeg, .csv, .json, .txt, .wav, .mp3, .xlsx, .xls
- Maximum upload size: controlled by INGEST_MAX_UPLOAD_SIZE_BYTES (default 20 MiB)
- Artifact path structure: {storage_root}/{tenant_id}/{module}/{YYYY}/{MM}/{DD}/{request_id}_{safe_filename}
- MIME enforcement: extension must be allowed and Content-Type must match EXTENSION_MIME_MAP
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import unicodedata
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

router = APIRouter(tags=["ingest"])
logger = logging.getLogger(__name__)

EXTENSION_MIME_MAP: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".csv": {"text/csv", "application/csv"},
    ".json": {"application/json"},
    ".txt": {"text/plain"},
    ".wav": {"audio/wav", "audio/x-wav"},
    ".mp3": {"audio/mpeg"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".xls": {"application/vnd.ms-excel"},
}

ALLOWED_EXTENSIONS: set[str] = set(EXTENSION_MIME_MAP)
ALLOWED_MIME_TYPES: set[str] = {
    mime
    for mimes in EXTENSION_MIME_MAP.values()
    for mime in mimes
}

MAX_UPLOAD_SIZE_BYTES = int(os.getenv("INGEST_MAX_UPLOAD_SIZE_BYTES", str(20 * 1024 * 1024)))
CHUNK_SIZE_BYTES = int(os.getenv("INGEST_CHUNK_SIZE_BYTES", str(64 * 1024)))
MAX_CHUNKS = int(os.getenv("INGEST_MAX_CHUNKS", "4096"))
SLOW_UPLOAD_THRESHOLD_SECONDS = 120.0
SLOW_UPLOAD_SMALL_FILE_MAX_BYTES = 1024 * 1024

DEFAULT_STORAGE_ROOT = Path(os.getenv("INGEST_STORAGE_ROOT", "storage/uploads"))
DEFAULT_FALLBACK_ROOT = Path(os.getenv("INGEST_STORAGE_FALLBACK_ROOT", "storage/uploads_fallback"))

_SANITIZE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def _log_event(level: int, event: str, **payload: Any) -> None:
    payload["event"] = event
    payload.setdefault("security_event", False)
    logger.log(level, json.dumps(payload, ensure_ascii=True, sort_keys=True))


def _normalize_content_type(content_type: str | None) -> str:
    if not content_type:
        return ""
    return content_type.split(";", 1)[0].strip().lower()


def _sanitize_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFKC", filename or "").strip().replace("\x00", "")
    normalized = os.path.basename(normalized)
    cleaned = _SANITIZE_PATTERN.sub("_", normalized)
    cleaned = re.sub(r"_+", "_", cleaned).strip(" .")

    if not cleaned:
        raise HTTPException(status_code=400, detail="Invalid filename")

    base, ext = os.path.splitext(cleaned)
    ext = ext.lower()
    base = base[:180]
    cleaned = f"{base}{ext}" if base else ext
    cleaned = cleaned[:255]

    if not cleaned:
        raise HTTPException(status_code=400, detail="Invalid filename")

    return cleaned


def _safe_resolve(base_dir: Path, *parts: str) -> Path:
    base_resolved = base_dir.resolve()
    candidate = base_resolved.joinpath(*parts).resolve()

    if candidate != base_resolved and not str(candidate).startswith(f"{base_resolved}{os.sep}"):
        raise HTTPException(status_code=400, detail="Invalid artifact path")

    return candidate


def _prepare_storage_root() -> tuple[Path, bool]:
    try:
        DEFAULT_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        return DEFAULT_STORAGE_ROOT.resolve(), False
    except OSError:
        DEFAULT_FALLBACK_ROOT.mkdir(parents=True, exist_ok=True)
        return DEFAULT_FALLBACK_ROOT.resolve(), True


@router.post("/ingest")
async def ingest_file(
    request: Request,
    file: UploadFile = File(...),
    tenant_id: str = Form(...),
    module: str = Form(...),
) -> dict[str, Any]:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    started_at = time.monotonic()

    raw_filename = (file.filename or "").strip()
    normalized_content_type = _normalize_content_type(file.content_type)

    if not raw_filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if raw_filename.startswith(".") or raw_filename.startswith(".."):
        _log_event(
            logging.WARNING,
            "hidden_filename_rejected",
            request_id=request_id,
            tenant_id=tenant_id,
            module=module,
            filename=raw_filename,
            security_event=True,
        )
        raise HTTPException(status_code=400, detail="Hidden filenames are not allowed")

    if ".." in raw_filename:
        _log_event(
            logging.WARNING,
            "suspicious_filename_pattern_rejected",
            request_id=request_id,
            tenant_id=tenant_id,
            module=module,
            filename=raw_filename,
            security_event=True,
        )
        raise HTTPException(status_code=400, detail="Invalid filename")

    safe_filename = _sanitize_filename(raw_filename)

    if "/" in safe_filename or "\\" in safe_filename:
        _log_event(
            logging.WARNING,
            "filename_traversal_rejected",
            request_id=request_id,
            tenant_id=tenant_id,
            module=module,
            filename=safe_filename,
            security_event=True,
        )
        raise HTTPException(status_code=400, detail="Invalid filename")

    extension = Path(safe_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        _log_event(
            logging.WARNING,
            "extension_not_allowed",
            request_id=request_id,
            tenant_id=tenant_id,
            module=module,
            filename=safe_filename,
            extension=extension,
            security_event=True,
        )
        raise HTTPException(status_code=400, detail="File extension is not allowed")

    if normalized_content_type not in ALLOWED_MIME_TYPES:
        _log_event(
            logging.WARNING,
            "mime_not_allowed",
            request_id=request_id,
            tenant_id=tenant_id,
            module=module,
            filename=safe_filename,
            content_type=normalized_content_type,
            security_event=True,
        )
        raise HTTPException(status_code=400, detail="Content-Type is not allowed")

    if normalized_content_type not in EXTENSION_MIME_MAP[extension]:
        _log_event(
            logging.WARNING,
            "mime_extension_mismatch",
            request_id=request_id,
            tenant_id=tenant_id,
            module=module,
            filename=safe_filename,
            extension=extension,
            content_type=normalized_content_type,
            security_event=True,
        )
        raise HTTPException(status_code=400, detail="MIME type does not match file extension")

    tenant_safe = _sanitize_filename(tenant_id).replace(".", "_")
    module_safe = _sanitize_filename(module).replace(".", "_")
    if not tenant_safe or not module_safe:
        raise HTTPException(status_code=400, detail="Invalid tenant_id or module")

    storage_root, used_fallback = _prepare_storage_root()
    now = datetime.now(UTC)
    date_parts = [f"{now.year:04d}", f"{now.month:02d}", f"{now.day:02d}"]

    artifact_relative_parts = [tenant_safe, module_safe, *date_parts]
    artifact_dir = _safe_resolve(storage_root, *artifact_relative_parts)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{request_id}_{safe_filename}"
    final_path = _safe_resolve(artifact_dir, stored_filename)
    temp_path = _safe_resolve(artifact_dir, f".{stored_filename}.part")

    bytes_written = 0
    chunk_count = 0
    sha256 = hashlib.sha256()

    try:
        with temp_path.open("wb") as out_file:
            while True:
                chunk = await file.read(CHUNK_SIZE_BYTES)
                if not chunk:
                    break

                chunk_count += 1
                if chunk_count > MAX_CHUNKS:
                    _log_event(
                        logging.WARNING,
                        "chunk_limit_exceeded",
                        request_id=request_id,
                        tenant_id=tenant_id,
                        module=module,
                        filename=safe_filename,
                        chunk_count=chunk_count,
                        max_chunks=MAX_CHUNKS,
                        security_event=False,
                    )
                    raise HTTPException(status_code=413, detail="Too many chunks")

                chunk_len = len(chunk)
                bytes_written += chunk_len
                if bytes_written > MAX_UPLOAD_SIZE_BYTES:
                    _log_event(
                        logging.WARNING,
                        "size_limit_exceeded",
                        request_id=request_id,
                        tenant_id=tenant_id,
                        module=module,
                        filename=safe_filename,
                        bytes_written=bytes_written,
                        max_bytes=MAX_UPLOAD_SIZE_BYTES,
                        security_event=False,
                    )
                    raise HTTPException(status_code=413, detail="File too large")

                sha256.update(chunk)
                out_file.write(chunk)

        temp_path.replace(final_path)

    except HTTPException:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        _log_event(
            logging.ERROR,
            "upload_write_failed",
            request_id=request_id,
            tenant_id=tenant_id,
            module=module,
            filename=safe_filename,
            error=str(exc),
            security_event=False,
        )
        raise HTTPException(status_code=500, detail="Failed to persist upload") from exc
    finally:
        await file.close()

    elapsed = time.monotonic() - started_at
    file_hash_sha256 = sha256.hexdigest()

    if elapsed > SLOW_UPLOAD_THRESHOLD_SECONDS and bytes_written < SLOW_UPLOAD_SMALL_FILE_MAX_BYTES:
        _log_event(
            logging.WARNING,
            "slow_upload_suspected",
            request_id=request_id,
            tenant_id=tenant_id,
            module=module,
            filename=safe_filename,
            bytes_written=bytes_written,
            elapsed_seconds=round(elapsed, 3),
            reason="slow_upload_suspected",
            security_event=False,
        )

    artifact_relative_path = "/".join([*artifact_relative_parts, stored_filename])
    _log_event(
        logging.INFO,
        "upload_completed",
        request_id=request_id,
        tenant_id=tenant_id,
        module=module,
        filename=safe_filename,
        stored_filename=stored_filename,
        artifact_path=artifact_relative_path,
        bytes_written=bytes_written,
        chunk_count=chunk_count,
        elapsed_seconds=round(elapsed, 3),
        content_type=normalized_content_type,
        file_hash_sha256=file_hash_sha256,
        used_fallback_storage=used_fallback,
        security_event=False,
    )

    return {
        "ok": True,
        "request_id": request_id,
        "filename": stored_filename,
        "content_type": normalized_content_type,
        "size_bytes": bytes_written,
        "artifact_path": artifact_relative_path,
    }
