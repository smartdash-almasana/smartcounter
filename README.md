# SmartCounter

SmartCounter es un MVP local para revisar planillas contables (Excel/CSV), ejecutar análisis curado y recorrer el flujo completo de carga, resultado, observaciones, reglas, historial y cierre/exportación.

## Ejecutar la app local

```powershell
python smartcounter_ui.py
```

Abrir: `http://127.0.0.1:8501`

## Ejecutar unittest

```powershell
python -m unittest tests/test_materialize_for_pipeline.py -v
```

## Ejecutar smoke/regresión interno

```powershell
python run_smoke_regresion_mvp.py
```

## Ejecutar Playwright smoke

```powershell
npm install
npx playwright install chromium
npx playwright test tests/e2e/mvp_smoke.spec.js
```
