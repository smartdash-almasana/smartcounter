from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.adapters.message_adapter.message_adapter import MessageAdapter

router = APIRouter(tags=["message-ingest"])


class MessageIngestRequest(BaseModel):
    tenant_id: str
    text: str


@router.post("/message-ingest")
async def message_ingest(payload: MessageIngestRequest) -> dict[str, str]:
    adapter = MessageAdapter()

    try:
        result = adapter.process(
            payload.text,
            metadata={"tenant_id": payload.tenant_id},
        )
        result["contract_version"] = "module-ingestions.v2"
    except Exception as exc:
        raise HTTPException(status_code=502, detail="core error") from exc

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/module-ingestions",
                json=result,
            )
            response.raise_for_status()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="request error") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="core error") from exc

    return {
        "status": "processed",
        "module": "message_adapter",
    }

