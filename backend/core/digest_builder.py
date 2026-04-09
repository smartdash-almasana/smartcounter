from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


class DigestBuilder:
    def __init__(self, artifact_store: Any) -> None:
        self.store = artifact_store

    def build_latest(self, tenant_id: str) -> dict[str, Any]:
        artifacts = self._load_latest_results(tenant_id)

        signals = self._extract_signals(artifacts)
        summary = self._build_summary_block(artifacts)
        alerts = self._build_alerts(signals)
        suggested_actions = self._build_suggested_actions(alerts)
        question = self._build_question(alerts)

        digest: dict[str, Any] = {
            "tenant_id": tenant_id,
            "generated_at": self._now_iso(),
            "summary": summary,
            "alerts": alerts,
            "suggested_actions": suggested_actions,
            "question": question,
        }

        self._persist_digest(tenant_id, digest)
        return digest

    def _load_latest_results(self, tenant_id: str) -> list[dict[str, Any]]:
        tenant_root = self.store._tenant_root(tenant_id) / "module_ingestions"
        results: list[dict[str, Any]] = []

        if not tenant_root.exists() or not tenant_root.is_dir():
            return results

        for module_dir in sorted(tenant_root.iterdir(), key=lambda p: p.name):
            if not module_dir.is_dir():
                continue

            latest_file = module_dir / "latest.json"
            if not latest_file.exists() or not latest_file.is_file():
                continue

            try:
                latest = self._read_json(latest_file)
                if not isinstance(latest, dict):
                    continue

                result_path = latest.get("result_path")
                if not result_path:
                    continue

                result_file = Path(str(result_path))
                if not result_file.exists() or not result_file.is_file():
                    continue

                result = self._read_json(result_file)
                if isinstance(result, dict):
                    results.append(result)
            except Exception:
                continue

        return results

    def _read_json(self, path: Path) -> Any:
        reader = getattr(self.store, "_read_json", None)
        if callable(reader):
            return reader(path)

        reader_or_none = getattr(self.store, "_read_json_or_none", None)
        if callable(reader_or_none):
            data = reader_or_none(path)
            if data is None:
                raise ValueError("json_not_found")
            return data

        raise ValueError("json_reader_not_available")

    def _extract_signals(self, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []

        for result in artifacts:
            raw_alerts = result.get("alerts", [])
            if not isinstance(raw_alerts, list):
                continue

            module_name = str(result.get("module") or "unknown")
            for alert in raw_alerts:
                if not isinstance(alert, dict):
                    continue

                message = str(alert.get("message") or "").strip()
                if not message:
                    continue

                signals.append(
                    {
                        "severity": self._normalize_severity(alert.get("severity")),
                        "message": message,
                        "entity": str(alert.get("entity") or alert.get("entity_ref") or ""),
                        "module": module_name,
                    }
                )

        return signals

    def _build_summary_block(self, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
        invalid_rows = 0
        for result in artifacts:
            summary = result.get("summary", {})
            if not isinstance(summary, dict):
                continue

            raw_invalid = summary.get("invalid_rows", 0)
            try:
                invalid_rows += int(raw_invalid)
            except (TypeError, ValueError):
                continue

        if invalid_rows > 0:
            return {
                "main_issue": "Datos incompletos detectados",
                "impact": "No se pueden procesar correctamente los datos",
                "items_affected": invalid_rows,
                "human_readable": "Se detectaron datos incompletos que impiden procesar correctamente la información",
            }

        return {
            "main_issue": "Sin problemas críticos detectados",
            "impact": "La información puede procesarse correctamente",
            "items_affected": 0,
            "human_readable": "No se detectaron datos incompletos y la información puede procesarse correctamente",
        }

    def _build_alerts(self, signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        priority_map = {"high": 3, "medium": 2, "low": 1}
        grouped: dict[tuple[str, str], dict[str, Any]] = {}

        for signal in signals:
            raw_message = str(signal.get("message") or "").strip()
            if not raw_message:
                continue

            severity = self._normalize_severity(signal.get("severity"))
            entity = str(signal.get("entity") or "")
            key = (raw_message.lower(), entity)

            if key not in grouped:
                grouped[key] = {
                    "message": raw_message,
                    "count": 1,
                    "severity": severity,
                    "entity": entity,
                }
                continue

            grouped[key]["count"] = int(grouped[key]["count"]) + 1
            if priority_map.get(severity, 0) > priority_map.get(str(grouped[key]["severity"]), 0):
                grouped[key]["severity"] = severity

        sorted_groups = sorted(
            grouped.values(),
            key=lambda group: (
                -priority_map.get(str(group.get("severity") or "").lower(), 0),
                str(group.get("message") or ""),
            ),
        )

        alerts: list[dict[str, Any]] = []
        for group in sorted_groups[:3]:
            alerts.append(
                {
                    "severity": group.get("severity"),
                    "message": self._build_aggregated_alert_message(
                        raw_message=str(group.get("message") or ""),
                        count=int(group.get("count") or 0),
                    ),
                    "entity": group.get("entity"),
                }
            )

        return alerts

    def _build_question(self, alerts: list[dict[str, Any]]) -> str:
        if not alerts:
            return "Todo está en orden. ¿Querés revisar otro módulo?"
        return "¿Querés completar los datos faltantes para poder procesar esta información?"

    def _build_suggested_actions(self, alerts: list[dict[str, Any]]) -> list[dict[str, str]]:
        actions: list[dict[str, str]] = []

        for alert in alerts[:3]:
            message = str(alert.get("message") or "").lower()
            severity = self._normalize_severity(alert.get("severity"))

            if "falta monto" in message or "datos incompletos" in message:
                actions.append(
                    {
                        "type": "completar_datos",
                        "title": "Completar montos faltantes",
                        "description": "Hay registros sin monto. Completá los valores para poder procesarlos correctamente.",
                        "priority": "high",
                    }
                )
            else:
                actions.append(
                    {
                        "type": "revisar_datos",
                        "title": "Revisar datos",
                        "description": "Se detectaron inconsistencias que requieren revisión.",
                        "priority": severity,
                    }
                )

        return actions

    def _persist_digest(self, tenant_id: str, digest: dict[str, Any]) -> None:
        self.store.save(
            tenant_id=tenant_id,
            artifact_type="digest",
            data=digest,
        )

    def _now_iso(self) -> str:
        return datetime.utcnow().isoformat()

    def _normalize_severity(self, severity: Any) -> str:
        value = str(severity or "").strip().lower()
        if value in {"high", "medium", "low"}:
            return value
        return "low"

    def _contextualize_alert_message(self, message: str) -> str:
        normalized = message.strip()
        if not normalized:
            return "Registro incompleto detectado"

        lowered = normalized.lower()
        if lowered == "falta monto":
            return "Registro incompleto: falta monto en una operación detectada"

        if lowered.startswith("falta "):
            field = normalized[6:].strip()
            if field:
                return f"Registro incompleto: falta {field} en una operación detectada"

        return normalized

    def _build_aggregated_alert_message(self, raw_message: str, count: int) -> str:
        normalized = raw_message.strip()
        if count <= 0:
            count = 1

        lowered = normalized.lower()
        if lowered == "falta monto":
            if count == 1:
                return "1 registro incompleto: falta monto en una operación detectada"
            return f"{count} registros incompletos: falta monto en operaciones detectadas"

        if lowered.startswith("falta "):
            field = normalized[6:].strip()
            if field:
                if count == 1:
                    return f"1 registro incompleto: falta {field} en una operación detectada"
                return f"{count} registros incompletos: falta {field} en operaciones detectadas"

        if count == 1:
            return f"1 alerta detectada: {self._contextualize_alert_message(normalized)}"
        return f"{count} alertas detectadas: {self._contextualize_alert_message(normalized)}"
