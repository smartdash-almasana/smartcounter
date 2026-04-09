# Contrato: `module-ingestions.v2`

**Versión:** `module-ingestions.v2`  
**Fuente de verdad:** `backend/schemas/module_ingestions.py` + `backend/services/module_ingestion_service.py`  
**Estado:** CONGELADO – no modificar sin actualizar este documento.

---

## 1. Overview

Este contrato define el payload que cada módulo Edge (micro-saas) debe enviar al Core de SmartCounter cuando finaliza su análisis local.

El Core transforma ese payload en:

```
canonical_rows + findings
    → normalized_signals
    → daily_digest
    → actions
```

**Este endpoint es el único punto de entrada al Core.** Todo módulo Edge debe cumplirlo sin excepción.

---

## 2. Endpoint

```
POST /module-ingestions
Content-Type: application/json
```

No requiere autenticación en LOCAL_DEV. En producción: Bearer token o API key por `tenant_id`.

---

## 3. Payload completo

```json
{
  "contract_version": "module-ingestions.v2",
  "tenant_id": "acme_corp",
  "module": "stock_simple",
  "source_type": "google_sheets",
  "generated_at": "2026-04-07T15:00:00Z",
  "canonical_rows": [...],
  "findings": [...],
  "summary": {...},
  "suggested_actions": [...],
  "content_hash": null,
  "source_channel": null,
  "additional_artifacts": {},
  "parse_metadata": {},
  "audit_metadata": {}
}
```

---

## 4. Definición de cada campo

### `contract_version`
- **Tipo:** `string`
- **Obligatorio:** sí
- **Valor fijo:** `"module-ingestions.v2"`
- **Default en schema:** `"module-ingestions.v2"` (puede omitirse, pero NO se recomienda)
- **Validación:** si se envía con otro valor → `400 ValueError`

---

### `tenant_id`
- **Tipo:** `string`
- **Obligatorio:** sí
- **Descripción:** identificador único del tenant (empresa/negocio)
- **Regla:** solo caracteres alfanuméricos, guion `-` y guion bajo `_`. El Core sanitiza el valor con `_safe_path_part()` para armar rutas GCS.
- **Ejemplos:** `"acme_corp"`, `"debug"`, `"farmacia-norte"`

---

### `module`
- **Tipo:** `string` (enum)
- **Obligatorio:** sí
- **Valores válidos:** `"stock_simple"` | `"expense_evidence"` | `"excel_power_query_edge"`
- **Nota:** cada módulo tiene validaciones específicas adicionales (ver §8)

---

### `source_type`
- **Tipo:** `string` (enum)
- **Obligatorio:** sí
- **Valores válidos:** `"google_sheets"` | `"upload"` | `"email"` | `"drive"` | `"api"` | `"other"` | `"excel_power_query"`
- **Restricción `stock_simple`:** solo acepta `"google_sheets"`
- **Restricción `expense_evidence`:** acepta todos excepto `"excel_power_query"`

---

### `generated_at`
- **Tipo:** `string` (ISO 8601 / RFC 3339)
- **Obligatorio:** sí
- **Formato:** `"YYYY-MM-DDTHH:MM:SSZ"` o con offset `"+03:00"`
- **Regla:** debe incluir zona horaria. Sin zona → `400 ValueError`
- **Ejemplos:** `"2026-04-07T15:00:00Z"`, `"2026-04-07T12:00:00-03:00"`

---

### `canonical_rows`
- **Tipo:** `array<object>`
- **Obligatorio:** sí (puede ser `[]` si no hay filas)
- **Descripción:** filas ya procesadas, limpias y tipadas por el módulo Edge. **No se envían datos crudos.**
- **Ver §5 para estructura por módulo**

---

### `findings`
- **Tipo:** `array<object>`
- **Obligatorio:** sí (puede ser `[]`)
- **Descripción:** eventos relevantes detectados durante el análisis. Son los que generan `normalized_signals`.
- **Ver §7 para estructura y ejemplos**

---

### `summary`
- **Tipo:** `object`
- **Obligatorio:** sí
- **Descripción:** métricas de resumen del análisis. Estructura varía por módulo.
- **Ver §6 para estructura por módulo**

---

