"""
Sistema de actualizaciones automáticas desde GitHub
Verifica y descarga nuevas versiones de la aplicación
"""

import requests
import os
import zipfile
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path
from packaging import version as pkg_version
from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class UpdateChecker(QThread):
    """Thread para verificar actualizaciones en segundo plano"""
    
    # Señales
    update_available = pyqtSignal(dict)  # info de la actualización
    no_update = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, current_version, github_repo):
        """
        Args:
            current_version: Versión actual (ej: "1.0.0")
            github_repo: Repositorio GitHub (ej: "usuario/repo")
        """
        super().__init__()
        self.current_version = current_version
        self.github_repo = github_repo
        self.api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
    
    def run(self):
        """Verifica si hay actualizaciones disponibles"""
        try:
            # Llamar a la API de GitHub
            response = requests.get(self.api_url, timeout=10)
            
            if response.status_code == 404:
                self.error.emit("No se encontraron releases en GitHub")
                return
            
            response.raise_for_status()
            release_data = response.json()
            
            # Extraer información
            latest_version = release_data['tag_name'].lstrip('v')
            download_url = None
            
            # Buscar el asset .exe o .zip
            for asset in release_data.get('assets', []):
                name = asset['name'].lower()
                if name.endswith('.exe') or name.endswith('.zip'):
                    download_url = asset['browser_download_url']
                    break
            
            if not download_url:
                self.error.emit("No se encontró archivo de actualización")
                return
            
            # Comparar versiones
            if pkg_version.parse(latest_version) > pkg_version.parse(self.current_version):
                update_info = {
                    'version': latest_version,
                    'url': download_url,
                    'release_notes': release_data.get('body', ''),
                    'published_at': release_data.get('published_at', ''),
                    'size': asset.get('size', 0)
                }
                self.update_available.emit(update_info)
            else:
                self.no_update.emit()
        
        except requests.RequestException as e:
            self.error.emit(f"Error de conexión: {str(e)}")
        except Exception as e:
            self.error.emit(f"Error inesperado: {str(e)}")


class UpdateDownloader(QThread):
    """Thread para descargar e instalar actualizaciones"""
    
    # Señales
    progress = pyqtSignal(int, int)  # bytes descargados, total
    finished = pyqtSignal(str)  # ruta del archivo descargado
    error = pyqtSignal(str)
    
    def __init__(self, download_url, filename):
        super().__init__()
        self.download_url = download_url
        self.filename = filename
        self.temp_dir = tempfile.gettempdir()
    
    def run(self):
        """Descarga el archivo de actualización"""
        try:
            response = requests.get(self.download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            file_path = os.path.join(self.temp_dir, self.filename)
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total_size)
            
            self.finished.emit(file_path)
        
        except Exception as e:
            self.error.emit(f"Error al descargar: {str(e)}")


