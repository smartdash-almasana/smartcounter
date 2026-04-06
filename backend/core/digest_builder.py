from __future__ import annotations

from datetime import datetime
from typing import Any


class DigestBuilder:
    def __init__(self, artifact_store: Any) -> None:
        self.store = artifact_store

    def build_latest(self, tenant_id: str) -> dict[str, Any]:
        artifacts = self._load_latest_artifacts(tenant_id)

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

    def _load_latest_artifacts(self, tenant_id: str) -> list[dict[str, Any]]:
        raw = self.store.get_latest_by_tenant(tenant_id)
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        return []

    def _extract_signals(self, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []

        for art in artifacts:
            findings = art.get("findings", [])
            if not isinstance(findings, list):
                continue

            module_name = str(art.get("module") or "unknown")
            for finding in findings:
                if not isinstance(finding, dict):
                    continue
                signals.append(
                    {
                        "severity": self._normalize_severity(finding.get("severity")),
                        "message": str(finding.get("message") or ""),
                        "entity": str(finding.get("entity_ref") or ""),
                        "module": module_name,
                    }
                )

        return signals

    def _build_summary_block(self, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
        total_findings = 0
        modules: list[dict[str, Any]] = []

        for art in artifacts:
            summary = art.get("summary", {})
            if not isinstance(summary, dict):
                summary = {}

            findings_count = summary.get("findings_count", 0)
            if isinstance(findings_count, (int, float)):
                total_findings += int(findings_count)

            modules.append(
                {
                    "module": art.get("module") or "unknown",
                    "rows": summary.get("total_rows"),
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
            key=lambda signal: priority_map.get(str(signal.get("severity", "")).lower(), 0),
            reverse=True,
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
