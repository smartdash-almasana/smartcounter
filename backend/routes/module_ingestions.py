import logging
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException

from backend.core.action_store import ActionStore
from backend.schemas.action_jobs import ActionFromSignalRequest
from backend.schemas.module_ingestions import (
    ModuleIngestionRequest,
    ModuleIngestionResponse,
)
from backend.services.module_ingestion_service import (
    get_module_ingestion,
    persist_module_ingestion,
)

router = APIRouter(tags=["module-ingestions"])
log = logging.getLogger(__name__)
action_store = ActionStore()


@router.post("/module-ingestions", response_model=ModuleIngestionResponse)
def create_module_ingestion(payload: ModuleIngestionRequest):
    try:
        result = persist_module_ingestion(payload)
        print("DEBUG RESPONSE:", result)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/module-ingestions/{ingestion_id}")
def get_module_ingestion_by_id(ingestion_id: str):
    try:
        return get_module_ingestion(ingestion_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="ingestion_id no encontrado") from exc


@router.get("/actions/latest")
def get_latest_actions(tenant_id: str):
    return action_store.get_latest_actions(tenant_id)


@router.post("/action-jobs/from-signal")
def create_action_job_from_signal(payload: ActionFromSignalRequest):
    tenant_id = str(payload.tenant_id or "").strip()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")

    action_type = str(payload.action_type or "").strip()
    if not action_type:
        raise HTTPException(status_code=400, detail="action_type is required")

    module = str(payload.module or "").strip() or "unknown"
    source_signal_code = str(payload.source_signal_code or "").strip() or "unknown_signal"
    context = payload.context if isinstance(payload.context, dict) else {}

    action_id = "act_" + uuid.uuid4().hex[:12]

    action = {
        "id": action_id,
        "type": action_type,
        "priority": "high",
        "title": str(context.get("title") or "Acción requerida"),
        "description": f"Acción generada desde señal {source_signal_code}",
        "module": module,
        "source_ref": source_signal_code,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    try:
        latest_actions = action_store.get_latest_actions(tenant_id)
        actions = latest_actions.get("actions", [])
        if not isinstance(actions, list):
            actions = []
        actions.append(action)
        action_store.save_latest_actions(tenant_id, actions)
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Failed creating manual action from signal")
        raise HTTPException(status_code=500, detail="Failed creating action from signal") from exc

    return {
        "ok": True,
        "action_id": action_id,
        "status": "pending",
    }
