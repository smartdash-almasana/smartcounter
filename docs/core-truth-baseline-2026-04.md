# Core Truth Baseline (2026-04)

## Decisión de lectura oficial
- `module-ingestions` se lee hoy como bus de captura/persistencia.
- `revision-jobs` se lee hoy como pipeline cognitivo vigente.
- `normalized_signals` explícito es deuda abierta.
- `action engine` de ejecución es deuda abierta.
- Hermes-Bridge v1 debe enchufarse primero al plano cognitivo, no asumir un core unificado inexistente.

## A. Resumen Ejecutivo Del Core Actual
- El core HTTP real está en FastAPI con entrypoint en `app.py` y el router modular de ingesta en `backend/routes/module_ingestions.py`.
- `POST /module-ingestions` está conectado y operativo a nivel wiring: `app.py:25`, `backend/routes/module_ingestions.py:12-15`.
- Esa ingesta persiste artefactos en GCS (no en disco local): `backend/services/module_ingestion_service.py:17-18`, `backend/services/module_ingestion_service.py:67-71`.
- El contrato real acepta `stock_simple` y `expense_evidence` en schema: `backend/schemas/module_ingestions.py:6`.
- Para `stock_simple`, validación mínima real: solo exige `source_type=google_sheets`: `backend/services/module_ingestion_service.py:74-76`.
- Para `expense_evidence` sí hay validación fuerte de shape, findings, summary y prioridades: `backend/services/module_ingestion_service.py:109-151`.
- No hay idempotencia por hash ni deduplicación en `module-ingestions`; siempre genera `ing_*` nuevo: `backend/utils/ids.py:4-5`, `backend/services/module_ingestion_service.py:169`.
- Existe un flujo multipaso separado (`revision-jobs/*`) con perfilado, curación, handoff y parse final: `app.py:212-1459`.
- Normalización interna real está en `revision_tabular.py` y `revision_pdf_text.py`: `revision_tabular.py:294-368`, `revision_pdf_text.py:104-143`.
- `normalized_signals` como artefacto explícito no existe en código (no confirmado por nombre equivalente).
- Action engine de ejecución no existe: el core solo valida/persiste `suggested_actions`, no las ejecuta: `backend/services/module_ingestion_service.py:137-151`.
- La parte más sólida hoy es el pipeline `revision-jobs` (wiring completo de endpoints y estados).
- La parte más verde es `module-ingestions` como bus de entrada: valida/persiste, pero no tiene procesamiento downstream propio ni cobertura estática visible dedicada.

## B. Mapa De Capacidad Real Por Bloque

### 1) `module-ingestions`
- **Estado:** IMPLEMENTADO
- **Qué hace exactamente:** recibe JSON, valida por módulo, persiste artefactos JSON y responde `accepted`.
- **Qué archivos lo prueban:** `backend/routes/module_ingestions.py:12-26`, `backend/services/module_ingestion_service.py:166-219`.
- **Qué endpoints/funciones/services participan:** `create_module_ingestion`, `persist_module_ingestion`.
- **Qué limitaciones tiene hoy:** no endpoint de lectura/listado de ingestas; no procesamiento posterior explícito.

### 2) validación de contrato
- **Estado:** PARCIAL
- **Qué hace exactamente:** schema obligatorio de top-level + validaciones específicas fuertes solo para `expense_evidence`.
- **Qué archivos lo prueban:** `backend/schemas/module_ingestions.py:37-46`, `backend/services/module_ingestion_service.py:74-76`, `backend/services/module_ingestion_service.py:109-151`.
- **Qué endpoints/funciones/services participan:** `ModuleIngestionRequest`, `_validate_stock_simple_payload`, `_validate_expense_evidence_payload`.
- **Qué limitaciones tiene hoy:** `generated_at` es `str` libre; en `stock_simple` no se valida shape interno de filas/findings.

### 3) persistencia de artefactos
- **Estado:** IMPLEMENTADO
- **Qué hace exactamente:** sube `input`, `canonical_rows`, `findings`, `summary`, `suggested_actions`, `result` a bucket GCS.
- **Qué archivos lo prueban:** `backend/services/module_ingestion_service.py:176-189`, `backend/services/module_ingestion_service.py:211`.
- **Qué endpoints/funciones/services participan:** `persist_module_ingestion`, `_upload_json`.
- **Qué limitaciones tiene hoy:** docs dicen local; código real usa GCS.

