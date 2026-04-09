from typing import Any, Dict

from pydantic import BaseModel, Field


class ActionFromSignalRequest(BaseModel):
    tenant_id: str | None = None
    module: str | None = None
    source_signal_code: str | None = None
    action_type: str | None = None
    context: Dict[str, Any] = Field(default_factory=dict)


class ActionJobsFromDigestRequest(BaseModel):
    tenant_id: str
    digest: Dict[str, Any] = Field(default_factory=dict)


class ActionJobConfirmRequest(BaseModel):
    action: str
