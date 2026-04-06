from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class ActionStore:
    def __init__(self, storage_root: str = "storage") -> None:
        self.storage_root = Path(storage_root)

    def save_latest_actions(self, tenant_id: str, actions: list[dict]) -> None:
        base = self._base_path(tenant_id)
        self._ensure_dir(base)

        payload = {
            "tenant_id": tenant_id,
            "generated_at": self._now_iso(),
            "actions": actions if isinstance(actions, list) else [],
        }

        target = base / "latest.json"
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_latest_actions(self, tenant_id: str) -> dict:
        target = self._base_path(tenant_id) / "latest.json"
        if not target.exists():
            return {
                "tenant_id": tenant_id,
                "generated_at": None,
                "actions": [],
            }

        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            return {
                "tenant_id": data.get("tenant_id", tenant_id),
                "generated_at": data.get("generated_at"),
                "actions": data.get("actions", []),
            }
        except Exception:
            return {
                "tenant_id": tenant_id,
                "generated_at": None,
                "actions": [],
            }

    def _base_path(self, tenant_id: str) -> Path:
        return self.storage_root / f"tenant_{tenant_id}" / "actions"

    def _ensure_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")