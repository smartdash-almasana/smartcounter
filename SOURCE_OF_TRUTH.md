# SOURCE OF TRUTH — SmartCounter

## Fuente Oficial

**GitHub / rama `main`** es la única fuente de verdad del proyecto.

Ningún entorno local ni remoto tiene precedencia sobre `main`.  
Si hay conflicto entre cualquier entorno y `main`, gana `main`.

---

## Roles de cada entorno

| Entorno | Rol permitido | Rol prohibido |
|---|---|---|
| **PC local** | Único lugar de edición y staging | No es fuente de verdad |
| **GitHub `main`** | Fuente oficial y punto de integración | No se edita directo |
| **Cloud Shell** | Solo validación y ejecución de smokes | No se edita código aquí |

---

## Flujo obligatorio

```
PC local (edición) → git status + git diff auditado → staging explícito → commit limpio → push → GitHub main → pull en Cloud Shell → ejecución / validación
```

No existe ningún otro flujo válido.

---

## Prohibiciones explícitas

- **No editar en Cloud Shell.** Ni un solo archivo.
- **No hacer `git add .`** en ningún entorno.
- **No pushear sin auditar `git status` y `git diff` primero.**
- **No mezclar cambios de backend, smokes y artefactos en el mismo commit.**
- **No asumir que lo que está en Cloud Shell = lo que está en `main`.** Siempre hacer `git pull` antes de validar.
- **No usar archivos descargados / copiados de Cloud Shell como fuente de edición en PC.**
- **No editar directamente en GitHub (web editor).**

---

## Última actualización

2026-04-02 — Establecido como reset metodológico post-contaminación multi-entorno.
