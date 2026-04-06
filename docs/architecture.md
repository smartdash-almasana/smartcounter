# Arquitectura SmartCounter

## Pipeline completo

```text
Fuente (Sheet/CSV/XLSX)
  -> Apps Script module
  -> POST /ingest/analyze
  -> Ingestión (persistencia de artefacto)
  -> Ejecución de módulo (análisis)
  -> Salida: canonical_rows/findings/summary/suggested_actions
  -> Digest Builder
  -> Salida ejecutiva (alerts/question)
```

## Sistema basado en artefactos

SmartCounter persiste artefactos por ejecución y opera sobre ellos.

Artefactos típicos por corrida:

- `input`
- `canonical_rows`
- `findings`
- `summary`
- `suggested_actions`
- `digest` (agregado)

Ventajas operativas:

- trazabilidad por corrida
- reproducibilidad
- desacople entre ingestión, análisis y digest

## Diseño sin DB (flujo principal)

El flujo principal no requiere base de datos transaccional:

- lectura/escritura en artifact store
- contratos explícitos entre capas
- agregación posterior por digest

Esto simplifica despliegue inicial y auditoría de ejecución.

## Modelo plug & play de módulos

Cada módulo implementa un contrato estable y puede agregarse sin romper core.

Contrato de salida esperado por core:

```json
{
  "canonical_rows": [],
  "findings": [],
  "summary": {},
  "suggested_actions": []
}
```

El core orquesta, el módulo decide reglas de negocio del dominio.
