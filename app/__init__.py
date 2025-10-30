"""
Sistema de Envío de Comprobantes
Aplicación de escritorio para envío masivo de comprobantes por correo

IMPORTANTE: La versión se importa desde app.version (fuente única de verdad)
"""

# Importar versión desde el archivo central
from app.version import __version__, __author__, __app_name__

__all__ = ['__version__', '__author__', '__app_name__']