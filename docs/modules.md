# Módulos SmartCounter

## Template base Apps Script

Ruta:

```text
apps_script/templates/base_module/
```

Archivos:

- `Config.gs`
- `Ui.gs`
- `Parser.gs`
- `Rules.gs`
- `Findings.gs`
- `Reports.gs`
- `SmartCounterClient.gs`
- `README.md`

## Cómo crear un módulo nuevo

1. Copiar `apps_script/templates/base_module/` a una carpeta nueva.
2. Definir `MODULE_NAME` del módulo.
3. Ajustar reglas en `Rules.gs`.
4. Ajustar findings en `Findings.gs`.
5. Ajustar summary/actions en `Reports.gs`.
6. Mantener intacto el contrato de salida.

## Contrato (obligatorio)

Todo módulo debe producir:

```json
{
  "tenant_id": "string",
  "module": "string",
  "source_type": "google_sheets|csv",
  "generated_at": "ISO-8601",
  "canonical_rows": [],
  "findings": [],
  "summary": {},
  "suggested_actions": []
}
```

## Reglas de compatibilidad

- `canonical_rows` siempre array
- `findings` siempre array
- `suggested_actions` siempre array
- salida determinística (orden estable)
- sin dependencias externas

## Ejecución estándar

```text
SmartCounter menu -> Run Analysis
```

Flujo interno:

```text
parse -> rules -> findings -> summary -> suggested_actions -> validate -> send
```
