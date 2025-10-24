"""
Pestaña de Ambiente de Pruebas
Permite realizar envíos de prueba REALES a un correo específico
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QTextEdit, QMessageBox, QLineEdit,
                             QFileDialog, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from app.core.email_sender import EmailSender
from app.core.excel_processor import ExcelProcessor
from app.core.zip_handler import ZipHandler
import os


class PruebaEnvioWorker(QThread):
    """Worker para envío de prueba real"""
    progreso = pyqtSignal(str)  # mensaje de progreso
    finalizado = pyqtSignal(bool, str)  # exito, mensaje

    def __init__(self, smtp_config, email_destino, archivos_adjuntos, nit_cliente, nombre_cliente, logger):
        super().__init__()
        self.smtp_config = smtp_config
        self.email_destino = email_destino
        self.archivos_adjuntos = archivos_adjuntos
        self.nit_cliente = nit_cliente
        self.nombre_cliente = nombre_cliente
        self.logger = logger

    def run(self):
        """Ejecuta el envío de prueba"""
        try:
            self.progreso.emit("Conectando al servidor SMTP...")
            
            # Importar lo necesario
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.base import MIMEBase
            from email import encoders
            from email.utils import formataddr
            import os
            import zipfile
            import tempfile
            
            self.progreso.emit("Preparando correo de prueba...")
            
            # ✅ CREAR ZIP CON TODOS LOS PDFs
            self.progreso.emit(f"Comprimiendo {len(self.archivos_adjuntos)} archivo(s) en ZIP...")
            
            # Crear archivo ZIP temporal
            temp_dir = tempfile.gettempdir()
            nombre_zip = f"Comprobantes_NIT_{self.nit_cliente}_{self.nombre_cliente.replace(' ', '_')[:30]}.zip"
            ruta_zip = os.path.join(temp_dir, nombre_zip)
            
            # Comprimir todos los PDFs
            with zipfile.ZipFile(ruta_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for archivo_path in self.archivos_adjuntos:
                    try:
                        # Agregar archivo al ZIP con su nombre original
                        nombre_archivo = os.path.basename(archivo_path)
                        zipf.write(archivo_path, nombre_archivo)
                        self.progreso.emit(f"  ✓ Agregado: {nombre_archivo}")
                    except Exception as e:
                        self.progreso.emit(f"  ⚠️ Error al agregar {os.path.basename(archivo_path)}: {str(e)}")
            
            # Verificar tamaño del ZIP
            tamano_zip_mb = os.path.getsize(ruta_zip) / (1024 * 1024)
            self.progreso.emit(f"ZIP creado: {nombre_zip} ({tamano_zip_mb:.2f} MB)")
            
            # Advertencia si el ZIP es muy grande (>25 MB para Outlook)
            if tamano_zip_mb > 25:
                self.progreso.emit("⚠️ ADVERTENCIA: El ZIP supera 25 MB, puede ser rechazado por algunos servidores")
            
            # Crear mensaje
            msg = MIMEMultipart()
            
            # Formato correcto del remitente
            from_name = self.smtp_config.get('from_name', 'Sistema Comprobantes')
            from_email = self.smtp_config['username']
            msg['From'] = formataddr((from_name, from_email))
            
            msg['To'] = self.email_destino
            msg['Subject'] = f"[PRUEBA] Comprobantes - NIT {self.nit_cliente} - {self.nombre_cliente}"
            
            # ✅ CUERPO DEL CORREO PERSONALIZADO
            cuerpo_html = f"""
    <html>
    <body>
        <h2>🧪 Correo de Prueba - Sistema de Envío de Comprobantes</h2>
        
        <p><strong>Estimado(a) cliente,</strong></p>
        
        <p>Este es un correo de prueba del sistema de envío automático de comprobantes.</p>
        
        <hr>
        
        <h3>📋 Información del Destinatario:</h3>
        <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
            <tr>
                <td style="padding: 8px; background-color: #f0f0f0; font-weight: bold;">NIT:</td>
                <td style="padding: 8px;">{self.nit_cliente}</td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f0f0f0; font-weight: bold;">Razón Social:</td>
                <td style="padding: 8px;">{self.nombre_cliente}</td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f0f0f0; font-weight: bold;">Archivos incluidos:</td>
                <td style="padding: 8px;">{len(self.archivos_adjuntos)} documento(s)</td>
            </tr>
            <tr>
                <td style="padding: 8px; background-color: #f0f0f0; font-weight: bold;">Tamaño del archivo:</td>
                <td style="padding: 8px;">{tamano_zip_mb:.2f} MB</td>
            </tr>
        </table>
        
        <hr>
        
        <h3>📦 Adjunto:</h3>
        <p>Encontrará un archivo ZIP adjunto que contiene todos sus comprobantes en formato PDF.</p>
        
        <p><strong>Nombre del archivo:</strong> {nombre_zip}</p>
        
        <hr>
        
        <p style="color: #666; font-size: 12px;">
            <strong>Nota:</strong> Este es un correo de prueba generado automáticamente por el Sistema de Envío de Comprobantes.
            En un envío real, este correo se enviaría a: <strong>{self.nombre_cliente}</strong>
        </p>
        
        <p style="color: #999; font-size: 11px; margin-top: 20px;">
            Por favor, no responda a este correo. Este mensaje fue generado automáticamente.
        </p>
    </body>
    </html>
            """
            
            msg.attach(MIMEText(cuerpo_html, 'html'))
            
            # ✅ ADJUNTAR EL ARCHIVO ZIP
            self.progreso.emit(f"Adjuntando archivo ZIP...")
            try:
                with open(ruta_zip, 'rb') as adjunto:
                    parte = MIMEBase('application', 'zip')
                    parte.set_payload(adjunto.read())
                    encoders.encode_base64(parte)
                    parte.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{nombre_zip}"'
                    )
                    msg.attach(parte)
            except Exception as e:
                self.finalizado.emit(False, f"❌ Error al adjuntar ZIP: {str(e)}")
                return
            
            # Enviar correo
            self.progreso.emit(f"Enviando a {self.email_destino}...")
            
            servidor = self.smtp_config['server']
            puerto = self.smtp_config['port']
            usuario = self.smtp_config['username']
            password = self.smtp_config['password']
            usar_tls = self.smtp_config.get('use_tls', True)
            
            # Conectar y enviar
            if usar_tls:
                server = smtplib.SMTP(servidor, puerto, timeout=30)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(servidor, puerto, timeout=30)
            
            server.login(usuario, password)
            server.send_message(msg)
            server.quit()
            
            # Limpiar archivo ZIP temporal
            try:
                os.remove(ruta_zip)
                self.progreso.emit("✓ Archivo temporal limpiado")
            except:
                pass
            
            self.finalizado.emit(
                True, 
                f"✅ Correo enviado exitosamente a {self.email_destino}\n"
                f"   • Archivo ZIP: {nombre_zip}\n"
                f"   • Tamaño: {tamano_zip_mb:.2f} MB\n"
                f"   • PDFs incluidos: {len(self.archivos_adjuntos)}"
            )
            
        except smtplib.SMTPAuthenticationError:
            self.finalizado.emit(False, "❌ Error de autenticación: Usuario o contraseña incorrectos")
        except smtplib.SMTPException as e:
            self.finalizado.emit(False, f"❌ Error SMTP: {str(e)}")
        except Exception as e:
            self.finalizado.emit(False, f"❌ Error: {str(e)}")
    
class PruebasTab(QWidget):
    """Pestaña de ambiente de pruebas con envío real"""
    
    def __init__(self, config, db, logger):
        super().__init__()
        self.config = config
        self.db = db
        self.logger = logger
        
        self.excel_processor = None
        self.zip_handler = None
        self.clientes = []
        self.archivos_por_nit = {}
        self.cliente_prueba = None
        self.archivos_prueba = []
        
        self._crear_interfaz()
    
    def _crear_interfaz(self):
        """Crea la interfaz de la pestaña"""
        layout = QVBoxLayout(self)
        
        # Título
        titulo = QLabel("🧪 Ambiente de Pruebas - Envío Real")
        titulo.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(titulo)
        
        # Descripción
        desc = QLabel(
            "Use esta pestaña para realizar UN envío de prueba REAL a su propio correo.\n"
            "Seleccione un cliente y envíe sus comprobantes a su email para verificar que todo funciona."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("padding: 10px; background-color: #d1ecf1; border-radius: 5px; color: #000;")
        layout.addWidget(desc)
        
        # Grupo: Cargar archivos
        grupo_archivos = self._crear_grupo_archivos()
        layout.addWidget(grupo_archivos)
        
        # Grupo: Configuración de prueba
        grupo_config = self._crear_grupo_configuracion()
        layout.addWidget(grupo_config)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Log
        self.txt_log = QTextEdit()
        self.txt_log.setMaximumHeight(150)
        self.txt_log.setReadOnly(True)
        self.txt_log.setPlaceholderText("Aquí se mostrará el resultado del envío de prueba...")
        layout.addWidget(self.txt_log)
        
        # Botón enviar prueba
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_enviar_prueba = QPushButton("🚀 Enviar Prueba Real")
        self.btn_enviar_prueba.setMinimumHeight(40)
        self.btn_enviar_prueba.setEnabled(False)
        self.btn_enviar_prueba.setStyleSheet("""
            QPushButton {
                background-color: #28a745; color: white; font-weight: bold;
                border-radius: 5px; padding: 8px 20px; font-size: 14px;
            }
            QPushButton:hover { background-color: #218838; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        self.btn_enviar_prueba.clicked.connect(self._enviar_prueba)
        btn_layout.addWidget(self.btn_enviar_prueba)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
    
    def _crear_grupo_archivos(self):
        """Grupo para cargar archivos"""
        grupo = QGroupBox("📁 Cargar Archivos de Prueba")
        layout = QVBoxLayout()
        
        # Excel
        excel_layout = QHBoxLayout()
        self.label_excel = QLabel("❌ Excel no cargado")
        excel_layout.addWidget(self.label_excel)
        excel_layout.addStretch()
        btn_excel = QPushButton("📊 Cargar Excel")
        btn_excel.clicked.connect(self._cargar_excel)
        excel_layout.addWidget(btn_excel)
        layout.addLayout(excel_layout)
        
        # ZIP
        zip_layout = QHBoxLayout()
        self.label_zip = QLabel("❌ ZIP no cargado")
        zip_layout.addWidget(self.label_zip)
        zip_layout.addStretch()
        btn_zip = QPushButton("📦 Cargar ZIP")
        btn_zip.clicked.connect(self._cargar_zip)
        zip_layout.addWidget(btn_zip)
        layout.addLayout(zip_layout)
        
        grupo.setLayout(layout)
        return grupo
    
    def _crear_grupo_configuracion(self):
        """Grupo de configuración de prueba"""
        grupo = QGroupBox("⚙️ Configuración de Prueba")
        layout = QVBoxLayout()
        
        # Email de prueba
        email_layout = QHBoxLayout()
        email_layout.addWidget(QLabel("Email destino (tu correo):"))
        self.txt_email_prueba = QLineEdit()
        self.txt_email_prueba.setPlaceholderText("tu_correo@ejemplo.com")
        email_layout.addWidget(self.txt_email_prueba)
        layout.addLayout(email_layout)
        
        # NIT cliente
        nit_layout = QHBoxLayout()
        nit_layout.addWidget(QLabel("NIT del cliente a probar:"))
        self.txt_nit_prueba = QLineEdit()
        self.txt_nit_prueba.setPlaceholderText("Ej: 900554896")
        nit_layout.addWidget(self.txt_nit_prueba)
        layout.addLayout(nit_layout)
        
        # Botón buscar
        btn_buscar = QPushButton("🔍 Buscar Cliente y Archivos")
        btn_buscar.clicked.connect(self._buscar_cliente)
        layout.addWidget(btn_buscar)
        
        # Info del cliente encontrado
        self.label_cliente_info = QLabel("")
        self.label_cliente_info.setWordWrap(True)
        layout.addWidget(self.label_cliente_info)
        
        grupo.setLayout(layout)
        return grupo
    
    def _cargar_excel(self):
        """Carga el archivo Excel"""
        archivo, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Excel", "",
            "Archivos Excel (*.xlsx *.xls)"
        )
        if not archivo:
            return
        
        self.excel_processor = ExcelProcessor(self.logger)
        exito, mensaje, clientes = self.excel_processor.procesar_archivo(archivo)
        
        if exito:
            self.clientes = clientes
            self.label_excel.setText(f"✅ {os.path.basename(archivo)} - {len(clientes)} clientes")
            self.label_excel.setStyleSheet("color: green;")
        else:
            QMessageBox.critical(self, "Error", f"Error al cargar Excel:\n{mensaje}")
            self.label_excel.setText("❌ Error al cargar Excel")
    
    def _cargar_zip(self):
        """Carga el archivo ZIP"""
        archivo, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar ZIP", "",
            "Archivos ZIP (*.zip)"
        )
        if not archivo:
            return
        
        self.zip_handler = ZipHandler(self.logger)
        exito, mensaje, archivos_por_nit = self.zip_handler.procesar_zip(archivo)
        
        if exito:
            self.archivos_por_nit = archivos_por_nit
            self.label_zip.setText(f"✅ {os.path.basename(archivo)} - {len(archivos_por_nit)} NITs")
            self.label_zip.setStyleSheet("color: green;")
        else:
            QMessageBox.critical(self, "Error", f"Error al cargar ZIP:\n{mensaje}")
            self.label_zip.setText("❌ Error al cargar ZIP")
    
    def _buscar_cliente(self):
        """Busca el cliente y sus archivos"""
        if not self.clientes or not self.archivos_por_nit:
            QMessageBox.warning(self, "Advertencia", "Debe cargar primero el Excel y el ZIP")
            return
        
        nit_buscar = self.txt_nit_prueba.text().strip()
        if not nit_buscar:
            QMessageBox.warning(self, "Advertencia", "Ingrese un NIT para buscar")
            return
        
        # Buscar cliente
        from app.utils.validator import Validator
        nit_normalizado = Validator.normalizar_nit(nit_buscar)
        
        cliente_encontrado = None
        for cliente in self.clientes:
            if Validator.nits_coinciden(cliente['nit'], nit_normalizado):
                cliente_encontrado = cliente
                break
        
        if not cliente_encontrado:
            self.label_cliente_info.setText(f"❌ No se encontró el cliente con NIT {nit_buscar}")
            self.label_cliente_info.setStyleSheet("color: red;")
            self.btn_enviar_prueba.setEnabled(False)
            return
        
        # Buscar archivos
        archivos = self.zip_handler.obtener_archivos_por_nit(cliente_encontrado['nit'])
        if not archivos:
            archivos = self.zip_handler.buscar_archivos_por_nit_flexible(
                cliente_encontrado['nit'],
                cliente_encontrado['nombre']
            )
        
        if not archivos:
            self.label_cliente_info.setText(
                f"⚠️ Cliente encontrado pero sin archivos:\n"
                f"NIT: {cliente_encontrado['nit']}\n"
                f"Nombre: {cliente_encontrado['nombre']}"
            )
            self.label_cliente_info.setStyleSheet("color: orange;")
            self.btn_enviar_prueba.setEnabled(False)
            return
        
        # Todo OK
        self.cliente_prueba = cliente_encontrado
        self.archivos_prueba = archivos
        
        self.label_cliente_info.setText(
            f"✅ Cliente encontrado:\n"
            f"NIT: {cliente_encontrado['nit']}\n"
            f"Nombre: {cliente_encontrado['nombre']}\n"
            f"Email original: {cliente_encontrado['email']}\n"
            f"Archivos: {len(archivos)}"
        )
        self.label_cliente_info.setStyleSheet("color: green;")
        self.btn_enviar_prueba.setEnabled(True)
    
    def _enviar_prueba(self):
        """Envía el correo de prueba REAL"""
        email_destino = self.txt_email_prueba.text().strip()
        if not email_destino:
            QMessageBox.warning(self, "Advertencia", "Ingrese su email de destino")
            return
        
        # Validar email
        from app.utils.validator import Validator
        es_valido, mensaje = Validator.validar_email(email_destino)
        if not es_valido:
            QMessageBox.warning(self, "Email inválido", mensaje)
            return
        
        # Obtener configuración SMTP
        smtp = self.config.get_smtp_config()
        servidor = smtp.get('server', '')
        puerto = smtp.get('port', 0)
        usuario = smtp.get('username', '')
        password = smtp.get('password', '')
        
        es_valido, mensaje = Validator.validar_configuracion_smtp(servidor, puerto, usuario, password or "x")
        if not es_valido:
            QMessageBox.warning(self, "Configuración inválida",
                              f"Configure correctamente SMTP en la pestaña Configuración:\n{mensaje}")
            return
        
        # Pedir contraseña si no está guardada
        if not password:
            from PyQt6.QtWidgets import QInputDialog
            password, ok = QInputDialog.getText(
                self, "Contraseña requerida",
                "Introduce la contraseña del correo:",
                QLineEdit.EchoMode.Password
            )
            if not ok or not password:
                return
        
        smtp_config = {
            'server': servidor,
            'port': puerto,
            'username': usuario,
            'password': password,
            'use_tls': smtp.get('use_tls', True),
            'from_name': 'Sistema de Comprobantes [PRUEBA]'
        }
        
        # Confirmar
        respuesta = QMessageBox.question(
            self, "Confirmar envío de prueba",
            f"¿Enviar correo de prueba REAL?\n\n"
            f"A: {email_destino}\n"
            f"Cliente: {self.cliente_prueba['nombre']}\n"
            f"Archivos: {len(self.archivos_prueba)}\n\n"
            f"⚠️ Este es un envío REAL, se enviará un correo electrónico.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        
        # Iniciar envío
        self.btn_enviar_prueba.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(0)  # Modo indeterminado
        self.txt_log.clear()
        
        self.worker = PruebaEnvioWorker(
            smtp_config,
            email_destino,
            self.archivos_prueba,
            self.cliente_prueba['nit'],
            self.cliente_prueba['nombre'],
            self.logger
        )
        
        self.worker.progreso.connect(self._on_progreso)
        self.worker.finalizado.connect(self._on_finalizado)
        self.worker.start()
    
    def _on_progreso(self, mensaje):
        """Actualiza el progreso"""
        self.txt_log.append(mensaje)
    
    def _on_finalizado(self, exito, mensaje):
        """Envío finalizado"""
        self.progress_bar.setVisible(False)
        self.btn_enviar_prueba.setEnabled(True)
        
        self.txt_log.append(f"\n{mensaje}")
        
        if exito:
            QMessageBox.information(self, "Envío exitoso", mensaje)
        else:
            QMessageBox.critical(self, "Error en envío", mensaje)