class AutoUpdater:
    """Gestor principal de actualizaciones automáticas"""
    
    def __init__(self, parent, current_version, github_repo):
        """
        Args:
            parent: Widget padre (MainWindow)
            current_version: Versión actual de la app
            github_repo: Repositorio GitHub (formato: "usuario/repositorio")
        """
        self.parent = parent
        self.current_version = current_version
        self.github_repo = github_repo
    
    def check_for_updates(self, silent=False):
        """
        Verifica si hay actualizaciones disponibles
        
        Args:
            silent: Si es True, no muestra mensaje cuando no hay actualizaciones
        """
        self.silent = silent
        
        # Crear y configurar el thread
        self.checker = UpdateChecker(self.current_version, self.github_repo)
        self.checker.update_available.connect(self._on_update_available)
        self.checker.no_update.connect(lambda: self._on_no_update(silent))
        self.checker.error.connect(self._on_error)
        
        # Iniciar verificación
        if not silent:
            QMessageBox.information(
                self.parent,
                "Buscando actualizaciones",
                "Verificando si hay nuevas versiones disponibles..."
            )
        
        self.checker.start()
    
    def _on_update_available(self, update_info):
        """Callback cuando hay una actualización disponible"""
        version = update_info['version']
        notes = update_info['release_notes']
        size_mb = update_info['size'] / (1024 * 1024)
        
        mensaje = f"""
<h3>🎉 Nueva versión disponible: v{version}</h3>
<p><b>Versión actual:</b> v{self.current_version}</p>
<p><b>Tamaño:</b> {size_mb:.2f} MB</p>
<hr>
<h4>Novedades:</h4>
<p>{notes if notes else 'Ver detalles en GitHub'}</p>
<hr>
<p><small><b>Nota:</b> La aplicación se cerrará y reiniciará automáticamente después de actualizar.</small></p>
"""
        
        reply = QMessageBox.question(
            self.parent,
            "Actualización Disponible",
            mensaje,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._download_and_install(update_info)
    
    def _on_no_update(self, silent):
        """Callback cuando no hay actualizaciones"""
        if not silent:
            QMessageBox.information(
                self.parent,
                "Sin actualizaciones",
                f"Ya tienes la última versión (v{self.current_version})"
            )
    
    def _on_error(self, error_message):
        """Callback cuando hay un error"""
        if not self.silent:
            QMessageBox.warning(
                self.parent,
                "Error al verificar actualizaciones",
                f"No se pudo verificar actualizaciones:\n{error_message}\n\n"
                "Verifica tu conexión a internet o intenta más tarde."
            )
    
    def _download_and_install(self, update_info):
        """Descarga e instala la actualización"""
        url = update_info['url']
        filename = os.path.basename(url)
        
        # Crear diálogo de progreso
        progress_dialog = QProgressDialog(
            "Descargando actualización...",
            "Cancelar",
            0, 100,
            self.parent
        )
        progress_dialog.setWindowTitle("Actualizando")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setAutoClose(False)
        
        # Crear downloader
        self.downloader = UpdateDownloader(url, filename)
        
        def on_progress(downloaded, total):
            if total > 0:
                percent = int((downloaded / total) * 100)
                progress_dialog.setValue(percent)
                progress_dialog.setLabelText(
                    f"Descargando actualización...\n"
                    f"{downloaded / (1024*1024):.2f} MB / {total / (1024*1024):.2f} MB"
                )
        
        def on_finished(file_path):
            progress_dialog.close()
            self._install_update(file_path, filename)
        
        def on_error(error_msg):
            progress_dialog.close()
            QMessageBox.critical(
                self.parent,
                "Error de descarga",
                f"No se pudo descargar la actualización:\n{error_msg}"
            )
        
        # Conectar señales
        self.downloader.progress.connect(on_progress)
        self.downloader.finished.connect(on_finished)
        self.downloader.error.connect(on_error)
        
        # Manejar cancelación
        progress_dialog.canceled.connect(self.downloader.terminate)
        
        # Iniciar descarga
        self.downloader.start()
    
    def _install_update(self, file_path, filename):
        """Instala la actualización descargada"""
        try:
            if filename.endswith('.exe'):
                # Actualización .exe directa
                self._install_exe(file_path)
            elif filename.endswith('.zip'):
                # Actualización .zip (descomprimir y reemplazar)
                self._install_zip(file_path)
            else:
                QMessageBox.warning(
                    self.parent,
                    "Formato no soportado",
                    f"El formato de actualización no es compatible: {filename}"
                )
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Error de instalación",
                f"No se pudo instalar la actualización:\n{str(e)}"
            )
    
    def _install_exe(self, exe_path):
        """Instala una actualización .exe"""
        # Crear script de actualización
        current_exe = sys.executable if getattr(sys, 'frozen', False) else None
        
        if not current_exe:
            QMessageBox.warning(
                self.parent,
                "Actualización no disponible",
                "Las actualizaciones solo están disponibles en la versión ejecutable"
            )
            return
        
        # Script batch para Windows
        batch_script = f"""@echo off
echo Actualizando aplicacion...
timeout /t 2 /nobreak > nul
taskkill /F /IM "{os.path.basename(current_exe)}" > nul 2>&1
timeout /t 1 /nobreak > nul
copy /Y "{exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
        
        batch_path = os.path.join(tempfile.gettempdir(), "update_app.bat")
        with open(batch_path, 'w') as f:
            f.write(batch_script)
        
        QMessageBox.information(
            self.parent,
            "Instalando actualización",
            "La aplicación se cerrará y se actualizará automáticamente.\n"
            "Espera unos segundos a que se reinicie."
        )
        
        # Ejecutar script y cerrar aplicación
        subprocess.Popen(['cmd', '/c', batch_path], 
                        creationflags=subprocess.CREATE_NO_WINDOW)
        
        # Cerrar la aplicación
        self.parent.close()
    
    def _install_zip(self, zip_path):
        """Instala una actualización .zip"""
        try:
            # Extraer ZIP
            extract_dir = os.path.join(tempfile.gettempdir(), "app_update")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Buscar el .exe en el ZIP
            exe_files = list(Path(extract_dir).rglob("*.exe"))
            
            if not exe_files:
                QMessageBox.warning(
                    self.parent,
                    "Error",
                    "No se encontró archivo ejecutable en la actualización"
                )
                return
            
            # Instalar el .exe encontrado
            self._install_exe(str(exe_files[0]))
        
        except Exception as e:
            raise Exception(f"Error al procesar ZIP: {str(e)}")
