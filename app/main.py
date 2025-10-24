"""
Punto de entrada principal de la aplicación
Sistema de Envío de Comprobantes
"""

import sys
import os

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from app.ui.main_window import MainWindow
from app.version import __version__, __app_name__
from app.utils.logger import get_logger


def verificar_dependencias():
    """Verifica que todas las dependencias estén instaladas"""
    dependencias_faltantes = []
    
    try:
        import openpyxl
    except ImportError:
        dependencias_faltantes.append("openpyxl")
    
    try:
        import pandas
    except ImportError:
        dependencias_faltantes.append("pandas")
    
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        dependencias_faltantes.append("cryptography")
    
    if dependencias_faltantes:
        return False, dependencias_faltantes
    
    return True, []


def main():
    """Función principal"""
    # Crear aplicación
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    
    # Estilo
    app.setStyle('Fusion')
    
    # Verificar dependencias
    exito, faltantes = verificar_dependencias()
    if not exito:
        QMessageBox.critical(
            None, "Dependencias faltantes",
            f"Faltan dependencias:\n\n{', '.join(faltantes)}\n\n"
            "Ejecute: pip install -r requirements.txt"
        )
        sys.exit(1)
    
    # Inicializar logger
    try:
        logger = get_logger()
        logger.info(f"Iniciando {__app_name__} v{__version__}", modulo="Main")
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Error al inicializar logs:\n{str(e)}")
        sys.exit(1)
    
    # Crear ventana principal
    try:
        ventana = MainWindow()
        ventana.show()
    except Exception as e:
        logger.error(f"Error al crear ventana: {e}", modulo="Main", exc_info=True)
        QMessageBox.critical(None, "Error crítico", 
                           f"Error al iniciar:\n{str(e)}\n\nRevise los logs.")
        sys.exit(1)
    
    # Ejecutar aplicación
    sys.exit(app.exec())


if __name__ == "__main__":
    main()