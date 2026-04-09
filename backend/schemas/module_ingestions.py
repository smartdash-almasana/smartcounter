from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


ModuleName = Literal["stock_simple", "expense_evidence", "excel_power_query_edge"]
SourceType = Literal[
    "google_sheets",
    "upload",
    "email",
    "drive",
    "api",
    "other",
    "excel_power_query",
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
    contract_version: str = "module-ingestions.v2"
    source_channel: str | None = None
    tenant_id: str
    module: str
    source_type: str
    generated_at: str
    content_hash: str | None = None
    canonical_rows: List[Dict[str, Any]]
    findings: List[Dict[str, Any]]
    summary: Dict[str, Any]
    suggested_actions: List[Dict[str, Any]]
    additional_artifacts: Dict[str, Any] = Field(default_factory=dict)
    parse_metadata: Dict[str, Any] = Field(default_factory=dict)
    audit_metadata: Dict[str, Any] = Field(default_factory=dict)


class ModuleIngestionResponse(BaseModel):
    ok: bool
    ingestion_id: str
    contract_version: str
    tenant_id: str
    module: str
    status: str
    deduplicated: bool
    deduped: bool
    content_hash: str
    artifacts: Dict[str, str]
