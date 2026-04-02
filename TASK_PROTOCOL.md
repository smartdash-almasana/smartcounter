# TASK PROTOCOL — Protocolo para Agentes (Antigravity / Codex / GPT)

## Formato obligatorio al recibir una tarea

Antes de tocar cualquier archivo, el agente debe declarar:

```
OBJETIVO ACOTADO:
  [ una sola oración: qué se va a hacer y en qué archivo/s ]

ARCHIVOS PERMITIDOS:
  [ lista explícita de archivos que el agente puede leer y/o modificar ]

ARCHIVOS PROHIBIDOS:
  [ lista explícita de archivos que el agente NO debe tocar ]

CAMBIO MÍNIMO:
  [ descripción del cambio más pequeño posible que resuelva el objetivo ]
```

---

## Salida obligatoria al finalizar

El agente debe responder siempre con estos 5 bloques, usando las letras exactas:

```
A. ARCHIVOS MODIFICADOS:
   [ lista de archivos tocados con path completo ]

B. RESUMEN DE CAMBIOS:
   [ descripción en 2-3 líneas de qué se hizo y por qué ]

C. DIFF O FRAGMENTO CLAVE:
   [ diff o bloque de código del cambio principal ]

D. COMANDOS PARA VERIFICAR:
   [ comandos git o de ejecución para que el humano valide el cambio ]

E. ESTADO DE COMMIT:
   [ "No se realizó ningún commit." O "Commit realizado: [SHA] - [mensaje]" ]
```

---

## Restricciones no negociables

- **No hacer commit salvo orden explícita del humano.**
- **No hacer push salvo orden explícita del humano.**
- **No asumir que un archivo en disco = archivo en `main`.** Verificar siempre.
- **No editar archivos fuera de los ARCHIVOS PERMITIDOS.**
- **No instalar dependencias sin autorización.**
- **No modificar smokes si el objetivo es backend, y viceversa.**

---

## Protocolo de contaminación detectada

Si el agente detecta cualquiera de estas señales:

- Archivos con cambios no trackeados que no corresponden al objetivo
- `git status` con archivos inesperados en staging
- `node_modules/`, `__pycache__/`, `.env` en el staging area
- Diferencias entre lo esperado y lo encontrado en disco

**→ CONGELAR. No tocar nada. Reportar primero.**

```
⚠️ CONTAMINACIÓN DETECTADA

Descripción: [ qué se encontró ]
Archivos afectados: [ lista ]
Estado del staging: [ limpio / contaminado ]
Acción tomada: Ninguna. Esperando instrucción del humano.
```

---

## Regla de oro

> El agente resuelve exactamente lo que se le pide, en los archivos declarados, con el cambio más pequeño posible.  
> Cualquier otra cosa es ruido y potencial daño.
