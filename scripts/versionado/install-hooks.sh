#!/bin/bash
# Script de instalación de Git Hooks para Linux/Mac
# Instala los hooks de versionado automático

echo "================================================"
echo "  Instalador de Git Hooks"
echo "  Sistema de Versionado Automático"
echo "================================================"
echo ""

# Obtener el directorio raíz del repositorio
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$REPO_ROOT" ]; then
    echo "✗ Error: No se encuentra un repositorio Git"
    exit 1
fi

HOOKS_DIR="$REPO_ROOT/.git/hooks"
SOURCE_HOOK="$REPO_ROOT/.githooks/pre-commit"
TARGET_HOOK="$HOOKS_DIR/pre-commit"

# Verificar que existe el directorio de hooks
if [ ! -d "$HOOKS_DIR" ]; then
    echo "✗ Error: No existe el directorio .git/hooks"
    exit 1
fi

# Verificar que existe el hook source
if [ ! -f "$SOURCE_HOOK" ]; then
    echo "✗ Error: No se encuentra el hook en .githooks/pre-commit"
    exit 1
fi

# Copiar el hook
echo "Instalando hook pre-commit..."
cp "$SOURCE_HOOK" "$TARGET_HOOK"

# Dar permisos de ejecución
chmod +x "$TARGET_HOOK"

echo "✓ Hook pre-commit instalado correctamente"
echo ""
echo "Configurando Git para usar .githooks..."

# Configurar Git para usar el directorio .githooks
git config core.hooksPath .githooks

echo "✓ Git configurado para usar .githooks"
echo ""
echo "================================================"
echo "  Instalación completada exitosamente"
echo "================================================"
echo ""
echo "A partir de ahora, cada vez que hagas un commit,"
echo "la versión se incrementará automáticamente."
echo ""
echo "Comandos útiles:"
echo "  - Ver versión actual:  python3 bump_version.py --check"
echo "  - Incremento manual:"
echo "    * Patch (1.0.0 -> 1.0.1): python3 bump_version.py --type patch"
echo "    * Minor (1.0.0 -> 1.1.0): python3 bump_version.py --type minor"
echo "    * Major (1.0.0 -> 2.0.0): python3 bump_version.py --type major"
echo ""
