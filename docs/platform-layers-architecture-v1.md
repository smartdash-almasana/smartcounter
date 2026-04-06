> Nota de alcance
> - Este documento describe la arquitectura objetivo integral de capas de SmartCounter.
> - No representa literalmente el estado actual implementado.
> - Para la verdad operativa vigente debe consultarse `docs/core-truth-baseline-2026-04.md`.
> - Para la arquitectura objetivo del core debe consultarse `docs/core-target-architecture-v1.md`.

# 1. Propósito del documento
Este documento fija el mapa arquitectónico madre por capas de SmartCounter para evitar mezcla de responsabilidades entre captura, saneamiento técnico, semántica core, inferencia y ejecución.

# 2. Tesis general de la plataforma
SmartCounter es una plataforma por capas donde:
- los edges capturan y presentan;
- Google Apps Script es edge operativo prioritario dentro de Google Workspace;
- n8n actúa como middleware de orquestación y saneamiento técnico cuando hace falta;
- el core absorbe normalización, semántica, findings, señales, auditoría y action readiness;
- Hermes aporta inferencia controlada;
- la capa ejecutiva consume señales y acciones listas para confirmación;
- la ejecución externa ocurre fuera del core.

# 3. Principio rector por capas
La arquitectura debe seguir este encadenamiento:

**dolor -> edge -> ingestión -> normalización -> inferencia controlada -> findings -> señales -> resumen -> acción lista -> confirmación -> ejecución externa**

# 4. Vista general de capas

| Capa | Nombre | Propósito principal | Dependencia de IA | Responsable principal |
|---|---|---|---|---|
| 0 | Fuentes origen | Exponer datos operativos reales | No | Sistema/fuente externa |
| 1 | Edge operativo | Captura, UX y envío | No | Equipos de implementación |
| 2 | Ingestión core | Contrato, validación, idempotencia, trazabilidad | No | Core backend |
| 3 | Normalización/parsers | Parseo determinístico y modelo canónico | No | Core backend |
| 4 | Hermes-Bridge | Inferencia controlada con trazabilidad | Sí | Core + Hermes |
| 5 | Findings | Hallazgos estructurados y taxonomía común | Parcial | Core |
| 6 | Summary | Síntesis estructurada por módulo | Parcial | Core |
| 7 | Normalized signals | Señales transversales estables | Parcial | Core |
| 8 | Action readiness | Objetos de acción confirmables | Parcial | Core |
| 9 | Digest ejecutivo | Priorización y vista de decisión | Parcial | Capa ejecutiva |
| 10 | Action Engine futuro | Confirmación y ejecución externa | No (asistencia opcional) | Capa de ejecución |
| 11 | Auditoría/billing/storage | Evidencia, costo y gobierno de datos | No | Plataforma |

Diagrama textual de referencia:

```text
[C0 Fuentes]
   -> [C1 Edge]
   -> [C2 Ingestión Core]
   -> [C3 Normalización/Parsers]
   -> [C4 Hermes-Bridge]
   -> [C5 Findings]
   -> [C6 Summary]
   -> [C7 Normalized Signals]
   -> [C8 Action Readiness]
   -> [C9 Digest Ejecutivo]
   -> [C10 Action Engine Futuro]
   -> [C11 Auditoría/Billing/Storage]
```

# 5. Capa 0 — Fuentes y sistemas de origen
La arquitectura prevé fuentes heterogéneas: Excel, Google Sheets, Drive, Gmail, APIs, homebanking, PDFs, imágenes, TXT fiscales, marketplaces y ERPs.

Esta capa no pertenece al core. El core debe consumir representaciones controladas de estas fuentes.

# 6. Capa 1 — Edge operativo
El edge debe concentrarse en:
- captura de datos,
- UX operativa,
- empaquetado mínimo,
- envío al core.

El edge no debe asumir semántica de negocio fuerte.

# 7. Google Apps Script como edge prioritario
En la versión objetivo, Google Apps Script debe ser edge prioritario en Google Workspace por proximidad a planillas, formularios y documentos operativos.

Debe hacer:
- captura operativa,
- UX contextual,
- validación de forma básica,
- envío de payloads al core,
- feedback de estado al usuario.

No debe hacer:
- semántica fuerte,
- findings definitivos de plataforma,
- generación de normalized signals,
- ejecución de acciones sensibles.

Apps Script debe enchufarse por contratos estables de ingestión y mantenerse liviano para no derivar a mini-core.

# 8. n8n como capa de orquestación y saneamiento técnico
La arquitectura prevé n8n como middleware técnico cuando la ingesta requiere conectividad y transformación previa.

n8n debe hacer:
- intake multiformato,
- mapping técnico,
- limpieza superficial,
- routing,
- control de conectores.

n8n no debe hacer:
- findings definitivos,
- normalized signals definitivos,
- semántica de acción del core.

n8n no reemplaza Apps Script y no reemplaza el core.

# 9. Capa 2 — Ingestión del core
La ingestión del core debe operar como inbox robusto con:
- contrato estable,
- validación,
- idempotencia,
- persistencia,
- trazabilidad.

Su función es absorber y registrar con control, no ejecutar razonamiento de negocio completo.

# 10. Capa 3 — Normalización y parsers
La arquitectura prevé una capa determinística que debe producir:
- parseo reproducible,
- canonical rows,
- provenance por campo,
- `parse_state` explícito,
- errores parciales tipados,
- parsers por tipo de fuente.

