from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


DigestPriority = Literal["p0", "p1", "p2", "p3"]
DigestSeverity = Literal["critical", "high", "medium", "low", "info"]


class DigestAlertItem(BaseModel):
    signal_id: str
    module: str
    signal_code: str
    severity: DigestSeverity
    priority: DigestPriority
    score: float = Field(ge=0.0, le=1.0)
    summary: str
    entity_scope: Dict[str, str] = Field(default_factory=dict)


class FotoDeHoy(BaseModel):
    fecha: str
    total_senales_activas: int
    total_alertas_visibles: int
    total_alertas_alta_prioridad: int
    modulos_con_alertas: List[str] = Field(default_factory=list)
    resumen_modulos: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class LoQueImportaAhora(BaseModel):
    alertas: List[DigestAlertItem] = Field(default_factory=list)


class PreguntaDelDia(BaseModel):
    texto: str
    signal_id_referencia: str | None = None
    prioridad_objetivo: DigestPriority | None = None


class DailyDigestV1(BaseModel):
    digest_version: Literal["daily_digest.v1"]
    tenant_id: str
    generated_at: str
    foto_de_hoy: FotoDeHoy
    lo_que_importa_ahora: LoQueImportaAhora
    pregunta_del_dia: PreguntaDelDia