### `suggested_actions`
- **Tipo:** `array<object>`
- **Obligatorio:** sí (puede ser `[]`)
- **Descripción:** acciones recomendadas por el módulo Edge, procesadas por `ActionEngine`
- **Estructura por ítem:**
  ```json
  {
    "type": "string",
    "payload": {
      "severity": "high | medium | low"
    }
  }
  ```
- **Nota `expense_evidence`:** requiere campos adicionales — ver §8.3

---

### `content_hash`
- **Tipo:** `string | null`
- **Obligatorio:** no
- **Formato:** SHA-256 hex de 64 caracteres
- **Uso:** si se provee, el Core verifica que coincida con el hash calculado internamente. Si no se provee, el Core lo calcula solo.
- **Propósito:** deduplicación exacta. Si el Core ya recibió un payload con ese hash → responde `accepted_deduped` sin reprocesar.

---

### `source_channel`
- **Tipo:** `string | null`
- **Obligatorio:** no
- **Uso:** identificador del canal de origen (`"apps_script"`, `"api"`, etc.). Solo para trazabilidad.

---

### `additional_artifacts`
- **Tipo:** `object`
- **Obligatorio:** no (default: `{}`)
- **Uso módulo `expense_evidence`:** puede incluir artefactos extra que se persisten en GCS con prefijo `/extra_` si colisionan con nombres reservados.
- **Nombres reservados** (se renombran automáticamente): `input`, `canonical_rows`, `findings`, `summary`, `suggested_actions`, `normalized_signals`, `request_meta`, `digest`, `result`

---

### `parse_metadata` / `audit_metadata`
- **Tipo:** `object`
- **Obligatorio:** no (default: `{}`)
- **Uso:** metadatos de trazabilidad opcionales. Se persisten en `request_meta.json` por ingestion.

---

## 5. `canonical_rows` — estructura por módulo

### `stock_simple`

Campos **obligatorios** por fila:

| Campo | Tipo | Descripción |
|---|---|---|
| `row_id` | `string` | ID único de la fila |
| `producto` | `string` (no vacío) | Nombre del producto |
| `stock_actual` | `number` | Stock actual en unidades |
| `stock_minimo` | `number` | Umbral mínimo definido |
| `consumo_promedio_diario` | `number` | Consumo promedio diario calculado |
| `requires_review` | `boolean` | Si la fila requiere revisión humana |

**Ejemplo:**
```json
[
  {
    "row_id": "row_001",
    "producto": "Paracetamol 500mg",
    "stock_actual": 3,
    "stock_minimo": 20,
    "consumo_promedio_diario": 1.5,
    "requires_review": true
  },
  {
    "row_id": "row_002",
    "producto": "Ibuprofeno 400mg",
    "stock_actual": 150,
    "stock_minimo": 30,
    "consumo_promedio_diario": 4.0,
    "requires_review": false
  }
]
```

---

### `expense_evidence`

El shape de cada fila está **congelado** en `ExpenseEvidenceFrozenRow`. Campos requeridos:

| Campo | Tipo |
|---|---|
| `request_id` | `string` |
| `submitted_at` | `string` (ISO) |
| `requester_name` | `string` |
| `merchant_name` | `string` |
| `document_type` | `string` |
| `document_date` | `string` |
| `document_cuit` | `string` |
| `amount` | `float \| int` |
| `currency` | `string` |
| `payment_method` | `string` |
| `category` | `string` |
| `evidence_list` | `array<object>` |
| `status` | `string` |

Opcionales: `observation_note`, `policy_flag`, `resolved_at`, `resolver_name`

**Ejemplo:**
```json
[
  {
    "request_id": "EXP-2026-0042",
    "submitted_at": "2026-04-01T09:00:00Z",
    "requester_name": "Juan Pérez",
    "merchant_name": "Papelería Norte",
    "document_type": "factura",
    "document_date": "2026-04-01",
    "document_cuit": "20-12345678-9",
    "amount": 4500.00,
    "currency": "ARS",
    "payment_method": "transferencia",
    "category": "insumos_oficina",
    "evidence_list": [{"type": "image", "url": "gs://bucket/ev_042.jpg"}],
    "status": "pending_review"
  }
]
```