# 11. Capa 4 — Hermes-Bridge / inferencia controlada
Hermes debe aportar inferencia controlada para casos ambiguos o de enriquecimiento no determinístico.

Debe producir:
- candidatos de salida,
- trazas de inferencia,
- justificación utilizable por el core.

No debe reemplazar contrato, validación ni decisiones finales de estado.

# 12. Capa 5 — Findings
Los findings deben ser uniformes entre módulos:
- taxonomía común,
- severidad homogénea,
- fuente de hallazgo (`RULE`/`HERMES`),
- codificación jerárquica.

# 13. Capa 6 — Summary y síntesis estructurada
Cada flujo debe emitir summary estructurado por módulo.

Debe separarse:
- facts verificables,
- narrativa derivada.

La narrativa no debe sustituir facts.

# 14. Capa 7 — Normalized signals
La arquitectura prevé normalized signals para estabilizar semántica cross-module.

Deben servir para:
- priorización consistente,
- consumo ejecutivo,
- desacople entre findings y acción.

# 15. Capa 8 — Action readiness
Esta capa debe transformar intención en objetos confirmables de acción.

Debe distinguir:
- `suggested_actions` (propuesta),
- `action_ready_objects` (preparado para confirmación).

# 16. Capa 9 — Digest / capa ejecutiva
El digest debe consumir summaries y signals, no datos crudos.

Debe proveer:
- priorización,
- síntesis para decisión,
- contexto para confirmación.

# 17. Capa 10 — Action Engine futuro
El Action Engine, en la versión objetivo, debe:
- presentar acciones,
- recibir confirmación,
- ejecutar contra sistemas externos,
- notificar resultado.

No debe redefinir semántica del core.

# 18. Capa 11 — Auditoría, billing y storage
La plataforma debe sostener:
- artefactos por etapa,
- auditoría de decisiones,
- eventos de billing,
- metadatos indexables.

Se prevé separación entre almacenamiento de artefactos, índices de consulta y eventos de costo.

# 19. Qué vive en cada capa
- C0: datos y documentos de origen.
- C1: captura, UX, empaquetado mínimo.
- C2: contrato, validación, idempotencia, persistencia inicial.
- C3: normalización y parseo canónico.
- C4: inferencia controlada con trace.
- C5: findings normalizados.
- C6: summary estructurado.
- C7: normalized signals.
- C8: readiness de acción.
- C9: digest ejecutivo.
- C10: ejecución externa confirmada.
- C11: auditoría, billing y storage transversal.

# 20. Qué está prohibido en cada capa
- C1: semántica de negocio fuerte en edge.
- C1: findings definitivos en Apps Script.
- C2: ejecución de acciones en ingestión.
- C3: decisiones ejecutivas finales en parsers.
- C4: inferencia sin trace auditable.
- C5: taxonomías no homogéneas por módulo.
- C6: narrativa sin respaldo factual.
- C7: normalized signals definitivos en n8n.
- C8: ejecución directa de acciones.
- C9: decisión basada en raw sin signals/summaries.
- C10: reescritura semántica del core.
- C11: eventos sin correlación técnica.

# 21. Flujos canónicos permitidos
- Apps Script -> Core.
- Apps Script -> n8n -> Core.
- Drive/Gmail -> n8n -> Core.
- Upload web -> Core.
- Core -> Hermes -> Core.
- Core -> Digest.
- Core -> Action Ready -> Action Engine futuro.

# 22. Flujos explícitamente no permitidos
- Apps Script -> Hermes directo.
- Apps Script -> Action Engine directo.
- n8n -> findings definitivos sin core.
- n8n -> normalized signals definitivos.
- Hermes -> ejecución externa directa.
- edge -> acción sensible sin confirmación.

# 23. Rol de Apps Script en la factoría
Apps Script debe ser el edge operativo prioritario en entornos Google: proximidad al usuario, captura rápida y envío contractual al core. Su valor es operativo; su límite es semántico.

# 24. Rol de n8n en la factoría
n8n debe cumplir rol de integración y saneamiento técnico: conectores, transformaciones básicas y routing. Debe mantenerse como middleware, no como núcleo de interpretación.

# 25. Relación entre Apps Script, n8n y Core
- Apps Script presenta y capta.
- n8n limpia y enruta cuando corresponde.
- Core interpreta y gobierna semántica, trazabilidad y readiness.

# 26. Relación entre Core y Hermes
Hermes propone inferencias. El core decide aceptación, estado y persistencia canónica.

# 27. Relación entre señales, digest y acción
- finding != signal.
- signal != action.
- digest consume signals y summaries.
- action readiness convierte intención en objeto confirmable para ejecución.

# 28. Riesgos de contaminación entre capas
- edge demasiado inteligente,
- n8n convertido en mini-core,
- Hermes caja negra sin trazas,
- findings heterogéneos,
- signals inestables,
- action engine contaminando semántica,
- falta de idempotencia en ingestión.

# 29. Secuencia recomendada de endurecimiento
1. contratos
2. ingestión robusta
3. normalización
4. findings comunes
5. normalized_signals
6. Hermes
7. action readiness
8. digest
9. action engine

# 30. Definición final
En la versión objetivo, SmartCounter debe operar como plataforma por capas con fronteras estrictas: edge captura, n8n sanea técnicamente, core gobierna semántica y preparación de acción, Hermes asiste con inferencia controlada y la ejecución externa se mantiene fuera del núcleo semántico.
