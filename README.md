# SmartCounter

## Qué es
SmartCounter es una plataforma de análisis operativo con flujo:

`ingest -> analyze -> findings -> digest -> actions`

- **ingest**: recibe artefactos (CSV/XLSX/JSON) y los persiste.
- **analyze**: ejecuta un módulo y produce salida estructurada.
- **findings**: hallazgos normalizados por severidad y entidad.
- **digest**: resumen ejecutivo diario a partir de artefactos.
- **actions**: acciones sugeridas para operar.

## Arquitectura

- **backend**: motor core (FastAPI + contratos + servicios).
- **apps_script**: fábrica de módulos edge para Google Sheets/Apps Script.

El backend no depende de base de datos para el flujo principal de artefactos: opera sobre almacenamiento de artefactos y contratos versionados.

## Estructura del repo

```text
backend/
  api/
  routes/
  schemas/
  services/
apps_script/
  templates/
    base_module/
  stock_simple/
docs/
```

## Primer flujo funcional

1. Un módulo Apps Script arma el contrato SmartCounter.
2. Envía `POST /ingest/analyze` al backend.
3. El backend persiste artefactos y ejecuta módulo.
4. El digest agrega señales/hallazgos en salida ejecutiva.
5. Se consume por UI, Telegram o capa de acciones.

## Quick start

### 1) Backend

```powershell
uvicorn app:app --host 0.0.0.0 --port 8000
```

Endpoint base de integración:

```text
POST /ingest/analyze
```

### 2) Template Apps Script

Ruta:

```text
apps_script/templates/base_module/
```

Uso rápido:

1. Copiar la carpeta `base_module` para un módulo nuevo.
2. Configurar `TENANT_ID`, `MODULE_NAME`, `SOURCE_TYPE`, `SMARTCOUNTER_BASE_URL`.
3. En Google Sheets ejecutar `SmartCounter -> Run Analysis`.
4. Verificar respuesta backend y artefactos.

## Documentación clave

- [Arquitectura](docs/architecture.md)
- [Módulos](docs/modules.md)
- [Digest](docs/digest.md)
