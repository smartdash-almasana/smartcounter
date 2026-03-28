# Inventario Minimo de Arranque (SmartCounter)

## Alcance de este inventario

Este inventario describe el estado minimo actual de `E:\BuenosPasos\smartcounter` para arrancar trabajo operativo sin tocar otros repositorios ni carpetas externas.

## Estructura detectada

- `excel_reader.py`
- `smartcounter/README.md`
- `smartcounter/PRODUCT_SCOPE.md`
- `smartcounter/MVP.md`
- `smartcounter/DOMAIN_MODEL.md`
- `smartcounter/ROADMAP.md`

## Estado operativo actual

- Base documental: presente.
- Lector Excel inicial: presente (`excel_reader.py`).
- Entrypoint de ejecucion propio: presente (`run_local.py`).
- Pipeline-curated: presente (deteccion header/tabular + mapping semantico base + normalizacion tipos base + warnings estructurados + `normalization_summary`).

## Baseline corto pipeline-curated (pack focal)

- `03_encabezado_desplazado.xlsx`: header fila 7, mapping `3/0/0`, warning `header_shifted`.
- `04_semantica_inestable.xlsx`: header fila 2, mapping `2/1/0`, warning `header_shifted`.
- `07_formulas_ocultos.xlsx`: header fila 3, mapping `3/0/0`, warning `header_shifted`.
- `08_montos_mixtos_signos.xlsx`: header fila 1, mapping `3/0/0`, warnings de monto (moneda, inválido, signo, separadores) con resumen por campo y ejemplos.

## Limites vigentes (fase actual)

- No resuelve automáticamente ambigüedades semánticas.
- Cobertura aún limitada para fórmula/ocultos como clase específica.
- No hace normalización profunda completa de todas las columnas.

## Decisiones minimas para continuidad inmediata

- Mantener `excel_reader.py` en la raiz por ahora para evitar movimientos innecesarios.
- Tomar `smartcounter/` como carpeta documental de producto.
- Crear como siguiente paso un runner local minimo para ejecutar lectura sobre un archivo Excel.

## Fronteras y restricciones vigentes

- No tocar `E:\BuenosPasos\smartexcel`.
- No tocar `E:\BuenosPasos\smartexcel_app`.
- Sin frontend.
- Sin refactor masivo.
