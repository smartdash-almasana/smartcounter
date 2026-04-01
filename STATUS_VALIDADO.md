# STATUS VALIDADO — SmartCounter MVP

Fecha de corte: 2026-03-31

## Estado actual
Este bloque quedó validado y congelado.

### Endpoints validados
- `POST /revision-jobs/{job_id}/curated-return`
- `POST /revision-jobs/{job_id}/final-parse`
- `GET /revision-jobs/{job_id}`

## Comportamiento validado

### curated-return
Caso bueno (`demo.csv`)
- `status = curated_return_valid`
- `next_action = ready_for_final_parse`

Caso malo (`demo_bad.csv`)
- `status = curated_return_invalid`
- `next_action = investigate_curated_return`

### final-parse
Caso bueno después de `demo.csv`
- `status = final_parse_ready`
- `next_action = done`
- `row_count = 1`

Caso malo después de `demo_bad.csv`
- `status = final_parse_invalid`
- `next_action = investigate_final_parse`

## Correcciones confirmadas
- `submit_curated_return(...)` deduplica warnings correctamente
- no duplica `duplicate_rows`
- no duplica `fecha_needs_normalization` si ya existe `invalid_fecha`
- no duplica `fecha_vencimiento_needs_normalization` si ya existe `invalid_fecha_vto`
- `final_parse(...)` acepta `curated_return_invalid`

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

## Runner único
```bash
./run_all_smokes.sh