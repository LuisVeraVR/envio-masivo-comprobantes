REM Script de verificación (verificar_sistema.bat)
@echo off
echo Verificando requisitos del sistema...
echo.

REM Verificar Windows
ver | findstr /i "Windows" >nul
if %errorlevel% neq 0 (
    echo [ERROR] Sistema operativo no compatible
    exit /b 1
)

REM Verificar espacio en disco (al menos 500MB)
for /f "tokens=3" %%a in ('dir /-c ^| find "bytes free"') do set free=%%a
if %free% LSS 500000000 (
    echo [ADVERTENCIA] Espacio en disco bajo
)

REM Verificar permisos de escritura
echo test > test_permisos.tmp 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] No tiene permisos de escritura
    exit /b 1
)
del test_permisos.tmp 2>nul

echo [OK] Sistema compatible
echo.
pause
```

#### **2.2. Proceso de Instalación Paso a Paso**

**Opción A: Instalación Manual (Recomendada para pocas operativas)**

1. **Descomprimir** el archivo ZIP en una ubicación permanente:
```
   C:\SistemaEnvioComprobantes\