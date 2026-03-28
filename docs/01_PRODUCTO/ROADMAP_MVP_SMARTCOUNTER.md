# ROADMAP MVP SmartCounter (Baseline vivo)

## Estado actual confirmado
- Pipeline-curated operativo con:
  - detección header/tabular,
  - mapping semántico base,
  - normalización base (fecha, monto, cuit, nulos),
  - warnings estructurados,
  - `normalization_summary`.

## Hitos inmediatos (fase corta)
1. Mantener baseline estable sobre 03, 04, 07 y 08.
2. Reducir fricción en revisión humana de ambigüedades semánticas.
3. Mejorar cobertura de casos fórmula/ocultos sin romper compatibilidad.

## Criterio de avance
- Cada ajuste debe conservar resultados de baseline o mejorar sin regresión en los 4 casos focales.
