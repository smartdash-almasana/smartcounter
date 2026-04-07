from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


class ActionEngine:
    def build_actions(
        self,
        tenant_id: str,
        digest: dict,
        module_suggested_actions: list[dict],
        debug: bool = False,
    ) -> list[dict]:
        actions: list[dict] = []

        alerts = digest.get("lo_que_importa_ahora", {}).get("alertas", [])
        if isinstance(alerts, list):
            for alert in alerts:
                if isinstance(alert, dict):
                    actions.append(self._map_alert_to_action(alert, debug=debug))

        if isinstance(module_suggested_actions, list):
            for action in module_suggested_actions:
                if isinstance(action, dict):
                    actions.append(self._map_suggested_action(action, debug=debug))

        actions = self._deduplicate(actions)
        actions = self._sort_by_priority(actions)
        return actions

    def _map_alert_to_action(self, alert: dict, debug: bool = False) -> dict:
        module = str(alert.get("module") or "unknown").strip()
        severity = str(alert.get("severity") or "").strip()
        message = str(alert.get("message") or "").strip()

        action = {
            "id": self._generate_id(),
            "type": "review_issue",
            "priority": self._assign_priority(severity),
            "title": self._generate_title(
                {
                    "module": module,
                    "title": "[MODULE] Acción requerida",
                    "type": "review_issue",
                }
            ),
            "description": self._generate_description(
                {
                    "description": message,
                    "message": message,
                    "type": "review_issue",
                }
            ),
            "module": module,
            "source_ref": str(alert.get("source_ref") or "digest_alert").strip(),
            "status": "pending",
            "created_at": self._now_iso(),
        }

        if debug:
            action["debug_source"] = "alert"

        return self._normalize_action(action)

    def _map_suggested_action(self, action: dict, debug: bool = False) -> dict:
        module = str(action.get("module") or "unknown").strip()
        payload = action.get("payload")
        payload = payload if isinstance(payload, dict) else {}

        severity = payload.get("severity")
        priority = self._assign_priority(severity if severity is not None else "medium")

        action_type = str(action.get("type") or "review_issue").strip()

        mapped = {
            "id": self._generate_id(),
            "type": action_type,
            "priority": priority,
            "title": self._generate_title(
                {
                    "module": module,
                    "title": action.get("title"),
                    "type": action_type,
                }
            ),
            "description": self._generate_description(
                {
                    "description": action.get("description"),
                    "payload": payload,
                    "type": action_type,
                }
            ),
            "module": module,
            "source_ref": "suggested_action",
            "status": "pending",
            "created_at": self._now_iso(),
        }

        if debug:
            mapped["debug_source"] = "suggested_action"

        return self._normalize_action(mapped)

    def _assign_priority(self, severity: str) -> str:
        value = str(severity or "").strip().lower()
        if value in {"high", "critical", "urgent"}:
            return "high"
        if value in {"medium", "warning"}:
            return "medium"
        if value in {"low", "info"}:
            return "low"
        return "medium"

    def _generate_title(self, alert_or_action: dict) -> str:
        module_upper = str(alert_or_action.get("module") or "unknown").strip().upper()

        explicit = alert_or_action.get("title")
        if isinstance(explicit, str) and explicit.strip():
            template = explicit.strip()
            if "[MODULE]" in template:
                return template.replace("[MODULE]", module_upper)
            return template

        action_type = str(alert_or_action.get("type") or "review_issue").strip().replace("_", " ")
        return f"[{module_upper}] {action_type.capitalize()}"

    def _generate_description(self, alert_or_action: dict) -> str:
        explicit = alert_or_action.get("description")
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip()

        message = alert_or_action.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()

        payload = alert_or_action.get("payload")
        if isinstance(payload, dict) and payload:
            parts: list[str] = []
            for key in sorted(payload.keys()):
                if len(parts) >= 5:
                    break
                value = payload.get(key)
                if isinstance(value, (dict, list, tuple, set)):
                    continue
                if value is None:
                    continue
                text = str(value).strip()
                if not text:
                    continue
                if len(text) > 100:
                    text = text[:100] + "..."
                parts.append(f"{str(key).strip()}={text}")
            if parts:
                return "; ".join(parts)

        action_type = str(alert_or_action.get("type") or "acción").strip()
        return f"Revisar {action_type}."

    def _deduplicate(self, actions: list[dict]) -> list[dict]:
        rank = {"high": 3, "medium": 2, "low": 1}
        unique: list[dict] = []
        index_by_key: dict[tuple[str, str, str], int] = {}

        for action in actions:
            key = (
                str(action.get("type") or "").strip().lower(),
                str(action.get("module") or "").strip().lower(),
                str(action.get("title") or "").strip().lower(),
            )

            existing_idx = index_by_key.get(key)
            if existing_idx is None:
                index_by_key[key] = len(unique)
                unique.append(action)
                continue

            current = unique[existing_idx]
            current_rank = rank.get(str(current.get("priority") or "medium").lower(), 2)
            new_rank = rank.get(str(action.get("priority") or "medium").lower(), 2)

            if new_rank > current_rank:
                unique[existing_idx] = action

        return unique

    def _sort_by_priority(self, actions: list[dict]) -> list[dict]:
        rank = {"high": 3, "medium": 2, "low": 1}
        return sorted(
            actions,
            key=lambda a: rank.get(a.get("priority", "medium"), 2),
            reverse=True,
        )

    def _normalize_action(self, action: dict) -> dict:
        normalized = dict(action)

        normalized["type"] = str(normalized.get("type") or "review_issue").strip().lower()
        normalized["priority"] = str(normalized.get("priority") or "medium").strip().lower()
        normalized["module"] = str(normalized.get("module") or "unknown").strip().lower()
        normalized["title"] = str(normalized.get("title") or "").strip()
        normalized["description"] = str(normalized.get("description") or "").strip()
        normalized["source_ref"] = str(normalized.get("source_ref") or "").strip()
        if not normalized.get("status"):
            normalized["status"] = "pending"
        normalized["created_at"] = str(normalized.get("created_at") or self._now_iso()).strip()

        if "debug_source" in normalized:
            normalized["debug_source"] = str(normalized.get("debug_source") or "").strip().lower()

        return normalized

    def _generate_id(self) -> str:
        return "act_" + uuid4().hex[:12]

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