### 4) soporte por módulo
- **Estado:** PARCIAL
- **Qué hace exactamente:** acepta exactamente `stock_simple` y `expense_evidence`.
- **Qué archivos lo prueban:** `backend/schemas/module_ingestions.py:6`, `backend/services/module_ingestion_service.py:154-163`.
- **Qué endpoints/funciones/services participan:** `ModuleName`, `_validate_payload_for_module`.
- **Qué limitaciones tiene hoy:** nuevos módulos requieren cambio de código (`Literal` + branch validator).

### 5) normalización semántica
- **Estado:** IMPLEMENTADO (en `revision-jobs`, no en `module-ingestions`)
- **Qué hace exactamente:** mapeo de headers, normalización importe/fechas, perfilado y `next_action`.
- **Qué archivos lo prueban:** `revision_tabular.py:46-208`, `revision_tabular.py:258-368`, `app.py:930-1108`.
- **Qué endpoints/funciones/services participan:** `run_tabular_profile`, `build_tabular_normalized_preview`, `build_normalized_preview`, `build_auto_curate_preview`.
- **Qué limitaciones tiene hoy:** `module-ingestions` no normaliza payload entrante.

### 6) `additional_artifacts`
- **Estado:** PARCIAL
- **Qué hace exactamente:** soportado solo en `expense_evidence`; sanitiza key y evita colisión con nombres reservados (`extra_...`).
- **Qué archivos lo prueban:** `backend/schemas/module_ingestions.py:46`, `backend/services/module_ingestion_service.py:52-59`, `backend/services/module_ingestion_service.py:191-200`.
- **Qué endpoints/funciones/services participan:** `ModuleIngestionRequest.additional_artifacts`, `persist_module_ingestion`.
- **Qué limitaciones tiene hoy:** ignorado para `stock_simple`.

### 7) signals / prioridades
- **Estado:** PARCIAL
- **Qué hace exactamente:** existe `priority` solo como validación de `suggested_actions` en `expense_evidence`; en revisión se usa `issues/severity` para `next_action`.
- **Qué archivos lo prueban:** `backend/services/module_ingestion_service.py:141-147`, `revision_common.py:34-43`.
- **Qué endpoints/funciones/services participan:** `_validate_expense_evidence_payload`, `decide_next_action_from_issues`.
- **Qué limitaciones tiene hoy:** no hay entidad/artefacto `normalized_signals` explícito.

### 8) digest / resumen
- **Estado:** PARCIAL
- **Qué hace exactamente:** hay resumen operativo de handoff (`summary_text`) y `curated_return_summary` en flujo `revision-jobs`.
- **Qué archivos lo prueban:** `app.py:751-857`, `app.py:1418-1450`.
- **Qué endpoints/funciones/services participan:** `build_handoff_summary`, `submit_curated_return`.
- **Qué limitaciones tiene hoy:** no existe capa ejecutiva unificada transversal al core modular.

### 9) action engine
- **Estado:** NO IMPLEMENTADO
- **Qué hace exactamente:** hoy solo persiste/valida acciones sugeridas; no ejecuta acciones (`mail`, `evento`, etc.).
- **Qué archivos lo prueban:** `backend/services/module_ingestion_service.py:137-151`, `backend/services/module_ingestion_service.py:189`.
- **Qué endpoints/funciones/services participan:** validación y persistencia de `suggested_actions`.
- **Qué limitaciones tiene hoy:** no scheduler, no dispatcher, no workers.

### 10) multipaso cognitivo
- **Estado:** IMPLEMENTADO (en `revision-jobs`)
- **Qué hace exactamente:** perfilado -> decisión -> selección adapter -> paquete -> preview -> handoff -> curated return -> final parse.
- **Qué archivos lo prueban:** `app.py:272-1570`, `revision_common.py:34-43`.
- **Qué endpoints/funciones/services participan:** endpoints `revision-jobs/*` y `decide_next_action_from_issues`.
- **Qué limitaciones tiene hoy:** es un flujo separado de `module-ingestions`.

### 11) billing-friendly idempotency / content hashing
- **Estado:** PARCIAL
- **Qué hace exactamente:** calcula hash SHA-256 en `revision-jobs` y `curated-return`.
- **Qué archivos lo prueban:** `app.py:222-239`, `app.py:1303`, `revision_common.py:26-27`.
- **Qué endpoints/funciones/services participan:** `create_revision_job`, `submit_curated_return`, `sha256_bytes`.
- **Qué limitaciones tiene hoy:** no usa hash para deduplicar ni rechazar repetidos; `module-ingestions` no hashea.

