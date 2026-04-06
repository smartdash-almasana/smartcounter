# module-ingestions.v2 Spec

## 1. Objetivo
Definir `module-ingestions.v2` como inbox robusto del core SmartCounter para recibir payloads modulares, validarlos, deduplicarlos, persistir artefactos y exponer trazabilidad técnica.

## 2. Alcance
Esta spec cubre:
- `POST /module-ingestions`.
- `GET /module-ingestions/{ingestion_id}`.
- Contrato `module-ingestions.v2`.
- Reglas de validación top-level y por módulo.
- Idempotencia por `content_hash`.
- Persistencia en GCS y artefactos mínimos.

## 3. Qué hace
- Recibe un payload modular tipado.
- Valida contrato y reglas por módulo.
- Calcula/verifica `content_hash`.
- Aplica dedupe por clave `{tenant_id}:{module}:{content_hash}`.
- Persiste request y artefactos derivados en GCS.
- Devuelve `ingestion_id` y metadatos de estado.
- Permite consulta de estado y artefactos por `ingestion_id`.

## 4. Qué no hace
- No ejecuta acciones (`action engine`).
- No genera ni materializa `normalized_signals`.
- No reemplaza ni absorbe `revision-jobs`.
- No integra Hermes como parte nativa del inbox.
- No realiza enriquecimiento cognitivo multipaso.

## 5. Endpoint
- `POST /module-ingestions`
- `GET /module-ingestions/{ingestion_id}`

## 6. Request schema v2

```json
{
  "contract_version": "module-ingestions.v2",
  "tenant_id": "demo001",
  "module": "stock_simple",
  "source_type": "google_sheets",
  "generated_at": "2026-04-05T15:40:00Z",
  "content_hash": "sha256_hex_64",
  "canonical_rows": [],
  "findings": [],
  "summary": {},
  "suggested_actions": [],
  "additional_artifacts": {},
  "parse_metadata": {
    "edge": "apps_script",
    "edge_version": "1.0.0",
    "source_ref": "spreadsheet_id_or_file_ref"
  },
  "audit_metadata": {
    "trace_id": "trace-123",
    "request_id": "req-123",
    "actor_type": "system",
    "actor_id": "stocksimple-bot"
  }
}
```

## 7. Campos obligatorios
- `contract_version`
- `tenant_id`
- `module`
- `source_type`
- `generated_at`
- `content_hash`
- `canonical_rows`
- `findings`
- `summary`
- `suggested_actions`

## 8. Campos opcionales
- `additional_artifacts` (default `{}`)
- `parse_metadata` (default `{}`)
- `audit_metadata` (default `{}`)

## 9. Enums controlados
- `contract_version`: `module-ingestions.v2`
- `module`: `stock_simple`, `expense_evidence`
- `source_type`: `google_sheets`, `upload`, `email`, `drive`, `api`, `other`
- `audit_metadata.actor_type`: `user`, `system`, `service` (si se envía)
- `suggested_actions[].priority` (cuando aplique): `high`, `medium`, `low`

## 10. Reglas de validación top-level
- `contract_version` debe ser exactamente `module-ingestions.v2`.
- `tenant_id` no vacío, normalizable para path seguro.
- `generated_at` debe ser timestamp RFC3339/ISO-8601 válido con zona (`Z` u offset).
- `content_hash` debe ser SHA-256 hex en minúsculas (`^[a-f0-9]{64}$`).
- `canonical_rows` debe ser lista de objetos.
- `findings` debe ser lista de objetos.
- `summary` debe ser objeto.
- `suggested_actions` debe ser lista de objetos.
- `additional_artifacts`, `parse_metadata`, `audit_metadata` deben ser objetos cuando estén presentes.

## 11. Validación por módulo
### `stock_simple`
- `source_type` obligatorio: `google_sheets`.
- Cada fila en `canonical_rows` debe incluir, como mínimo:
  - `row_id` (string)
  - `producto` (string no vacío)
  - `stock_actual` (number)
  - `stock_minimo` (number)
  - `consumo_promedio_diario` (number)
  - `requires_review` (boolean)
- `summary` debe incluir, como mínimo:
  - `total_rows`, `valid_rows`, `invalid_rows`
- `findings[].code` debe ser string no vacío.

### `expense_evidence`
- Mantiene compatibilidad con validación vigente.
- `source_type` permitido dentro de enum general.
- `canonical_rows[]` validado contra shape congelado de `ExpenseEvidenceFrozenRow`.
- `findings` requiere `finding_type` válido (o `code` por compatibilidad controlada).
- `summary` debe incluir claves mínimas de casos totales/estado.
- `suggested_actions[]` requiere `action_type`, `priority`, `description`, `context`.

## 12. Idempotencia y content_hash
- Clave de dedupe: `{tenant_id}:{module}:{content_hash}`.
- Semántica:
  - Si no existe registro previo para la clave: crear nueva ingesta.
  - Si existe y el payload canónico coincide: responder reutilizando la ingesta previa (`deduped=true`).
  - Si existe clave pero difiere payload material: responder `409 conflict` con error tipado.
- `content_hash` debe representar el contenido canónico del payload funcional (no metadatos volátiles).

## 13. Response schema v2

