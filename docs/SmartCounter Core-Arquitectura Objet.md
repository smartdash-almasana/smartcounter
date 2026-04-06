````md
# SmartCounter Core — Arquitectura Objetivo v1

> **Nota de posicionamiento**
>
> Este documento describe la **arquitectura objetivo** del core SmartCounter.
> No representa de forma literal el estado implementado actual del backend.
> Para la verdad operativa vigente debe consultarse `docs/core-truth-baseline-2026-04.md`.

---

## A. Tesis del core

### En qué consiste realmente el core SmartCounter

El core SmartCounter apunta a ser una **fábrica de artefactos canónicos** para operación PyME.  
Su función es recibir evidencia operativa heterogénea —archivos, imágenes, payloads API, correos, exportes, capturas y lotes documentales— y convertirla en:

- estructuras normalizadas;
- hallazgos semánticos;
- señales priorizadas;
- objetos de acción preparados para confirmación.

No debe entenderse como un backend de aplicación tradicional, ni como una suma de scripts, ni como un OCR aislado. La arquitectura objetivo lo concibe como la **infraestructura semántica, cognitiva y transaccional** que le da forma industrial a la evidencia del negocio.

### Su frontera

La frontera del core debe empezar cuando llega evidencia y terminar cuando produce:

- artefactos normalizados;
- findings catalogados;
- normalized signals;
- action ready objects listos para confirmación.

Todo lo que ocurre antes —captura, formularios, sidebars, carga manual, menús, bots, Apps Script, correo de entrada— es **edge**.  
Todo lo que ocurre después de la confirmación —escritura contable, envío de emails, actualización de sistemas externos, calendarios, ERP, storage local— es **ejecución externa** habilitada por el core, pero no realizada por él.

### Qué problemas resuelve

La arquitectura objetivo debe resolver estos problemas estructurales:

1. **Caos documental heterogéneo**  
   Convertir formatos y fuentes dispares en estructuras comparables y trazables.

2. **Reinvención por módulo**  
   Evitar que cada microservicio defina su propio parser, su propio modelo de findings, su propia semántica de severidad y su propia capa de auditoría.

3. **Falta de trazabilidad**  
   Garantizar provenance por campo, raw snapshot preservado e inference trace cuando interviene IA.

4. **Dificultad para priorizar cross-module**  
   Permitir que conciliación, stock, IVA, sueldos, gastos, márgenes y otros módulos hablen un idioma común de señales y acción.

5. **Ausencia de action readiness controlada**  
   Preparar acciones con contexto suficiente para mostrar, confirmar y ejecutar sin opacidad ni automatismo ciego.

### Qué NO debe intentar resolver

El core no debe:

- ejecutar acciones sensibles sin confirmación;
- reemplazar sistemas definitivos contables, fiscales o operativos;
- convertirse en CRM, ERP o UI principal;
- absorber la UX de los módulos;
- tomar decisiones autónomas de negocio;
- ser el canal final de conversación con el usuario;
- procesar formatos desconocidos sin degradación explícita y trazable.

### Google Apps Script como borde operativo prioritario

La arquitectura objetivo debe reconocer explícitamente a **Google Apps Script** como un **edge operativo prioritario y fundacional** dentro de la factoría SmartCounter.

Apps Script:

- **no es el core**;
- **sí es** un canal estratégico de captura, UX operativa, integración con Google Workspace y presentación contextual;
- debe servir para Sheets, Forms, Drive, Gmail, sidebars, menús y micro-módulos verticales;
- debe convivir con otros enchufes futuros sin absorber la semántica ni la complejidad del core.

En la visión objetivo, módulos como `ConciliSimple`, `StockSimple`, `AprobaSimple`, `ExpenseEvidence`, `LibroSueldosSimple`, `IVASimple`, `MonoSimple`, `BridgeSimple`, `CommerceSyncSimple` y `RentableSimple` pueden tener edges en Apps Script, pero su interpretación estructural, findings, señales, auditoría y action readiness deben vivir en el core.

---

## B. Capas internas del core

### Capa 1 — Intake gateway

**Propósito**  
Ser el primer punto de contacto del core con el mundo exterior y asignar identidad transaccional a cada ingesta.

**Inputs**
- payload crudo vía HTTP multipart;
- JSON;
- binario adjunto;
- stream;
- lote comprimido;
- referencia a evidencia externa.

**Outputs**
- `execution_id` (preferentemente UUID v7);
- `content_hash` (SHA-256 del payload crudo);
- `tenant_id` validado;
- `received_at` UTC;
- `source_type` preliminar;
- `raw_blob` persistido.

**Reglas**
- toda ingesta debe recibir `execution_id` único;
- el gateway no debe interpretar contenido;
- el raw debe persistirse antes de avanzar;
- el content hash debe servir como llave de idempotencia futura;
- no debe rechazar por formato: eso se delega.

