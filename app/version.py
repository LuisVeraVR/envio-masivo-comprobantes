"""
Control de versión de la aplicación

Este archivo es la ÚNICA FUENTE DE VERDAD para la versión de la aplicación.
Para actualizar la versión, use el script: python update_version.py X.Y.Z
"""

__version__ = "1.1.2"
__author__ = "Luis Vera"
__app_name__ = "Sistema Envío Comprobantes"
__app_id__ = "comprobantes-app"

# Historial de versiones
VERSION_HISTORY = {
    "1.0.0": [
        "Versión inicial",
        "Envío de comprobantes con NIT obligatorio en asunto",
        "Procesamiento de Excel y ZIP",
        "Reportes de rebotados, bloqueados, inexistentes",
        "Sistema de actualizaciones automáticas",
        "Configuración de emails en copia (CC)",
        "Modo de pruebas"
    ],
    "1.1.0": [
        "Mejoras en la interfaz de usuario",
        "Sistema de pruebas mejorado",
        "Correcciones de bugs"
    ],
    "1.1.1": [
        "Plantilla descargable de Excel para correos",
        "Mejoras en la configuración SMTP",
        "Correcciones menores"
    ],
    "1.1.2": [
        "Manual de usuario expandido y detallado",
        "Matching de NITs preciso y estricto (soluciona problema de clientes de más)",
        "Detección automática de NITs similares con advertencias",
        "Sistema de versionado automático centralizado"
    ]
}

def get_version():
    """Retorna la versión actual"""
    return __version__

def get_app_info():
    """Retorna información completa de la app"""
    return {
        "version": __version__,
        "name": __app_name__,
        "author": __author__,
        "app_id": __app_id__
    }

def get_changelog(version=None):
    """
    Obtiene el changelog de una versión específica o de todas
    
    Args:
        version: Versión específica (opcional)
        
    Returns:
        Lista de cambios o diccionario completo
    """
    if version:
        return VERSION_HISTORY.get(version, [])
    return VERSION_HISTORY