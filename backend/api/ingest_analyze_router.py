from __future__ import annotations

import logging
from typing import Any, Protocol, cast

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from backend.api.ingest_router import _log_event, ingest_file

try:
    from backend.core.module_executor import ModuleExecutor
except ImportError:

    class ModuleExecutor(Protocol):
        def execute(self, module: str, payload: dict[str, Any]) -> dict[str, Any]:
            ...


router = APIRouter(tags=["ingest", "analyze"])


@router.post("/ingest/analyze")
async def ingest_and_analyze(
    request: Request,
    file: UploadFile = File(...),
    tenant_id: str = Form(...),
    module: str = Form(...),
) -> dict[str, Any]:
    """Persist an uploaded file through the ingestion pipeline and immediately execute the target module."""
    ingestion_result = await ingest_file(
        request=request,
        file=file,
        tenant_id=tenant_id,
        module=module,
    )

    artifact_path = str(ingestion_result["artifact_path"])
    filename = str(ingestion_result["filename"])
    content_type = str(ingestion_result["content_type"])

    payload: dict[str, Any] = {
        "tenant_id": tenant_id,
        "module": module,
        "artifact_path": artifact_path,
        "filename": filename,
        "content_type": content_type,
    }

    request_id = str(ingestion_result.get("request_id", ""))
    executor_obj = getattr(request.app.state, "module_executor", None)
    if executor_obj is None:
        _log_event(
            logging.ERROR,
            "module_executor_missing",
            request_id=request_id,
            tenant_id=tenant_id,
            module=module,
            artifact_path=artifact_path,
            security_event=False,
        )
        raise HTTPException(status_code=500, detail="Module executor is not configured")

    executor = cast(ModuleExecutor, executor_obj)

    try:
        result = await run_in_threadpool(executor.execute, module, payload)
    except HTTPException:
        raise
    except (LookupError, KeyError) as exc:
        _log_event(
            logging.WARNING,
            "module_not_found",
            request_id=request_id,
            tenant_id=tenant_id,
            module=module,
            artifact_path=artifact_path,
            error=str(exc),
            security_event=False,
        )
        raise HTTPException(status_code=404, detail="Module not found") from exc
    except ValueError as exc:
        _log_event(
            logging.WARNING,
            "module_execution_validation_failed",
            request_id=request_id,
            tenant_id=tenant_id,
            module=module,
            artifact_path=artifact_path,
            error=str(exc),
            security_event=False,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _log_event(
            logging.ERROR,
            "module_execution_failed",
            request_id=request_id,
            tenant_id=tenant_id,
            module=module,
            artifact_path=artifact_path,
            error=str(exc),
            security_event=False,
        )
        raise HTTPException(status_code=500, detail="Module execution failed") from exc

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "module": module,
        "artifact_path": artifact_path,
        "run_id": result["run_id"],
        "summary": result["summary"],
        "signals": result["signals"],
        "actions": result["actions"],
    }
