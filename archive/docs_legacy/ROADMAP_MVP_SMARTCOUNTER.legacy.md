Sí.
Y te lo voy a bajar a **roadmap real hasta MVP**, no teoría.

Lo central: **no estás en etapa de inventar más features**. Estás en etapa de **cerrar un núcleo que ya mostró valor**: caos de entrada contable argentino, con foco en IVA primero y venta inicial posible por LSD. Eso ya quedó validado por el material y por el baseline real del pipeline.  

# Norte del producto

## Qué es SmartCounter

Un SaaS para estudios contables argentinos que:

* recibe archivos caóticos
* detecta estructura
* mapea columnas
* normaliza valores
* emite warnings útiles
* devuelve una salida curada para revisión humana

## Qué no es

* no es ERP
* no es “subidor automático a AFIP”
* no es conciliación automática total
* no reemplaza criterio del contador

Eso también quedó bien marcado en la investigación: primero resolver **caos de entrada**, después pensar output oficial.  

---

# Veredicto de roadmap

## Construir primero

**IVA / Libro IVA**

Porque:

* más volumen
* más frecuencia
* más variedad de formatos
* mejor terreno para entrenar detector, mapper y normalizador

## Vender primero

**Libro de Sueldos Digital**

Porque:

* más miedo
* más riesgo percibido
* error más caro
* valor comercial más fácil de cobrar

Esto no coincide, y está bien que no coincida. Ya salió así en ambos informes.  

---

# Estado real actual

Ya tienes una base no trivial:

* `pipeline-curated` corriendo
* 4 casos de test pack validados
* detección header/tabular
* mapping base
* normalización base
* warnings estructurados
* `normalization_summary`
* baseline documentado en docs internas

Y el caso más valioso hoy es `08_montos_mixtos_signos.xlsx`, porque ya mostró que el sistema puede transformar caos real en salida revisable. 

---

# Roadmap hasta MVP

Lo dividiría en **5 etapas**.

## Etapa 1 — Núcleo confiable de curaduría

**Objetivo:** que SmartCounter sea muy bueno leyendo y ordenando planillas problemáticas.

### Debe quedar sólido

* detección tabular/header
* inferencia básica de headers
* diccionario de aliases
* normalización de:

  * fechas
  * montos
  * CUIT/CUIL
  * nulos
* warnings estructurados
* salida curada por archivo

### Entregable de etapa

Un comando o flujo que, dado un Excel/CSV real, devuelva:

* estructura detectada
* columnas originales
* mapping canónico
* warnings
* preview normalizado
* resumen por campo/código

### Criterio de cierre

Cuando puedas correr eso sobre un pack de 15–25 archivos reales y el resultado sea **revisable con ahorro real de tiempo**.

## Etapa 2 — Especialización IVA

**Objetivo:** convertir el núcleo genérico en una herramienta muy útil para comprobantes.

### Capacidades

* reconocer columnas IVA típicas
* validar aritmética básica:

  * neto + IVA + exento/percepciones vs total
* detectar duplicados
* detectar tipos de comprobante conflictivos
* rectificar warning de notas de crédito/signos
* detectar moneda/tipo de cambio faltante como warning

### Salida MVP IVA

Una tabla normalizada con columnas estándar y warnings por línea.

### Criterio de cierre

Que un contador pueda agarrar un Excel o CSV feo de compras/ventas y pasar de caos a una tabla limpia **sin tener que reconstruir todo a mano**.

## Etapa 3 — Capa comercial LSD

**Objetivo:** abrir el frente que más se vende, sin prometer automatización total.

### Capacidades

* prevalidación de conceptos
* chequeo de CUIL
* chequeo de rangos básicos
* duplicados por CUIL/período
* warnings de longitud/formato
* señalamiento de incompatibilidades obvias

### Ojo

No intentar en MVP:

* replicar toda la lógica de ARCA
* validar online contra todo
* reemplazar sistema de liquidación

### Oferta

“No te liquido sueldos; te detecto antes lo que te va a rebotar o comprometer.”

## Etapa 4 — Experiencia mínima de producto

**Objetivo:** sacar a SmartCounter de “script útil” y convertirlo en MVP vendible.

### Necesitas

* upload simple de archivo
* procesamiento
* vista de salida curada
* descarga CSV/XLSX limpio
* panel muy simple de warnings
* historial básico de archivos procesados

