"""
Módulo de Auto-Actualización (PyQt6)
Verifica y descarga actualizaciones desde GitHub Releases
"""

from __future__ import annotations

import requests
import os
import sys
import subprocess
import tempfile
import logging
from typing import Optional, Callable

# UI (PyQt6)
try:
    from PyQt6.QtWidgets import QMessageBox, QWidget, QProgressDialog
    from PyQt6.QtCore import Qt
    _HAS_QT = True
except Exception:
    _HAS_QT = False

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


class AutoUpdater:
    """
    Maneja la verificación e instalación de actualizaciones.

    Constructor esperado por MainWindow:
        AutoUpdater(parent: QWidget | None, current_version: str, github_repo: str)

    Uso:
        self.updater = AutoUpdater(self, __version__, "usuario/repo")
        self.updater.check_for_updates(silent=True)   # al iniciar
        self.updater.check_for_updates(silent=False)  # desde menú "Buscar actualizaciones"
    """

    def __init__(self, parent: Optional["QWidget"], current_version: str, github_repo: str):
        if not github_repo or "/" not in github_repo:
            raise ValueError("github_repo debe ser 'owner/repo'")

        self.parent = parent
        self.current_version = (current_version or "").lstrip("v")
        self.github_repo = github_repo
        self.api_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"

    # ---------------- API principal ---------------- #

    def check_for_updates(self, silent: bool = True) -> None:
        """
        Verifica si hay una nueva versión. Si hay, pregunta al usuario y, si acepta,
        descarga e instala. Si `silent=True` y no hay actualización, no muestra diálogos.
        """
        info = self._fetch_latest_release()
        if info.get("error"):
            logger.warning(f"No se pudo verificar actualizaciones: {info['error']}")
            if not silent and _HAS_QT and self.parent:
                QMessageBox.warning(self.parent, "Actualizaciones",
                                    f"No se pudo verificar actualizaciones:\n{info['error']}")
            return

        if not info.get("available"):
            logger.info("La aplicación está actualizada")
            if not silent and _HAS_QT and self.parent:
                QMessageBox.information(self.parent, "Actualizaciones", "Ya estás en la última versión.")
            return

        # Hay actualización disponible
        version = info["version"]
        notes = info.get("release_notes", "Sin descripción")
        download_url = info["download_url"]

        if self._confirm_update_dialog(version, notes):
            try:
                self._download_and_install(download_url)
            except Exception as e:
                self._show_error_dialog(f"Error al actualizar: {e}")

    # ---------------- Lógica interna ---------------- #

    def _fetch_latest_release(self) -> dict:
        try:
            logger.info(f"Verificando actualizaciones... Versión actual: {self.current_version}")
            resp = requests.get(self.api_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            latest_version = str(data.get("tag_name", "")).lstrip("v")
            logger.info(f"Última versión en GitHub: {latest_version}")

            if self._is_newer_version(latest_version):
                url = self._get_exe_download_url(data)
                if not url:
                    return {"available": False, "error": "No se encontró ejecutable .exe en el release"}
                return {
                    "available": True,
                    "version": latest_version,
                    "download_url": url,
                    "release_notes": data.get("body", "Sin descripción")
                }

            return {"available": False}
        except requests.exceptions.RequestException as e:
            return {"available": False, "error": f"Error de conexión: {e}"}
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _is_newer_version(self, latest: str) -> bool:
        try:
            cur = [int(x) for x in (self.current_version or "0.0.0").split(".")]
            lat = [int(x) for x in (latest or "0.0.0").split(".")]
            # Normaliza longitudes
            n = max(len(cur), len(lat))
            cur += [0] * (n - len(cur))
            lat += [0] * (n - len(lat))
            return lat > cur
        except Exception:
            return False

    def _get_exe_download_url(self, release_data: dict) -> Optional[str]:
        for asset in release_data.get("assets", []):
            name = asset.get("name", "")
            if name.lower().endswith(".exe"):
                return asset.get("browser_download_url")
        return None

    # ---------------- Descarga & instalación ---------------- #

    def _download_and_install(self, url: str) -> None:
        logger.info(f"Descargando actualización: {url}")

        # Descarga con barra de progreso (si hay Qt)
        tmp_dir = tempfile.gettempdir()
        tmp_exe = os.path.join(tmp_dir, "AppUpdate_new.exe")

        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", "0") or 0)

            progress = None
            if _HAS_QT and self.parent and total > 0:
                progress = QProgressDialog("Descargando actualización...", "Cancelar", 0, 100, self.parent)
                progress.setWindowModality(Qt.WindowModality.ApplicationModal)
                progress.setMinimumDuration(0)
                progress.setValue(0)

            downloaded = 0
            with open(tmp_exe, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 64):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress and total:
                        progress.setValue(int(downloaded * 100 / total))
                        if progress.wasCanceled():
                            raise Exception("Descarga cancelada por el usuario")

            if progress:
                progress.setValue(100)

        self._install_update(tmp_exe)

    def _install_update(self, new_exe_path: str) -> None:
        # Si está congelado (PyInstaller), reemplaza el exe actual.
        if getattr(sys, "frozen", False):
            current_exe = sys.executable
        else:
            logger.warning("Modo desarrollo detectado: se omite reemplazo de .exe (solo simulación).")
            return

        current_dir = os.path.dirname(current_exe)
        update_script = os.path.join(current_dir, "update_temp.bat")

        script = f"""@echo off
echo Instalando actualización...
timeout /t 2 /nobreak >nul

:retry
del /f /q "{current_exe}" 2>nul
if exist "{current_exe}" (
    timeout /t 1 /nobreak >nul
    goto retry
)

move /y "{new_exe_path}" "{current_exe}"

start "" "{current_exe}"

timeout /t 1 /nobreak >nul
del /f /q "%~f0"
"""

        with open(update_script, "w", encoding="utf-8") as fh:
            fh.write(script)

        logger.info("Lanzando script de actualización y cerrando la aplicación...")
        # Sin ventana de consola
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW
        subprocess.Popen(update_script, shell=True, creationflags=flags)
        # Salir de la app actual
        sys.exit(0)

    # ---------------- Diálogos ---------------- #

    def _confirm_update_dialog(self, version: str, notes: str) -> bool:
        msg = (
            f"Nueva versión disponible: v{version}\n\n"
            f"Versión actual: v{self.current_version}\n\n"
            f"Cambios:\n{notes[:600]}{'...' if len(notes) > 600 else ''}\n\n"
            f"¿Desea actualizar ahora? La aplicación se reiniciará."
        )

        if _HAS_QT and self.parent:
            box = QMessageBox(self.parent)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("Actualización disponible")
            box.setText(msg)
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            return box.exec() == QMessageBox.StandardButton.Yes

        # Fallback consola
        logger.info(msg)
        try:
            return input("Actualizar? (s/n): ").strip().lower() == "s"
        except Exception:
            return False

    def _show_error_dialog(self, message: str) -> None:
        if _HAS_QT and self.parent:
            QMessageBox.critical(self.parent, "Error de actualización", message)
        else:
            logger.error(message)
