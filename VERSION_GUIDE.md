# 📦 Guía de Versionado Automático

Esta guía explica cómo actualizar la versión de la aplicación de forma automática y centralizada.

## 🎯 Sistema de Versión Única

La versión de la aplicación está centralizada en **`app/version.py`** (fuente única de verdad).
Todos los demás archivos importan la versión desde este archivo.

### Archivos que usan la versión:
- `app/__init__.py` - Importa desde `app/version.py`
- `app/main.py` - Usa la versión en logs y configuración
- `app/ui/main_window.py` - Muestra la versión en la ventana
- `app/config.py` - Registra versión en configuración

## 🚀 Cómo Actualizar la Versión

### Opción 1: Script Automático (Recomendado)

El script `update_version.py` actualiza automáticamente la versión en todos los lugares necesarios.

```bash
# Ver versión actual
python update_version.py --show

# Actualizar a una versión específica
python update_version.py 1.2.3

# Incrementar versión automáticamente
python update_version.py --patch    # 1.1.2 -> 1.1.3
python update_version.py --minor    # 1.1.2 -> 1.2.0
python update_version.py --major    # 1.1.2 -> 2.0.0

# Actualizar con notas de versión
python update_version.py --patch --notes

# Actualizar y crear tag de git
python update_version.py 1.2.3 --tag

# Actualizar, crear tag y hacer push
python update_version.py 1.2.3 --tag --push
```

### Opción 2: Manual

Si prefieres actualizar manualmente:

1. Edita `app/version.py`:
   ```python
   __version__ = "1.2.3"  # Nueva versión
   ```

2. Agrega entrada en `VERSION_HISTORY`:
   ```python
   VERSION_HISTORY = {
       ...
       "1.2.3": [
           "Cambio 1",
           "Cambio 2",
           "Cambio 3"
       ]
   }
   ```

3. Commitea y crea tag:
   ```bash
   git add app/version.py
   git commit -m "chore: Bump version to 1.2.3"
   git tag -a v1.2.3 -m "Release 1.2.3"
   git push && git push origin v1.2.3
   ```

## 📋 Ejemplos de Uso

### Ejemplo 1: Corrección de bug (patch)
```bash
# Versión actual: 1.1.2
python update_version.py --patch --notes

# El script preguntará:
# > Ingrese las notas de la versión:
#   - Corrección de error en matching de NITs
#   - Mejora de logs de advertencia
#   - (presionar Enter para terminar)

# Resultado: Versión actualizada a 1.1.3
```

### Ejemplo 2: Nueva funcionalidad (minor)
```bash
# Versión actual: 1.1.2
python update_version.py --minor --tag --push

# Resultado:
# - Versión actualizada a 1.2.0
# - Tag v1.2.0 creado
# - Push automático al repositorio
```

### Ejemplo 3: Cambio importante (major)
```bash
# Versión actual: 1.1.2
python update_version.py --major --notes --tag

# Resultado:
# - Versión actualizada a 2.0.0 (con notas)
# - Tag v2.0.0 creado
# - Listo para push manual
```

### Ejemplo 4: Versión específica con todo automatizado
```bash
python update_version.py 1.5.0 --tag --push
```

## 🔢 Formato de Versión (Semantic Versioning)

La aplicación usa [versionado semántico](https://semver.org/lang/es/):

```
MAJOR.MINOR.PATCH
  │     │     │
  │     │     └─── Correcciones de bugs (1.1.2 -> 1.1.3)
  │     └───────── Nuevas funcionalidades (1.1.2 -> 1.2.0)
  └─────────────── Cambios incompatibles (1.1.2 -> 2.0.0)
```

### Cuándo incrementar cada número:

- **PATCH** (X.Y.Z+1): Correcciones de bugs, mejoras menores
  - Ejemplo: Corregir error de validación, mejorar mensaje de error

- **MINOR** (X.Y+1.0): Nuevas funcionalidades compatibles
  - Ejemplo: Agregar nuevo reporte, nueva opción de configuración

- **MAJOR** (X+1.0.0): Cambios incompatibles
  - Ejemplo: Cambiar formato de base de datos, eliminar funcionalidad

## 📝 Buenas Prácticas

1. **Siempre documenta cambios**: Usa `--notes` para agregar notas de versión

2. **Crea tags para releases**: Usa `--tag` para crear tags de git automáticamente

3. **Sigue convenciones de commit**:
   ```
   feat: Nueva funcionalidad
   fix: Corrección de bug
   docs: Cambios en documentación
   chore: Tareas de mantenimiento (como bump de versión)
   ```

4. **Actualiza VERSION_HISTORY**: El historial ayuda a usuarios a ver cambios

5. **Haz push de tags**: No olvides `git push origin vX.Y.Z` o usa `--push`

## 🔧 Verificación

Después de actualizar la versión, verifica que esté correcta:

```bash
# Ver versión en el código
python -c "from app.version import __version__; print(__version__)"

# Ver versión en git
git tag -l

# Ver versión en la aplicación
python app/main.py  # Aparecerá en el título de la ventana
```

## 🐛 Solución de Problemas

### Error: "La nueva versión debe ser mayor que la actual"
- Verifica que estés incrementando correctamente la versión
- Usa `--show` para ver la versión actual

### Error: "Hay cambios sin commitear"
- El script automáticamente comiteará `app/version.py`
- Si hay otros cambios, commitéalos primero o usa `git stash`

### Error: "Tag ya existe"
- Elimina el tag existente: `git tag -d vX.Y.Z`
- O usa una versión diferente

## 📚 Referencias

- [Semantic Versioning](https://semver.org/lang/es/)
- [Git Tags](https://git-scm.com/book/es/v2/Fundamentos-de-Git-Etiquetado)
- [Convenciones de Commits](https://www.conventionalcommits.org/es/)

## 💡 Ayuda

Para ver todas las opciones disponibles:
```bash
python update_version.py --help
```

Para ver la versión actual:
```bash
python update_version.py --show
```