### No necesitas aún

* dashboard sofisticado
* multiusuario complejo
* analytics avanzado
* automatizaciones extravagantes

## Etapa 5 — MVP comercial real

**Objetivo:** cobrar.

### Paquete MVP

* módulo IVA operativo
* módulo LSD pre-validador inicial
* UI simple
* 1 estudio piloto
* 1 workflow repetible
* pricing simple

### Posicionamiento

No vender:
“IA contable”

Vender:
“Te ordena y pre-valida la planilla antes de que vos pierdas tiempo o te rebote.”

---

# Backlog real prioritario

## P0 — imprescindible

1. robustecer test pack y baseline
2. ampliar casos reales
3. cerrar diccionario de columnas v1
4. endurecer warnings genéricos
5. endurecer normalizador de montos/fechas/CUIT
6. salida curada exportable

## P1 — valor fuerte IVA

7. reglas aritméticas IVA
8. duplicados por clave compuesta
9. tipos de comprobante y signos
10. warnings de campos críticos faltantes

## P1.5 — valor comercial LSD

11. catálogo base de conceptos
12. warnings de concepto no reconocido
13. validación básica de CUIL/rangos
14. duplicados y formato fijo

## P2 — producto

15. upload + vista resultado
16. descarga de salida curada
17. historial básico
18. configuración mínima de tipo de archivo/caso de uso

---

# Lo que no debes hacer ahora

No haría ahora:

* AFIP uploader automático
* engine fiscal completo
* conciliación bancaria full automática
* dashboard complejo
* arquitectura enterprise
* multi-tenant sofisticado
* shared-engine perfecto
* refactor grande por elegancia

Eso te mata tiempo y no te acerca al MVP.

---

# MVP exacto que yo construiría

## MVP v1

**Nombre funcional:** SmartCounter Curador IVA

### Input

* Excel/CSV de ventas o compras
* archivos desordenados, manuales o exportados

### Output

* tabla normalizada
* warnings por fila
* resumen de errores
* exportable

### Usuario

* estudio contable pequeño/mediano
* contador que hoy limpia planillas a mano

### Promesa

“Subís la planilla como venga y te la devuelvo ordenada, señalada y lista para revisión.”

## MVP v1.5 comercial

Agregar:

* pre-chequeo LSD básico
* oferta premium por riesgo

---

# Secuencia recomendada

## Fase 1

Cerrar núcleo de curaduría sobre IVA.

## Fase 2

Probar con 1–3 contadores reales.

## Fase 3

Medir:

* cuánto tiempo ahorra
* qué warnings sí sirven
* qué columnas fallan más
* qué archivos son imposibles

## Fase 4

Con eso, sumar LSD como capa comercial.

---

# Riesgos reales

## Riesgo 1

Querer resolver demasiado pronto la salida oficial.

## Riesgo 2

Confundir “mucha validación” con “mucho valor”.

## Riesgo 3

Meterte a UI compleja antes de cerrar motor.

## Riesgo 4

Construir para casos ideales y no para Excels sucios.

## Riesgo 5

Seguir en loops de prompts sin hito de producto.

---

# Qué haría yo desde mañana

## Sprint 1

Cerrar **núcleo IVA curador**.

Entregables:

* más casos reales
* baseline ampliado
* export limpio
* reglas IVA mínimas

## Sprint 2

Armar **interfaz mínima usable**.

Entregables:

* upload
* procesamiento
* tabla resultado
* descarga

## Sprint 3

Piloto con contador real.

Entregables:

* 10–20 archivos reales
* métricas de ahorro
* lista de fallos

## Sprint 4

Entrar con **LSD pre-validador**.

Entregables:

* conceptos
* CUIL
* duplicados
* longitudes / formato

---

# Mi recomendación final

Tu MVP no debe ser:

**“plataforma contable integral con IA”**

Tu MVP debe ser:

**“mesa de revisión inteligente para planillas contables problemáticas”**

Eso está mucho más cerca, es más vendible, es más construible y calza perfecto con lo que ya has validado técnica y documentalmente.  

# Decisión concreta

Seguiría así:

1. **IVA primero para construir**
2. **LSD primero para vender**
3. **conciliación bancaria después**
4. **UI mínima solo cuando el motor ya ahorre tiempo real**
5. **piloto humano antes de ampliar alcance**

