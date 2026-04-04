from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


ModuleName = Literal["stock_simple", "expense_evidence"]
SourceType = Literal[
    "google_sheets",
    "upload",
    "email",
    "drive",
    "api",
    "other",
]


class ExpenseEvidenceFrozenRow(BaseModel):
    request_id: str
    submitted_at: str
    requester_name: str
    merchant_name: str
    document_type: str
    document_date: str
    document_cuit: str
    amount: float | int
    currency: str
    payment_method: str
    category: str
    evidence_list: List[Dict[str, Any]]
    status: str
    observation_note: str | None = None
    policy_flag: str | bool | None = None
    resolved_at: str | None = None
    resolver_name: str | None = None


class ModuleIngestionRequest(BaseModel):
    tenant_id: str
    module: ModuleName
    source_type: SourceType
    generated_at: str
    canonical_rows: List[Dict[str, Any]]
    findings: List[Dict[str, Any]]
    summary: Dict[str, Any]
    suggested_actions: List[Dict[str, Any]]
    additional_artifacts: Dict[str, Any] = Field(default_factory=dict)


class ModuleIngestionResponse(BaseModel):
    ok: bool
    ingestion_id: str
    tenant_id: str
    module: str
    status: str
    artifacts: Dict[str, str]
