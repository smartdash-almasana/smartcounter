# Contract: POST /module-ingestions

## Endpoint
- `POST /module-ingestions`

## Request minimo
```json
{
  "tenant_id": "demo001",
  "module": "stock_simple",
  "source_type": "google_sheets",
  "generated_at": "ISO_TIMESTAMP",
  "canonical_rows": [],
  "findings": [],
  "summary": {},
  "suggested_actions": []
}
```

## Reglas vigentes
- Todos los campos de primer nivel son obligatorios.
- `module` debe ser `stock_simple`.

## Response
```json
{
  "ok": true,
  "ingestion_id": "ing_xxx"
}
```

## Persistencia local
Se crea:
- `storage/module_ingestions/<tenant_id>/<module>/<ingestion_id>/input.json`
- `canonical_rows.json`
- `findings.json`
- `summary.json`
- `suggested_actions.json`
