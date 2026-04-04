# Manual Operativo de la Factoría SmartCounter

## Estándar de trabajo para diseñar, prototipar y acoplar módulos

> Propósito: establecer un flujo único, repetible y coherente para construir todos los módulos de la factoría SmartCounter con el menor ruido posible, reduciendo fricción, evitando gasto prematuro de tokens en build y garantizando un enchufe consistente al core.

---

## 1. Principio rector

La factoría no construye scripts aislados.
Construye **módulos acoplables al core SmartCounter**.

Por lo tanto, el orden correcto no es:

**idea → código → parche → acople improvisado**

El orden correcto es:

**dolor → contrato → prototipo → validación → build → acople**

---

## 2. Regla de oro de la factoría

### Nunca ir directo a build si no existe primero:

* misión exacta del módulo
* flujo UX mínimo
* contrato de entrada
* contrato de salida
* reglas determinísticas
* edge cases reales
* criterios de aceptación
* estrategia de acople al core

### Traducción operativa

Antigravity, Codex o cualquier builder **no se usa para pensar producto**.
Se usa para **implementar una especificación ya cerrada**.

---

## 3. Qué es SmartCounter dentro de este estándar

SmartCounter es el **core**.

Responsabilidades del core:

* recibir módulos
* validar contratos
* persistir artefactos
* normalizar señales
* construir resúmenes
* preparar acciones futuras bajo confirmación

### Contrato común mínimo del core

```json
{
  "tenant_id": "demo001",
  "module": "[module_name]",
  "source_type": "google_sheets",
  "generated_at": "ISO_TIMESTAMP",
  "canonical_rows": [],
  "findings": [],
  "summary": {},
  "suggested_actions": []
}
```

---

## 4. Qué es un módulo dentro de este estándar

Un módulo es un **microservicio funcional** orientado a resolver un dolor operativo específico.

Ejemplos:

* StockSimple
* ConciliSimple
* AprobaSimple
* RentableSimple
* OnboardSimple
* LibroSueldosSimple

### Un módulo correcto:

* resuelve un dolor claro
* recibe una fuente operativa real
* produce artefactos compatibles con el core
* no redefine la arquitectura madre
* no rompe la coherencia de SmartCounter

---

## 5. Qué es Google AI Studio en este flujo

Google AI Studio es el **laboratorio de prototipado previo al build**.

### AI Studio se usa para:

* cerrar misión del módulo
* definir UX sin fricción
* diseñar contrato de entrada
* diseñar contrato de salida
* definir reglas determinísticas
* listar edge cases
* redactar criterios de aceptación
* preparar el prompt final de implementación

### AI Studio no se usa para:

* improvisar arquitectura
* codear a ciegas
* reemplazar el core
* inventar payloads durante el build
* decidir producto mientras ya se está implementando

---

## 6. Qué es el Gem arquitecto para Gemini

El Gem arquitecto es un **asistente especializado de pre-build**.

No construye código final.
No reemplaza al builder.
No genera scripts libres.

### Su función

Convertir un dolor operativo en una **especificación lista para construir**.

### Nombre recomendado del Gem

**SmartCounter Module Architect**

### Misión del Gem

Antes de cualquier implementación, devolver:

* misión exacta del módulo
* flujo UX ideal
* contrato de entrada
* contrato de salida
* reglas determinísticas
* edge cases reales
* supuestos de entorno
* criterios de aceptación
* riesgos de adopción
* prompt final para build

---

## 7. Instrucciones maestras del Gem arquitecto

Pegar esto en Gemini Gems como instrucciones del Gem:

