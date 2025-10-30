# 📧 Sistema de Envío Masivo de Comprobantes

Sistema de escritorio para envío masivo de comprobantes por correo electrónico con seguimiento de estado y reportes.

## 🚀 Características

- **Envío masivo** de comprobantes PDF por correo electrónico
- **Matching preciso** de NITs entre Excel y archivos PDF
- **Detección automática** de NITs similares con advertencias
- **Reportes detallados** de envíos exitosos y fallidos
- **Modo de pruebas** para validar antes de enviar
- **Configuración SMTP** flexible (Gmail, Outlook, etc.)
- **Actualizaciones automáticas** desde GitHub
- **Manual de usuario** completo e interactivo

## 📦 Instalación

### Desde código fuente:
```bash
# Clonar repositorio
git clone https://github.com/LuisVeraVR/envio-masivo-comprobantes.git
cd envio-masivo-comprobantes

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python app/main.py
```

### Desde ejecutable:
Descarga el ejecutable (.exe) desde [Releases](https://github.com/LuisVeraVR/envio-masivo-comprobantes/releases)

## 📖 Uso Básico

1. **Configurar SMTP** en la pestaña Configuración
2. **Preparar Excel** con columnas: NIT, Nombre, Email
3. **Preparar ZIP** con archivos PDF (nombre debe contener el NIT)
4. **Cargar archivos** en la pestaña Envío de Comprobantes
5. **Revisar coincidencias** antes de enviar
6. **Enviar correos** y revisar reportes

Para más detalles, consulta el **Manual de Usuario** desde el menú Ayuda de la aplicación.

## 🔧 Desarrollo

### Actualizar versión

El proyecto usa un sistema de versionado automático centralizado:

```bash
# Ver versión actual
python update_version.py --show

# Incrementar versión automáticamente
python update_version.py --patch    # Correcciones de bugs
python update_version.py --minor    # Nuevas funcionalidades
python update_version.py --major    # Cambios incompatibles

# Actualizar con notas y crear tag
python update_version.py --patch --notes --tag --push
```

Ver [VERSION_GUIDE.md](VERSION_GUIDE.md) para más detalles sobre el sistema de versionado.

### Estructura del proyecto

```
envio-masivo-comprobantes/
├── app/
│   ├── core/           # Lógica principal (Excel, ZIP, Email)
│   ├── database/       # Base de datos y modelos
│   ├── ui/            # Interfaz gráfica (PyQt6)
│   ├── utils/         # Utilidades (validación, logging, actualizaciones)
│   ├── config.py      # Gestor de configuración
│   ├── version.py     # ⭐ Fuente única de verdad para la versión
│   └── main.py        # Punto de entrada
├── config.json        # Configuración de la aplicación
├── update_version.py  # ⭐ Script de actualización de versión
└── VERSION_GUIDE.md   # ⭐ Guía de versionado
```

### Comandos útiles

```bash
# Ejecutar aplicación
python app/main.py

# Ejecutar con logging detallado
python app/main.py --debug

# Limpiar archivos temporales
rm -rf temp/ logs/ __pycache__/ **/__pycache__/

# Compilar a ejecutable (PyInstaller)
pyinstaller --onefile --windowed app/main.py
```

## 📋 Requisitos del Sistema

- Python 3.8+
- Windows 10/11, macOS 10.14+, o Linux
- Conexión a internet (para envío de correos)
- Servidor SMTP configurado

## 🐛 Solución de Problemas

### Error: "clientes de más"
- Asegúrate de que los NITs en el Excel coincidan **EXACTAMENTE** con los del ZIP
- Revisa los logs para ver advertencias sobre NITs similares
- El sistema ahora usa matching exacto por defecto

### Error: "SMTP authentication failed"
- Gmail requiere **contraseña de aplicación** (no tu contraseña normal)
- Verifica que el servidor SMTP y puerto sean correctos
- Usa la opción "Probar conexión SMTP" en el menú Herramientas

### Error: "No se encontraron archivos PDF"
- Verifica que el ZIP contenga archivos PDF
- Los nombres de archivo deben contener el NIT
- Formatos soportados: `NIT 12345678.pdf`, `NIT._ 12345678.pdf`, etc.

Para más ayuda, consulta el Manual de Usuario en la aplicación.

## 📄 Licencia

Copyright © 2024 Luis Vera - CORREAGRO S.A.

## 🆘 Soporte

Para reportar problemas o solicitar funcionalidades:
- **Email**: inteligenciadenegocios@correagro.com
- **Issues**: https://github.com/LuisVeraVR/envio-masivo-comprobantes/issues

## 📝 Changelog

Ver [app/version.py](app/version.py) para el historial completo de versiones.

### Versión 1.1.2 (Actual)
- Manual de usuario expandido y detallado
- Matching de NITs preciso y estricto (soluciona problema de clientes de más)
- Detección automática de NITs similares con advertencias
- Sistema de versionado automático centralizado
