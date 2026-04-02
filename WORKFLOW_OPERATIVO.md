# WORKFLOW OPERATIVO — SmartCounter

## Reglas de staging y commit

### 1. Nunca usar `git add .`
Staging solo por archivo o bloque explícito:
```bash
git add path/al/archivo.py
git add path/al/otro.md
```

### 2. Un frente por commit
Cada commit debe tener **un solo propósito** declarado.  
No mezclar en el mismo commit:
- backend + smokes
- smokes + documentación
- refactor + fix
- artefactos generados + código fuente

### 3. Auditoría obligatoria antes de cada push

```bash
git status
git diff --staged
# Revisar manualmente. Si hay ruido, abortar y limpiar.
```

Si aparece algo inesperado en el diff → **no pushear**.

### 4. Nunca editar en Cloud Shell

Cloud Shell es solo para:
- `git pull` desde `main`
- ejecutar smokes
- leer logs

Cualquier edición en Cloud Shell **contamina** y **rompe la trazabilidad**.

### 5. Formato de commit obligatorio

```
[frente]: descripción corta

Archivos afectados:
- path/archivo1
- path/archivo2
```

Ejemplos de frente: `smoke`, `backend`, `doc`, `fix`, `config`

### 6. No mezclar artefactos / node_modules

Verificar `.gitignore` antes de cada staging.  
Si hay `node_modules/`, `__pycache__/`, `.env`, o archivos generados → limpiar antes.

```bash
git status | grep -v "nothing to commit"
```

### 7. Pull en Cloud Shell siempre antes de validar

```bash
git pull origin main
```

Nunca validar smokes sobre una copia desactualizada.

---

## Checklist pre-push (obligatorio)

- [ ] `git status` auditado
- [ ] `git diff --staged` revisado línea por línea
- [ ] Un solo frente en el commit
- [ ] Artefactos/node_modules no incluidos
- [ ] Mensaje de commit con formato correcto
- [ ] Cloud Shell actualizado con pull
