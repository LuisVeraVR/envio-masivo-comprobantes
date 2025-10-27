"""
Pestaña de Configuración
Permite a las operativas configurar SMTP, emails en copia y modo de pruebas
MEJORADO: Con indicadores de progreso y ayuda para contraseñas
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QLineEdit, QSpinBox, QCheckBox, QPushButton,
                             QTextEdit, QMessageBox, QFormLayout, QProgressDialog)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QCursor


class ConfiguracionTab(QWidget):
    """Pestaña de configuración de la aplicación"""
    
    # Señal emitida cuando se actualiza la configuración
    configuracion_actualizada = pyqtSignal()
    
    def __init__(self, config, db, logger):
        """Inicializa la pestaña de configuración"""
        super().__init__()
        
        self.config = config
        self.db = db
        self.logger = logger
        
        self._crear_interfaz()
        self._cargar_configuracion()
    
    def _crear_interfaz(self):
        """Crea la interfaz de la pestaña"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Título
        titulo = QLabel("⚙️ Configuración del Sistema")
        titulo.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(titulo)
        
        # Grupos
        layout.addWidget(self._crear_grupo_smtp())
        layout.addWidget(self._crear_grupo_cc())
        layout.addWidget(self._crear_grupo_pruebas())
        
        # Botones
        botones_layout = QHBoxLayout()
        botones_layout.addStretch()
        
        self.btn_probar = QPushButton("🔍 Probar Conexión")
        self.btn_probar.clicked.connect(self._probar_conexion)
        self.btn_probar.setMinimumHeight(35)
        botones_layout.addWidget(self.btn_probar)
        
        self.btn_guardar = QPushButton("💾 Guardar Configuración")
        self.btn_guardar.clicked.connect(self._guardar_configuracion)
        self.btn_guardar.setMinimumHeight(35)
        self.btn_guardar.setStyleSheet("""
            QPushButton {
                background-color: #28a745; color: white; font-weight: bold;
                border-radius: 5px; padding: 5px 15px;
            }
            QPushButton:hover { background-color: #218838; }
        """)
        botones_layout.addWidget(self.btn_guardar)
        
        layout.addLayout(botones_layout)
        layout.addStretch()
    
    def _crear_grupo_smtp(self):
        """Crea el grupo de configuración SMTP con ayuda mejorada"""
        grupo = QGroupBox("📧 Configuración de Correo SMTP")
    
        form_layout = QFormLayout()
    
        self.txt_servidor = QLineEdit()
        self.txt_servidor.setPlaceholderText("Ej: smtp.gmail.com o smtp.office365.com")
        form_layout.addRow("Servidor SMTP:", self.txt_servidor)
    
        self.spin_puerto = QSpinBox()
        self.spin_puerto.setRange(1, 65535)
        self.spin_puerto.setValue(587)
        form_layout.addRow("Puerto:", self.spin_puerto)
    
        self.chk_tls = QCheckBox("Usar TLS (recomendado)")
        self.chk_tls.setChecked(True)
        form_layout.addRow("", self.chk_tls)
    
        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText("Ej: tu-correo@empresa.com")
        form_layout.addRow("Usuario (Email):", self.txt_usuario)
    
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Contraseña o Contraseña de Aplicación")
    
        password_layout = QHBoxLayout()
        password_layout.addWidget(self.txt_password)
    
        self.btn_mostrar_password = QPushButton("👁")
        self.btn_mostrar_password.setMaximumWidth(40)
        self.btn_mostrar_password.setCheckable(True)
        self.btn_mostrar_password.clicked.connect(self._toggle_password)
        password_layout.addWidget(self.btn_mostrar_password)
    
        form_layout.addRow("Contraseña:", password_layout)
    
        # ✅ AYUDA MEJORADA SOBRE CONTRASEÑAS
        ayuda = QLabel(
            "<small><b>💡 IMPORTANTE:</b><br>"
            "<b>Office365/Outlook:</b> Requiere <u>contraseña de aplicación</u> con 2FA activo<br>"
            "<b>Gmail:</b> Requiere <u>contraseña de aplicación</u> con verificación en 2 pasos<br>"
            "<b>Servidores corporativos:</b> Generalmente funciona con contraseña normal<br><br>"
            "Si falla, prueba con contraseña de aplicación (ver ayuda en 'Probar Conexión')</small>"
        )
        ayuda.setWordWrap(True)
        ayuda.setStyleSheet("background-color: #fff3cd; padding: 8px; border-radius: 4px; border: 1px solid #ffc107;")
        form_layout.addRow("", ayuda)
    
        grupo.setLayout(form_layout)
        return grupo
    
    def _crear_grupo_cc(self):
        """Crea el grupo de emails en copia"""
        grupo = QGroupBox("📋 Emails en Copia (CC)")
        layout = QVBoxLayout()
        
        desc = QLabel("Ingrese los emails que recibirán copia de todos los envíos.\n"
                     "Separe múltiples emails con coma (,) o punto y coma (;)")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)
        
        self.txt_emails_cc = QTextEdit()
        self.txt_emails_cc.setMaximumHeight(100)
        self.txt_emails_cc.setPlaceholderText("Ej: copia1@empresa.com, copia2@empresa.com")
        layout.addWidget(self.txt_emails_cc)
        
        self.label_contador_cc = QLabel("0 emails configurados")
        self.label_contador_cc.setStyleSheet("font-size: 11px; color: #666;")
        layout.addWidget(self.label_contador_cc)
        
        self.txt_emails_cc.textChanged.connect(self._actualizar_contador_cc)
        
        grupo.setLayout(layout)
        return grupo
    
    def _crear_grupo_pruebas(self):
        """Crea el grupo de modo de pruebas"""
        grupo = QGroupBox("🧪 Modo de Pruebas")
        layout = QVBoxLayout()
        
        self.chk_modo_prueba = QCheckBox("Activar modo de pruebas")
        self.chk_modo_prueba.toggled.connect(self._toggle_modo_prueba)
        layout.addWidget(self.chk_modo_prueba)
        
        desc = QLabel("En modo pruebas, los envíos se simulan sin enviar correos reales.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; padding-left: 20px;")
        layout.addWidget(desc)
        
        prueba_layout = QFormLayout()
        self.txt_email_prueba = QLineEdit()
        self.txt_email_prueba.setPlaceholderText("Email para pruebas (opcional)")
        self.txt_email_prueba.setEnabled(False)
        prueba_layout.addRow("Email de prueba:", self.txt_email_prueba)
        
        layout.addLayout(prueba_layout)
        grupo.setLayout(layout)
        return grupo
    
    def _toggle_password(self):
        """Muestra u oculta la contraseña"""
        if self.btn_mostrar_password.isChecked():
            self.txt_password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_mostrar_password.setText("🙈")
        else:
            self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_mostrar_password.setText("👁")
    
    def _toggle_modo_prueba(self, activado):
        """Activa o desactiva el modo de pruebas"""
        self.txt_email_prueba.setEnabled(activado)
    
    def _actualizar_contador_cc(self):
        """Actualiza el contador de emails en copia"""
        from app.utils.validator import Validator
        
        texto = self.txt_emails_cc.toPlainText()
        if not texto.strip():
            self.label_contador_cc.setText("0 emails configurados")
            return
        
        es_valido, mensaje, emails_validos = Validator.validar_lista_emails(texto)
        
        if emails_validos:
            self.label_contador_cc.setText(f"{len(emails_validos)} email(s) configurado(s)")
            color = "#5cb85c" if es_valido else "#d9534f"
            self.label_contador_cc.setStyleSheet(f"font-size: 11px; color: {color};")
        else:
            self.label_contador_cc.setText("0 emails válidos")
            self.label_contador_cc.setStyleSheet("font-size: 11px; color: #d9534f;")
    
    def _cargar_configuracion(self):
        """Carga la configuración actual"""
        smtp = self.config.get_smtp_config()
        self.txt_servidor.setText(smtp.get('server', ''))
        self.spin_puerto.setValue(smtp.get('port', 587))
        self.chk_tls.setChecked(smtp.get('use_tls', True))
        self.txt_usuario.setText(smtp.get('username', ''))
        self.txt_password.setText(smtp.get('password', ''))
        
        emails_cc = self.config.get_emails_copia()
        if emails_cc:
            self.txt_emails_cc.setPlainText(', '.join(emails_cc))
        
        self.chk_modo_prueba.setChecked(self.config.is_test_mode())
        self.txt_email_prueba.setText(self.config.get_test_email())
    
    def _guardar_configuracion(self):
        """Guarda la configuración"""
        from app.utils.validator import Validator
        
        servidor = self.txt_servidor.text().strip()
        puerto = self.spin_puerto.value()
        usuario = self.txt_usuario.text().strip()
        password = self.txt_password.text()
        
        es_valido, mensaje = Validator.validar_configuracion_smtp(servidor, puerto, usuario, password)
        if not es_valido:
            QMessageBox.warning(self, "Configuración inválida", mensaje)
            return
        
        texto_cc = self.txt_emails_cc.toPlainText().strip()
        emails_validos = []
        if texto_cc:
            es_valido, mensaje, emails_validos = Validator.validar_lista_emails(texto_cc)
            if not es_valido:
                respuesta = QMessageBox.question(
                    self, "Emails inválidos",
                    f"{mensaje}\n\n¿Continuar solo con los emails válidos?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if respuesta == QMessageBox.StandardButton.No:
                    return
        
        self.config.set_smtp_config(servidor, puerto, usuario, password, self.chk_tls.isChecked())
        self.config.set_emails_copia(emails_validos)
        self.config.set_test_mode(self.chk_modo_prueba.isChecked(), self.txt_email_prueba.text().strip())
        
        self.logger.info(f"Configuración guardada - SMTP: {usuario}, CC: {len(emails_validos)} emails", 
                        modulo="ConfiguracionTab")
        
        QMessageBox.information(self, "Configuración guardada", 
                               "La configuración ha sido guardada exitosamente.")
        
        self.configuracion_actualizada.emit()
    
    def _probar_conexion(self):
        """Prueba la conexión SMTP con indicador de progreso y ayuda mejorada"""
        from app.core.email_sender import EmailSender
        from app.utils.validator import Validator
        from PyQt6.QtWidgets import QApplication
        
        servidor = self.txt_servidor.text().strip()
        puerto = self.spin_puerto.value()
        usuario = self.txt_usuario.text().strip()
        password = self.txt_password.text()
        
        es_valido, mensaje = Validator.validar_configuracion_smtp(servidor, puerto, usuario, password or "x")
        if not es_valido:
            QMessageBox.warning(self, "Configuración inválida", mensaje)
            return
        
        smtp_config = {
            'server': servidor,
            'port': puerto,
            'username': usuario,
            'password': password,
            'use_tls': self.chk_tls.isChecked(),
            'from_name': 'Sistema de Comprobantes'
        }
        
        # ✅ CREAR PROGRESS DIALOG
        progress = QProgressDialog(
            "Conectando al servidor SMTP...\nEsto puede tomar unos segundos.",
            None,  # Sin botón cancelar
            0, 0,  # Modo indeterminado
            self
        )
        progress.setWindowTitle("⏳ Probando Conexión")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.setMinimumWidth(400)
        progress.show()
        
        # Procesar eventos para mostrar el diálogo
        QApplication.processEvents()
        
        # Cambiar cursor
        self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
        
        resultado_exito = False
        resultado_mensaje = ""
        
        try:
            progress.setLabelText("🔐 Autenticando con el servidor...\nPor favor espere...")
            QApplication.processEvents()
            
            sender = EmailSender(smtp_config, self.db, self.logger)
            resultado_exito, resultado_mensaje = sender.probar_conexion()
            
        except Exception as e:
            resultado_exito = False
            resultado_mensaje = str(e)
        finally:
            progress.close()
            self.unsetCursor()
        
        # ✅ MOSTRAR RESULTADO CON AYUDA CONTEXTUAL
        if resultado_exito:
            QMessageBox.information(
                self, 
                "✅ Conexión Exitosa", 
                f"<b>¡Perfecto!</b><br><br>"
                f"{resultado_mensaje}<br><br>"
                f"<b>La configuración SMTP es correcta.</b><br>"
                f"Puedes guardar y comenzar a usar el sistema."
            )
        else:
            # Analizar el tipo de error
            error_bajo = resultado_mensaje.lower()
            
            if any(x in error_bajo for x in ['autenticación', 'authentication', 'login', 'username', 'password', '535']):
                # ✅ ERROR DE AUTENTICACIÓN - DAR AYUDA ESPECÍFICA
                self._mostrar_ayuda_autenticacion(resultado_mensaje, servidor)
            else:
                # Otro tipo de error
                QMessageBox.critical(
                    self, 
                    "❌ Error de Conexión", 
                    f"<b>Error al conectar:</b><br><br>"
                    f"{resultado_mensaje}<br><br>"
                    f"<b>Verifica:</b><br>"
                    f"• Servidor y puerto correctos<br>"
                    f"• Conexión a internet<br>"
                    f"• Firewall no está bloqueando<br>"
                    f"• El servidor SMTP está disponible"
                )
    
    def _mostrar_ayuda_autenticacion(self, error_mensaje, servidor):
        """Muestra ayuda específica para errores de autenticación"""
        # Detectar proveedor
        proveedor = "desconocido"
        if "office365" in servidor.lower() or "outlook" in servidor.lower():
            proveedor = "office365"
        elif "gmail" in servidor.lower():
            proveedor = "gmail"
        
        # Construir mensaje de ayuda
        mensaje = f"<h3>❌ Error de Autenticación</h3>"
        mensaje += f"<p><b>Error del servidor:</b><br>{error_mensaje}</p>"
        mensaje += "<hr>"
        
        if proveedor == "office365":
            mensaje += """
<h4>💡 Solución para Office365/Outlook:</h4>
<ol>
<li><b>Activa la autenticación de dos factores (2FA)</b></li>
<li><b>Genera una contraseña de aplicación:</b>
   <ul>
   <li>Ve a: <a href='https://account.microsoft.com/security'>account.microsoft.com/security</a></li>
   <li>Selecciona "Opciones de seguridad avanzadas"</li>
   <li>En "Contraseñas de aplicación", crea una nueva</li>
   <li>Copia esa contraseña (sin espacios)</li>
   </ul>
</li>
<li><b>Usa esa contraseña aquí</b> (no tu contraseña normal)</li>
</ol>
<p><b>Nota:</b> Office365 <u>requiere</u> contraseña de aplicación para SMTP.</p>
"""
        elif proveedor == "gmail":
            mensaje += """
<h4>💡 Solución para Gmail:</h4>
<ol>
<li><b>Activa la verificación en 2 pasos</b></li>
<li><b>Genera una contraseña de aplicación:</b>
   <ul>
   <li>Ve a: <a href='https://myaccount.google.com/apppasswords'>myaccount.google.com/apppasswords</a></li>
   <li>Selecciona "Correo" y "Windows Computer"</li>
   <li>Copia la contraseña generada (16 caracteres)</li>
   </ul>
</li>
<li><b>Usa esa contraseña aquí</b> (no tu contraseña normal)</li>
</ol>
<p><b>Nota:</b> Gmail <u>requiere</u> contraseña de aplicación.</p>
"""
        else:
            mensaje += """
<h4>💡 Soluciones generales:</h4>
<ul>
<li><b>Verifica usuario y contraseña</b></li>
<li><b>Prueba con contraseña de aplicación:</b>
   <ul>
   <li>Activa 2FA en tu cuenta</li>
   <li>Genera una contraseña de aplicación</li>
   <li>Úsala aquí en lugar de tu contraseña normal</li>
   </ul>
</li>
<li><b>Contacta al administrador IT</b> si es servidor corporativo</li>
</ul>
"""
        
        mensaje += "<hr><p><small><b>¿Qué es una contraseña de aplicación?</b><br>"
        mensaje += "Es una contraseña especial de 16 caracteres que generas para aplicaciones "
        mensaje += "que no soportan verificación en 2 pasos. Es más segura que tu contraseña normal.</small></p>"
        
        # Mostrar en un QMessageBox con HTML
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Error de Autenticación SMTP")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(mensaje)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setMinimumWidth(600)
        msg_box.exec()