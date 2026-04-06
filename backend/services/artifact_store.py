from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


class ArtifactStore:
    def __init__(self, base_path: str = "storage") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _safe_part(self, value: str, fallback: str = "unknown") -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", str(value or "").strip())
        return cleaned or fallback

    def _tenant_root(self, tenant_id: str) -> Path:
        tenant = self._safe_part(tenant_id)
        path = self.base_path / f"tenant_{tenant}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _module_base_path(self, tenant_id: str, module: str) -> Path:
        module_part = self._safe_part(module)
        base = self._tenant_root(tenant_id) / "module_ingestions" / module_part
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _ingestion_path(self, tenant_id: str, module: str, ingestion_id: str) -> Path:
        ingestion_part = self._safe_part(ingestion_id)
        path = self._module_base_path(tenant_id, module) / ingestion_part
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)

    def _read_json_or_none(self, path: Path) -> Any | None:
        if not path.exists() or not path.is_file():
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return None

    def save_ingestion_artifacts(
        self,
        tenant_id: str,
        module: str,
        ingestion_id: str,
        artifacts: dict[str, Any],
    ) -> dict[str, str]:
        base = self._ingestion_path(tenant_id, module, ingestion_id)
        required_keys = [
            "input",
            "canonical_rows",
            "findings",
            "summary",
            "suggested_actions",
            "result",
        ]

        normalized: dict[str, Any] = dict(artifacts or {})
        normalized.setdefault("input", {})
        normalized.setdefault("canonical_rows", [])
        normalized.setdefault("findings", [])
        normalized.setdefault("summary", {})
        normalized.setdefault("suggested_actions", [])
        normalized.setdefault("result", {})

        paths: dict[str, str] = {}
        for key in required_keys:
            filename = f"{self._safe_part(key)}.json"
            full = base / filename
            self._write_json(full, normalized.get(key))
            paths[key] = str(full)

        for key, value in normalized.items():
            if key in paths:
                continue
            filename = f"{self._safe_part(key)}.json"
            full = base / filename
            self._write_json(full, value)
            paths[key] = str(full)

        return paths

    def save_module_latest(
        self,
        tenant_id: str,
        module: str,
        latest_payload: dict[str, Any],
    ) -> str:
        base = self._module_base_path(tenant_id, module)
        base.mkdir(parents=True, exist_ok=True)
        path = base / "latest.json"
        self._write_json(path, latest_payload)
        return str(path)

    def save_digest(self, tenant_id: str, digest: dict[str, Any]) -> str:
        full = self._tenant_root(tenant_id) / "digests" / "latest.json"
        self._write_json(full, digest)
        return str(full)

    def save(self, tenant_id: str, artifact_type: str, data: dict[str, Any]) -> None:
        if artifact_type == "digest":
            self.save_digest(tenant_id, data)

    def _parse_iso(self, value: Any) -> datetime:
        raw = str(value or "").strip()
        if not raw:
            return datetime.min
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return datetime.min

    def _load_ingestion_record(self, ingestion_dir: Path, module: str) -> dict[str, Any] | None:
        result = self._read_json_or_none(ingestion_dir / "result.json")
        findings = self._read_json_or_none(ingestion_dir / "findings.json")
        summary = self._read_json_or_none(ingestion_dir / "summary.json")
        suggested_actions = self._read_json_or_none(ingestion_dir / "suggested_actions.json")
        canonical_rows = self._read_json_or_none(ingestion_dir / "canonical_rows.json")

        generated_at = None
        if isinstance(result, dict):
            generated_at = result.get("generated_at") or result.get("accepted_at")

        if generated_at is None:
            try:
                generated_at = datetime.fromtimestamp(ingestion_dir.stat().st_mtime).isoformat()
            except Exception:
                generated_at = ""

        return {
            "module": module,
            "ingestion_id": ingestion_dir.name,
            "generated_at": generated_at,
            "canonical_rows": canonical_rows if isinstance(canonical_rows, list) else [],
            "findings": findings if isinstance(findings, list) else [],
            "summary": summary if isinstance(summary, dict) else {},
            "suggested_actions": suggested_actions if isinstance(suggested_actions, list) else [],
            "result": result if isinstance(result, dict) else {},
        }

    def load_latest_ingestions(self, tenant_id: str, limit: int = 5) -> list[dict[str, Any]]:
        tenant_root = self._tenant_root(tenant_id)
        base = tenant_root / "module_ingestions"

        if not base.exists() or not base.is_dir():
            return []

        results: list[dict[str, Any]] = []

        for module_dir in sorted(base.iterdir(), key=lambda p: p.name):
            if not module_dir.is_dir():
                continue
            module = module_dir.name

            for ingestion_dir in sorted(module_dir.iterdir(), key=lambda p: p.name):
                if not ingestion_dir.is_dir():
                    continue
                record = self._load_ingestion_record(ingestion_dir, module)
                if record is not None:
                    results.append(record)

        results.sort(key=lambda item: self._parse_iso(item.get("generated_at")), reverse=True)
        return results[: max(1, int(limit))]

    def get_latest_by_tenant(self, tenant_id: str, limit: int = 20) -> list[dict[str, Any]]:
        records = self.load_latest_ingestions(tenant_id, limit=limit * 4)

        latest_by_module: dict[str, dict[str, Any]] = {}
        for record in records:
            module = str(record.get("module") or "unknown")
            if module in latest_by_module:
                continue
            latest_by_module[module] = {
                "module": module,
                "findings": record.get("findings", []),
                "summary": record.get("summary", {}),
                "suggested_actions": record.get("suggested_actions", []),
                "generated_at": record.get("generated_at"),
            }
            if len(latest_by_module) >= max(1, int(limit)):
                break

        return list(latest_by_module.values())