---

## 6. `summary` — estructura por módulo

### `stock_simple`

Campos **obligatorios:**

```json
{
  "total_rows": 50,
  "valid_rows": 47,
  "invalid_rows": 3
}
```

Campos opcionales adicionales: cualquier métrica extra del módulo.

---

### `expense_evidence`

Campos **obligatorios:**

```json
{
  "total_cases": 12,
  "ready_for_approval_cases": 5,
  "needs_completion_cases": 4,
  "low_quality_cases": 2,
  "duplicate_suspected_cases": 0,
  "high_amount_cases": 1,
  "invalid_cases": 0
}
```

---

## 7. `findings` — CRÍTICO

### Definición

Un finding es un evento relevante detectado por el módulo Edge durante su análisis. **Los findings son la materia prima de los `normalized_signals`.**

Solo los findings cuyo `code` tenga un mapeo en `FINDING_TO_SIGNAL` generarán señales. El resto se persiste pero no activa lógica downstream.

### Estructura de un finding

```json
{
  "code": "string",
  "severity": "critical | high | medium | low | info",
  "message": "string",
  "row_id": "string | null",
  "sku": "string | null",
  "detected_at": "ISO8601 | null",
  "expires_at": "ISO8601 | null",
  "resolved": false,
  "source": "RULE | HERMES",
  "score": 0.0,
  "confidence": 0.0,
  "evidence": {}
}
```

Campos mínimos reales (los otros tienen defaults seguros): `code` (obligatorio para `stock_simple`), `severity`.

---

### Mapeo `finding.code` → `signal_code` (por módulo)

#### `stock_simple`
| `code` | `signal_code` generado |
|---|---|
| `low_stock_detected` | `stock_break_risk` |
| `critical_stock_detected` | `stock_break_risk` |
| `overstock_detected` | `stock_overstock_risk` |
| `invalid_stock_row` | `stock_data_quality_issue` |

#### `expense_evidence`
| `code` / `finding_type` | `signal_code` generado |
|---|---|
| `missing_evidence` | `expense_evidence_missing` |
| `illegible_evidence` | `expense_evidence_low_quality` |
| `evidence_quality_low` | `expense_evidence_low_quality` |
| `duplicate_evidence_suspected` | `expense_duplicate_suspected` |
| `high_amount_expense` | `expense_policy_risk` |
| `missing_key_fields` | `expense_policy_risk` |

#### `concili_simple` *(módulo futuro, mapeo ya registrado)*
| `code` | `signal_code` generado |
|---|---|
| `unmatched_movement` | `conciliation_unmatched_movement` |
| `amount_mismatch` | `conciliation_amount_mismatch` |
| `date_mismatch` | `conciliation_date_mismatch` |

---

### Ejemplos reales de findings

```json
[
  {
    "code": "low_stock_detected",
    "severity": "high",
    "message": "Stock de Paracetamol 500mg está por debajo del mínimo (3 / mínimo 20)",
    "row_id": "row_001",
    "sku": "PARA-500"
  },
  {
    "code": "critical_stock_detected",
    "severity": "critical",
    "message": "Stock de Insulina agotado. Riesgo inmediato.",
    "row_id": "row_015",
    "sku": "INS-U100"
  },
  {
    "code": "overstock_detected",
    "severity": "low",
    "message": "Stock de Vitamina C excede 10x el mínimo. Riesgo de vencimiento.",
    "row_id": "row_033",
    "sku": "VIT-C1G"
  },
  {
    "code": "missing_evidence",
    "severity": "high",
    "message": "Gasto EXP-2026-0042 no tiene comprobante adjunto.",
    "row_id": null
  },
  {
    "code": "high_amount_expense",
    "severity": "medium",
    "message": "Gasto de $85.000 supera el límite de política (máx $50.000).",
    "row_id": null,
    "evidence": {"limit": 50000, "actual": 85000}
  }
]
```

---

## 8. Reglas de validación por módulo

### 8.1 Reglas globales
| Campo | Error si... |
|---|---|
| `contract_version` | valor distinto de `"module-ingestions.v2"` |
| `generated_at` | sin zona horaria, o no parseable como ISO |
| `module` | valor no registrado en el enum |
| `source_type` | valor no registrado en el enum |
| `canonical_rows` | ítem que no sea `object` |
| `findings` | ítem que no sea `object` |

