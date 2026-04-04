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

ExpenseSourceChannel = Literal["drive", "email", "upload", "other"]
ExpenseEvidenceType = Literal[
    "invoice_pdf",
    "invoice_image",
    "ticket",
    "receipt",
    "bank_transfer",
    "payment_screenshot",
    "manual_note",
    "mixed",
]
ExpensePaymentMethod = Literal["cash", "debit", "credit", "transfer", "wallet", "unknown"]
ExpenseEvidenceQuality = Literal["high", "medium", "low", "insufficient"]
ExpenseDocumentStatus = Literal[
    "captured",
    "needs_review",
    "needs_completion",
    "ready_for_approval",
    "duplicate_suspected",
    "invalid",
]


class ExpenseEvidenceCanonicalRow(BaseModel):
    expense_case_id: str
    evidence_id: str
    source_channel: ExpenseSourceChannel
    evidence_type: ExpenseEvidenceType
    file_name: str
    file_url: str | None = None
    uploaded_at: str
    submitted_by: str | None = None
    merchant_name: str | None = None
    merchant_tax_id: str | None = None
    expense_date: str | None = None
    amount: float | int | None = None
    currency: str | None = None
    expense_category: str | None = None
    description: str | None = None
    payment_method: ExpensePaymentMethod = "unknown"
    evidence_quality: ExpenseEvidenceQuality
    document_status: ExpenseDocumentStatus
    linked_case_count: int = 1
    requires_review: bool
    confidence: float
    notes: str = ""


class ExpenseEvidenceFrozenRow(BaseModel):
    request_id: str
    evidence_list: List[Dict[str, Any]]
    status: str
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
