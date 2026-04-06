from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from backend.core.digest_builder import DigestBuilder
from backend.services.artifact_store import ArtifactStore

router = APIRouter(tags=["digest"])


@router.get("/digest/latest")
def get_latest_digest(
    request: Request,
    tenant_id: str | None = Query(None),
):
    tenant = (tenant_id or "").strip()
    if not tenant:
        raise HTTPException(status_code=400, detail="tenant_id is required")

    try:
        artifact_store = getattr(request.app.state, "artifact_store", None) or ArtifactStore()
        builder = DigestBuilder(artifact_store)
        digest = builder.build_latest(tenant)
        return digest
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to build latest digest")
