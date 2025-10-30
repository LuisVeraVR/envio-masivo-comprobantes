"""
Módulo de Auto-Actualización
Verifica y descarga actualizaciones desde GitHub Releases
"""

import requests
import os
import sys
import subprocess
import tempfile
import logging
from pathlib import Path

# ==================== CONFIGURACIÓN ====================
GITHUB_REPO = "LuisVeraVR/envio-masivo-comprobantes"  # ⚠️ CAMBIAR ESTO
CURRENT_VERSION = "1.1.1"  # ⚠️ Actualizar en cada release
# =======================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoUpdater:
    """Maneja la verificación e instalación de actualizaciones"""
    
    def __init__(self):
        self.api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        self.current_version = CURRENT_VERSION
        
    def check_for_updates(self):
        """
        Verifica si hay una nueva versión disponible
        
        Returns:
            dict: {
                'available': bool,
                'version': str,
                'download_url': str,
                'release_notes': str,
                'error': str (opcional)
            }
        """
        try:
            logger.info(f"Verificando actualizaciones... Versión actual: {self.current_version}")
            
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            latest_version = release_data['tag_name'].replace('v', '')
            
            logger.info(f"Última versión en GitHub: {latest_version}")
            
            # Comparar versiones
            if self._is_newer_version(latest_version):
                download_url = self._get_exe_download_url(release_data)
                
                if not download_url:
                    return {
                        'available': False,
                        'error': 'No se encontró ejecutable en el release'
                    }
                
                return {
                    'available': True,
                    'version': latest_version,
                    'download_url': download_url,
                    'release_notes': release_data.get('body', 'Sin descripción')
                }
            
            return {'available': False}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red al verificar actualizaciones: {e}")
            return {'available': False, 'error': f'Error de conexión: {e}'}
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return {'available': False, 'error': str(e)}
    
    def _is_newer_version(self, latest_version):
        """Compara versiones (formato: X.Y.Z)"""
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            latest_parts = [int(x) for x in latest_version.split('.')]
            
            return latest_parts > current_parts
        except:
            return False
    
    def _get_exe_download_url(self, release_data):
        """Extrae URL del ejecutable .exe del release"""
        for asset in release_data.get('assets', []):
            if asset['name'].endswith('.exe'):
                return asset['browser_download_url']
        return None
    
    def download_and_install(self, download_url, progress_callback=None):
        """
        Descarga e instala la actualización
        
        Args:
            download_url (str): URL del ejecutable
            progress_callback (callable): Función para reportar progreso (opcional)
        """
        try:
            logger.info(f"Descargando actualización desde: {download_url}")
            
            # Descargar a archivo temporal
            temp_dir = tempfile.gettempdir()
            temp_exe = os.path.join(temp_dir, 'SistemaEnvioComprobantes_new.exe')
            
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(temp_exe, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            progress_callback(progress)
            
            logger.info("Descarga completada. Preparando instalación...")
            
            # Crear script de actualización
            self._install_update(temp_exe)
            
        except Exception as e:
            logger.error(f"Error durante la actualización: {e}")
            raise
    
    def _install_update(self, new_exe_path):
        """Crea script batch para reemplazar ejecutable y reiniciar"""
        
        # Obtener ruta del ejecutable actual
        if getattr(sys, 'frozen', False):
            # Ejecutándose como .exe
            current_exe = sys.executable
        else:
            # Ejecutándose como script Python (desarrollo)
            logger.warning("Ejecutando en modo desarrollo, actualización simulada")
            return
        
        current_dir = os.path.dirname(current_exe)
        update_script = os.path.join(current_dir, 'update_temp.bat')
        
        # Crear script de actualización
        script_content = f"""@echo off
echo Instalando actualizacion...
timeout /t 2 /nobreak >nul

REM Intentar eliminar ejecutable anterior
:retry
del /f /q "{current_exe}" 2>nul
if exist "{current_exe}" (
    timeout /t 1 /nobreak >nul
    goto retry
)

REM Mover nuevo ejecutable
move /y "{new_exe_path}" "{current_exe}"

REM Reiniciar aplicación
start "" "{current_exe}"

REM Auto-eliminar este script
timeout /t 1 /nobreak >nul
del /f /q "%~f0"
"""
        
        with open(update_script, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        logger.info("Ejecutando script de actualización y cerrando aplicación...")
        
        # Ejecutar script y cerrar aplicación actual
        subprocess.Popen(update_script, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        sys.exit(0)


# ==================== FUNCIÓN PRINCIPAL ====================

def check_and_notify_update(parent_window=None):
    """
    Función principal para verificar actualizaciones al iniciar la app
    
    Args:
        parent_window: Ventana principal de la aplicación (Tkinter, PyQt, etc.)
    
    Returns:
        bool: True si se está instalando actualización, False si no hay o se canceló
    """
    updater = AutoUpdater()
    update_info = updater.check_for_updates()
    
    if not update_info.get('available'):
        if update_info.get('error'):
            logger.warning(f"No se pudo verificar actualizaciones: {update_info['error']}")
        else:
            logger.info("La aplicación está actualizada")
        return False
    
    # Hay actualización disponible
    version = update_info['version']
    notes = update_info['release_notes']
    
    # Mostrar diálogo (detectar framework UI)
    user_accepted = _show_update_dialog(version, notes, parent_window)
    
    if user_accepted:
        try:
            # Descargar e instalar
            updater.download_and_install(update_info['download_url'])
            return True
        except Exception as e:
            _show_error_dialog(f"Error al actualizar: {e}", parent_window)
            return False
    
    return False


def _show_update_dialog(version, notes, parent=None):
    """Muestra diálogo de actualización (detecta framework automáticamente)"""
    
    message = f"""
Nueva versión disponible: v{version}

Versión actual: v{CURRENT_VERSION}

Cambios:
{notes[:300]}{'...' if len(notes) > 300 else ''}

¿Desea actualizar ahora?
La aplicación se reiniciará automáticamente.
    """.strip()
    
    # Intentar con tkinter (más común)
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        if parent is None:
            root = tk.Tk()
            root.withdraw()
            result = messagebox.askyesno("Actualización Disponible", message, icon='info')
            root.destroy()
        else:
            result = messagebox.askyesno("Actualización Disponible", message, icon='info', parent=parent)
        
        return result
        
    except ImportError:
        pass
    
    # Intentar con PyQt5
    try:
        from PyQt5.QtWidgets import QMessageBox
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Actualización Disponible")
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        return msg_box.exec_() == QMessageBox.Yes
        
    except ImportError:
        pass
    
    # Fallback: consola
    logger.info(message)
    response = input("Actualizar? (s/n): ").lower()
    return response == 's'


def _show_error_dialog(message, parent=None):
    """Muestra diálogo de error"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        if parent is None:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error de Actualización", message)
            root.destroy()
        else:
            messagebox.showerror("Error de Actualización", message, parent=parent)
    except:
        logger.error(message)


# ==================== TESTING ====================

if __name__ == "__main__":
    """Ejecutar para probar el módulo de actualización"""
    print("Probando módulo de actualización...")
    check_and_notify_update()