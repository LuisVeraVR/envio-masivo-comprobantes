"""
Control de versión de la aplicación
"""

__version__ = "1.1.3"
__author__ = "Luis Vera"
__app_name__ = "Sistema Envío Comprobantes"
__app_id__ = "comprobantes-app"

# Historial de versiones
VERSION_HISTORY = {
    "1.1.3": [
        "Actualización automática de versión",
        "Fecha: 2025-10-30"
    ],

    "1.1.2": [
        "Prueba del sistema de versionado automático",
        "Fecha: 2025-10-30"
    ],

    "1.1.1": [
        "Versión actual",
        "Mejoras en el sistema"
    ],
    "1.0.0": [
        "Versión inicial",
        "Envío de comprobantes con NIT obligatorio en asunto",
        "Procesamiento de Excel y ZIP",
        "Reportes de rebotados, bloqueados, inexistentes",
        "Sistema de actualizaciones automáticas",
        "Configuración de emails en copia (CC)",
        "Modo de pruebas"
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