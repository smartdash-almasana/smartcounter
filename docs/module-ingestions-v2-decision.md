# module-ingestions.v2 Decision

## 1. Decisión
`module-ingestions.v2` se define como inbox robusto de captura/persistencia del core SmartCounter. No se define como pipeline cognitivo completo.

## 2. Motivación
El estado real actual separa dos planos: ingesta/persistencia y pipeline cognitivo. La decisión evita sobrecargar `module-ingestions` con responsabilidades que hoy pertenecen a otro flujo.

## 3. Qué entra en v2
- Contrato duro (`contract_version = module-ingestions.v2`).
- Validación top-level y por módulo.
- `content_hash`.
- Idempotencia/dedupe por `{tenant_id}:{module}:{content_hash}`.
- Persistencia en GCS de artefactos y `request_meta.json`.
- Trazabilidad por `ingestion_id` y consulta de estado.

## 4. Qué queda fuera de v2
- Action engine de ejecución.
- `normalized_signals` como capa formal.
- Orquestación cognitiva multipaso.
- Integración Hermes en esta fase.

## 5. Relación con `revision-jobs`
`revision-jobs` sigue siendo el plano cognitivo más maduro del sistema. `module-ingestions.v2` no lo reemplaza ni lo absorbe.

## 6. Relación con Apps Script
Apps Script sigue como edge prioritario. Envía payloads al inbox y consume `ingestion_id`; no se convierte en mini-core.

## 7. Próximos pasos
- Cerrar implementación backend de v2 según contrato.
- Mantener compatibilidad operativa con Apps Script.
- Incorporar Hermes después, sobre el plano cognitivo, no dentro del inbox v2.
