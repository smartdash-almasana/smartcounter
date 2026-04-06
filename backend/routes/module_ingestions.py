import hashlib
import json
import logging

from fastapi import APIRouter, HTTPException

from backend.core.action_store import ActionStore
from backend.schemas.module_ingestions import (
    ModuleIngestionRequest,
    ModuleIngestionResponse,
)
from backend.services.artifact_store import ArtifactStore
from backend.services.module_ingestion_service import (
    get_module_ingestion,
)
from backend.utils.ids import build_ingestion_id

router = APIRouter(tags=["module-ingestions"])
log = logging.getLogger(__name__)
action_store = ActionStore()


@router.post("/module-ingestions", response_model=ModuleIngestionResponse)
def create_module_ingestion(payload: ModuleIngestionRequest):
    try:
        payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()

        ingestion_id = build_ingestion_id()
        tenant_id = str(payload_dict.get("tenant_id") or "").strip()
        module = str(payload_dict.get("module") or "").strip()

        findings_list = payload_dict.get("findings", [])
        if not isinstance(findings_list, list):
            findings_list = []

        artifacts_payload = {
            "input": payload_dict,
            "canonical_rows": payload_dict.get("canonical_rows", []),
            "findings": findings_list,
            "summary": payload_dict.get("summary", {}),
            "suggested_actions": payload_dict.get("suggested_actions", []),
            "result": {
                "tenant_id": tenant_id,
                "module": module,
                "ingestion_id": ingestion_id,
                "generated_at": payload_dict.get("generated_at"),
                "summary": payload_dict.get("summary", {}),
                "alerts": findings_list,
                "findings_count": len(findings_list),
            },
        }

        artifact_store = ArtifactStore()
        paths = artifact_store.save_ingestion_artifacts(
            tenant_id=tenant_id,
            module=module,
            ingestion_id=ingestion_id,
            artifacts=artifacts_payload,
        )

        latest_payload = {
            "tenant_id": tenant_id,
            "module": module,
            "latest_ingestion_id": ingestion_id,
            "updated_at": payload_dict.get("generated_at"),
            "result_path": paths["result"],
        }
        artifact_store.save_module_latest(
            tenant_id=tenant_id,
            module=module,
            latest_payload=latest_payload,
        )

        content_hash = hashlib.sha256(
            json.dumps(payload_dict, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        log.info(f"[INGESTION SAVED] tenant={tenant_id} module={module} ingestion={ingestion_id}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "ok": True,
        "ingestion_id": ingestion_id,
        "contract_version": payload_dict.get("contract_version", "module-ingestions.v2"),
        "tenant_id": tenant_id,
        "module": module,
        "status": "accepted",
        "deduplicated": False,
        "deduped": False,
        "content_hash": content_hash,
        "artifacts": paths,
    }


@router.get("/module-ingestions/{ingestion_id}")
def get_module_ingestion_by_id(ingestion_id: str):
    try:
        return get_module_ingestion(ingestion_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="ingestion_id no encontrado") from exc


@router.get("/actions/latest")
def get_latest_actions(tenant_id: str):
    return action_store.get_latest_actions(tenant_id)