**Riesgos**
- pérdida de raw antes de persistir;
- hash mal calculado;
- intake demasiado “inteligente”.

**Dependencia de IA**  
Ninguna.

---

### Capa 2 — Ingestion contract validation

**Propósito**  
Validar que la ingesta cumple el contrato madre mínimo y puede ser ruteada al módulo correcto.

**Inputs**
- objeto de ingesta emitido por el gateway.

**Outputs**
- contrato validado;
- `module` resuelto;
- `source_type` confirmado;
- errores de validación;
- estado `VALID`, `PARTIAL` o `REJECTED`.

**Reglas**
- si `module` no está presente, solo puede inferirse por metadata o heurística de origen, nunca por contenido profundo;
- si el `tenant_id` no tiene habilitado el módulo, debe rechazarse;
- los opcionales ausentes deben quedar ausentes, no inventarse;
- una ingesta `PARTIAL` puede avanzar si el núcleo del contrato está completo.

**Riesgos**
- validación demasiado laxa;
- validación demasiado estricta;
- inferencia impropia de módulo.

**Dependencia de IA**  
Ninguna. Debe ser una capa determinística.

---

### Capa 3 — Normalizer engine

**Propósito**  
Convertir evidencia cruda en `canonical_rows`, sin depender del formato original.

**Inputs**
- evidencia validada;
- metadatos de contrato;
- información de parser disponible.

**Outputs**
- `canonical_rows[]`;
- `parse_state`;
- `confidence` por fila/campo;
- `provenance` por campo;
- `raw_snapshot`;
- `normalization_notes[]`;
- `parse_errors[]`.

**Reglas**
- el parseo determinístico ocurre aquí;
- todo formato conocido debe pasar primero por parser sin IA;
- todo campo debe conservar provenance;
- las partes ambiguas deben marcarse para inferencia, no resolverse opacamente.

**Riesgos**
- parsers frágiles;
- supuestos de layout rígidos;
- mezcla incorrecta entre determinismo e inferencia.

**Dependencia de IA**  
Indirecta. La capa puede derivar fragmentos a Hermes, pero no debe delegar todo por defecto.

---

### Capa 4 — Evidence parser library

**Propósito**  
Ser la biblioteca de parsers específicos invocados por el normalizer engine.

**Naturaleza**  
No es una capa autónoma del flujo, sino una colección de adaptadores homogéneos.

**Parsers objetivo v1**
- CSV / TSV;
- XLS / XLSX;
- OFX;
- MT940 / MT950;
- TXT delimitado o posicional;
- XML fiscal;
- JSON tabular;
- PDF textual estructurado.

**Segunda fase**
- PDF visual;
- imagen/captura;
- email con adjuntos;
- ZIP con lotes.

**Interfaz esperada de parser**
- recibe evidencia cruda;
- devuelve `canonical_rows` parciales o completos;
- devuelve metadatos de parseo;
- declara tolerancias conocidas.

---

### Capa 5 — Inference layer / Hermes Agent bridge

**Propósito**  
Resolver lo que el parseo determinístico no puede.

**Inputs**
- fragmentos con `parse_state = NEEDS_INFERENCE` o `VISUAL_INPUT`;
- contexto del módulo;
- tarea de inferencia precisa;
- schema esperado.

**Outputs**
- `canonical_rows_candidates[]`;
- `inference_trace[]`;
- `confidence` por campo;
- `reasoning_notes`;
- `unresolved_fragments`.

**Reglas**
- Hermes nunca debe reemplazar el raw;
- Hermes nunca debe decidir acción de negocio;
- Hermes produce candidatos, no verdad final automática;
- toda inferencia debe quedar auditada y versionada.

**Riesgos**
- caja negra;
- inferencia aceptada sin provenance;
- dependencia excesiva del agente.

**Dependencia de IA**  
Sí, estrictamente delimitada.

---

### Capa 6 — Finding engine

**Propósito**  
Detectar hallazgos semánticamente relevantes sobre `canonical_rows` normalizados.

**Inputs**
- `canonical_rows`;
- contexto del módulo;
- reglas de dominio;
- candidate findings sugeridos por Hermes si aplicara.

**Outputs**
- `findings[]` con taxonomía común;
- `finding_code`;
- severidad;
- `entity_ref`;
- `suggested_action_type`;
- extensiones por dominio.

**Reglas**
- findings por regla dura deben marcarse como `source = RULE`;
- findings sugeridos por Hermes deben marcarse como `source = HERMES`;
- ningún módulo debe romper el catálogo semántico central.

**Dependencia de IA**  
Parcial.

---

### Capa 7 — Summary builder

