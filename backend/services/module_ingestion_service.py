import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# storage import handled below

from backend.core.action_engine import ActionEngine
from backend.core.action_store import ActionStore
from backend.schemas.module_ingestions import (
    ExpenseEvidenceFrozenRow,
    ModuleIngestionRequest,
)
from backend.schemas.normalized_signals import NormalizedSignalV1
from backend.services.daily_digest_builder import build_daily_digest_v1
from backend.utils.ids import build_ingestion_id
from revision_common import now_iso

PROJECT_ID = os.getenv("PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "smartseller-490511"))
BUCKET_NAME = os.getenv("BUCKET_NAME", "smartcounter-review-dev")
logger = logging.getLogger(__name__)

import os

LOCAL_DEV = os.getenv("LOCAL_DEV") == "true"

# Global for lazy loading
_lazy_bucket = None

def _get_bucket():
    global _lazy_bucket
    if LOCAL_DEV:
        return None
    if _lazy_bucket is not None:
        return _lazy_bucket
    
    try:
        from google.cloud import storage
        client = storage.Client(project=PROJECT_ID)
        _lazy_bucket = client.bucket(BUCKET_NAME)
        return _lazy_bucket
    except Exception as e:
        logger.warning(f"GCS disabled/failed: {e}. Running in local mode.")
        return None

# Keep these as None at module level; functions will call _get_bucket()
storage_client = None
bucket = None

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

REQUIRED_STOCK_SIMPLE_ROW_KEYS = {
    "row_id",
    "producto",
    "stock_actual",
    "stock_minimo",
    "consumo_promedio_diario",
    "requires_review",
}

REQUIRED_STOCK_SIMPLE_SUMMARY_KEYS = {
    "total_rows",
    "valid_rows",
    "invalid_rows",
}

RESERVED_ARTIFACT_NAMES = {
    "input",
    "canonical_rows",
    "findings",
    "summary",
    "suggested_actions",
    "normalized_signals",
    "request_meta",
    "digest",
    "result",
}

SEVERITY_RANK = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}

FINDING_TO_SIGNAL = {
    "stock_simple": {
        "critical_stock_detected": "stock_break_risk",
        "low_stock_detected": "stock_break_risk",
        "overstock_detected": "stock_overstock_risk",
        "invalid_stock_row": "stock_data_quality_issue",
    },
    "expense_evidence": {
        "missing_evidence": "expense_evidence_missing",
        "illegible_evidence": "expense_evidence_low_quality",
        "evidence_quality_low": "expense_evidence_low_quality",
        "duplicate_evidence_suspected": "expense_duplicate_suspected",
        "high_amount_expense": "expense_policy_risk",
        "missing_key_fields": "expense_policy_risk",
    },
    "concili_simple": {
        "unmatched_movement": "conciliation_unmatched_movement",
        "amount_mismatch": "conciliation_amount_mismatch",
        "date_mismatch": "conciliation_date_mismatch",
    },
}


def _safe_path_part(value: str) -> str:
    cleaned = "".join(ch for ch in str(value) if ch.isalnum() or ch in ("-", "_"))
    return cleaned or "unknown"

def _save_local_json(object_name: str, payload: Any):
    path = Path("storage") / object_name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)

def _load_local_json(object_name: str):
    path = Path("storage") / object_name
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _upload_json(object_name: str, payload) -> None:
    lbucket = _get_bucket()
    if lbucket is None:
        _save_local_json(object_name, payload)
        return

    lbucket.blob(object_name).upload_from_string(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False, default=str),
        content_type="application/json",
    )


def _load_json_or_none(object_name: str):
    lbucket = _get_bucket()
    if lbucket is None:
        return _load_local_json(object_name)

    blob = lbucket.blob(object_name)
    if not blob.exists():
        return None
    return json.loads(blob.download_as_text())


