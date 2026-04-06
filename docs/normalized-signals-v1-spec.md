# normalized_signals.v1 Spec

## 1. Propósito
`normalized_signals.v1` define una capa semántica estable y transversal que transforma findings heterogéneos de módulos en señales comparables para consumo de digest y preparación de acción.

## 2. Findings vs Signals
- `finding`: observación puntual, dependiente de módulo, fila o evidencia concreta.
- `signal`: estado semántico normalizado, comparable cross-module, orientado a priorización y decisión.

Regla: múltiples findings pueden consolidarse en una sola signal.

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
```

## 4. Enums mínimos
- `signal_version`: `normalized_signals.v1`
- `state`: `active`, `resolved`, `expired`
- `severity`: `critical`, `high`, `medium`, `low`, `info`
- `priority`: `p0`, `p1`, `p2`, `p3`
- `evidence.sources[]`: `RULE`, `HERMES`

## 5. Severidad, score y priority
- `severity`: impacto semántico del problema.
- `score`: confianza normalizada `[0..1]`.
- `priority`: orden operativo para digest y readiness.

Regla base sugerida:
- `critical` + `score>=0.8` => `p0`
- `high` => `p1`
- `medium` => `p2`
- `low|info` => `p3`

## 6. 10 signal_codes iniciales
1. `stock_break_risk`
2. `stock_overstock_risk`
3. `stock_data_quality_issue`
4. `expense_evidence_missing`
5. `expense_evidence_low_quality`
6. `expense_policy_risk`
7. `expense_duplicate_suspected`
8. `conciliation_unmatched_movement`
9. `conciliation_amount_mismatch`
10. `conciliation_date_mismatch`

## 7. Reglas de mapping finding -> signal
Reglas mínimas:
- Determinar `entity_scope` desde el finding (SKU, request_id, movimiento, etc.).
- Mapear `finding.code` a `signal_code` por tabla de módulo.
- Consolidar findings equivalentes por clave: `{tenant_id, module, entity_scope, signal_code}`.
- `severity` final = máxima severidad entre findings consolidados.
- `score` final = combinación determinística (máximo o promedio ponderado, fijo por módulo).
- `state` inicial = `active`.

Tabla inicial de mapping:
- `stock_simple`
  - `critical_stock_detected` -> `stock_break_risk`
  - `low_stock_detected` -> `stock_break_risk`
  - `overstock_detected` -> `stock_overstock_risk`
  - `invalid_stock_row` -> `stock_data_quality_issue`
- `expense_evidence`
  - `missing_evidence` -> `expense_evidence_missing`
  - `illegible_evidence` -> `expense_evidence_low_quality`
  - `evidence_quality_low` -> `expense_evidence_low_quality`
  - `duplicate_evidence_suspected` -> `expense_duplicate_suspected`
  - `high_amount_expense` -> `expense_policy_risk`
  - `missing_key_fields` -> `expense_policy_risk`
- `concili_simple`
  - `unmatched_movement` -> `conciliation_unmatched_movement`
  - `amount_mismatch` -> `conciliation_amount_mismatch`
  - `date_mismatch` -> `conciliation_date_mismatch`

## 8. Expiración y resolución
- `resolved`: cuando una nueva evidencia confirma cierre semántico del caso.
- `expired`: cuando supera `expires_at` sin confirmación de vigencia.

Reglas v1:
- toda signal `active` debe tener `expires_at`.
- al resolverse, setear `resolved_at` y `resolution_reason`.
- `expired` no implica `resolved`; implica vencimiento operacional.

## 9. Relación con digest
Digest consume `normalized_signals`, no findings crudos.

Consumo mínimo de digest:
- `signal_code`
- `state`
- `severity`
- `score`
- `priority`
- `summary`
- `entity_scope`

## 10. Relación con action readiness
Action readiness no parte directo de findings.

Entrada esperada:
- signals activas priorizadas (`p0/p1` principalmente)
- contexto de summary + evidencia consolidada

Salida esperada:
- objetos confirmables (`action_ready_objects`) sin ejecutar acción.

## 11. Ejemplos por módulo

### 11.1 stock_simple
```json
{
  "signal_version": "normalized_signals.v1",
  "signal_id": "sig_stock_001",
  "tenant_id": "demo001",
  "entity_scope": {"entity_type": "item", "entity_id": "SKU-123"},
  "module": "stock_simple",
  "signal_code": "stock_break_risk",
  "state": "active",
  "severity": "high",
  "score": 0.91,
  "priority": "p1",
  "summary": "Stock bajo con cobertura crítica",
  "evidence": {"finding_ids": ["finding_10"], "sources": ["RULE"], "facts": {"dias_cobertura": 2.7}},
  "lifecycle": {"detected_at": "2026-04-06T12:00:00Z", "updated_at": "2026-04-06T12:00:00Z", "expires_at": "2026-04-13T12:00:00Z", "resolved_at": null, "resolution_reason": null},
  "links": {"module_ingestion_id": "ing_abc", "job_id": null, "artifact_refs": []}
}
```

### 11.2 expense_evidence
```json
{
  "signal_version": "normalized_signals.v1",
  "signal_id": "sig_exp_001",
  "tenant_id": "demo001",
  "entity_scope": {"entity_type": "expense_case", "entity_id": "REQ-1"},
  "module": "expense_evidence",
  "signal_code": "expense_evidence_missing",
  "state": "active",
  "severity": "critical",
  "score": 0.95,
  "priority": "p0",
  "summary": "Caso de gasto sin evidencia adjunta",
  "evidence": {"finding_ids": ["finding_77"], "sources": ["RULE"], "facts": {"request_id": "REQ-1"}},
  "lifecycle": {"detected_at": "2026-04-06T13:00:00Z", "updated_at": "2026-04-06T13:00:00Z", "expires_at": "2026-04-10T13:00:00Z", "resolved_at": null, "resolution_reason": null},
  "links": {"module_ingestion_id": "ing_def", "job_id": null, "artifact_refs": []}
}
```

### 11.3 concili_simple
```json
{
  "signal_version": "normalized_signals.v1",
  "signal_id": "sig_conc_001",
  "tenant_id": "demo001",
  "entity_scope": {"entity_type": "account", "entity_id": "CTA-AR-01"},
  "module": "concili_simple",
  "signal_code": "conciliation_amount_mismatch",
  "state": "active",
  "severity": "medium",
  "score": 0.82,
  "priority": "p2",
  "summary": "Diferencia de importe en conciliación",
  "evidence": {"finding_ids": ["finding_204"], "sources": ["RULE"], "facts": {"delta": 1520.5}},
  "lifecycle": {"detected_at": "2026-04-06T14:00:00Z", "updated_at": "2026-04-06T14:00:00Z", "expires_at": "2026-04-20T14:00:00Z", "resolved_at": null, "resolution_reason": null},
  "links": {"module_ingestion_id": "ing_xyz", "job_id": null, "artifact_refs": []}
}
```

## 12. Riesgos semánticos
1. Over-mapping: demasiados finding codes apuntando al mismo `signal_code` sin contexto.
2. Under-mapping: signals demasiado específicas que impiden comparabilidad cross-module.
3. Inconsistencia de severidad entre módulos para el mismo tipo de riesgo.
4. Scores no calibrados entre RULE y HERMES.
5. Dedupe semántico incorrecto por mala definición de `entity_scope`.
6. Signals que nunca expiran y degradan digest.
7. Resoluciones sin evidencia verificable (`resolution_reason` débil).
8. Digest consumiendo findings directos y salteando signals.
9. Action readiness disparado desde findings en vez de signals.
10. Deriva de taxonomía sin control de versión.

## 13. Entregables solicitados (resumen)
- A) Documento Markdown completo: este archivo.
- B) Schema JSON ejemplo: sección 3.
- C) 10 signal_codes iniciales: sección 6.
- D) Reglas de mapping finding -> signal: sección 7.
- E) Riesgos semánticos: sección 12.