**Propósito**  
Construir la síntesis estructurada de la ingesta.

**Inputs**
- `canonical_rows`;
- `findings`;
- metadatos de parseo;
- contexto del módulo.

**Outputs**
- `summary` estructurado;
- métricas clave;
- estado de la ingesta;
- cuentas de filas procesadas, fallidas, inferidas y relevantes.

**Reglas**
- el summary debe ser derivado, no fuente de verdad;
- siempre debe apuntar a artefactos de origen;
- la narrativa generada por Hermes debe quedar marcada.

**Dependencia de IA**  
Opcional para redacción, no para facts base.

---

### Capa 8 — Normalized signals layer

**Propósito**  
Traducir findings y summary a señales normalizadas comparables entre módulos.

**Inputs**
- `findings`;
- `summary`;
- `canonical_rows` seleccionados.

**Outputs**
- `normalized_signals[]`.

**Reglas**
- la semántica debe ser estable aunque los módulos evolucionen;
- el ranking debe ser reproducible;
- la señal no debe depender del wording narrativo.

**Dependencia de IA**  
Ninguna para generación; opcional para ranking contextual futuro.

---

### Capa 9 — Action readiness layer

**Propósito**  
Transformar `suggested_actions` en `action_ready_objects` con contexto suficiente para confirmar y ejecutar fuera del core.

**Inputs**
- `findings`;
- `normalized_signals`;
- `summary`;
- entidades relevantes.

**Outputs**
- `action_ready_objects[]` con estado `PENDING_CONFIRMATION`.

**Reglas**
- no ejecuta;
- no presenta por sí misma;
- preserva contexto suficiente para eventual Action Engine.

**Dependencia de IA**  
Ninguna.

---

### Capa 10 — Audit & billing layer

**Propósito**  
Registrar inmutablemente qué ocurrió y producir eventos facturables sin duplicación.

**Inputs**
- outputs de todas las capas previas.

**Outputs**
- `audit_log`;
- `billing_events`.

**Reglas**
- audit log append-only;
- billing idempotente por contenido y tipo de evento;
- retry safe.

**Dependencia de IA**  
Ninguna.

---

### Capa 11 — Storage & retrieval layer

**Propósito**  
Persistir y recuperar todos los artefactos del core.

**Responsabilidades**
- bucket/object storage para blobs y JSON grandes;
- índices en DB para navegación y consultas;
- metadata index para lookup rápido;
- políticas de retención y acceso por tenant.

---

## C. Contrato madre del core

El contrato madre debe ser el schema raíz emitido por toda ingesta al salir del core.  
Todos los módulos deben producirlo y todo consumidor downstream debe poder leerlo sin lógica especial por módulo.

### Schema raíz conceptual

