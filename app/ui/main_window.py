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
    QMessageBox,
    QLabel,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from app.version import __version__, __app_name__
from app.config import ConfigManager
from app.database.models import Database
from app.utils.logger import get_logger
from app.utils.updater import AutoUpdater


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""

    def __init__(self):
        """Inicializa la ventana principal"""
        super().__init__()

        # Inicializar componentes
        self.config = ConfigManager()
        self.db = Database()
        self.logger = get_logger(db_manager=self.db)

        # Importante: asegurar que exista antes de crear el menú
        self.updater = None

        # Configurar ventana
        self.setWindowTitle(f"{__app_name__} v{__version__}")
        self.setMinimumSize(1000, 700)

        # Crear interfaz
        self._crear_menu()
        self._crear_interfaz()
        self._crear_barra_estado()

        # ✅ Inicializar sistema de actualizaciones
        self._inicializar_actualizaciones()

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

        # 🔄 Buscar actualizaciones (siempre visible)
        accion_actualizar = QAction("🔄 Buscar Actualizaciones", self)
        accion_actualizar.triggered.connect(self._buscar_actualizaciones)
        menu_ayuda.addAction(accion_actualizar)
        menu_ayuda.addSeparator()

        accion_acerca = QAction("Acerca de...", self)
        accion_acerca.triggered.connect(self._mostrar_acerca_de)
        menu_ayuda.addAction(accion_acerca)

        accion_manual = QAction("Manual de usuario", self)
        accion_manual.triggered.connect(self._mostrar_manual)
        menu_ayuda.addAction(accion_manual)

    def _buscar_actualizaciones(self):
        """Handler del menú Ayuda → Buscar Actualizaciones"""
        try:
            if self.updater:
                self.updater.check_for_updates(silent=False)
                return

            # Si no está inicializado aún, crear uno ad-hoc
            repo = self.config.get("update.github_repo", "")
            if not repo:
                QMessageBox.information(
                    self,
                    "Actualizaciones",
                    "El sistema de actualizaciones no está configurado (falta github_repo).",
                )
                return

            updater = AutoUpdater(self, __version__, repo)
            updater.check_for_updates(silent=False)
        except Exception as e:
            QMessageBox.critical(self, "Actualizaciones", f"Error al buscar actualizaciones: {e}")

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
        from PyQt6.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QPushButton

        # Crear diálogo personalizado para el manual
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Manual de Usuario")
        dialogo.setMinimumSize(700, 600)

        layout = QVBoxLayout()

        # Área de texto para el manual
        texto_manual = QTextEdit()
        texto_manual.setReadOnly(True)
        texto_manual.setHtml("""
<h2 style="color: #2c3e50;">📖 Manual de Usuario - Envío Masivo de Comprobantes</h2>

<h3 style="color: #3498db;">1. ⚙️ Configuración Inicial</h3>
<p><b>Antes de enviar comprobantes, debe configurar:</b></p>
<ul>
  <li><b>Servidor SMTP:</b> Vaya a <b>Configuración</b> y complete los datos de su servidor de correo
    <ul>
      <li>Gmail: smtp.gmail.com, puerto 587 (requiere contraseña de aplicación)</li>
      <li>Outlook: smtp.office365.com, puerto 587</li>
    </ul>
  </li>
  <li><b>Emails en copia (opcional):</b> Configure correos que recibirán copia de todos los envíos</li>
  <li><b>Modo prueba:</b> Active esta opción para hacer pruebas sin enviar correos reales</li>
</ul>

<h3 style="color: #3498db;">2. 📧 Preparación de Archivos</h3>

<p><b style="color: #e74c3c;">⚠️ IMPORTANTE - Formato del Excel:</b></p>
<ul>
  <li>El Excel debe contener las columnas: <b>NIT</b>, <b>Nombre</b> y <b>Email</b></li>
  <li>Los NITs deben estar <b>completos y correctos</b> (sin dígito verificador o con él, separado por guion)</li>
  <li>Ejemplos válidos: <code>900219353</code> o <code>900219353-1</code></li>
  <li>Los emails pueden estar separados por coma (,) o punto y coma (;) para múltiples destinatarios</li>
  <li>Puede descargar la plantilla desde la pestaña <b>Envío de Comprobantes</b></li>
</ul>

<p><b style="color: #e74c3c;">⚠️ CRÍTICO - Nombres de Archivos PDF en el ZIP:</b></p>
<ul>
  <li>Los PDFs deben tener el <b>NIT exacto</b> en el nombre del archivo</li>
  <li><b>El NIT en el archivo debe coincidir EXACTAMENTE con el NIT del Excel</b></li>
  <li>Ejemplos correctos:
    <ul>
      <li><code>NIT 900219353.pdf</code></li>
      <li><code>NIT._ 31404561.pdf</code></li>
      <li><code>1085245654-5.pdf</code> (con dígito verificador)</li>
      <li><code>RF-84838082-900219353-V-F-F.pdf</code> (formato especial)</li>
    </ul>
  </li>
  <li><b style="color: #c0392b;">⚠️ Verifique que no haya NITs similares (ej: 12345678 y 123456789)</b>
      ya que esto puede causar confusiones en el matching</li>
</ul>

<h3 style="color: #3498db;">3. 📤 Proceso de Envío</h3>
<ol>
  <li><b>Cargar Excel:</b> Clic en "📁 Cargar Excel" y seleccione el archivo con la información de clientes
    <ul>
      <li>Verá un resumen de clientes cargados</li>
      <li>Revise que los NITs estén correctos</li>
    </ul>
  </li>
  <li><b>Cargar ZIP:</b> Clic en "📦 Cargar ZIP" y seleccione el archivo con los PDFs
    <ul>
      <li>El sistema extraerá los NITs de los nombres de archivo</li>
      <li>Verá un resumen de coincidencias encontradas</li>
    </ul>
  </li>
  <li><b>Revisar coincidencias:</b> Clic en "📋 Ver Detalles" para revisar:
    <ul>
      <li>✅ Clientes con archivos encontrados</li>
      <li>⚠️ Clientes sin archivos (no se enviarán)</li>
      <li>⚠️ Archivos sin cliente (se ignorarán)</li>
    </ul>
  </li>
  <li><b>Configurar mensaje:</b> Personalice el asunto y cuerpo del correo
    <ul>
      <li>Use <code>{nombre}</code> para incluir el nombre del cliente</li>
      <li>Use <code>{nit}</code> para incluir el NIT</li>
    </ul>
  </li>
  <li><b>Enviar:</b> Clic en "📨 Enviar Correos"
    <ul>
      <li>Verá una barra de progreso</li>
      <li>Los envíos exitosos se marcarán en verde ✅</li>
      <li>Los errores se marcarán en rojo ❌</li>
    </ul>
  </li>
</ol>

<h3 style="color: #3498db;">4. 📊 Reportes y Seguimiento</h3>
<ul>
  <li>Vaya a la pestaña <b>Reportes</b> para ver el historial de envíos</li>
  <li>Puede filtrar por fecha y estado (exitoso/fallido)</li>
  <li>Puede exportar reportes a Excel</li>
  <li>Los logs detallados están disponibles en <b>Herramientas → Ver carpeta de logs</b></li>
</ul>

<h3 style="color: #3498db;">5. 🧪 Ambiente de Pruebas</h3>
<ul>
  <li>Use esta pestaña para probar envíos sin afectar clientes reales</li>
  <li>Puede enviar correos de prueba a direcciones específicas</li>
  <li>Verifique que los PDFs se adjunten correctamente</li>
</ul>

<h3 style="color: #e74c3c;">⚠️ Advertencias Importantes</h3>
<ul>
  <li><b>NITs duplicados:</b> Si hay NITs repetidos en el Excel, solo se procesará el primero</li>
  <li><b>Matching de NITs:</b> El sistema hace matching EXACTO por NIT. Si el NIT del Excel
      es diferente al del archivo PDF (aunque sea por un dígito), NO se encontrará coincidencia</li>
  <li><b>Archivos múltiples:</b> Si un NIT tiene varios PDFs en el ZIP, se enviarán todos adjuntos</li>
  <li><b>Límites de tamaño:</b> Los adjuntos no deben superar los 25 MB (límite de Gmail y otros servidores)</li>
  <li><b>Contraseñas de aplicación:</b> Gmail requiere contraseñas de aplicación, no su contraseña normal</li>
</ul>

<h3 style="color: #27ae60;">💡 Consejos y Buenas Prácticas</h3>
<ul>
  <li>Siempre revise las coincidencias antes de enviar</li>
  <li>Use el modo prueba primero con pocos clientes</li>
  <li>Mantenga respaldos de sus archivos Excel y ZIP</li>
  <li>Revise los logs en caso de errores</li>
  <li>Use nombres de archivo consistentes para los PDFs</li>
  <li>Verifique que los NITs en Excel y ZIP sean exactamente iguales</li>
</ul>

<h3 style="color: #3498db;">🆘 Solución de Problemas</h3>
<ul>
  <li><b>Error SMTP:</b> Verifique usuario, contraseña y conexión a internet</li>
  <li><b>No se encuentran archivos:</b> Verifique que el NIT esté en el nombre del PDF</li>
  <li><b>Clientes de más:</b> Asegúrese de que no haya NITs similares (ej: 12345678 vs 123456789)</li>
  <li><b>Errores al cargar Excel:</b> Verifique que las columnas tengan los nombres correctos</li>
</ul>

<p style="color: #7f8c8d; margin-top: 20px;"><i>Para soporte técnico: inteligenciadenegocios@correagro.com</i></p>
""")

        layout.addWidget(texto_manual)

        # Botón cerrar
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialogo.accept)
        layout.addWidget(btn_cerrar)

        dialogo.setLayout(layout)
        dialogo.exec()

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

    def _inicializar_actualizaciones(self):
        """Inicializa el sistema de actualizaciones automáticas"""
        github_repo = self.config.get("update.github_repo", "")

        if github_repo:
            try:
                self.updater = AutoUpdater(self, __version__, github_repo)

                # Verificar actualizaciones al iniciar (después de 3 segundos)
                if self.config.get("update.check_on_startup", True):
                    QTimer.singleShot(3000, lambda: self.updater.check_for_updates(silent=True))

                self.logger.info(
                    f"Sistema de actualizaciones inicializado: {github_repo}",
                    modulo="MainWindow"
                )
            except Exception as e:
                self.logger.error(
                    f"Error al inicializar actualizaciones: {e}",
                    modulo="MainWindow",
                    exc_info=True
                )
        else:
            self.logger.warning(
                "Sistema de actualizaciones no configurado (falta github_repo)",
                modulo="MainWindow"
            )
            self.updater = None
