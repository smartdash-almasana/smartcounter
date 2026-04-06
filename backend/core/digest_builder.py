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
        question = self._build_question(alerts)

        digest: dict[str, Any] = {
            "tenant_id": tenant_id,
            "generated_at": self._now_iso(),
            "summary": summary,
            "alerts": alerts,
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
        total_findings = 0
        modules: list[dict[str, Any]] = []

        for result in artifacts:
            summary = result.get("summary", {})
            if not isinstance(summary, dict):
                summary = {}

            alerts = result.get("alerts", [])
            if isinstance(alerts, list):
                total_findings += len(alerts)

            modules.append(
                {
                    "module": result.get("module") or "unknown",
                    "summary": summary,
                }
            )

        return {
            "modules": modules,
            "total_findings": total_findings,
        }

    def _build_alerts(self, signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        priority_map = {"high": 3, "medium": 2, "low": 1}

        sorted_signals = sorted(
            signals,
            key=lambda signal: (
                -priority_map.get(str(signal.get("severity", "")).lower(), 0),
                str(signal.get("message") or ""),
                str(signal.get("entity") or ""),
            ),
        )

        alerts: list[dict[str, Any]] = []
        for signal in sorted_signals[:3]:
            alerts.append(
                {
                    "severity": signal.get("severity"),
                    "message": signal.get("message"),
                    "entity": signal.get("entity"),
                }
            )

        return alerts

    def _build_question(self, alerts: list[dict[str, Any]]) -> str:
        if not alerts:
            return "Todo está en orden. ¿Querés revisar otro módulo?"

        top = alerts[0]

        if top.get("severity") == "high":
            return f"Hay un problema crítico: {top.get('message')}. ¿Querés resolverlo ahora?"

        if top.get("severity") == "medium":
            return f"Esto requiere atención: {top.get('message')}. ¿Lo revisamos?"

        return "Hay pequeños ajustes pendientes. ¿Querés verlos?"

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
