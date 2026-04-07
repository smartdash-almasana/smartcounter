import logging

from fastapi import APIRouter, HTTPException

from backend.core.action_store import ActionStore
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

