# PIPELINE_CURATED

## Flujo actual
1. Detecta región tabular y header.
2. Ejecuta mapping semántico base.
3. Normaliza tipos base (fecha, monto, cuit, nulos) en preview.
4. Emite warnings estructurados.
5. Devuelve salida curada para revisión humana con `normalization_summary`.

## Baseline confirmado (pack focal)
- `03_encabezado_desplazado.xlsx`
  - header: `Resumen Clientes`, fila 7
  - mapping: `mapped 3 / ambiguous 0 / unmapped 0`
  - warning_codes: `header_shifted`
- `04_semantica_inestable.xlsx`
  - header: `Saldos`, fila 2
  - mapping: `mapped 2 / ambiguous 1 / unmapped 0`
  - warning_codes: `header_shifted`
- `07_formulas_ocultos.xlsx`
  - header: `CXC Mar-26`, fila 3
  - mapping: `mapped 3 / ambiguous 0 / unmapped 0`
  - warning_codes: `header_shifted`
- `08_montos_mixtos_signos.xlsx`
  - header: `Cobranzas`, fila 1
  - mapping: `mapped 3 / ambiguous 0 / unmapped 0`
  - warning_codes: `amount_accounting_sign_parentheses`, `amount_currency_ambiguous`, `amount_invalid_format`, `amount_negative_sign_detected`, `amount_separator_inferred_thousands`
  - normalization_summary: `by_field = {"monto": 6}` con ejemplos reales (`-45000`, `(32.500)`, `USD 300`, `abc`, `$ 120.000`).

## Límites vigentes
- No resuelve automáticamente ambigüedades semánticas.
- Cobertura todavía limitada para fórmula/ocultos como clase específica.
- Sin normalización profunda completa de todas las columnas.
