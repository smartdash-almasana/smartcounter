from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.adapters.message_adapter.message_adapter import MessageAdapter

router = APIRouter(tags=["message-ingest"])


class MessageIngestRequest(BaseModel):
    tenant_id: str
    text: str


def _build_module_ingestion_payload(result: dict, tenant_id: str) -> dict:
    raw_rows = result.get("canonical_rows")
    canonical_rows = raw_rows if isinstance(raw_rows, list) else []

    stock_rows = []
    for idx, row in enumerate(canonical_rows):
        if not isinstance(row, dict):
            continue

        producto = str(row.get("entity") or "").strip() or "unknown"
        raw_amount = row.get("amount", 0.0)
        try:
            stock_actual = float(raw_amount)
        except (TypeError, ValueError):
            stock_actual = 0.0

        stock_rows.append(
            {
                "row_id": f"msg_{idx + 1}",
                "producto": producto,
                "stock_actual": stock_actual,
                "stock_minimo": 1.0,
                "consumo_promedio_diario": 1.0,
                "requires_review": bool(stock_actual <= 1.0),
            }
        )

    raw_findings = result.get("findings")
    findings = raw_findings if isinstance(raw_findings, list) else []
    stock_findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue

        severity = str(finding.get("severity") or "low").strip().lower()
        code = (
            "critical_stock_detected"
            if severity in {"critical", "high"}
            else "low_stock_detected"
        )
        stock_findings.append(
            {
                "code": code,
                "message": str(finding.get("message") or "message adapter finding"),
                "severity": severity if severity in {"critical", "high", "medium", "low"} else "low",
            }
        )

    generated_at = result.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at.strip():
        generated_at = datetime.now(timezone.utc).isoformat()

    raw_actions = result.get("suggested_actions")
    suggested_actions = raw_actions if isinstance(raw_actions, list) else []

    return {
        "contract_version": "module-ingestions.v2",
        "source_channel": "api",
        "tenant_id": tenant_id,
        "module": "stock_simple",
        "source_type": "google_sheets",
        "generated_at": generated_at,
        "canonical_rows": stock_rows,
        "findings": stock_findings,
        "summary": {
            "total_rows": len(stock_rows),
            "valid_rows": len(stock_rows),
            "invalid_rows": 0,
        },
        "suggested_actions": suggested_actions,
    }


@router.post("/message-ingest")
async def message_ingest(payload: MessageIngestRequest) -> dict[str, str]:
    adapter = MessageAdapter()

    try:
        result = adapter.process(
            payload.text,
            metadata={"tenant_id": payload.tenant_id},
        )
        module_payload = _build_module_ingestion_payload(result, payload.tenant_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="core error") from exc

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/module-ingestions",
                json=module_payload,
            )
            response.raise_for_status()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="request error") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="core error") from exc

    return {
        "status": "processed",
        "module": "message_adapter",
    }
