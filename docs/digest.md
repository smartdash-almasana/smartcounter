# Digest Builder

## Qué resuelve

El digest toma artefactos recientes y genera una vista ejecutiva compacta:

- **La foto de hoy**
- **Lo que importa ahora**
- **La pregunta del día**

## Flujo lógico

```text
artifacts (findings/summary)
  -> extracción de señales
  -> orden por severidad
  -> top alerts
  -> pregunta contextual
  -> digest final
```

## Señales -> alertas -> pregunta

1. Se leen findings desde artefactos.
2. Se normaliza severidad y se elimina ruido.
3. Se seleccionan alertas prioritarias (top N).
4. Se genera una pregunta accionable basada en la alerta principal.

## Estructura esperada de digest

```json
{
  "tenant_id": "string",
  "generated_at": "ISO-8601",
  "summary": {
    "modules": [],
    "total_findings": 0
  },
  "alerts": [],
  "question": "string",
  "priority_score": 0
}
```

## Concepto de salida Telegram

La salida para Telegram es una representación del digest:

- bloque 1: foto de hoy
- bloque 2: alertas con prioridad visual
- bloque 3: pregunta del día

No cambia el contrato core; solo cambia el formato de presentación.

## Límites de alcance

- no agrega nueva lógica de negocio por módulo
- no reemplaza acciones
- no introduce DB
- consume artefactos existentes
