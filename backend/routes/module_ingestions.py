from fastapi import APIRouter, HTTPException

from backend.schemas.module_ingestions import (
    ModuleIngestionRequest,
    ModuleIngestionResponse,
)
from backend.services.module_ingestion_service import persist_module_ingestion

router = APIRouter(tags=["module-ingestions"])


@router.post("/module-ingestions", response_model=ModuleIngestionResponse)
def create_module_ingestion(payload: ModuleIngestionRequest):
    try:
        persisted = persist_module_ingestion(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "ok": True,
        "ingestion_id": persisted["ingestion_id"],
        "tenant_id": persisted["tenant_id"],
        "module": persisted["module"],
        "status": persisted["status"],
        "artifacts": persisted["artifacts"],
    }
