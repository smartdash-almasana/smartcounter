# SmartCounter

SmartCounter combina un backend FastAPI y modulos edge para ingestar y persistir artefactos operativos.

## Arranque backend

```powershell
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Zonas del repo

- `app.py`: entrypoint FastAPI vigente.
- `backend/routes`: rutas extraidas/modulares (incluye `module-ingestions`).
- `backend/services`: logica de negocio de backend.
- `backend/schemas`: contratos Pydantic.
- `backend/utils`: utilidades compartidas.
- `apps_script/stock_simple`: modulo edge Apps Script StockSimple.
- `scripts/smokes`: smokes operativos y runner de regresion.
- `fixtures/demo`: CSV demo/fixture para pruebas manuales.
- `storage/module_ingestions`: persistencia local de artefactos de ingestas de modulo.
- `docs`: operacion y contratos vigentes.
- `archive`: snapshots y documentos legados archivados.
- `tests`: pruebas automatizadas actuales.

## Ejecutar unittest

```powershell
python -m unittest tests/test_materialize_for_pipeline.py -v
```

## Ejecutar smoke/regresion interno

```powershell
python scripts/smokes/run_smoke_regresion_mvp.py
```

## Ejecutar lote de smokes

```bash
bash scripts/smokes/run_all_smokes.sh
```

## Ejecutar Playwright smoke

```powershell
npm install
npx playwright install chromium
npx playwright test tests/e2e/mvp_smoke.spec.js
```
