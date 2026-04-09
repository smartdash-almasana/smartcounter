from __future__ import annotations

from typing import Any

from backend.services.action_job_service import create_action_jobs


def create_action_jobs_from_suggestions(
    tenant_id: str,
    suggested_actions: list[dict],
    context: dict[str, Any] | None = None,
) -> list[dict]:
    jobs = create_action_jobs(tenant_id=tenant_id, suggested_actions=suggested_actions)

    safe_context = context if isinstance(context, dict) else {}
    if not safe_context:
        return jobs

    for job in jobs:
        draft = job.get("draft")
        if isinstance(draft, dict):
            draft["context"] = safe_context

    return jobs