---

### 8.2 `stock_simple`
| Regla | Error |
|---|---|
| `source_type` ≠ `"google_sheets"` | `400 ValueError` |
| `summary` sin `total_rows`, `valid_rows`, `invalid_rows` | `400 ValueError` |
| Fila sin `row_id`, `producto`, `stock_actual`, `stock_minimo`, `consumo_promedio_diario`, `requires_review` | `400 ValueError` |
| `producto` vacío | `400 ValueError` |
| `stock_actual` / `stock_minimo` / `consumo_promedio_diario` no numéricos | `400 ValueError` |
| `requires_review` no es `boolean` | `400 ValueError` |
| Finding sin `code` | `400 ValueError` |

---

### 8.3 `expense_evidence`
| Regla | Error |
|---|---|
| `source_type` = `"excel_power_query"` | `400 ValueError` |
| Fila que no cumple `ExpenseEvidenceFrozenRow` | `400 ValueError` |
| Finding sin `finding_type` ni `code` | `400 ValueError` |
| `finding_type` y `code` distintos entre sí | `400 ValueError` (mismatch) |
| `finding_type` fuera de los valores permitidos | `400 ValueError` |
| `summary` sin los 7 campos requeridos | `400 ValueError` |
| `suggested_actions[i]` sin `action_type`, `priority`, `description`, `context` | `400 ValueError` |
| `suggested_actions[i].priority` fuera de `high/medium/low` | `400 ValueError` |
| `suggested_actions[i].context` no es `object` | `400 ValueError` |

---

## 9. Ejemplo completo end-to-end — `stock_simple`

```json
{
  "contract_version": "module-ingestions.v2",
  "tenant_id": "farmacia_norte",
  "module": "stock_simple",
  "source_type": "google_sheets",
  "generated_at": "2026-04-07T15:00:00Z",
  "canonical_rows": [
    {
      "row_id": "row_001",
      "producto": "Paracetamol 500mg",
      "stock_actual": 3,
      "stock_minimo": 20,
      "consumo_promedio_diario": 1.5,
      "requires_review": true
    },
    {
      "row_id": "row_002",
      "producto": "Ibuprofeno 400mg",
      "stock_actual": 150,
      "stock_minimo": 30,
      "consumo_promedio_diario": 4.0,
      "requires_review": false
    }
  ],
  "findings": [
    {
      "code": "low_stock_detected",
      "severity": "high",
      "message": "Paracetamol 500mg bajo mínimo (3 / mín 20)",
      "row_id": "row_001",
      "sku": "PARA-500"
    }
  ],
  "summary": {
    "total_rows": 2,
    "valid_rows": 2,
    "invalid_rows": 0
  },
  "suggested_actions": [
    {
      "type": "generar_orden_compra",
      "payload": {
        "severity": "high"
      }
    }
  ]
}
```

**Respuesta esperada (200):**
```json
{
  "ok": true,
  "ingestion_id": "ing_a1b2c3d4e5f6",
  "contract_version": "module-ingestions.v2",
  "tenant_id": "farmacia_norte",
  "module": "stock_simple",
  "status": "accepted",
  "deduplicated": false,
  "deduped": false,
  "content_hash": "sha256hex...",
  "artifacts": {
    "input": "tenant_farmacia_norte/module_ingestions/stock_simple/ing_.../input.json",
    "canonical_rows": "...",
    "findings": "...",
    "normalized_signals": "...",
    "summary": "...",
    "suggested_actions": "...",
    "request_meta": "...",
    "digest": "...",
    "result": "..."
  }
}
```

**Si el mismo payload se envía de nuevo (deduplicación):**
```json
{
  "status": "accepted_deduped",
  "deduplicated": true
}
```

---

## 10. Flujo interno del sistema

