from fastapi import APIRouter, HTTPException

from backend.schemas.module_ingestions import (
    ModuleIngestionRequest,
    ModuleIngestionResponse,
)
from backend.services.module_ingestion_service import (
    get_module_ingestion,
    persist_module_ingestion,
)

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
        "contract_version": persisted["contract_version"],
        "tenant_id": persisted["tenant_id"],
        "module": persisted["module"],
        "status": persisted["status"],
        "deduplicated": persisted["deduplicated"],
        "deduped": persisted["deduped"],
        "content_hash": persisted["content_hash"],
        "artifacts": persisted["artifacts"],
    }


@router.get("/module-ingestions/{ingestion_id}")
def get_module_ingestion_by_id(ingestion_id: str):
    try:
        return get_module_ingestion(ingestion_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="ingestion_id no encontrado") from exc

