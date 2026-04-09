from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.action_job_service import create_action_jobs, confirm_action, execute_action

router = APIRouter(tags=["action-jobs"])


class ActionJobsFromDigestRequest(BaseModel):
    tenant_id: str
    digest: dict[str, Any] = Field(default_factory=dict)


class ActionJobConfirmRequest(BaseModel):
    decision: str


@router.post("/action-jobs/from-digest")
def action_jobs_from_digest(payload: ActionJobsFromDigestRequest) -> dict[str, Any]:
    tenant_id = str(payload.tenant_id or "").strip()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")

    digest = payload.digest if isinstance(payload.digest, dict) else {}
    suggested_actions = digest.get("suggested_actions", [])
    if not isinstance(suggested_actions, list):
        suggested_actions = []

    jobs = create_action_jobs(tenant_id=tenant_id, suggested_actions=suggested_actions)
    return {
        "ok": True,
        "jobs": jobs,
    }


@router.post("/action-jobs/{action_id}/confirm")
def confirm_action_job(action_id: str, payload: ActionJobConfirmRequest) -> dict[str, Any]:
    decision = str(payload.decision or "").strip().lower()
    if decision not in {"confirm", "cancel"}:
        raise HTTPException(status_code=400, detail="decision must be 'confirm' or 'cancel'")

    try:
        job = confirm_action(action_id=action_id, decision=decision)
    except ValueError as exc:
        if str(exc) == "action not found":
            raise HTTPException(status_code=404, detail="action not found") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "ok": True,
        "job": job,
    }


@router.post("/action-jobs/{action_id}/execute")
def execute_action_job(action_id: str) -> dict[str, Any]:
    try:
        job = execute_action(action_id=action_id)
    except ValueError as exc:
        if str(exc) == "action not found":
            raise HTTPException(status_code=404, detail="action not found") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "ok": True,
        "job": job,
    }
