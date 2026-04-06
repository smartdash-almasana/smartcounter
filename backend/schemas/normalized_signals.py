from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


SignalState = Literal["active", "resolved", "expired"]
SignalSeverity = Literal["critical", "high", "medium", "low", "info"]
SignalPriority = Literal["p0", "p1", "p2", "p3"]
SignalSource = Literal["RULE", "HERMES"]
SignalModule = Literal["stock_simple", "expense_evidence", "concili_simple"]


class SignalEntityScope(BaseModel):
    entity_type: str
    entity_id: str


class SignalEvidence(BaseModel):
    finding_ids: List[str] = Field(default_factory=list)
    sources: List[SignalSource] = Field(default_factory=list)
    facts: Dict[str, Any] = Field(default_factory=dict)


class SignalLifecycle(BaseModel):
    detected_at: str
    updated_at: str
    expires_at: str | None = None
    resolved_at: str | None = None
    resolution_reason: str | None = None


class SignalLinks(BaseModel):
    module_ingestion_id: str | None = None
    job_id: str | None = None
    artifact_refs: List[str] = Field(default_factory=list)


class NormalizedSignalV1(BaseModel):
    signal_version: Literal["normalized_signals.v1"]
    signal_id: str
    tenant_id: str
    entity_scope: SignalEntityScope
    module: SignalModule
    signal_code: str
    state: SignalState
    severity: SignalSeverity
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    priority: SignalPriority
    summary: str
    evidence: SignalEvidence
    lifecycle: SignalLifecycle
    links: SignalLinks