```json
{
  "ok": true,
  "ingestion_id": "ing_abc123",
  "contract_version": "module-ingestions.v2",
  "tenant_id": "demo001",
  "module": "stock_simple",
  "status": "accepted",
  "deduped": false,
  "content_hash": "sha256_hex_64",
  "artifacts": {
    "input": "gcs://bucket/path/input.json",
    "canonical_rows": "gcs://bucket/path/canonical_rows.json",
    "findings": "gcs://bucket/path/findings.json",
    "summary": "gcs://bucket/path/summary.json",
    "suggested_actions": "gcs://bucket/path/suggested_actions.json",
    "request_meta": "gcs://bucket/path/request_meta.json",
    "result": "gcs://bucket/path/result.json"
  }
}
```

## 14. Estados válidos
- `accepted`
- `accepted_deduped`
- `rejected_validation`
- `rejected_conflict`
- `error`

## 15. Errores tipados
Formato:

```json
{
  "ok": false,
  "error": {
    "type": "validation_error",
    "code": "INVALID_GENERATED_AT",
    "message": "generated_at debe ser RFC3339 con zona",
    "field": "generated_at"
  }
}
```

Tipos mínimos:
- `validation_error`
- `idempotency_conflict`
- `unsupported_module`
- `unsupported_contract_version`
- `storage_error`
- `internal_error`

Códigos mínimos:
- `INVALID_CONTRACT_VERSION`
- `INVALID_GENERATED_AT`
- `INVALID_CONTENT_HASH`
- `DUPLICATE_HASH_CONFLICT`
- `MODULE_VALIDATION_FAILED`
- `INGESTION_NOT_FOUND`

## 16. Persistencia de artefactos
Se mantiene persistencia en GCS bajo prefijo:
- `tenant_<tenant_id>/module_ingestions/<module>/<ingestion_id>/`

Artefactos mínimos:
- `input.json`
- `canonical_rows.json`
- `findings.json`
- `summary.json`
- `suggested_actions.json`
- `request_meta.json`
- `result.json`

`result.json` debe incluir: `status`, `accepted_at`, `content_hash`, `dedupe_key`, `contract_version`.

## 17. additional_artifacts
- Tipo: objeto `map<string, any>`.
- Se persiste como `<artifact_key>.json` dentro del prefijo de ingesta.
- Keys deben sanitizarse a formato path-safe.
- Si key colisiona con nombres reservados (`input`, `canonical_rows`, `findings`, `summary`, `suggested_actions`, `request_meta`, `result`), se renombra con prefijo `extra_`.
- Para `stock_simple` y `expense_evidence` está permitido; el uso queda optativo por módulo.

## 18. parse_metadata
Objeto opcional para trazas técnicas del edge/parser.
Campos sugeridos:
- `edge` (ej. `apps_script`)
- `edge_version`
- `parser_version`
- `source_ref`
- `source_filename`
- `source_row_count`

No reemplaza `summary`; es metadata de captura.

## 19. audit_metadata
Objeto opcional para auditoría transversal.
Campos sugeridos:
- `trace_id`
- `request_id`
- `actor_type`
- `actor_id`
- `submitted_from_ip` (si aplica)

Debe persistirse íntegro en `request_meta.json`.

## 20. GET /module-ingestions/{ingestion_id}
Respuesta base:

```json
{
  "ok": true,
  "ingestion_id": "ing_abc123",
  "contract_version": "module-ingestions.v2",
  "tenant_id": "demo001",
  "module": "stock_simple",
  "status": "accepted",
  "content_hash": "sha256_hex_64",
  "deduped": false,
  "artifacts": {},
  "created_at": "2026-04-05T15:40:01Z"
}
```

Reglas:
- Requiere `tenant_id` como query param o cabecera de contexto multitenant.
- Debe devolver `404` con `INGESTION_NOT_FOUND` si no existe.
- No ejecuta procesamiento adicional; solo lectura de estado/artefactos.

## 21. Observabilidad mínima
- Registrar en `result.json`:
  - `status`, `accepted_at`, `content_hash`, `dedupe_key`, `deduped`, `contract_version`.
- Registrar en `request_meta.json`:
  - snapshot de request top-level + `parse_metadata` + `audit_metadata`.
- Exponer en respuestas:
  - `ingestion_id`, `status`, `content_hash`, `deduped`.

## 22. Compatibilidad con Apps Script
- Apps Script es edge prioritario para `stock_simple`.
- El edge envía payloads al inbox; no ejecuta responsabilidades de core.
- El contrato v2 mantiene `POST /module-ingestions` y `ingestion_id` en respuesta.
- Requisito específico de Apps Script:
  - incluir `contract_version` y `content_hash` en payload.
  - `source_type` para `stock_simple` permanece `google_sheets`.

## 23. Criterios de aceptación
- `POST /module-ingestions` acepta `module-ingestions.v2` y rechaza versiones inválidas.
- `generated_at` inválido devuelve `validation_error` tipado.
- `content_hash` inválido devuelve `validation_error` tipado.
- Dedupe por `{tenant_id}:{module}:{content_hash}` operativo y trazable.
- `ingestion_id` siempre presente en respuestas exitosas.
- Persistencia en GCS incluye `request_meta.json`.
- Validación de `stock_simple` reforzada y de `expense_evidence` conservada.
- `GET /module-ingestions/{ingestion_id}` disponible para trazabilidad.

## 24. Definición final
`module-ingestions.v2` se define como inbox estable del core SmartCounter: contrato estricto, validación controlada, idempotencia por hash, persistencia en GCS y trazabilidad operativa. No es pipeline cognitivo, no es action engine y no asume integración nativa de Hermes.
