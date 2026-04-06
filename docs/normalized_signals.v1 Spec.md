# normalized_signals.v1 Spec

## 1. Propósito

`normalized_signals.v1` define una capa semántica estable y transversal que transforma findings heterogéneos de módulos en señales comparables para consumo de digest y preparación de acción.

---

## 2. Findings vs Signals

- `finding`: observación puntual, dependiente de módulo, fila o evidencia concreta.
- `signal`: estado semántico normalizado, comparable cross-module, orientado a priorización y decisión.

**Regla:** múltiples findings pueden consolidarse en una sola signal.

---

## 3. Schema v1 (objeto signal)

```json
{
  "signal_version": "normalized_signals.v1",
  "signal_id": "sig_01JABC...",
  "tenant_id": "demo001",
  "entity_scope": {
    "entity_type": "item|expense_case|invoice|client|account|batch",
    "entity_id": "string"
  },
  "module": "stock_simple|expense_evidence|concili_simple",
  "signal_code": "stock_break_risk",
  "state": "active|resolved|expired",
  "severity": "critical|high|medium|low|info",
  "score": 0.92,
  "confidence": 0.95,
  "priority": "p0|p1|p2|p3",
  "summary": "Riesgo de quiebre de stock en SKU-123",
  "evidence": {
    "finding_ids": ["finding_1", "finding_2"],
    "sources": ["RULE", "HERMES"],
    "facts": {}
  },
  "lifecycle": {
    "detected_at": "2026-04-06T12:00:00Z",
    "updated_at": "2026-04-06T12:05:00Z",
    "expires_at": "2026-04-13T12:00:00Z",
    "resolved_at": null,
    "resolution_reason": null
  },
  "links": {
    "module_ingestion_id": "ing_xxx",
    "job_id": "rev_xxx",
    "artifact_refs": []
  }
}