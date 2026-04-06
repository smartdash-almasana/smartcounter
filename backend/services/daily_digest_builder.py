from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.schemas.daily_digest import DailyDigestV1

PRIORITY_RANK = {
    "p0": 0,
    "p1": 1,
    "p2": 2,
    "p3": 3,
}

SEVERITY_RANK = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}

MAX_VISIBLE_ALERTS = 7


def _to_float(value: Any, default: float) -> float:
    try:
        casted = float(value)
    except Exception:
        return default
    return max(0.0, min(1.0, casted))


def _normalize_priority(value: Any) -> str:
    candidate = str(value or "p2").strip().lower()
    if candidate in PRIORITY_RANK:
        return candidate
    return "p2"


def _normalize_severity(value: Any) -> str:
    candidate = str(value or "medium").strip().lower()
    if candidate in SEVERITY_RANK:
        return candidate
    return "medium"


def _sort_key(signal: Dict[str, Any]) -> tuple[int, int, float]:
    priority = _normalize_priority(signal.get("priority"))
    severity = _normalize_severity(signal.get("severity"))
    score = _to_float(signal.get("score"), 0.0)
    return (
        PRIORITY_RANK[priority],
        -SEVERITY_RANK[severity],
        -score,
    )


def _build_question(top_alert: Dict[str, Any] | None) -> Dict[str, Any]:
    if not top_alert:
        return {
            "texto": "No hay alertas activas de alta prioridad hoy. ¿Querés revisar tendencias del día?",
            "signal_id_referencia": None,
            "prioridad_objetivo": None,
        }

    priority = _normalize_priority(top_alert.get("priority"))
    signal_id = str(top_alert.get("signal_id") or "")
    summary = str(top_alert.get("summary") or "alerta principal").strip()

    return {
        "texto": f"¿Cómo resolvemos primero esta alerta {priority}: {summary}?",
        "signal_id_referencia": signal_id or None,
        "prioridad_objetivo": priority,
    }


def build_daily_digest_v1(
    tenant_id: str,
    normalized_signals: List[Dict[str, Any]],
    summaries_by_module: Dict[str, Dict[str, Any]] | None = None,
    generated_at: datetime | None = None,
    max_visible_alerts: int = MAX_VISIBLE_ALERTS,
) -> Dict[str, Any]:
    now_dt = generated_at or datetime.now(timezone.utc)
    now_iso = now_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    date_iso = now_iso[:10]

    active_signals: List[Dict[str, Any]] = []
    for signal in normalized_signals or []:
        if not isinstance(signal, dict):
            continue
        state = str(signal.get("state") or "").strip().lower()
        if state != "active":
            continue
        active_signals.append(signal)

    sorted_active = sorted(active_signals, key=_sort_key)
    capped_alerts = sorted_active[: max(1, int(max_visible_alerts))]

    alert_items: List[Dict[str, Any]] = []
    for signal in capped_alerts:
        alert_items.append(
            {
                "signal_id": str(signal.get("signal_id") or ""),
                "module": str(signal.get("module") or "unknown"),
                "signal_code": str(signal.get("signal_code") or "unknown_signal"),
                "severity": _normalize_severity(signal.get("severity")),
                "priority": _normalize_priority(signal.get("priority")),
                "score": _to_float(signal.get("score"), 0.0),
                "summary": str(signal.get("summary") or "").strip() or "Sin resumen",
                "entity_scope": signal.get("entity_scope") if isinstance(signal.get("entity_scope"), dict) else {},
            }
        )

    modules_with_alerts = sorted({str(item["module"]) for item in alert_items})
    high_priority_count = sum(1 for item in alert_items if item["priority"] in {"p0", "p1"})

    digest_payload = {
        "digest_version": "daily_digest.v1",
        "tenant_id": tenant_id,
        "generated_at": now_iso,
        "foto_de_hoy": {
            "fecha": date_iso,
            "total_senales_activas": len(active_signals),
            "total_alertas_visibles": len(alert_items),
            "total_alertas_alta_prioridad": high_priority_count,
            "modulos_con_alertas": modules_with_alerts,
            "resumen_modulos": summaries_by_module or {},
        },
        "lo_que_importa_ahora": {
            "alertas": alert_items,
        },
        "pregunta_del_dia": _build_question(alert_items[0] if alert_items else None),
    }

    validated = DailyDigestV1.model_validate(digest_payload)
    return validated.model_dump()
