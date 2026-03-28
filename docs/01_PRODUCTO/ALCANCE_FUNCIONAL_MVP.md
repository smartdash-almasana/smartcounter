# Alcance Funcional MVP

## 1. Funcionalidades que si entran en MVP v1

- Detectar hoja util, region tabular y header real en un Excel local.
- Ejecutar mapping semantico base de columnas con estado `mapped`, `ambiguous` o `unmapped`.
- Normalizar en preview tipos base: `fecha`, `monto`, `cuit/cuil` y `null`.
- Emitir warnings estructurados para deteccion, mapping y normalizacion.
- Entregar una salida curada para revision humana con `normalization_summary`.

## 2. Funcionalidades que no entran

- Clasificacion completa de todos los tipos de planilla.
- Resolucion automatica de ambiguedades semanticas.
- Normalizacion profunda de todas las columnas del archivo.
- Formula/ocultos tratados como clase completa de analisis.
- Scoring contable final.
- Export AFIP/ARCA.
- Conciliacion completa.
- ERP, dashboard o suite contable integral.

## 3. Flujo minimo de usuario

1. El operador corre `run_local.py --excel <archivo> --pipeline-curated`.
2. El sistema detecta tabla/header.
3. El sistema propone mapping semantico base.
4. El sistema normaliza valores evidentes en preview.
5. El sistema devuelve warnings y resumen curado para revision humana.

## 4. Artefactos de entrada aceptados

- Un archivo Excel local por corrida.
- Hojas con encabezados desplazados, aliases inestables y montos sucios.
- Baseline ya confirmado sobre:
  - `03_encabezado_desplazado.xlsx`
  - `04_semantica_inestable.xlsx`
  - `07_formulas_ocultos.xlsx`
  - `08_montos_mixtos_signos.xlsx`

## 5. Artefactos de salida entregados

- `sheet`
- `header_row_1based`
- `semantic_mapping`
- `normalized_preview`
- `warnings_estructurados`
- `normalization_summary`

## 6. Limites actuales del motor

- No adivina significado cuando una columna queda ambigua.
- No cubre todavia bien formula/ocultos como categoria especifica en la salida curada.
- No reconstruye dataset final contable completo.
- No reemplaza revision humana.

## 7. Criterio de aceptacion del MVP

- El MVP v1 se considera aceptable si un operador contable puede correrlo sobre un Excel real y obtener una salida que:
  - detecta correctamente la tabla/header,
  - muestra que columnas entendio,
  - explicita que columnas o valores requieren revision,
  - y ahorra el primer filtro manual sin ocultar riesgo.

## 8. Dependencia exacta del pipeline-curated actual

- Este MVP depende directamente del pipeline-curated ya operativo.
- El alcance funcional actual es exactamente lo que hoy entrega ese pipeline:
  - detector tabular/header,
  - mapper semantico base,
  - normalizador base,
  - warnings estructurados,
  - `normalization_summary`.
- Baseline confirmado:
  - `03`: header correcto, mapping `3/0/0`, warning `header_shifted`
  - `04`: header correcto, mapping `2/1/0`, warning `header_shifted`
  - `07`: header correcto, mapping `3/0/0`, warning `header_shifted`
  - `08`: header correcto, mapping `3/0/0`, warnings de monto con resumen y ejemplos utiles para revision
