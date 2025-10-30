@echo off
echo ========================================
echo   EMPAQUETADO PARA DISTRIBUCION
echo ========================================

set VERSION=1.1.3
set PACKAGE_NAME=SistemaEnvioComprobantes_v%VERSION%

echo.
echo [1/3] Creando carpeta de distribucion...
mkdir "release\%PACKAGE_NAME%" 2>nul
mkdir "release\%PACKAGE_NAME%\logs" 2>nul
mkdir "release\%PACKAGE_NAME%\data" 2>nul
mkdir "release\%PACKAGE_NAME%\reportes" 2>nul
mkdir "release\%PACKAGE_NAME%\temp" 2>nul

echo [2/3] Copiando archivos...
copy "dist\SistemaEnvioComprobantes.exe" "release\%PACKAGE_NAME%\" >nul
if exist "README.md" copy "README.md" "release\%PACKAGE_NAME%\MANUAL_USUARIO.txt" >nul
if exist "config.json.example" copy "config.json.example" "release\%PACKAGE_NAME%\" >nul

echo [3/3] Creando archivo ZIP...
powershell Compress-Archive -Path "release\%PACKAGE_NAME%\*" -DestinationPath "release\%PACKAGE_NAME%.zip" -Force

echo.
echo ========================================
echo   PAQUETE LISTO: release\%PACKAGE_NAME%.zip
echo ========================================
pause