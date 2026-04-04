import json
import os
from typing import Dict

from google.cloud import storage

from backend.schemas.module_ingestions import (
    ExpenseEvidenceCanonicalRow,
    ExpenseEvidenceFrozenRow,
    ModuleIngestionRequest,
)
from backend.utils.ids import build_ingestion_id
from revision_common import now_iso

PROJECT_ID = os.getenv("PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "smartseller-490511"))
BUCKET_NAME = os.getenv("BUCKET_NAME", "smartcounter-review-dev")

storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(BUCKET_NAME)

ALLOWED_EXPENSE_SOURCE_TYPES = {
    "upload",
    "email",
    "drive",
    "api",
    "other",
    "google_sheets",
}

ALLOWED_EXPENSE_FINDING_TYPES = {
    "missing_evidence",
    "illegible_evidence",
    "missing_key_fields",
    "duplicate_evidence_suspected",
    "unsupported_evidence_type",
    "high_amount_expense",
    "expense_date_inconsistent",
    "merchant_not_identified",
    "ready_for_approval",
    "evidence_quality_low",
}

REQUIRED_EXPENSE_SUMMARY_KEYS = {
    "total_cases",
    "ready_for_approval_cases",
    "needs_completion_cases",
    "low_quality_cases",
    "duplicate_suspected_cases",
    "high_amount_cases",
    "invalid_cases",
}

RESERVED_ARTIFACT_NAMES = {
    "input",
    "canonical_rows",
    "findings",
    "summary",
    "suggested_actions",
    "result",
}


def _safe_path_part(value: str) -> str:
    cleaned = "".join(ch for ch in str(value) if ch.isalnum() or ch in ("-", "_"))
    return cleaned or "unknown"


def _upload_json(object_name: str, payload) -> None:
    bucket.blob(object_name).upload_from_string(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        content_type="application/json",
    )


def _validate_stock_simple_payload(payload: ModuleIngestionRequest) -> None:
    if payload.source_type != "google_sheets":
        raise ValueError("stock_simple solo admite source_type=google_sheets")


def _validate_expense_row_shape(row: dict, idx: int) -> None:
    has_core_shape = all(key in row for key in ("expense_case_id", "evidence_id", "document_status"))
    has_frozen_shape = all(key in row for key in ("request_id", "evidence_list", "status"))

    try:
        if has_core_shape:
            if hasattr(ExpenseEvidenceCanonicalRow, "model_validate"):
                ExpenseEvidenceCanonicalRow.model_validate(row)
            else:
                ExpenseEvidenceCanonicalRow.parse_obj(row)
            return

        if has_frozen_shape:
            if hasattr(ExpenseEvidenceFrozenRow, "model_validate"):
                ExpenseEvidenceFrozenRow.model_validate(row)
            else:
                ExpenseEvidenceFrozenRow.parse_obj(row)
            return
    except Exception as exc:
        raise ValueError(f"canonical_rows[{idx}] invalido para expense_evidence: {exc}") from exc

    raise ValueError(
        f"canonical_rows[{idx}] no coincide con un shape soportado para expense_evidence "
        "(core o borde congelado)."
    )


def _extract_finding_type(finding: dict, idx: int) -> str:
    finding_type = finding.get("finding_type")
    code = finding.get("code")

    if finding_type and code and finding_type != code:
        raise ValueError(
            f"findings[{idx}] tiene mismatch entre finding_type ('{finding_type}') y code ('{code}')."
        )

    resolved = finding_type or code
    if not resolved:
        raise ValueError(
            f"findings[{idx}] requiere finding_type (code solo se acepta temporalmente por backward compatibility)."
        )

    return str(resolved)


def _validate_expense_evidence_payload(payload: ModuleIngestionRequest) -> None:
    if payload.source_type not in ALLOWED_EXPENSE_SOURCE_TYPES:
        allowed = ", ".join(sorted(ALLOWED_EXPENSE_SOURCE_TYPES))
        raise ValueError(f"expense_evidence source_type invalido. Valores permitidos: {allowed}")

    for idx, row in enumerate(payload.canonical_rows):
        if not isinstance(row, dict):
            raise ValueError(f"canonical_rows[{idx}] debe ser un objeto")
        _validate_expense_row_shape(row, idx)

    for idx, finding in enumerate(payload.findings):
        if not isinstance(finding, dict):
            raise ValueError(f"findings[{idx}] debe ser un objeto")

        finding_type = _extract_finding_type(finding, idx)
        if finding_type not in ALLOWED_EXPENSE_FINDING_TYPES:
            allowed_types = ", ".join(sorted(ALLOWED_EXPENSE_FINDING_TYPES))
            raise ValueError(
                f"findings[{idx}].finding_type invalido para expense_evidence: {finding_type}. "
                f"Valores permitidos: {allowed_types}"
            )

    missing_summary_keys = [key for key in REQUIRED_EXPENSE_SUMMARY_KEYS if key not in payload.summary]
    if missing_summary_keys:
        raise ValueError(
            "summary incompleto para expense_evidence. Faltan: " + ", ".join(sorted(missing_summary_keys))
        )

    for idx, action in enumerate(payload.suggested_actions):
        if not isinstance(action, dict):
            raise ValueError(f"suggested_actions[{idx}] debe ser un objeto")

        for field_name in ("action_type", "priority", "description", "context"):
            if field_name not in action:
                raise ValueError(f"suggested_actions[{idx}] requiere campo '{field_name}'")

        if action.get("priority") not in {"high", "medium", "low"}:
            raise ValueError(
                f"suggested_actions[{idx}].priority invalido: {action.get('priority')}"
            )

        if not isinstance(action.get("context"), dict):
            raise ValueError(f"suggested_actions[{idx}].context debe ser un objeto")


def _validate_payload_for_module(payload: ModuleIngestionRequest) -> None:
    if payload.module == "stock_simple":
        _validate_stock_simple_payload(payload)
        return

    if payload.module == "expense_evidence":
        _validate_expense_evidence_payload(payload)
        return

    raise ValueError(f"Modulo no soportado: {payload.module}")


def persist_module_ingestion(payload: ModuleIngestionRequest) -> Dict[str, object]:
    _validate_payload_for_module(payload)

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

    if payload.module == "expense_evidence" and payload.additional_artifacts:
        for raw_key, raw_value in payload.additional_artifacts.items():
            key = _safe_path_part(str(raw_key)).lower()
            if not key:
                continue

            artifact_key = key if key not in RESERVED_ARTIFACT_NAMES else f"extra_{key}"
            artifact_path = f"{prefix}/{artifact_key}.json"
            _upload_json(artifact_path, raw_value)
            artifacts[artifact_key] = artifact_path

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
