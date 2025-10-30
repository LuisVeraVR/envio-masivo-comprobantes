@echo off
REM Script de instalación de Git Hooks para Windows
REM Instala los hooks de versionado automático

echo ================================================
echo   Instalador de Git Hooks
echo   Sistema de Versionado Automatico
echo ================================================
echo.

REM Obtener el directorio raíz del repositorio
for /f "delims=" %%i in ('git rev-parse --show-toplevel 2^>nul') do set REPO_ROOT=%%i

if "%REPO_ROOT%"=="" (
    echo X Error: No se encuentra un repositorio Git
    pause
    exit /b 1
)

REM Convertir ruta de Git (/) a Windows (\)
set REPO_ROOT=%REPO_ROOT:/=\%

set HOOKS_DIR=%REPO_ROOT%\.git\hooks
set SOURCE_HOOK=%REPO_ROOT%\.githooks\pre-commit
set TARGET_HOOK=%HOOKS_DIR%\pre-commit

REM Verificar que existe el directorio de hooks
if not exist "%HOOKS_DIR%" (
    echo X Error: No existe el directorio .git\hooks
    pause
    exit /b 1
)

REM Verificar que existe el hook source
if not exist "%SOURCE_HOOK%" (
    echo X Error: No se encuentra el hook en .githooks\pre-commit
    pause
    exit /b 1
)

REM Copiar el hook
echo Instalando hook pre-commit...
copy /Y "%SOURCE_HOOK%" "%TARGET_HOOK%" >nul

echo + Hook pre-commit instalado correctamente
echo.
echo Configurando Git para usar .githooks...

REM Configurar Git para usar el directorio .githooks
git config core.hooksPath .githooks

echo + Git configurado para usar .githooks
echo.
echo ================================================
echo   Instalacion completada exitosamente
echo ================================================
echo.
echo A partir de ahora, cada vez que hagas un commit,
echo la version se incrementara automaticamente.
echo.
echo Comandos utiles:
echo   - Ver version actual:  python bump_version.py --check
echo   - Incremento manual:
echo     * Patch (1.0.0 -^> 1.0.1): python bump_version.py --type patch
echo     * Minor (1.0.0 -^> 1.1.0): python bump_version.py --type minor
echo     * Major (1.0.0 -^> 2.0.0): python bump_version.py --type major
echo.
pause
