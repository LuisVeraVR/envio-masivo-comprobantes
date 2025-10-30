# Sistema de Versionado Automático

Este proyecto cuenta con un sistema de versionado automático que incrementa el número de versión cada vez que realizas un commit en Git.

## ¿Cómo funciona?

El sistema utiliza un **Git hook pre-commit** que se ejecuta automáticamente antes de cada commit. Este hook:

1. Lee la versión actual del proyecto
2. La incrementa automáticamente (patch: x.x.X)
3. Actualiza todos los archivos con números de versión
4. Agrega una entrada al historial de versiones
5. Incluye los cambios en el commit actual

## Instalación

### Primer uso

Para activar el sistema de versionado automático, ejecuta el script de instalación:

**Linux/Mac:**
```bash
./install-hooks.sh
```

**Windows:**
```cmd
install-hooks.bat
```

Estos scripts:
- Copian el hook pre-commit a `.git/hooks/`
- Configuran Git para usar el directorio `.githooks/`
- Dan permisos de ejecución necesarios

## Archivos que se actualizan automáticamente

El sistema actualiza la versión en estos archivos:

1. **app/version.py** - Versión principal y historial
2. **app/__init__.py** - Versión del módulo
3. **package.bat** - Versión para empaquetado

## Uso diario

### Versionado automático

Una vez instalado, el versionado es completamente automático:

```bash
# Haces cambios en tu código
git add .
git commit -m "feat: Nueva funcionalidad"

# El hook se ejecuta automáticamente y:
# - Incrementa la versión (ej: 1.1.3 -> 1.1.4)
# - Actualiza todos los archivos
# - Incluye los cambios en el commit
```

### Versionado manual

Si necesitas controlar manualmente la versión:

#### Ver versión actual
```bash
python3 bump_version.py --check
```

#### Incrementar versión patch (1.0.0 -> 1.0.1)
```bash
python3 bump_version.py --type patch
```

#### Incrementar versión minor (1.0.0 -> 1.1.0)
```bash
python3 bump_version.py --type minor
```

#### Incrementar versión major (1.0.0 -> 2.0.0)
```bash
python3 bump_version.py --type major
```

#### Con mensaje personalizado
```bash
python3 bump_version.py --type minor --message "Agregado sistema de reportes"
```

## Versionado Semántico

El proyecto sigue el estándar de [Semantic Versioning](https://semver.org/):

**MAJOR.MINOR.PATCH** (ejemplo: 2.1.4)

- **MAJOR** (2): Cambios incompatibles con versiones anteriores
- **MINOR** (1): Nuevas funcionalidades compatibles
- **PATCH** (4): Correcciones de bugs compatibles

### Cuándo usar cada tipo

- **patch**: Correcciones de bugs, cambios menores
  - `git commit -m "fix: Corregir error en validación"`
  - Automático con el hook

- **minor**: Nuevas funcionalidades compatibles
  - `python3 bump_version.py --type minor`
  - `git commit -m "feat: Agregar exportación a PDF"`

- **major**: Cambios que rompen compatibilidad
  - `python3 bump_version.py --type major`
  - `git commit -m "BREAKING CHANGE: Nueva API de configuración"`

## Historial de versiones

El historial se mantiene automáticamente en `app/version.py`:

```python
VERSION_HISTORY = {
    "1.1.3": [
        "Actualización automática de versión",
        "Fecha: 2025-10-30"
    ],
    "1.1.2": [
        "Prueba del sistema de versionado automático",
        "Fecha: 2025-10-30"
    ],
    # ...
}
```

## Estructura de archivos

```
proyecto/
├── bump_version.py          # Script de versionado
├── install-hooks.sh         # Instalador Linux/Mac
├── install-hooks.bat        # Instalador Windows
├── .githooks/
│   └── pre-commit          # Hook de Git
├── app/
│   ├── version.py          # Versión principal
│   └── __init__.py         # Versión del módulo
└── package.bat             # Versión para empaquetado
```

## Desactivar el versionado automático

Si necesitas desactivar temporalmente el versionado automático:

```bash
# Desactivar hooks
git config core.hooksPath ""

# O hacer commit sin ejecutar hooks
git commit --no-verify -m "mensaje"
```

Para reactivar:
```bash
git config core.hooksPath .githooks
```

## Solución de problemas

### El hook no se ejecuta

1. Verifica que el hook esté instalado:
   ```bash
   ls -la .githooks/pre-commit
   ```

2. Verifica la configuración de Git:
   ```bash
   git config core.hooksPath
   ```
   Debe mostrar: `.githooks`

3. Reinstala el hook:
   ```bash
   ./install-hooks.sh  # o install-hooks.bat en Windows
   ```

### Versiones desincronizadas

Si los archivos tienen versiones diferentes, sincronízalos manualmente:

```bash
# Esto actualizará todos los archivos a la misma versión
python3 bump_version.py --type patch
```

### El script falla

Verifica que tienes Python 3 instalado:
```bash
python3 --version
```

## Mejores prácticas

1. **No edites manualmente los números de versión** - Deja que el sistema lo haga
2. **Usa el tipo de versión correcto** - patch para bugs, minor para features, major para breaking changes
3. **Commits atómicos** - Un commit = un cambio = un incremento de versión
4. **Mensajes descriptivos** - Usa mensajes claros en tus commits

## Integración con GitHub/GitLab

El versionado automático funciona perfectamente con plataformas de Git:

```bash
# Hacer cambios
git add .
git commit -m "feat: Nueva funcionalidad"  # Versión se incrementa automáticamente

# Push al remoto
git push origin main
```

El historial de versiones se mantiene en el repositorio y es visible para todo el equipo.

## Comandos rápidos

```bash
# Ver versión actual
python3 bump_version.py --check

# Versionado automático (con commit)
git add .
git commit -m "mensaje"

# Versionado manual minor
python3 bump_version.py --type minor
git add .
git commit -m "mensaje"

# Reinstalar hooks
./install-hooks.sh
```

---

Para más información sobre versionado semántico, visita: https://semver.org/