```
POST /module-ingestions (payload)
    │
    ├─ 1. Validación del schema (Pydantic)
    │       └─ 422 si tipos incorrectos
    │
    ├─ 2. Validación de negocio por módulo
    │       └─ 400 ValueError si reglas rotas
    │
    ├─ 3. Cálculo de content_hash (SHA-256)
    │       └─ Deduplicación: si existe → accepted_deduped
    │
    ├─ 4. build_normalized_signals_from_payload(payload)
    │       └─ findings → consolida por (tenant, module, entity, signal_code)
    │       └─ produce: normalized_signals[]
    │
    ├─ 5. build_daily_digest_v1(tenant_id, normalized_signals, summary)
    │       └─ filtra señales activas
    │       └─ ordena por priority → severity → score
    │       └─ produce: digest { foto_de_hoy, lo_que_importa_ahora, pregunta_del_dia }
    │
    ├─ 6. ActionEngine.build_actions(digest, suggested_actions)
    │       └─ alerts del digest → acciones type=review_issue
    │       └─ suggested_actions del módulo → acciones mapeadas
    │       └─ deduplicación + ordenamiento por priority
    │
    ├─ 7. ActionStore.save_latest_actions(tenant_id, actions)
    │       └─ disponible en GET /actions/latest?tenant_id=...
    │
    └─ 8. Persistencia en GCS (o no-op en LOCAL_DEV)
            └─ artifacts: input, canonical_rows, findings, normalized_signals,
                          summary, suggested_actions, request_meta, digest, result
```

---

## 11. Anti-patterns — lo que NO se debe hacer

### ❌ Enviar datos crudos en `canonical_rows`
```json
// MAL: fila sin normalizar
{ "A": "paracetamol", "B": "3 unidades", "C": "si" }

// BIEN: fila canónica con tipos correctos
{ "row_id": "r1", "producto": "Paracetamol 500mg", "stock_actual": 3, ... }
```

---

### ❌ Omitir `findings` cuando hay anomalías
Si el módulo detectó stock bajo mínimo pero no envía el finding `low_stock_detected`, el Core **nunca sabrá** que hay un riesgo. Los `canonical_rows` no se analizan downstream.

---

### ❌ Inventar `signal_code` en `findings`
El pipeline usa el campo `code` para buscar en `FINDING_TO_SIGNAL`. Un `code` no registrado produce un finding silencioso (se persiste pero no genera señal).

```json
// MAL: code inventado
{ "code": "hay_poco_stock", "severity": "high" }

// BIEN: code registrado en el contrato
{ "code": "low_stock_detected", "severity": "high" }
```

---

### ❌ Duplicar lógica del Core en el Edge
El módulo Edge **no debe** calcular `normalized_signals`, ni construir `digest`, ni decidir qué acciones ejecutar. Solo envía `findings` con los datos correctos. El Core hace el resto.

---

### ❌ Enviar `generated_at` sin zona horaria
```json
// MAL
"generated_at": "2026-04-07T15:00:00"

// BIEN
"generated_at": "2026-04-07T15:00:00Z"
```

---

### ❌ Mezclar `finding_type` y `code` con valores distintos (`expense_evidence`)
```json
// MAL: mismatch → 400 ValueError
{ "finding_type": "missing_evidence", "code": "evidence_quality_low" }

// BIEN: un solo campo, o ambos con el mismo valor
{ "finding_type": "missing_evidence" }
```

---

### ❌ Crear un módulo con nombre no registrado
El campo `module` es un enum cerrado. Un módulo nuevo debe registrarse en el schema antes de poder enviar payloads.

```
ModuleName = Literal["stock_simple", "expense_evidence", "excel_power_query_edge"]
```

---

## 12. Agregar un nuevo módulo (checklist)

1. [ ] Agregar el nombre al `Literal` en `backend/schemas/module_ingestions.py`
2. [ ] Definir `source_type` permitidos para ese módulo
3. [ ] Definir `REQUIRED_*_SUMMARY_KEYS` y `REQUIRED_*_ROW_KEYS` si aplica
4. [ ] Agregar el mapeo `finding.code → signal_code` en `FINDING_TO_SIGNAL`
5. [ ] Implementar `_validate_{module}_payload()` y registrarla en `_validate_payload_for_module()`
6. [ ] Actualizar este documento con §5, §6, §7 y §8 del nuevo módulo
7. [ ] Agregar ejemplo end-to-end en §9

---

*Última actualización: 2026-04-07 | Derivado del código en producción*