### 12) observabilidad / logs / auditoría
- **Estado:** PARCIAL
- **Qué hace exactamente:** trazabilidad por artefactos JSON y endpoint de estado (`GET /revision-jobs/{job_id}`).
- **Qué archivos lo prueban:** `app.py:354-433`, `app.py:44-52`.
- **Qué endpoints/funciones/services participan:** `get_revision_job`, `load_json_from_gcs`, `save_json_to_gcs`.
- **Qué limitaciones tiene hoy:** sin logging estructurado ni métricas internas visibles.

### 13) evidencia estática disponible en tests/docs/scripts
- **Estado:** PARCIAL
- **Qué hay exactamente:** tests y smokes enfocados en pipeline UI/`revision-jobs`; no hay pruebas estáticas específicas de `module-ingestions`.
- **Qué archivos lo prueban:** `tests/test_materialize_for_pipeline.py:47-85`, `scripts/smokes/smoke_test.py:67-127`, `tests/e2e/mvp_smoke.spec.js:4-39`.
- **Qué limitaciones tiene hoy:** la cobertura visible no valida explícitamente contrato real de `POST /module-ingestions`.

## C. Tabla De Verdad Del Core

| Capacidad | Estado | Evidencia | Nivel de solidez | Comentario corto |
|---|---|---|---|---|
| `POST /module-ingestions` cableado | IMPLEMENTADO | `app.py:25`, `backend/routes/module_ingestions.py:12` | Medio | Ruta activa y servicio invocado |
| Validación top-level contrato | IMPLEMENTADO | `backend/schemas/module_ingestions.py:37-46` | Medio | Requiere campos base |
| Validación profunda `stock_simple` | PARCIAL | `backend/services/module_ingestion_service.py:74-76` | Bajo | Solo verifica `source_type` |
| Validación profunda `expense_evidence` | IMPLEMENTADO | `backend/services/module_ingestion_service.py:109-151` | Medio | Shape/summary/priority controlados |
| Persistencia artefactos | IMPLEMENTADO | `backend/services/module_ingestion_service.py:176-211` | Medio | Persistencia GCS |
| `additional_artifacts` | PARCIAL | `backend/services/module_ingestion_service.py:191-200` | Medio | Solo `expense_evidence` |
| Soporte nuevos módulos plug and play | NO IMPLEMENTADO | `backend/schemas/module_ingestions.py:6`, `backend/services/module_ingestion_service.py:154-163` | Bajo | Requiere cambio de código |
| Normalización tabular/pdf | IMPLEMENTADO | `revision_tabular.py`, `revision_pdf_text.py`, `app.py:930+` | Medio | Está en flujo `revision-jobs` |
| `normalized_signals` explícito | NO IMPLEMENTADO | Búsqueda estática sin definiciones | Bajo | No hay artefacto/contrato con ese nombre |
| Digest ejecutivo | PARCIAL | `app.py:751-857` | Medio | `summary_text` de handoff, no capa global |
| Action engine ejecución | NO IMPLEMENTADO | `backend/services/module_ingestion_service.py:137-151` | Bajo | Solo valida/persiste sugerencias |
| Idempotencia/dedupe por hash | NO IMPLEMENTADO | `backend/utils/ids.py:4-5`, `app.py:222`, `app.py:1303` | Bajo | Hash sin deduplicación |
| Observabilidad | PARCIAL | `app.py:354-433` | Medio | Estado por artefactos, sin métricas/logs |

## D. Enchufes Reales Del Core

### Endpoints FastAPI activos
- `GET /health` (`app.py:207`).
- `POST /module-ingestions` (`backend/routes/module_ingestions.py:12`).
- `POST /revision-jobs` y demás endpoints multipaso (`app.py:212-1459`).

### Schemas reales
- `ModuleIngestionRequest`, `ModuleIngestionResponse`, `ExpenseEvidenceFrozenRow` (`backend/schemas/module_ingestions.py:17-55`).

### Services reales
- `persist_module_ingestion` (`backend/services/module_ingestion_service.py:166`).
- `run_tabular_profile`, `build_tabular_normalized_preview` (`revision_tabular.py:294`, `revision_tabular.py:304`).
- `run_pdf_text_profile`, `build_pdf_text_normalized_preview` (`revision_pdf_text.py:104`, `revision_pdf_text.py:113`).

### Funciones públicas relevantes
- `create_module_ingestion` (`backend/routes/module_ingestions.py:13`).
- `create_revision_job`, `run_profile`, `get_revision_job`, `final_parse`, etc. (`app.py`).

