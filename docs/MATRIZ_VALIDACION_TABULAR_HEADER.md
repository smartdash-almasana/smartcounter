# Matriz Validacion Tabular Header

## Matriz de validacion propuesta

| archivo | categoría | sheet esperada | header_row_1based esperado | confianza esperada | warnings_estructurales esperados | observación breve |
|---|---|---|---:|---|---|---|
| `00_indice_casos.xlsx` | índice/meta (no tabular contable) | `Indice` | 1 | baja | `header_low_confidence`, `missing_expected_columns` | sirve para control de pack, no para extracción contable. |
| `01_tabular_limpio.xlsx` | tabular limpio | `Cobranzas` | 4 | alta | `header_shifted` | baseline simple para validar detección correcta. |
| `02_tabular_sucio_leve.xlsx` | tabular sucio leve | `Cobros marzo` | 3 | alta | `header_shifted` | encabezados con espacios/variantes y datos manuales típicos. |
| `03_encabezado_desplazado.xlsx` | estructura desplazada | `Resumen Clientes` | 7 | alta | `header_shifted` | caso clave de encabezado muy abajo. |
| `04_semantica_inestable.xlsx` | ambigüedad semántica | `Saldos` | 2 | alta | `header_shifted` | aliases no estándar (`empresa`, `vto`, `saldo`). |
| `05_color_como_dato.xlsx` | límite por semántica visual | `Gestión` | 4 | alta | `header_shifted` | detecta tabla, pero el significado depende de color. |
| `06_multiproposito_pyme.xlsx` | multipropósito/no contable puro | `Todo junto` | 4 | alta | `header_shifted`, `interleaved_empty_columns` | una hoja con dos bloques lógicos y columnas intercaladas. |
| `07_formulas_ocultos.xlsx` | fórmulas/ocultos | `CXC Mar-26` | 3 | alta | `header_shifted` | para detector header alcanza; ocultos/fórmulas quedan para warnings posteriores. |
| `08_montos_mixtos_signos.xlsx` | montos inestables | `Cobranzas` | 1 | alta | *(ninguno esperado)* | header claro, útil luego para normalización/warnings de monto. |

## Top 5 críticos

- `03_encabezado_desplazado.xlsx`: valida el riesgo principal del detector (header lejos de fila 1).
- `06_multiproposito_pyme.xlsx`: fuerza manejo de hoja mixta y columnas intercaladas.
- `04_semantica_inestable.xlsx`: estresa aliases reales antes del mapping formal.
- `07_formulas_ocultos.xlsx`: prepara terreno para warnings estructurados sin romper detección.
- `00_indice_casos.xlsx`: controla comportamiento en archivo no objetivo (confianza baja esperada).

## Huecos detectados

- caso multi-hoja donde la hoja útil no es la primera visible.
- caso con dos filas candidatas de header con puntaje similar (`ambiguous_header_candidates` real).
- caso con header mergeado/celdas combinadas y nombres partidos.
- caso con faltante total de una columna clave pero con tabla válida.
- caso con ruido largo previo y cortes múltiples de bloques tabulares separados.

## Baseline confirmado pipeline-curated (fase actual)

| archivo | header detectado | mapping (mapped/ambiguous/unmapped) | warning_codes | normalization_summary | aptitud revisión humana |
|---|---|---|---|---|---|
| `03_encabezado_desplazado.xlsx` | `Resumen Clientes`, fila 7 | `3 / 0 / 0` | `["header_shifted"]` | vacío | alta, caso limpio con desplazamiento bien detectado. |
| `04_semantica_inestable.xlsx` | `Saldos`, fila 2 | `2 / 1 / 0` | `["header_shifted"]` | vacío | media-alta, expone 1 ambigüedad semántica real. |
| `07_formulas_ocultos.xlsx` | `CXC Mar-26`, fila 3 | `3 / 0 / 0` | `["header_shifted"]` | vacío | alta para header/mapping; cobertura limitada en esta fase para fórmula/ocultos. |
| `08_montos_mixtos_signos.xlsx` | `Cobranzas`, fila 1 | `3 / 0 / 0` | `["amount_accounting_sign_parentheses","amount_currency_ambiguous","amount_invalid_format","amount_negative_sign_detected","amount_separator_inferred_thousands"]` | `by_field={"monto":6}` + ejemplos reales (`-45000`, `(32.500)`, `USD 300`, `abc`, `$ 120.000`) | alta, concentra y explica bien problemas reales de monto. |
