# RECOVERY PLAN — SmartCounter

Plan de saneamiento post-contaminación multi-entorno.  
Ejecutar en orden. No saltear pasos.

---

## Fase 1 — Congelación

**Objetivo:** No empeorar el estado actual.

```bash
# En PC local: no hacer ningún git add, commit, push hasta completar la auditoría
# En Cloud Shell: no editar nada
git status                  # documentar el estado actual
git stash list              # ver si hay stashes pendientes
git log --oneline -10       # ver los últimos 10 commits
```

Registrar el output en `SMARTCOUNTER_CURRENT_STATE.md`.

---

## Fase 2 — Auditoría local

**Objetivo:** Identificar qué está limpio y qué está contaminado.

```bash
# Ver todos los archivos modificados respecto a main
git diff origin/main --name-only

# Ver diff completo de archivos críticos (uno por vez)
git diff origin/main -- smoke_test.py
git diff origin/main -- <archivo_backend_principal>

# Verificar archivos no trackeados
git status --short
```

Clasificar cada archivo como:
- **LIMPIO** → coincide con `main` o tiene cambios válidos y auditados
- **EN AUDITORÍA** → cambios presentes, origen incierto
- **CONTAMINADO** → cambios que no deben estar (node_modules, artefactos, ediciones de Cloud Shell)

---

## Fase 3 — Rescate de archivos sanos

**Objetivo:** Recuperar versión canónica de archivos contaminados.

```bash
# Restaurar un archivo a su estado en main
git checkout origin/main -- path/al/archivo.py

# Si el archivo local tiene cambios válidos que querés conservar:
# 1. Copiar los cambios válidos a un .patch o un archivo temporal
# 2. Restaurar desde main
# 3. Aplicar solo los cambios válidos manualmente
```

---

## Fase 4 — Consolidación del lote limpio

**Objetivo:** Preparar un commit limpio con solo los cambios válidos.

```bash
# Staging explícito, archivo por archivo
git add path/archivo1.py
git add path/archivo2.md

# Verificar staging antes de continuar
git diff --staged

# Confirmar que no hay ruido
git status
```

Si hay algo en staging que no debería estar → sacar:
```bash
git restore --staged path/archivo_no_deseado.py
```

---

## Fase 5 — Commit limpio

```bash
git commit -m "[frente]: descripción corta del lote limpio

Archivos incluidos:
- path/archivo1.py
- path/archivo2.md"
```

---

## Fase 6 — Push

```bash
# Solo si el commit fue auditado y el staging estaba limpio
git push origin main
```

Verificar en GitHub que el commit aparece correctamente.

---

## Fase 7 — Pull en Cloud Shell

```bash
# En Cloud Shell (solo lectura, nunca editar)
git pull origin main
git log --oneline -3    # confirmar que el commit llegó
```

---

## Fase 8 — Validación final

```bash
# Ejecutar smokes contra el backend actualizado
# Comando exacto según el proyecto (completar en SMARTCOUNTER_CURRENT_STATE.md)
[ COMPLETAR: comando para correr smokes ]
```

Registrar resultado (OK / FAIL) en `SMARTCOUNTER_CURRENT_STATE.md`.

---

## Criterio de éxito

- `git diff origin/main -- <archivos_críticos>` devuelve vacío o solo cambios auditados
- Smokes pasan en Cloud Shell con el código de `main`
- `SMARTCOUNTER_CURRENT_STATE.md` actualizado con el nuevo estado

---

## Criterio de rollback

Si alguna fase falla:

```bash
# Volver al último commit conocido como bueno
git reset --hard <SHA_del_commit_bueno>
git push origin main --force-with-lease  # solo si es absolutamente necesario
```

SHA del último commit bueno: `[ COMPLETAR antes de ejecutar el plan ]`