### Qué espera cada enchufe
- `POST /module-ingestions` espera JSON conforme a `ModuleIngestionRequest` (`backend/schemas/module_ingestions.py:37-46`).
- `revision-jobs` espera form-data y archivo (`app.py:212-216`).

### Qué módulos acepta realmente hoy
- En contrato de schema: `stock_simple`, `expense_evidence` (`backend/schemas/module_ingestions.py:6`).
- Edge conectado visible: solo `stock_simple` Apps Script (`apps_script/stock_simple/Ui.gs:107-118`).

## E. Contrato Real Actual De `POST /module-ingestions`

### Shape real aceptado hoy (Pydantic)

```json
{
  "tenant_id": "str",
  "module": "stock_simple | expense_evidence",
  "source_type": "google_sheets | upload | email | drive | api | other",
  "generated_at": "str",
  "canonical_rows": [{}],
  "findings": [{}],
  "summary": {},
  "suggested_actions": [{}],
  "additional_artifacts": {}
}
```

Fuente: `backend/schemas/module_ingestions.py:37-46`.

### Campos obligatorios
- `tenant_id`, `module`, `source_type`, `generated_at`, `canonical_rows`, `findings`, `summary`, `suggested_actions` (por no tener default).

Fuente: `backend/schemas/module_ingestions.py:37-45`.

### Campos opcionales
- `additional_artifacts` (default `{}`).

Fuente: `backend/schemas/module_ingestions.py:46`.

### Módulos aceptados
- Solo `stock_simple` y `expense_evidence`; cualquier otro falla.

Fuente: `backend/services/module_ingestion_service.py:154-163`.

### Validaciones reales
- `stock_simple`: `source_type` debe ser `google_sheets` (`backend/services/module_ingestion_service.py:74-76`).
- `expense_evidence`: valida source_type permitido, shape de filas contra `ExpenseEvidenceFrozenRow`, tipo de findings, claves obligatorias de summary y formato de suggested_actions (`backend/services/module_ingestion_service.py:109-151`).

### Persistencia real que dispara
- Sube JSON a GCS en `tenant_<tenant>/module_ingestions/<module>/<ing_id>/...` con `input/canonical_rows/findings/summary/suggested_actions/result` (+ extras para `expense_evidence`).

Fuente: `backend/services/module_ingestion_service.py:173-211`.

### Qué pasa después de aceptar el payload
- Devuelve `ok`, `ingestion_id`, `tenant_id`, `module`, `status=accepted`, `artifacts`.
- No hay flujo posterior automático en el backend para esa ingesta.

Fuente: `backend/routes/module_ingestions.py:19-25` y búsqueda estática de referencias.

## F. Hallazgos Importantes

### Inconsistencia spec vs realidad
- Docs dicen `module=stock_simple` y persistencia local, pero código acepta también `expense_evidence` y persiste en GCS.
- Evidencia: `docs/module-ingestions-contract.md:22`, `docs/module-ingestions-contract.md:32-38`, `backend/schemas/module_ingestions.py:6`, `backend/services/module_ingestion_service.py:17-18`.

### Nombres engañosos
- `storage/module_ingestions` aparece en README/docs como persistencia activa, pero no está conectada al servicio real.
- Evidencia: `README.md:21`, `backend/services/module_ingestion_service.py:67-71`.

### Capacidad aparente no conectada
- Hay schema para `expense_evidence`, pero no aparece cliente edge integrado equivalente a `stock_simple`; solo Apps Script de stock publica al endpoint.
- Evidencia: `apps_script/stock_simple/Ui.gs:109`, `backend/schemas/module_ingestions.py:6`.

### Acople frágil
- Cliente Apps Script exige `parsed.ingestion_id`; el backend hoy lo devuelve, pero docs publican respuesta mínima distinta.
- Evidencia: `apps_script/stock_simple/SmartCounterClient.gs:31-33`, `docs/module-ingestions-contract.md:24-29`.

### Código no conectado
- Utilidad de persistencia local `backend/utils/json_files.py` no aparece usada por rutas/servicios actuales.
- Evidencia: `backend/utils/json_files.py` sin referencias en `app.py`/`backend`.

## G. Qué Está Listo Para Usar Como Base De Nuevos Módulos

### Listo y reutilizable
- Contrato base de ingesta + persistencia de artefactos + naming de paths + respuesta estandarizada: `backend/schemas/module_ingestions.py`, `backend/services/module_ingestion_service.py:166-219`.

