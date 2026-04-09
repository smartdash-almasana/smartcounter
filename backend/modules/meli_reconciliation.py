from __future__ import annotations

from typing import Any

from backend.services.action_orchestrator import create_action_jobs_from_suggestions


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def analyze_meli_reconciliation(rows: list[dict]) -> dict:
    findings: list[dict] = []
    suggested_actions: list[dict] = []

    total_orders = 0
    orders_with_diff = 0
    total_diff_amount = 0.0

    safe_rows = rows if isinstance(rows, list) else []

    for row in safe_rows:
        if not isinstance(row, dict):
            continue

        total_orders += 1

        order_id = str(row.get("order_id") or "unknown")
        amount_expected = _to_float(row.get("amount_expected"))
        amount_paid = _to_float(row.get("amount_paid"))
        diff = amount_expected - amount_paid

        if abs(diff) > 0:
            orders_with_diff += 1
            total_diff_amount += diff

            findings.append(
                {
                    "severity": "high",
                    "message": f"Diferencia detectada en orden {order_id}",
                    "entity": order_id,
                    "diff": diff,
                    "money_impact": abs(diff),
                }
            )

    if orders_with_diff > 0:
        suggested_actions.append(
            {
                "action_type": "generar_documento",
                "title": "Resumen de diferencias de conciliación",
                "description": "Se detectaron diferencias entre montos esperados y pagos recibidos",
                "economic_impact": abs(total_diff_amount),
                "payload": {
                    "format": "pdf",
                    "template": "meli_reconciliation_diff",
                    "data": {
                        "orders_with_diff": orders_with_diff,
                        "total_diff_amount": total_diff_amount,
                    },
                },
            }
        )

    summary = {
        "total_orders": total_orders,
        "orders_with_diff": orders_with_diff,
        "total_diff_amount": total_diff_amount,
        "estimated_recoverable_amount": abs(total_diff_amount),
    }

    return {
        "canonical_rows": safe_rows,
        "findings": findings,
        "summary": summary,
        "suggested_actions": suggested_actions,
    }


def run_meli_reconciliation(tenant_id: str, rows: list[dict]) -> dict:
    result = analyze_meli_reconciliation(rows)

    action_jobs = create_action_jobs_from_suggestions(
        tenant_id=tenant_id,
        suggested_actions=result.get("suggested_actions", []),
        context={
            "module": "meli_reconciliation",
            "summary": result.get("summary", {}),
        },
    )

    result["action_jobs"] = action_jobs
    return result
