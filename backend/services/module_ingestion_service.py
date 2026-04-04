import json
import os
from typing import Dict

from google.cloud import storage

from backend.schemas.module_ingestions import ModuleIngestionRequest
from backend.utils.ids import build_ingestion_id
from revision_common import now_iso

PROJECT_ID = os.getenv("PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "smartseller-490511"))
BUCKET_NAME = os.getenv("BUCKET_NAME", "smartcounter-review-dev")

storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(BUCKET_NAME)


def _safe_path_part(value: str) -> str:
    cleaned = "".join(ch for ch in str(value) if ch.isalnum() or ch in ("-", "_"))
    return cleaned or "unknown"


def _upload_json(object_name: str, payload) -> None:
    bucket.blob(object_name).upload_from_string(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        content_type="application/json",
    )


def persist_module_ingestion(payload: ModuleIngestionRequest) -> Dict[str, object]:
    ingestion_id = build_ingestion_id()
    tenant_part = _safe_path_part(payload.tenant_id)
    module_part = _safe_path_part(payload.module)

    prefix = f"tenant_{tenant_part}/module_ingestions/{module_part}/{ingestion_id}"

    payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    artifacts = {
        "input": f"{prefix}/input.json",
        "canonical_rows": f"{prefix}/canonical_rows.json",
        "findings": f"{prefix}/findings.json",
        "summary": f"{prefix}/summary.json",
        "suggested_actions": f"{prefix}/suggested_actions.json",
        "result": f"{prefix}/result.json",
    }

    _upload_json(artifacts["input"], payload_dict)
    _upload_json(artifacts["canonical_rows"], payload.canonical_rows)
    _upload_json(artifacts["findings"], payload.findings)
    _upload_json(artifacts["summary"], payload.summary)
    _upload_json(artifacts["suggested_actions"], payload.suggested_actions)

    result_payload = {
        "ok": True,
        "ingestion_id": ingestion_id,
        "tenant_id": payload.tenant_id,
        "module": payload.module,
        "status": "accepted",
        "artifacts": artifacts,
        "accepted_at": now_iso(),
    }
    _upload_json(artifacts["result"], result_payload)

    return {
        "ingestion_id": ingestion_id,
        "tenant_id": payload.tenant_id,
        "module": payload.module,
        "status": "accepted",
        "artifacts": artifacts,
    }