### Listo pero incompleto
- Mecánica de validación por módulo (`_validate_payload_for_module`) existe, pero requiere tocar código para cada nuevo módulo: `backend/services/module_ingestion_service.py:154-163`.

### No listo para escalar módulos sin fricción
- No hay registro dinámico de módulos.
- No hay downstream processor de ingestas.
- No hay idempotencia por contenido.
- No hay action engine.

## H. Frontera Real Actual Del Core

### Hasta acá llega hoy
- El core puede recibir ingestas modulares, validarlas (con distinto rigor por módulo), y persistir artefactos en GCS con trazabilidad por `ingestion_id`.

### Esto ya se puede usar
- `stock_simple` end-to-end de edge a `POST /module-ingestions` y almacenamiento de artifacts.
- Flujo `revision-jobs` multipaso con normalización y parse final como pipeline separado.

### Esto todavía no
- Orquestación automática post-ingesta modular.
- Ejecución de acciones.
- `normalized_signals` formal.
- Idempotencia/deduplicación por hash.
- Onboarding de módulos nuevos sin cambios de código.

## I. Evidencia Textual

### Ruta activa de ingesta modular
- Archivo: `app.py:25`.
- Función/Ruta: `app.include_router(module_ingestions_router)`.
- Demuestra: `/module-ingestions` está conectado al entrypoint principal.

### Contrato real del endpoint
- Archivo: `backend/routes/module_ingestions.py:12-26`.
- Función: `create_module_ingestion`.
- Demuestra: request tipado y response con `status` + `artifacts`.

### Módulos aceptados reales
- Archivo: `backend/schemas/module_ingestions.py:6`.
- Clase: `ModuleName = Literal["stock_simple","expense_evidence"]`.
- Demuestra: soporte declarado para 2 módulos.

### Persistencia real en cloud
- Archivo: `backend/services/module_ingestion_service.py:17-18`, `backend/services/module_ingestion_service.py:67-71`.
- Función: `_upload_json`.
- Demuestra: escritura en bucket GCS, no filesystem local.

### Validación fuerte solo en `expense_evidence`
- Archivo: `backend/services/module_ingestion_service.py:109-151`.
- Función: `_validate_expense_evidence_payload`.
- Demuestra: controles de shape/findings/summary/priority.

### `stock_simple` mínimo
- Archivo: `backend/services/module_ingestion_service.py:74-76`.
- Función: `_validate_stock_simple_payload`.
- Demuestra: regla puntual `source_type`.

### Sin deduplicación por hash en ingesta modular
- Archivo: `backend/utils/ids.py:4-5`, `backend/services/module_ingestion_service.py:169`.
- Demuestra: ID aleatorio por request; no chequeo previo.

### Multipaso cognitivo real del pipeline principal
- Archivo: `app.py:212-1459`, `revision_common.py:34-43`.
- Demuestra: estados + `next_action` basado en issues.

### Inconsistencia docs vs código
- Archivo: `docs/module-ingestions-contract.md:22`, `docs/module-ingestions-contract.md:32-38`, `backend/services/module_ingestion_service.py:17-18`.
- Demuestra: doc dice local + `stock_simple` only; código difiere.

### Edge realmente conectado hoy
- Archivo: `apps_script/stock_simple/Ui.gs:107-118`, `apps_script/stock_simple/SmartCounterClient.gs:8-13`.
- Demuestra: Apps Script envía payload real a `/module-ingestions`.

## J. Próximo Paso Más Lógico
- La frontera de verdad hoy está en ingesta y persistencia, no en orquestación post-ingesta modular.
- Para decidir producto/arquitectura, el punto crítico es alinear una única fuente de verdad de contrato (docs vs código).
- Separar explícitamente en documentación los dos planos reales: `module-ingestions` (capture/store) y `revision-jobs` (pipeline cognitivo).
- Definir si `module-ingestions` seguirá como inbox pasivo o pasará a disparar procesamiento real.

## Implicancia para próximos diseños
Cualquier especificación nueva (Hermes, nuevos módulos, signals, actions) debe partir de esta línea base operacional: dos planos reales separados, sin core unificado completo hoy. Diseñar sobre una arquitectura ideal no reflejada en código aumenta riesgo de desalineación entre contrato, implementación y operación.

En este marco, Hermes-Bridge v1 debe considerarse sidecar cognitivo acoplado primero al plano `revision-jobs`, no un reemplazo del core actual ni una prueba de core unificado inexistente.
