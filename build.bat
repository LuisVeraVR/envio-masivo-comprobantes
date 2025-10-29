@echo off
REM =====================================================
REM Script de Build - Sistema de Envío de Comprobantes
REM Genera el ejecutable usando PyInstaller
REM =====================================================

echo ========================================
echo   BUILD - Sistema Envio Comprobantes
echo ========================================
echo.

REM Verificar que PyInstaller esté instalado
python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller no esta instalado
    echo Instalando PyInstaller...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo instalar PyInstaller
        pause
        exit /b 1
    )
)

REM Limpiar builds anteriores
echo [1/5] Limpiando builds anteriores...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
echo     Limpieza completada

REM Verificar dependencias
echo.
echo [2/5] Verificando dependencias...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Error al instalar dependencias
    pause
    exit /b 1
)
echo     Dependencias verificadas

REM Construir ejecutable
echo.
echo [3/5] Construyendo ejecutable...
echo     Esto puede tomar varios minutos...
pyinstaller app.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo [ERROR] Error al construir ejecutable
    pause
    exit /b 1
)
echo     Ejecutable construido exitosamente

REM Crear carpetas necesarias
echo.
echo [4/5] Creando estructura de carpetas...
mkdir "dist\logs" 2>nul
mkdir "dist\data" 2>nul
mkdir "dist\reportes" 2>nul
mkdir "dist\temp" 2>nul
echo     Estructura creada

REM Copiar archivos adicionales (si existen)
echo.
echo [5/5] Copiando archivos adicionales...
if exist "README.md" copy "README.md" "dist\" >nul
if exist "config.json.example" copy "config.json.example" "dist\" >nul
echo     Archivos copiados

echo.
echo ========================================
echo   BUILD COMPLETADO EXITOSAMENTE
echo ========================================
echo.
echo Ejecutable generado en: dist\SistemaEnvioComprobantes.exe
echo.
echo Siguientes pasos:
echo 1. Probar el ejecutable en dist\
echo 2. Crear release en GitHub con el .exe
echo 3. Las operativas recibirán notificación de actualización
echo.
pause
