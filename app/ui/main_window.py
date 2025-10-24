"""
Ventana principal de la aplicación
Contiene el TabWidget con todas las pestañas
"""

from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QStatusBar,
    QMenuBar,
    QMenu,
    QMessageBox,
    QLabel,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon
from app.version import __version__, __app_name__
from app.config import ConfigManager
from app.database.models import Database
from app.utils.logger import get_logger


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""

    def __init__(self):
        """Inicializa la ventana principal"""
        super().__init__()

        # Inicializar componentes
        self.config = ConfigManager()
        self.db = Database()
        self.logger = get_logger(db_manager=self.db)

        # Configurar ventana
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.setMinimumSize(1000, 700)

        # Crear interfaz
        self._crear_menu()
        self._crear_interfaz()
        self._crear_barra_estado()

        # Verificar configuración inicial
        QTimer.singleShot(100, self._verificar_configuracion_inicial)

        self.logger.info(
            f"Aplicación iniciada - Versión {__version__}", modulo="MainWindow"
        )

    def _crear_menu(self):
        """Crea la barra de menú"""
        menubar = self.menuBar()

        # Menú Archivo
        menu_archivo = menubar.addMenu("&Archivo")

        accion_salir = QAction("&Salir", self)
        accion_salir.setShortcut("Ctrl+Q")
        accion_salir.triggered.connect(self.close)
        menu_archivo.addAction(accion_salir)

        # Menú Herramientas
        menu_herramientas = menubar.addMenu("&Herramientas")

        accion_limpiar_logs = QAction("Limpiar logs antiguos", self)
        accion_limpiar_logs.triggered.connect(self._limpiar_logs)
        menu_herramientas.addAction(accion_limpiar_logs)

        accion_ver_logs = QAction("Ver carpeta de logs", self)
        accion_ver_logs.triggered.connect(self._abrir_carpeta_logs)
        menu_herramientas.addAction(accion_ver_logs)

        accion_ver_reportes = QAction("Ver carpeta de reportes", self)
        accion_ver_reportes.triggered.connect(self._abrir_carpeta_reportes)
        menu_herramientas.addAction(accion_ver_reportes)

        menu_herramientas.addSeparator()

        accion_verificar_smtp = QAction("Probar conexión SMTP", self)
        accion_verificar_smtp.triggered.connect(self._probar_conexion_smtp)
        menu_herramientas.addAction(accion_verificar_smtp)

        # Menú Ayuda
        menu_ayuda = menubar.addMenu("A&yuda")

        accion_acerca = QAction("Acerca de...", self)
        accion_acerca.triggered.connect(self._mostrar_acerca_de)
        menu_ayuda.addAction(accion_acerca)

        accion_manual = QAction("Manual de usuario", self)
        accion_manual.triggered.connect(self._mostrar_manual)
        menu_ayuda.addAction(accion_manual)

    def _crear_interfaz(self):
        """Crea la interfaz principal con pestañas"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Crear TabWidget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)

        # Importar pestañas
        from app.ui.tabs.envio_tab import EnvioTab
        from app.ui.tabs.reportes_tab import ReportesTab
        from app.ui.tabs.pruebas_tab import PruebasTab
        from app.ui.tabs.configuracion_tab import ConfiguracionTab

        # Crear pestañas
        self.tab_envio = EnvioTab(self.config, self.db, self.logger)
        self.tab_reportes = ReportesTab(self.config, self.db, self.logger)
        self.tab_pruebas = PruebasTab(self.config, self.db, self.logger)
        self.tab_configuracion = ConfiguracionTab(self.config, self.db, self.logger)

        # Agregar pestañas al TabWidget
        self.tab_widget.addTab(self.tab_envio, "📧 Envío de Comprobantes")
        self.tab_widget.addTab(self.tab_reportes, "📊 Reportes")
        self.tab_widget.addTab(self.tab_pruebas, "🧪 Ambiente de Pruebas")
        self.tab_widget.addTab(self.tab_configuracion, "⚙️ Configuración")

        # Conectar señales
        self.tab_configuracion.configuracion_actualizada.connect(
            self._on_configuracion_actualizada
        )

        layout.addWidget(self.tab_widget)

    def _crear_barra_estado(self):
        """Crea la barra de estado"""
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Label de estado SMTP
        self.label_smtp = QLabel()
        self._actualizar_estado_smtp()
        self.statusBar.addPermanentWidget(self.label_smtp)

        # Label de modo prueba
        self.label_modo_prueba = QLabel()
        self._actualizar_estado_modo_prueba()
        self.statusBar.addPermanentWidget(self.label_modo_prueba)

        # Mensaje inicial
        self.statusBar.showMessage("Listo", 3000)

    def _actualizar_estado_smtp(self):
        """Actualiza el indicador de estado SMTP"""
        if self.config.is_smtp_configured():
            smtp = self.config.get_smtp_config()
            self.label_smtp.setText(f"✓ SMTP: {smtp['username']}")
            self.label_smtp.setStyleSheet("color: green; padding: 2px 5px;")
        else:
            self.label_smtp.setText("⚠ SMTP no configurado")
            self.label_smtp.setStyleSheet("color: orange; padding: 2px 5px;")

    def _actualizar_estado_modo_prueba(self):
        """Actualiza el indicador de modo prueba"""
        if self.config.is_test_mode():
            self.label_modo_prueba.setText("🧪 MODO PRUEBA")
            self.label_modo_prueba.setStyleSheet(
                "background-color: #FFA500; color: white; font-weight: bold; "
                "padding: 2px 8px; border-radius: 3px;"
            )
        else:
            self.label_modo_prueba.setText("")
            self.label_modo_prueba.setStyleSheet("")

    def _verificar_configuracion_inicial(self):
        """Verifica si es necesario configurar la aplicación por primera vez"""
        if not self.config.is_smtp_configured():
            respuesta = QMessageBox.question(
                self,
                "Configuración inicial",
                "No se ha configurado el servidor SMTP.\n\n"
                "¿Desea configurarlo ahora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if respuesta == QMessageBox.StandardButton.Yes:
                self.tab_widget.setCurrentWidget(self.tab_configuracion)

    def _on_configuracion_actualizada(self):
        """Callback cuando se actualiza la configuración"""
        self._actualizar_estado_smtp()
        self._actualizar_estado_modo_prueba()
        self.statusBar.showMessage("Configuración actualizada", 3000)

    def _limpiar_logs(self):
        """Limpia logs antiguos"""
        respuesta = QMessageBox.question(
            self,
            "Limpiar logs",
            "¿Desea eliminar los logs más antiguos que 30 días?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                self.logger.limpiar_logs_antiguos(30)
                QMessageBox.information(
                    self,
                    "Logs limpiados",
                    "Los logs antiguos han sido eliminados correctamente.",
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al limpiar logs: {str(e)}")

    def _abrir_carpeta_logs(self):
        """Abre la carpeta de logs en el explorador"""
        import os, subprocess, platform

        ruta = self.config.get("paths.logs", "logs/")
        os.makedirs(ruta, exist_ok=True)

        try:
            if platform.system() == "Windows":
                os.startfile(ruta)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir: {str(e)}")

    def _abrir_carpeta_reportes(self):
        """Abre la carpeta de reportes en el explorador"""
        import os, subprocess, platform

        ruta = self.config.get("paths.reports", "reportes/")
        os.makedirs(ruta, exist_ok=True)

        try:
            if platform.system() == "Windows":
                os.startfile(ruta)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir: {str(e)}")

    def _probar_conexion_smtp(self):
        """Prueba la conexión SMTP"""
        if not self.config.is_smtp_configured():
            QMessageBox.warning(
                self, "SMTP no configurado", "Primero debe configurar el servidor SMTP."
            )
            return

        from app.core.email_sender import EmailSender

        try:
            sender = EmailSender(self.config.get_smtp_config(), self.db, self.logger)
            exito, mensaje = sender.probar_conexion()

            if exito:
                QMessageBox.information(self, "Conexión exitosa", f"✓ {mensaje}")
            else:
                QMessageBox.critical(self, "Error de conexión", f"✗ {mensaje}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al probar conexión: {str(e)}")

    def _mostrar_acerca_de(self):
        """Muestra el diálogo 'Acerca de'"""
        texto = f"""
<h2>{__app_name__}</h2>
<p><b>Versión:</b> {__version__}</p>
<p>Sistema de envío masivo de comprobantes por correo electrónico</p>
<p><b>Soporte:</b> inteligenciadenegocios@correagro.com</p>
"""
        QMessageBox.about(self, f"Acerca de {__app_name__}", texto)

    def _mostrar_manual(self):
        """Muestra el manual de usuario"""
        texto = """
<h3>1. Configuración inicial</h3>
<p>Configure SMTP y emails en copia en la pestaña <b>Configuración</b></p>

<h3>2. Envío de comprobantes</h3>
<p>1. Cargar Excel con clientes<br>2. Cargar ZIP con PDFs<br>3. Enviar</p>

<h3>3. Reportes</h3>
<p>Genere reportes de envíos en la pestaña <b>Reportes</b></p>
"""
        QMessageBox.information(self, "Manual de Usuario", texto)

    def closeEvent(self, event):
        """Maneja el evento de cierre de la ventana"""
        respuesta = QMessageBox.question(
            self,
            "Salir",
            "¿Está seguro que desea salir?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            self.logger.info("Aplicación cerrada", modulo="MainWindow")
            event.accept()
        else:
            event.ignore()
