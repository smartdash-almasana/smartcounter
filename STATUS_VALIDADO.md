# STATUS VALIDADO — SmartCounter MVP

Fecha de corte: 2026-03-31

## Estado actual
Este bloque quedó validado y congelado.

### Endpoints validados
- `POST /revision-jobs/{job_id}/curated-return`
- `POST /revision-jobs/{job_id}/final-parse`
- `GET /revision-jobs/{job_id}`
- `POST /revision-jobs/{job_id}/curation-plan`
- `POST /revision-jobs/{job_id}/select-adapter`
- `POST /revision-jobs/{job_id}/google-adapter-plan`
- `POST /revision-jobs/{job_id}/microsoft-adapter-prompt`

## Comportamiento validado

### PDF / alcance actual
- pdf_text cerrado y validado en Cloud Shell
- caso vacío: next_action=human_review_required y normalized_preview vacío
- caso con texto real: next_action=guided_curation y normalized_preview con 1 fila
- alcance cerrado: PDF con texto extraíble sí
- fuera de alcance por ahora: PDF escaneado / OCR no

### curated-return
Caso bueno (`demo.csv`)
- `status = curated_return_valid`
- `next_action = ready_for_final_parse`

Caso malo (`demo_bad.csv`)
- `status = curated_return_invalid`
- `next_action = investigate_curated_return`
- warnings limpios:
  - `Fechas inválidas en fecha: 2`
  - `Filas duplicadas detectadas: 1`

### final-parse
Caso bueno después de `demo.csv`
- `status = final_parse_ready`
- `next_action = done`
- `row_count = 1`
- `warnings = []`

Caso malo después de `demo_bad.csv`
- `status = final_parse_invalid`
- `next_action = investigate_final_parse`

## Correcciones confirmadas
- `submit_curated_return(...)` deduplica warnings correctamente
- no duplica `duplicate_rows`
- no duplica `fecha_needs_normalization` si ya existe `invalid_fecha`
- no duplica `fecha_vencimiento_needs_normalization` si ya existe `invalid_fecha_vto`
- `final_parse(...)` acepta `curated_return_invalid`

## Reglas de cierre confirmadas
- `confirm-handoff` existe y funciona
- `confirm-handoff` es idempotente
- `canonical-export` no pisa `handoff_confirmed`
- mutaciones post-confirmación bloqueadas con `409`
- `select-adapter` validado con `409` para job cerrado
- `ALLOWED_ADAPTERS = {"google", "microsoft"}`

## Endurecimiento de GET /revision-jobs/{job_id}
Además de `profile` y `result`, ahora devuelve:
- `job_identity`
- `source_profile`
- `latest_execution`
- `artifacts`
- `status_summary`

## Smokes disponibles
- `smoke_test.py`
- `smoke_job_state.py`
- `smoke_get_revision_job.py`
- `smoke_curation_plan.py`
- `smoke_select_adapter.py`
- `smoke_google_adapter_plan.py`
- `smoke_microsoft_adapter_prompt.py`

## Runner único
```bash
./run_all_smokes.sh