```text
CoreIngestionResult {
  // Identidad
  schema_version:       string          OBLIGATORIO
  execution_id:         uuid-v7         OBLIGATORIO
  tenant_id:            string          OBLIGATORIO
  module:               ModuleEnum      OBLIGATORIO
  generated_at:         datetime-utc    OBLIGATORIO

  // Evidencia
  source_type:          SourceTypeEnum  OBLIGATORIO
  content_hash:         string          OBLIGATORIO
  evidence_refs:        EvidenceRef[]   OBLIGATORIO

  // Resultado principal
  canonical_rows:       CanonicalRow[]  OBLIGATORIO
  parse_state:          ParseStateEnum  OBLIGATORIO
  findings:             Finding[]       OBLIGATORIO
  summary:              Summary         OBLIGATORIO

  // Acción
  suggested_actions:    SuggestedAction[]   OPCIONAL
  action_ready_objects: ActionReadyObject[] OPCIONAL

  // Señales
  normalized_signals:   NormalizedSignal[]  OPCIONAL

  // Artefactos adicionales
  additional_artifacts: ArtifactRef[]       OPCIONAL

  // Metadatos de parseo
  parse_metadata: {
    parser_used:         string
    parser_version:      string
    rows_total:          integer
    rows_parsed:         integer
    rows_failed:         integer
    rows_inferred:       integer
    hermes_invoked:      boolean
    parse_errors:        ParseError[]
    normalization_notes: string[]
  }

  // Metadatos de auditoría
  audit_metadata: {
    intake_received_at: datetime-utc
    processing_ms:      integer
    billing_event_id:   uuid
    operator_id:        string
    client_ref:         string
  }
}
````

### Convenciones de nombres

* `snake_case` para todos los campos;
* enums en formato estable y controlado;
* timestamps siempre en UTC ISO 8601;
* arrays nunca nulos;
* IDs siempre explícitos y trazables.

### Versionado

* `schema_version` debe seguir semver;
* cambio destructivo = major;
* nuevo opcional = minor;
* consumidores deben ignorar campos desconocidos.

---

## D. Artefactos internos del core

Todos los artefactos deben identificarse por:

```text
{tenant_id}/{module}/{execution_id}/
```

### `input_raw`

**Propósito**
Preservar la evidencia exactamente como llegó.

**Formato**
Blob binario o texto crudo.

**Persistencia**
Permanente o según política del tenant.

**Visibilidad**
Interno.

---

### `input_normalized`

**Propósito**
Snapshot posterior al parseo, previo a interpretación de dominio.

**Formato**
JSON estructurado con provenance.

**Visibilidad**
Interno, exportable para depuración.

---

### `canonical_rows`

**Propósito**
Representación canónica de filas, registros o entidades extraídas.

**Formato**
JSON array de `CanonicalRow`.

---

### `findings`

**Propósito**
Hallazgos detectados en la ingesta.

**Formato**
JSON array de `Finding`.

**Visibilidad**
Visible a módulo, digest y consumers internos.

---

### `summary`

**Propósito**
Síntesis ejecutiva de la ingesta.

**Formato**
JSON estructurado por módulo.

**Visibilidad**
Visible; artefacto principal consumido por edges.

---

### `suggested_actions`

**Propósito**
Acciones sugeridas pero no ejecutadas.

**Formato**
JSON array.

---

### `normalized_signals`

**Propósito**
Señales estandarizadas para digest, dashboard y action flow.

**Formato**
JSON array.

---

### `inference_trace`

**Propósito**
Registrar qué hizo Hermes, con qué inputs y qué outputs propuso.

**Formato**
JSON array o JSON object versionado.

**Visibilidad**
Interno.

---

### `action_ready_objects`

**Propósito**
Acciones listas para mostrar y confirmar.

**Formato**
JSON array.

**Visibilidad**
Visible al operador a través del edge.

---

### `billing_events`

**Propósito**
Registrar eventos facturables idempotentes.

**Formato**
JSON o tabla indexada.

---

### `audit_log`

**Propósito**
Registro completo, inmutable y append-only de la ingesta.

**Formato**
JSONL o event log equivalente.

---

## E. Núcleo normalizador

El normalizer engine objetivo debe convertir fuentes heterogéneas en `canonical_rows` mediante tres fases:

1. **detección de formato**;
2. **parseo determinístico**;
3. **delegación controlada de ambigüedades**.

### Cómo convierte fuentes heterogéneas

Cada ingesta debe pasar por un detector de formato basado en:

* firma de contenido;
* metadatos de contrato;
* contexto de origen;
* heurísticas controladas.

No debe depender solo de extensión de archivo.

Una vez seleccionado el parser, debe ejecutarse primero en modo determinístico y extraer todo lo resoluble con certeza.

### Cómo separa parseo determinístico de inferencia

#### Modo `DETERMINISTIC`

Opera sin IA:

* parsers de formato conocido;
* mapeo de columnas;
* validaciones de tipos;
* coerciones explícitas.

#### Modo `INFERENCE_REQUIRED`

Se aplica cuando:

* el formato es visual;
* el layout no coincide con plantillas conocidas;
* hay ambigüedad semántica no resoluble por regla.

En ese caso se arma un paquete de contexto para Hermes con:

* fragmento problemático;
* tarea específica;
* schema esperado;
* metadata del módulo.

Hermes devuelve candidatos que el core debe aceptar, degradar o rechazar.

### Campos clave del modelo de parseo

* `parse_state` por fila: `DETERMINISTIC | INFERRED | PARTIAL | FAILED | MANUAL_REQUIRED`
* `confidence` por campo: `0.0–1.0`
* `provenance` por campo
* `raw_snapshot`
* `normalized_snapshot`
* `normalization_notes`

### Cómo maneja errores parciales

Los errores no deben ser binarios sino tipados:

* `FORMAT_UNRECOGNIZED`
* `COLUMN_UNMAPPED`
* `VALUE_INVALID`
* `ROW_INCOMPLETE`
* `INFERENCE_FAILED`

Una ingesta no debe colapsar completa si una parte útil puede avanzar.

---

## F. Modelo de findings

### Taxonomía común

Todo finding debe seguir un `finding_code` jerárquico:

```text
{DOMAIN}.{CATEGORY}.{SPECIFIC}
```

Ejemplos:

* `CONCILI.MATCH.UNMATCHED_DEBIT`
* `STOCK.LEVEL.BELOW_MINIMUM`
* `IVA.CLASSIFICATION.MISSING_CONDITION`

### Severidades

* `CRITICAL`
* `HIGH`
* `MEDIUM`
* `LOW`
* `INFO`

### Schema conceptual

```text
Finding {
  finding_id:            uuid-v7
  finding_code:          string
  domain:                string
  category:              FindingCategory
  severity:              SeverityEnum
  message:               string
  entity_ref:            EntityRef
  evidence_fragment:     string
  suggested_action_type: ActionTypeEnum
  source:                RULE | HERMES
  confidence:            float
  module_extensions:     object
}
```

### Findings transversales

* `PARSE.QUALITY.LOW_CONFIDENCE`
* `PARSE.COMPLETENESS.MISSING_FIELDS`
* `DATA.INTEGRITY.DUPLICATE_ROWS`
* `DATA.INTEGRITY.INVALID_DATES`
* `DATA.INTEGRITY.NEGATIVE_UNEXPECTED`
* `INFERENCE.QUALITY.MANUAL_REQUIRED`

### Findings por dominio — ejemplos

**ConciliSimple**

* `CONCILI.MATCH.UNMATCHED_DEBIT`
* `CONCILI.MATCH.UNMATCHED_CREDIT`
* `CONCILI.BALANCE.DIFFERENCE_UNEXPLAINED`
* `CONCILI.TIMING.OUTSTANDING_ITEM_OLD`

**StockSimple**

* `STOCK.LEVEL.BELOW_MINIMUM`
* `STOCK.LEVEL.ZERO_STOCK`
* `STOCK.COVERAGE.DAYS_CRITICAL`

**IVASimple**

* `IVA.CLASSIFICATION.MISSING_CONDITION`
* `IVA.PERIOD.MISMATCH`
* `IVA.COMPROBANTE.DUPLICATED`

**LibroSueldosSimple**

* `LSD.STRUCTURE.TXT_FORMAT_ERROR`
* `LSD.CONCEPT.UNKNOWN_CODE`
* `LSD.TOTALS.MISMATCH`

### Cómo evitar caos semántico cross-module

* catálogo central de categorías;
* dominio y categoría controlados por el core;
* los módulos solo extienden el nivel específico;
* versionado del catálogo junto al schema madre.

---

## G. Normalized signals

Las `normalized_signals` deben ser la interfaz estable entre el mundo interno del core y el mundo ejecutivo.

### Schema conceptual

```text
NormalizedSignal {
  signal_id:         uuid-v7
  signal_type:       SignalTypeEnum
  module:            ModuleEnum
  tenant_id:         string
  generated_at:      datetime-utc
  execution_id:      uuid
  finding_ref:       uuid
  title:             string
  description:       string
  severity:          SeverityEnum
  score:             float
  priority:          integer
  entity_ref:        EntityRef
  suggested_actions: uuid[]
  tags:              string[]
  expires_at:        datetime-utc
  is_resolved:       boolean
  resolved_at:       datetime-utc
}
```

### Reglas de generación

* findings `HIGH` y `CRITICAL` deben generar señal automática;
* findings `MEDIUM` pueden generar señal si el módulo lo indica;
* `LOW` e `INFO` deben tender a permanecer en summary;
* debe existir agregación para reducir ruido.

### Score y ranking

El score objetivo puede combinar:

* severidad base;
* freshness;
* prioridad del módulo según tenant;
* confianza;
* estado de resolución.

### Uso en digest

El digest objetivo debe poder construirse como:

* señales activas;
* ordenadas por prioridad;
* agrupadas por módulo;
* filtradas por resolución.

---

## H. Hermes Agent bridge

### Qué entradas recibe Hermes

Hermes debe recibir **paquetes estructurados**, no archivos crudos directos.
Cada paquete debe incluir:

* fragmento de evidencia;
* schema esperado;
* tarea específica;
* contexto del módulo;
* `tenant_id`;
* `inference_request_id`.

### Qué salidas devuelve

Hermes debe devolver:

* `canonical_rows_candidates[]`;
* `confidence_per_field[]`;
* `reasoning_notes[]`;
* `unresolved_fragments[]`;
* `inference_request_id`.

Hermes no debe devolver una decisión final de negocio ni una acción ejecutable.

### Qué tareas sí resuelve Hermes

* OCR visual multimodal;
* clasificación semántica;
* mapeo de columnas heterogéneas;
* resolución de fechas ambiguas;
* parsing de layouts documentales variables;
* generación de texto narrativo acotado;
* sugerencia de finding candidates.

### Qué tareas NO debe resolver Hermes

* decidir aceptabilidad de riesgo de negocio;
* ejecutar acciones;
* escribir directamente en storage;
* modificar artefactos finales;
* reemplazar validaciones determinísticas;
* saltarse el raw persistido.

### Cómo se audita

Cada invocación debe producir un `InferenceTrace`:

```text
InferenceTrace {
  inference_request_id: uuid
  execution_id:         uuid
  invoked_at:           datetime-utc
  model_id:             string
  prompt_version:       string
  task_type:            string
  input_fragment_hash:  string
  output_hash:          string
  tokens_used:          integer
  confidence_reported:  float
  accepted_by_core:     boolean
  rejection_reason:     string
}
```

### Versionado de prompts y modelos

Todo template debe tener versión explícita.
Todo output debe poder reconstruirse con:

* prompt version;
* model version;
* input hash;
* output hash.

### Cómo evitar dependencia ciega

* output con `confidence < 0.7` no debe aceptarse automáticamente;
* entre `0.7` y `0.9`, debe marcarse `requires_review`;
* incluso con alta confianza, el parse state debe conservar marca de inferido;
* el raw snapshot debe preservarse siempre.

### Regla dura vs inferencia Hermes

Todo campo en `canonical_rows` debe exponer `provenance.extraction_method`, por ejemplo:

* `rule`
* `header_mapping`
* `positional`
* `hermes_inference`
* `manual`

---

## I. Soporte multiformato

| Tipo de input             | Parser principal                       | Fallback                            | Hermes                           | Artefacto esperado                                 | Riesgo principal                     |
| ------------------------- | -------------------------------------- | ----------------------------------- | -------------------------------- | -------------------------------------------------- | ------------------------------------ |
| CSV / TSV                 | Parser tabular nativo                  | Detección automática de delimitador | No                               | `canonical_rows` completas                         | Encoding, separador decimal regional |
| XLSX / XLS                | Parser tabular con detección de hoja   | Exportación previa a CSV            | Solo si hay columnas ambiguas    | `canonical_rows` completas                         | Hojas múltiples, celdas mergeadas    |
| Google Sheets             | API + parser tabular                   | Export CSV                          | No                               | `canonical_rows` completas                         | Permisos, fórmulas sin valor         |
| OFX                       | Parser OFX estándar                    | Parser XML genérico                 | No                               | `canonical_rows` bancarias                         | Versiones incompatibles              |
| MT940 / MT950             | Parser SWIFT específico                | Parser posicional custom            | No                               | `canonical_rows` con movimientos                   | Variantes bancarias                  |
| TXT delimitado            | Detección heurística de delimitador    | Parser posicional manual            | Solo si estructura muy irregular | `canonical_rows` parciales                         | Sin encabezado, filas mixtas         |
| XML fiscal                | Parser validado por schema / XSD       | XPath genérico                      | No                               | `canonical_rows` completas                         | Namespaces, variantes AFIP/ARCA      |
| JSON tabular / API        | Parser JSON con schema mapping         | Schema inference controlada         | Solo para mapping ambiguo        | `canonical_rows` completas                         | Nesting profundo                     |
| PDF textual               | Extracción de texto + parser de layout | Parser posicional de texto plano    | Sí si el layout es irregular     | `canonical_rows` parciales + `normalization_notes` | Columnas no alineadas                |
| PDF visual / escaneado    | Hermes OCR multimodal                  | Ninguno determinístico              | Sí obligatorio                   | `canonical_rows` inferidas                         | Calidad de imagen                    |
| Imagen (JPG/PNG/WEBP)     | Hermes visión                          | Ninguno                             | Sí obligatorio                   | `canonical_rows` inferidas                         | Resolución, glare, texto parcial     |
| Screenshot de homebanking | Hermes visión + contexto bancario      | Ninguno                             | Sí                               | `canonical_rows` inferidas                         | Layout variable por banco            |
| Email con adjuntos        | Parser de email + pipeline por adjunto | Contexto del cuerpo                 | Sí si adjunto visual             | Artefactos por adjunto                             | MIME complejo, adjuntos anidados     |
| ZIP con lotes             | Descompresión + pipeline por archivo   | Ninguno                             | Según tipo contenido             | Batch + ejecuciones hijas                          | Archivos corruptos o mixtos          |

---

## J. Enchufes hacia micro-módulos edge

### Principio general

La arquitectura objetivo debe tener un único punto de entrada de ingesta, por ejemplo:

```text
POST /v1/ingestions
```

Todo edge debe acoplarse al contrato, no a endpoints por módulo.

### Contrato de acople del edge

El edge debe enviar el contrato mínimo:

* `tenant_id`
* `module`
* `source_type`
* `evidence_refs` o `evidence_payload`

Todo lo demás debe ser responsabilidad del core.

### Responsabilidades del edge

El edge debe:

* capturar la evidencia del origen;
* empaquetarla en el contrato mínimo;
* autenticarse por tenant;
* enviar al core;
* mostrar resumen o acciones si corresponde.

### Responsabilidades del core

El core debe:

* validar;
* parsear;
* normalizar;
* detectar findings;
* construir summary;
* generar señales;
* preparar acciones;
* auditar;
* persistir.

### Qué lógica queda prohibida en el edge

El edge no debe:

* normalizar de verdad;
* detectar findings;
* construir signals;
* invocar Hermes directamente;
* tomar decisiones semánticas;
* ejecutar acciones sensibles fuera del core.

### Qué validación mínima sí puede hacer el edge

* archivo no vacío;
* presencia de `tenant_id`;
* formato mínimo razonable;
* validaciones de UX de superficie.

### Google Apps Script como edge operativo

Google Apps Script debe quedar explicitado como uno de los **enchufes principales** de la arquitectura objetivo, no como ejemplo secundario.

#### Rol esperado de Apps Script

* captura y lectura desde Sheets, Forms, Drive y Gmail;
* UX operativa de baja fricción dentro de Google Workspace;
* sidebars y menús por vertical;
* staging liviano y envío al core;
* visualización de summary y action previews.

#### Qué no debe hacer Apps Script

* convertirse en mini-core;
* definir findings propios incompatibles;
* decidir semántica del negocio;
* resolver parsing complejo localmente;
* invocar Hermes por fuera del core.

#### Ejemplo de comportamiento correcto

Un módulo Apps Script de `ConciliSimple` debería:

1. leer extracto o archivo;
2. construir payload mínimo;
3. hacer `POST /v1/ingestions`;
4. mostrar summary en sidebar.

La lógica de conciliación real debe vivir en el core.

### Convivencia con otros enchufes

Apps Script debe convivir con:

* bots;
* email intake;
* uploads web;
* APIs;
* pipelines batch.

Pero su presencia debe seguir siendo estructural en la factoría SmartCounter, especialmente en escenarios Google Workspace.

---

## K. Capa de acción

La arquitectura objetivo debe seguir el patrón:

**Generar → Mostrar → Confirmar → Ejecutar**

El core solo debe abarcar las primeras dos fases; las otras deben ser habilitadas, no absorbidas.

### Cómo `suggested_actions` se transforman en `action_ready_objects`

Un `SuggestedAction` representa una intención.
Un `ActionReadyObject` representa esa intención ya contextualizada y lista para confirmarse.

### Schema conceptual

```text
ActionReadyObject {
  action_id:               uuid-v7
  action_type:             ActionTypeEnum
  status:                  PENDING_CONFIRMATION | CONFIRMED | REJECTED | EXECUTED | EXPIRED
  title:                   string
  description:             string
  impact_summary:          string
  execution_payload:       object
  source_finding_id:       uuid
  source_signal_id:        uuid
  execution_id:            uuid
  created_at:              datetime-utc
  expires_at:              datetime-utc
  confirmation_required_by: string
}
```

### Cómo se preserva el contexto

El `execution_payload` debe contener todo lo necesario para ejecutar sin tener que reinterpretar la ingesta original.

### Cómo se vincula con signals

Las acciones importantes pueden generar señales de recomendación, permitiendo que el digest muestre:

* qué pasó;
* qué conviene hacer.

### Qué deja listo para el Action Engine futuro

El core entrega el objeto en `PENDING_CONFIRMATION`.
El futuro Action Engine solo necesita:

* mostrarlo;
* recibir confirmación;
* ejecutar;
* devolver resultado.

---

## L. Billing

### Principio de diseño

El billing debe ser por **resultado observable**, no por intento.

### Schema conceptual

```text
BillingEvent {
  billing_event_id: uuid-v7
  execution_id:     uuid
  content_hash:     string
  tenant_id:        string
  module:           string
  event_type:       BillingEventType
  billable_result:  BillableResult
  generated_at:     datetime-utc
  idempotency_key:  string
}
```

### Idempotencia y retry safety

La arquitectura objetivo debe impedir doble facturación en:

* retries técnicos;
* reenvíos accidentales;
* reprocesamiento idéntico.

### Modelos soportados

* pago por uso;
* pago por resultado;
* bundles híbridos.

---

## M. Persistencia y storage

### Layout objetivo por tenant

```text
{storage_root}/
  {tenant_id}/
    {module}/
      {YYYY}/{MM}/{DD}/
        {execution_id}/
          input_raw.bin
          input_normalized.json
          canonical_rows.json
          findings.json
          summary.json
          suggested_actions.json
          action_ready_objects.json
          normalized_signals.json
          inference_trace.json
          audit_log.jsonl
          billing_events.json
          parse_metadata.json