```text
Sos el arquitecto de módulos de SmartCounter.

No asumas conocimiento previo.
Tomá como verdad solo lo que está en estas instrucciones y en los archivos de conocimiento cargados.

## Qué es SmartCounter
SmartCounter es el core de una fábrica de microservicios para PyMEs.

La arquitectura tiene 3 capas:
1. Ver: leer archivos operativos reales del negocio
2. Comprender: transformar hallazgos en síntesis y prioridades
3. Accionar: sugerir acciones, pero sin ejecutar nada sensible automáticamente

## Regla central
Toda acción sensible sigue:
Generar / Mostrar / Confirmar / Ejecutar

Nunca diseñes automatización sensible sin confirmación humana explícita.

## Rol de Apps Script
Google Apps Script es borde operativo.
No es el core.
Sirve para:
- recibir archivos
- dar UX liviana dentro de Google Workspace
- estructurar datos
- producir artefactos canónicos
- enviar payloads al core

## Rol del core SmartCounter
Recibe módulos y espera este contrato de salida:

{
  "tenant_id": "demo001",
  "module": "[module_name]",
  "source_type": "google_sheets",
  "generated_at": "ISO_TIMESTAMP",
  "canonical_rows": [],
  "findings": [],
  "summary": {},
  "suggested_actions": []
}

## Restricciones de diseño
- no conviertas Apps Script en el core
- no inventes arquitectura nueva
- no agregues dashboards salvo pedido explícito
- no muestres al cliente términos técnicos como:
  tenant_id, header_row, source_sheet, canonical_rows, findings, module
- evitá data entry manual si puede reemplazarse por carga de archivo o automatización simple
- priorizá UX natural, corta y vendible para PyME
- si una etiqueta visible no la entendería un dueño en 3 segundos, reescribila

## Tu trabajo
No implementes código final.
No des teoría general.
No me mandes a otra herramienta.
Diseñá un módulo listo para build.

## Formato obligatorio de salida
A. Misión exacta del módulo
B. Flujo UX ideal
C. Contrato de entrada
D. Contrato de salida
E. Reglas determinísticas
F. Edge cases reales
G. Supuestos de entorno
H. Criterios de aceptación
I. Riesgos de adopción
J. Prompt final para implementación

## Regla final
Si falta contexto crítico, hacé como máximo 5 preguntas al principio.
Si no falta, no preguntes y resolvé.
Respondé en español.
Sé concreto.
No uses jerga innecesaria.
```

---

## 8. Archivos de conocimiento recomendados para el Gem

Cargar al Gem los documentos madre de la factoría:

* tesis de fábrica SmartCounter
* contrato común de módulos
* resumen diario del dueño
* patrón Generar / Mostrar / Confirmar / Ejecutar
* protocolo Swarm / SmartCounter
* notas de dolores PyME por vertical

### Criterio

El Gem debe trabajar con:

* contexto de arquitectura
* contexto de producto
* contexto de UX del dueño
* contexto de seguridad del sistema

---

## 9. Prompt operativo para usar el Gem

Cada vez que se diseñe un módulo nuevo, usar este prompt dentro del Gem:

```text
Quiero diseñar un módulo nuevo para SmartCounter.

Nombre del módulo: [NOMBRE]
Dolor principal: [DOLOR]
Fuente operativa real: [CSV / XLSX / TXT / Google Sheet / carpeta / etc.]
Usuario operativo: [QUIÉN USA O CARGA]
Dueño que recibe valor: [QUIÉN DECIDE]
Resultado esperado: [RESULTADO]
Restricciones reales: [RESTRICCIONES]

Diseñalo en el formato obligatorio del Gem.
No implementes código todavía.
```

---

## 10. Flujo de trabajo oficial de la factoría

### Fase 0 — Dolor

Antes de abrir AI Studio, definir:

* qué problema resuelve el módulo
* quién lo sufre
* qué costo genera
* cómo se resuelve hoy

### Fase 1 — Gem arquitecto

Correr el Gem para obtener:

* misión
* UX
* contratos
* reglas
* edge cases
* criterios de aceptación

### Fase 2 — Prototipado en Google AI Studio

Con la salida del Gem:

* afinar el flujo UX
* tensionar el contrato
* probar variantes de lenguaje
* revisar qué campos sobran o faltan
* confirmar qué se resuelve con reglas y qué no

### Fase 3 — Auditoría humana

Revisión conjunta de la salida de AI Studio:

* coherencia con SmartCounter
* claridad semántica
* nivel de fricción
* acople al core
* viabilidad de demo

### Fase 4 — Prompt de build

Solo cuando la spec esté cerrada:

* redactar prompt de implementación
* builder ejecuta
* sin rediseñar producto

### Fase 5 — Auditoría técnica post-build

Revisión de:

* archivos
* contrato
* acople al core
* UX real
* smoke manual

### Fase 6 — Integración

Solo después:

* enchufe al core
* endpoint
* persistencia
* naming consistente
* compatibilidad con SmartCounter

---

## 11. Qué va primero y qué va después

### Siempre primero

* contrato
* UX
* reglas
* edge cases
* criterios de aceptación

### Siempre después

* código
* integración
* build masivo
* automatización avanzada

---

## 12. Regla de acople

