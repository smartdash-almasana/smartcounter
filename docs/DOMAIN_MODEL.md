# Domain Model

Este modelo es conceptual. No representa una implementacion cerrada.

## Entidades conceptuales

### Estudio
Unidad organizacional que administra clientes y define criterios operativos de trabajo contable.

### Cliente
Entidad atendida por el estudio. Es el contexto de negocio para archivos, reglas y decisiones historicas.

### Archivo
Documento de entrada (normalmente Excel) asociado a un cliente y a un ciclo operativo.

### TipoDePlanilla
Clasificacion funcional de la planilla (por ejemplo, IVA compras/ventas, mayor, balance, cobranzas).

### Hoja
Subestructura dentro del archivo. Puede contener tablas utiles, ruido o metadatos.

### TablaDetectada
Bloque tabular identificado como potencial fuente de datos contables.

### ColumnaOriginal
Encabezado y semantica observada en la fuente, sin normalizar.

### CampoCanonico
Campo destino normalizado del modelo contable interno (por ejemplo, fecha, CUIT, monto neto).

### ReglaDeMapping
Regla que vincula columna original con campo canonico, incluyendo criterios y nivel de confianza.

### ReglaDeLimpieza
Regla de transformacion para normalizar valores (formato de fecha, separadores, signos, moneda).

### Ambiguedad
Evento donde la interpretacion no es unica o confiable; requiere explicacion y posible revision humana.

### RevisionHumana
Intervencion del operador para confirmar, corregir o rechazar clasificacion, mapping o limpieza.

### Exportacion
Salida estructurada para consumo posterior (archivo, tabla o payload), con trazabilidad de decisiones.