def _parse_generated_at(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError("generated_at invalido: debe ser timestamp RFC3339/ISO-8601") from exc

    if parsed.tzinfo is None:
        raise ValueError("generated_at invalido: debe incluir zona horaria (Z u offset)")

    return parsed


def _parse_iso_or_none(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _validate_content_hash_format(content_hash: str) -> None:
    value = str(content_hash or "").strip().lower()
    is_hex = len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)
    if not is_hex:
        raise ValueError("content_hash invalido: debe ser SHA-256 hex de 64 caracteres")


def _canonical_payload_for_hash(payload: ModuleIngestionRequest) -> Dict[str, object]:
    return {
        "contract_version": payload.contract_version,
        "source_channel": payload.source_channel,
        "tenant_id": payload.tenant_id,
        "module": payload.module,
        "source_type": payload.source_type,
        "generated_at": payload.generated_at,
        "canonical_rows": payload.canonical_rows,
        "findings": payload.findings,
        "summary": payload.summary,
        "suggested_actions": payload.suggested_actions,
        "additional_artifacts": payload.additional_artifacts,
        "parse_metadata": payload.parse_metadata,
        "audit_metadata": payload.audit_metadata,
    }


def _compute_content_hash(payload: ModuleIngestionRequest) -> str:
    canonical = _canonical_payload_for_hash(payload)
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize_severity(raw_value: Any) -> str:
    value = str(raw_value or "medium").strip().lower()
    if value in SEVERITY_RANK:
        return value
    return "medium"


def _derive_priority(severity: str, score: float) -> str:
    if severity == "critical" and score >= 0.8:
        return "p0"
    if severity == "high":
        return "p1"
    if severity == "medium":
        return "p2"
    return "p3"


def _resolve_signal_state(finding: dict, now_dt: datetime) -> str:
    if bool(finding.get("resolved")):
        return "resolved"

    status_text = str(finding.get("status") or "").strip().lower()
    if status_text in {"resolved", "done", "closed"}:
        return "resolved"
    if status_text == "expired":
        return "expired"

    expires_raw = finding.get("expires_at")
    expires_dt = _parse_iso_or_none(str(expires_raw) if expires_raw else None)
    if expires_dt is not None and expires_dt < now_dt:
        return "expired"

    return "active"


def _merge_signal_state(current_state: str, incoming_state: str) -> str:
    rank = {"active": 3, "resolved": 2, "expired": 1}
    return current_state if rank[current_state] >= rank[incoming_state] else incoming_state


def _build_signal_id(tenant_id: str, module: str, entity_scope: dict, signal_code: str) -> str:
    base = json.dumps(
        {
            "tenant_id": tenant_id,
            "module": module,
            "entity_scope": entity_scope,
            "signal_code": signal_code,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
    return f"sig_{digest}"


def _build_signal_summary(module: str, signal_code: str, finding: dict) -> str:
    message = str(finding.get("message") or "").strip()
    if message:
        return message
    return f"{module}:{signal_code}"


def _extract_signal_code(module: str, finding: dict) -> str | None:
    mapping = FINDING_TO_SIGNAL.get(module, {})
    finding_code = str(finding.get("code") or finding.get("finding_type") or "").strip()
    return mapping.get(finding_code)


def _extract_entity_scope(module: str, finding: dict, canonical_rows: list[dict]) -> dict:
    if module == "stock_simple":
        row_id = str(finding.get("row_id") or "").strip()
        sku = str(finding.get("sku") or "").strip()
        if sku:
            return {"entity_type": "item", "entity_id": sku}

        if row_id:
            for row in canonical_rows:
                if str(row.get("row_id") or "") == row_id:
                    row_sku = str(row.get("sku") or "").strip()
                    if row_sku:
                        return {"entity_type": "item", "entity_id": row_sku}
                    return {"entity_type": "item", "entity_id": row_id}
            return {"entity_type": "item", "entity_id": row_id}

        return {"entity_type": "item", "entity_id": "unknown"}

    if module == "expense_evidence":
        req = str(finding.get("request_id") or "").strip()
        if not req and canonical_rows:
            req = str(canonical_rows[0].get("request_id") or "").strip()
        return {"entity_type": "expense_case", "entity_id": req or "unknown"}

    if module == "concili_simple":
        account_id = str(finding.get("account_id") or finding.get("entity_id") or "").strip()
        return {"entity_type": "account", "entity_id": account_id or "unknown"}

    return {"entity_type": "batch", "entity_id": "unknown"}


def _extract_score_confidence(finding: dict, severity: str) -> tuple[float, float]:
    default_score_by_severity = {
        "critical": 0.95,
        "high": 0.85,
        "medium": 0.65,
        "low": 0.40,
        "info": 0.20,
    }

    source = str(finding.get("source") or "RULE").strip().upper()
    default_confidence_by_source = {
        "RULE": 0.90,
        "HERMES": 0.75,
    }

    raw_score = finding.get("score", default_score_by_severity[severity])
    raw_confidence = finding.get("confidence", default_confidence_by_source.get(source, 0.70))

    try:
        score = float(raw_score)
    except Exception:
        score = default_score_by_severity[severity]

    try:
        confidence = float(raw_confidence)
    except Exception:
        confidence = default_confidence_by_source.get(source, 0.70)

    score = max(0.0, min(1.0, score))
    confidence = max(0.0, min(1.0, confidence))
    return score, confidence


def build_normalized_signals_from_payload(
    payload: ModuleIngestionRequest,
    now_dt: datetime | None = None,
) -> list[dict]:
    now_dt = now_dt or datetime.now(timezone.utc)
    now_str = now_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    consolidated: Dict[tuple[str, str, str, str, str], dict] = {}
    canonical_rows = payload.canonical_rows if isinstance(payload.canonical_rows, list) else []

    for idx, finding in enumerate(payload.findings):
        if not isinstance(finding, dict):
            continue

        signal_code = _extract_signal_code(payload.module, finding)
        if not signal_code:
            continue

        entity_scope = _extract_entity_scope(payload.module, finding, canonical_rows)
        key = (
            payload.tenant_id,
            payload.module,
            entity_scope.get("entity_type", "unknown"),
            entity_scope.get("entity_id", "unknown"),
            signal_code,
        )

        severity = _normalize_severity(finding.get("severity"))
        score, confidence = _extract_score_confidence(finding, severity)
        state = _resolve_signal_state(finding, now_dt)
        detected_at = finding.get("detected_at") or finding.get("created_at") or now_str
        updated_at = finding.get("updated_at") or now_str
        expires_at = finding.get("expires_at") or None
        source = str(finding.get("source") or "RULE").strip().upper()
        source = source if source in {"RULE", "HERMES"} else "RULE"
        finding_id = str(finding.get("finding_id") or f"finding_{idx + 1}")

        if key not in consolidated:
            signal_id = _build_signal_id(payload.tenant_id, payload.module, entity_scope, signal_code)
            priority = _derive_priority(severity, score)

            candidate = {
                "signal_version": "normalized_signals.v1",
                "signal_id": signal_id,
                "tenant_id": payload.tenant_id,
                "entity_scope": entity_scope,
                "module": payload.module,
                "signal_code": signal_code,
                "state": state,
                "severity": severity,
                "score": score,
                "confidence": confidence,
                "priority": priority,
                "summary": _build_signal_summary(payload.module, signal_code, finding),
                "evidence": {
                    "finding_ids": [finding_id],
                    "sources": [source],
                    "facts": finding.get("evidence") if isinstance(finding.get("evidence"), dict) else {},
                },
                "lifecycle": {
                    "detected_at": str(detected_at),
                    "updated_at": str(updated_at),
                    "expires_at": str(expires_at) if expires_at else None,
                    "resolved_at": str(finding.get("resolved_at")) if finding.get("resolved_at") else None,
                    "resolution_reason": str(finding.get("resolution_reason")) if finding.get("resolution_reason") else None,
                },
                "links": {
                    "module_ingestion_id": None,
                    "job_id": str(finding.get("job_id")) if finding.get("job_id") else None,
                    "artifact_refs": [],
                },
            }

            normalized = NormalizedSignalV1.model_validate(candidate)
            consolidated[key] = normalized.model_dump()
            continue

        current = consolidated[key]

        current["state"] = _merge_signal_state(str(current["state"]), state)

        current_sev = str(current["severity"])
        if SEVERITY_RANK[severity] > SEVERITY_RANK[current_sev]:
            current["severity"] = severity

        current["score"] = max(float(current["score"]), score)
        current["confidence"] = max(float(current["confidence"]), confidence)
        current["priority"] = _derive_priority(str(current["severity"]), float(current["score"]))

        if finding_id not in current["evidence"]["finding_ids"]:
            current["evidence"]["finding_ids"].append(finding_id)

        if source not in current["evidence"]["sources"]:
            current["evidence"]["sources"].append(source)

        current["lifecycle"]["updated_at"] = now_str

        existing_expires = _parse_iso_or_none(current["lifecycle"].get("expires_at"))
        incoming_expires = _parse_iso_or_none(str(expires_at) if expires_at else None)
        if incoming_expires and (not existing_expires or incoming_expires > existing_expires):
            current["lifecycle"]["expires_at"] = str(expires_at)

        if state == "resolved" and finding.get("resolved_at"):
            current["lifecycle"]["resolved_at"] = str(finding.get("resolved_at"))
            if finding.get("resolution_reason"):
                current["lifecycle"]["resolution_reason"] = str(finding.get("resolution_reason"))

        normalized = NormalizedSignalV1.model_validate(current)
        consolidated[key] = normalized.model_dump()

    return list(consolidated.values())


def _validate_stock_simple_payload(payload: ModuleIngestionRequest) -> None:
    if payload.source_type != "google_sheets":
        raise ValueError("stock_simple solo admite source_type=google_sheets")

    missing_summary = [k for k in REQUIRED_STOCK_SIMPLE_SUMMARY_KEYS if k not in payload.summary]
    if missing_summary:
        raise ValueError(
            "summary incompleto para stock_simple. Faltan: " + ", ".join(sorted(missing_summary))
        )

    for idx, row in enumerate(payload.canonical_rows):
        if not isinstance(row, dict):
            raise ValueError(f"canonical_rows[{idx}] debe ser un objeto")

        missing = [k for k in REQUIRED_STOCK_SIMPLE_ROW_KEYS if k not in row]
        if missing:
            raise ValueError(
                f"canonical_rows[{idx}] incompleto para stock_simple. Faltan: {', '.join(sorted(missing))}"
            )

        producto = str(row.get("producto") or "").strip()
        if not producto:
            raise ValueError(f"canonical_rows[{idx}].producto debe ser no vacio")

        for field in ("stock_actual", "stock_minimo", "consumo_promedio_diario"):
            if not isinstance(row.get(field), (int, float)):
                raise ValueError(f"canonical_rows[{idx}].{field} debe ser numero")

        if not isinstance(row.get("requires_review"), bool):
            raise ValueError(f"canonical_rows[{idx}].requires_review debe ser boolean")

    for idx, finding in enumerate(payload.findings):
        if not isinstance(finding, dict):
            raise ValueError(f"findings[{idx}] debe ser un objeto")
        if not str(finding.get("code") or "").strip():
            raise ValueError(f"findings[{idx}].code es requerido para stock_simple")


def _validate_expense_row_shape(row: dict, idx: int) -> None:
    try:
        if hasattr(ExpenseEvidenceFrozenRow, "model_validate"):
            ExpenseEvidenceFrozenRow.model_validate(row)
        else:
            ExpenseEvidenceFrozenRow.parse_obj(row)
    except Exception as exc:
        raise ValueError(
            f"canonical_rows[{idx}] invalido para expense_evidence (shape borde congelado): {exc}"
        ) from exc


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
    if payload.contract_version != "module-ingestions.v2":
        raise ValueError("contract_version invalido: usa module-ingestions.v2")

    _parse_generated_at(payload.generated_at)

    if payload.module == "stock_simple":
        _validate_stock_simple_payload(payload)
        return

    if payload.module == "expense_evidence":
        _validate_expense_evidence_payload(payload)
        return

    raise ValueError(f"Modulo no soportado: {payload.module}")


def persist_module_ingestion(payload: ModuleIngestionRequest) -> Dict[str, object]:
    _validate_payload_for_module(payload)

    print("  Substep 1: validation passed")
    computed_hash = _compute_content_hash(payload)
    print("  Substep 2: hash computed:", computed_hash)
    if payload.content_hash:
        _validate_content_hash_format(payload.content_hash)
        provided_hash = payload.content_hash.lower()
        if provided_hash != computed_hash:
            raise ValueError("content_hash invalido: no coincide con el payload")
        content_hash = provided_hash
    else:
        content_hash = computed_hash

    tenant_part = _safe_path_part(payload.tenant_id)
    module_part = _safe_path_part(payload.module)
    dedupe_object = f"tenant_{tenant_part}/module_ingestions/{module_part}/_dedupe/{content_hash}.json"
    print("  Substep 3: checking dedupe at", dedupe_object)
    existing = _load_json_or_none(dedupe_object)
    print("  Substep 4: dedupe check done, exists:", existing is not None)

    if existing and existing.get("ingestion_id"):
        result_object = existing.get("result_object")
        existing_result = _load_json_or_none(result_object) if result_object else None
        artifacts = (existing_result or {}).get("artifacts") or {}

        action_engine = ActionEngine()
        action_store = ActionStore()

        digest_path = artifacts.get("digest")
        existing_digest = (_load_json_or_none(digest_path) if digest_path else {}) or {}

        actions = action_engine.build_actions(
            tenant_id=payload.tenant_id,
            digest=existing_digest,
            module_suggested_actions=payload.suggested_actions,
        )

        action_store.save_latest_actions(
            tenant_id=payload.tenant_id,
            actions=actions,
        )

        return {
            "ingestion_id": existing["ingestion_id"],
            "contract_version": "module-ingestions.v2",
            "tenant_id": payload.tenant_id,
            "module": payload.module,
            "status": "accepted_deduped",
            "deduplicated": True,
            "deduped": True,
            "content_hash": content_hash,
            "artifacts": artifacts,
        }

    ingestion_id = build_ingestion_id()
    prefix = f"tenant_{tenant_part}/module_ingestions/{module_part}/{ingestion_id}"

    payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    payload_dict["content_hash"] = content_hash

    print("  Substep 5: generating signals and artifacts")
    normalized_signals = build_normalized_signals_from_payload(payload)
    print("  Substep 6: signals generated, count:", len(normalized_signals))

    artifacts = {
        "input": f"{prefix}/input.json",
        "canonical_rows": f"{prefix}/canonical_rows.json",
        "findings": f"{prefix}/findings.json",
        "normalized_signals": f"{prefix}/normalized_signals.json",
        "summary": f"{prefix}/summary.json",
        "suggested_actions": f"{prefix}/suggested_actions.json",
        "request_meta": f"{prefix}/request_meta.json",
        "digest": f"{prefix}/digest.json",
        "result": f"{prefix}/result.json",
    }

    print("  Substep 7: uploading artifacts")
    _upload_json(artifacts["input"], payload_dict)
    _upload_json(artifacts["canonical_rows"], payload.canonical_rows)
    _upload_json(artifacts["findings"], payload.findings)
    _upload_json(artifacts["normalized_signals"], normalized_signals)
    _upload_json(artifacts["summary"], payload.summary)
    _upload_json(artifacts["suggested_actions"], payload.suggested_actions)

    print("  Substep 8: building daily digest")
    summaries_by_module = {payload.module: payload.summary}
    daily_digest = build_daily_digest_v1(
        tenant_id=payload.tenant_id,
        normalized_signals=normalized_signals,
        summaries_by_module=summaries_by_module,
    )

    print("  Substep 9: building actions with ActionEngine")
    action_engine = ActionEngine()
    action_store = ActionStore()

    actions = action_engine.build_actions(
        tenant_id=payload.tenant_id,
        digest=daily_digest,
        module_suggested_actions=payload.suggested_actions,
    )

    print("  Substep 10: saving actions to ActionStore")
    action_store.save_latest_actions(
        tenant_id=payload.tenant_id,
        actions=actions,
    )

    _upload_json(artifacts["digest"], daily_digest)

    request_meta = {
        "contract_version": payload.contract_version,
        "source_channel": payload.source_channel,
        "tenant_id": payload.tenant_id,
        "module": payload.module,
        "source_type": payload.source_type,
        "generated_at": payload.generated_at,
        "content_hash": content_hash,
        "parse_metadata": payload.parse_metadata,
        "audit_metadata": payload.audit_metadata,
        "dedupe_key": f"{payload.tenant_id}:{payload.module}:{content_hash}",
        "received_at": now_iso(),
    }
    _upload_json(artifacts["request_meta"], request_meta)

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
        "contract_version": payload.contract_version,
        "source_channel": payload.source_channel,
        "tenant_id": payload.tenant_id,
        "module": payload.module,
        "status": "accepted",
        "deduplicated": False,
        "deduped": False,
        "content_hash": content_hash,
        "artifacts": artifacts,
        "accepted_at": now_iso(),
        "dedupe_key": f"{payload.tenant_id}:{payload.module}:{content_hash}",
    }
    _upload_json(artifacts["result"], result_payload)

    _upload_json(
        dedupe_object,
        {
            "ingestion_id": ingestion_id,
            "tenant_id": payload.tenant_id,
            "module": payload.module,
            "content_hash": content_hash,
            "result_object": artifacts["result"],
            "created_at": now_iso(),
        },
    )

    index_object = f"module_ingestion_index/{ingestion_id}.json"
    _upload_json(
        index_object,
        {
            "ingestion_id": ingestion_id,
            "tenant_id": payload.tenant_id,
            "module": payload.module,
            "result_object": artifacts["result"],
            "created_at": now_iso(),
        },
    )

    return {
        "ok": True,
        "ingestion_id": ingestion_id,
        "contract_version": payload.contract_version,
        "source_channel": payload.source_channel,
        "tenant_id": payload.tenant_id,
        "module": payload.module,
        "status": "accepted",
        "deduplicated": False,
        "deduped": False,
        "content_hash": content_hash,
        "artifacts": artifacts,
    }


def get_module_ingestion(ingestion_id: str) -> Dict[str, object]:
    index_object = f"module_ingestion_index/{ingestion_id}.json"
    index_data = _load_json_or_none(index_object)
    if not index_data:
        raise FileNotFoundError(ingestion_id)

    result_object = index_data.get("result_object")
    if not result_object:
        raise FileNotFoundError(ingestion_id)

    result_data = _load_json_or_none(result_object)
    if not result_data:
        raise FileNotFoundError(ingestion_id)

    return {
        "ok": True,
        "ingestion_id": result_data.get("ingestion_id", ingestion_id),
        "contract_version": result_data.get("contract_version", "module-ingestions.v2"),
        "tenant_id": result_data.get("tenant_id"),
        "module": result_data.get("module"),
        "status": result_data.get("status"),
        "deduplicated": bool(result_data.get("deduplicated", result_data.get("deduped", False))),
        "deduped": bool(result_data.get("deduped", False)),
        "content_hash": result_data.get("content_hash"),
        "artifacts": result_data.get("artifacts") or {},
        "created_at": index_data.get("created_at"),
    }