Todo módulo debe nacer preparado para enchufarse al core.

### Eso implica:

* mismo contrato raíz
* misma semántica de findings
* summary legible
* suggested_actions no ejecutadas
* naming consistente
* sin payloads arbitrarios

### Prohibido

* módulos que inventan su propio backend
* módulos que redefinen el contrato
* módulos que esconden lógica crítica en UI
* módulos que mezclan borde y core

---

## 13. Criterios de calidad antes de build

No se construye nada si no existe esto:

### Checklist de aprobación pre-build

* [ ] misión del módulo cerrada
* [ ] flujo UX paso a paso
* [ ] lenguaje visible natural para cliente
* [ ] contrato de entrada definido
* [ ] contrato de salida definido
* [ ] schema de canonical_rows
* [ ] schema de findings
* [ ] schema de summary
* [ ] schema de suggested_actions
* [ ] reglas determinísticas explícitas
* [ ] edge cases reales listados
* [ ] supuestos de entorno declarados
* [ ] criterios de aceptación definidos
* [ ] prompt de build listo

Si falta uno de estos puntos, no se pasa a implementación.

---

## 14. Criterios de calidad de UX

Todo módulo debe pasar esta prueba:

### Test de comprensión en 3 segundos

Si un dueño de PyME ve un texto visible del módulo y no lo entiende en 3 segundos, ese texto está mal.

### Prohibido mostrar al cliente

* tenant_id
* header_row
* base_url
* source_sheet
* canonical_rows
* findings
* module
* wording técnico interno

### Sí mostrar

* archivo cargado
* estado actual
* qué requiere atención
* próxima acción sugerida
* resultado en lenguaje humano

---

## 15. Cuándo usar Antigravity o Codex

### Sí usar builder cuando:

* el módulo ya fue prototipado
* el contrato ya está cerrado
* el flujo UX ya fue definido
* los edge cases ya están listados
* el prompt de build ya existe

### No usar builder cuando:

* todavía no sabés cómo entra el dato
* todavía no sabés qué ve el usuario
* todavía no sabés cómo sale el payload
* todavía estás discutiendo producto

---

## 16. Qué hace cada parte del sistema

### El usuario fundador

* valida dolor
* decide prioridad comercial
* trae contexto del mercado

### El Gem arquitecto

* estructura el módulo
* blinda el contrato
* propone el flujo

### Google AI Studio

* prototipa y afina la especificación
* reduce errores caros antes del build

### El builder

* implementa exactamente lo que ya fue decidido

### SmartCounter core

* recibe
* valida
* persiste
* normaliza
* prepara digest y acciones futuras

---

## 17. Plantilla de ficha estándar de módulo

Cada módulo debe quedar resumido en esta ficha:

```md
# [Nombre del módulo]

## Misión
[una frase]

## Dolor
[qué duele y a quién]

## Usuario operativo
[quién lo usa o carga]

## Dueño que recibe valor
[quién decide]

## Fuente operativa real
[CSV / XLSX / TXT / carpeta / sheet / etc.]

## Contrato de entrada
[campos mínimos]

## Contrato de salida
[shape compatible con SmartCounter]

## Reglas determinísticas
[listado]

## Edge cases
[listado]

## UX visible
[qué ve el usuario]

## Qué no debe ver
[listado]

## Criterios de aceptación
[listado]

## Prompt final para build
[texto final]
```

---

## 18. Primera pregunta obligatoria antes de cualquier módulo

Antes de arrancar un módulo nuevo, siempre responder esto:

### 1. Qué problema exacto resuelve

### 2. Quién carga el dato o lo opera

### 3. Quién recibe el valor real

### 4. Cuál es la fuente operativa real

### 5. Qué resultado visible tiene que devolver

Sin esas 5 respuestas, no se abre build.

---

## 19. Frase operativa del estándar

**Primero prototipar. Después construir.**

No gastar tokens de build para descubrir producto.
No gastar UX real del cliente en configuraciones internas.
No improvisar el acople.

---

## 20. Cierre

Este manual fija el estándar de la factoría:

* Gemini Gem = arquitecto de pre-build
* Google AI Studio = laboratorio de prototipado
* Builder = implementación cerrada
* SmartCounter = core estable de acople

### Fórmula oficial

**dolor → contrato → prototipo → validación → build → acople**

Ese es el flujo que reduce fricción, baja el ruido, evita gastar tokens inútiles y mantiene coherencia con SmartCounter.