```

### Qué va en bucket

* blobs;
* artefactos JSON;
* evidencia original;
* traces;
* logs append-only.

### Qué va en DB

* tabla `ingestions`;
* tabla `findings`;
* tabla `normalized_signals`;
* índices de acciones;
* metadata de billing.

### Qué va en metadata index

* paths por ejecución;
* resolución rápida de artefactos;
* navegación sin escanear bucket completo.

### Retención objetivo

* `input_raw`: configurable, con default razonable;
* `audit_log` y `billing_events`: permanentes;
* `canonical_rows` y `findings`: retención larga;
* `inference_trace`: retención auditada;
* acciones expiradas: retención más corta.

### Seguridad

* aislamiento por prefijo de tenant;
* IAM por service account;
* artefactos no públicos;
* logs append-only.

---

## N. Roadmap de endurecimiento del core

### Fase 1 — Fundación del contrato

**Objetivo**

* schema madre documentado;
* intake gateway;
* contract validation;
* layout de storage;
* audit básico;
* billing event inicial.

### Fase 2 — Normalizer + findings comunes

**Objetivo**

* parsers base;
* `canonical_rows` con provenance;
* catálogo de findings transversales;
* reglas duras iniciales para módulos prioritarios.

### Fase 3 — Hermes bridge + multiformato

**Objetivo**

* inference trace;
* PDF textual con fallback;
* imagen y PDF visual;
* prompts versionados;
* aceptación controlada de inferencia.

### Fase 4 — Signals + digest

**Objetivo**

* normalized signals;
* score y ranking;
* digest multi-módulo.

### Fase 5 — Action readiness + billing completo

**Objetivo**

* action ready objects;
* confirm/reject;
* billing por eventos;
* ciclo completo Generar → Mostrar → Confirmar.

### Endurecimiento para Apps Script

Parte del endurecimiento del core debe estar pensado explícitamente para soportar **micro-módulos Apps Script cada vez más ricos**, sin que eso los convierta en mini-cores.

Eso implica:

* contrato estable;
* responses previsibles;
* summary consumible por sidebar;
* actions presentables;
* mínima lógica de negocio en Apps Script;
* máxima semántica en el core.

---

## O. Qué debe estar listo antes del edge avanzado

### Antes de OCR fuerte

* parse state operativo;
* inference trace persistido;
* política de confidence;
* Hermes bridge estable.

### Antes de PDFs complejos AFIP/ARCA

* parser XML/XSD real;
* findings fiscales relevantes;
* pruebas con documentos reales.

### Antes de WhatsApp / bots

* soporte de imagen maduro;
* actions listas para confirmación;
* edge con lógica de presentación, no de negocio.

### Antes de Apps Script más ricos

* endpoint estable de ingesta;
* summary recuperable;
* digest disponible;
* contrato de acople publicado;
* autenticación por tenant;
* respuestas consistentes para sidebars y UX de Workspace.

---

## P. Riesgos de arquitectura

### Edge demasiado inteligente

Si Apps Script, bots o edges empiezan a acumular lógica de negocio, el core pierde coherencia.

### Findings heterogéneos

Si cada módulo inventa códigos incompatibles, el dashboard y el digest se vuelven incomparables.

### Hermes como caja negra

Sin `inference_trace`, confidence y raw preservado, el sistema pierde auditabilidad.

### Falta de idempotencia

Sin control por `content_hash`, aparecen duplicados en billing, findings y señales.

### Schema débil

Si los opcionales se convierten en cajón de sastre, la semántica se fragmenta.

### Documentos sin provenance

Sin provenance por campo, no se puede impugnar ni reproducir resultados.

### Señales inestables

Si el schema de `normalized_signals` cambia sin gobernanza, los consumers se rompen.

### Billing ambiguo

Sin criterio claro de resultado facturable, el sistema se vuelve comercialmente inconsistente.

### Normalizer sin tolerancia a errores parciales

Si todo es todo-o-nada, la realidad operativa de PyMEs queda fuera del sistema.

### Versionado de prompts ignorado

Si los prompts cambian sin versión, la inferencia histórica deja de ser reproducible.

---

## Q. Definición final

SmartCounter core debe ser la **infraestructura semántica de la operación PyME**.

Debe recibir evidencia heterogénea, convertirla en artefactos canónicos trazables, detectar hallazgos con taxonomía común, construir síntesis ejecutiva, producir señales comparables entre módulos, preparar acciones bajo control humano, registrar todo de manera auditable y habilitar facturación por resultado observable.

No debe ser un script.
No debe ser un OCR aislado.
No debe ser una app puntual de conciliación.

Debe ser el centro de gravedad que hace que microservicios distintos —conciliación, stock, sueldos, IVA, márgenes, aprobaciones, gastos, comercio, puentes, recategorización— hablen el mismo idioma, produzcan artefactos coherentes y habiliten acción sin perder trazabilidad.

Su valor central debe residir en:

* la normalización de la evidencia;
* la semántica de los hallazgos;
* la estabilidad de las señales;
* la preparación de acción bajo confirmación;
* y la preservación de trazabilidad extremo a extremo.

Todo lo demás son enchufes.

```
```
