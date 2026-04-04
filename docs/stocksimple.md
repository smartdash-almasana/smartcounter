# StockSimple Edge Module (Apps Script)

## Ubicacion
- `apps_script/stock_simple/`

## Flujo MVP
1. Google Sheet de stock
2. `runStockSimple()` arma `canonical_rows`, `findings`, `summary`, `suggested_actions`
3. Envía JSON a `POST /module-ingestions`
4. Backend persiste artefactos locales en `storage/module_ingestions/`

## Config minima en Apps Script
- `TENANT_ID`
- `SMARTCOUNTER_BASE_URL` (URL publica accesible desde internet)
- `SOURCE_SHEET_NAME`
- `HEADER_ROW`

## Hojas de salida
- `Stock_Canonico`
- `Stock_Findings`
- `Stock_Resumen`
