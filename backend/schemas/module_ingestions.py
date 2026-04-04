from typing import Any, Dict, List, Literal

from pydantic import BaseModel


class ModuleIngestionRequest(BaseModel):
    tenant_id: str
    module: Literal["stock_simple"]
    source_type: Literal["google_sheets"]
    generated_at: str
    canonical_rows: List[Dict[str, Any]]
    findings: List[Dict[str, Any]]
    summary: Dict[str, Any]
    suggested_actions: List[Dict[str, Any]]


class ModuleIngestionResponse(BaseModel):
    ok: bool
    ingestion_id: str
    tenant_id: str
    module: str
    status: str
    artifacts: Dict[str, str]
