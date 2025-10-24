"""
Enviador de correos electrónicos
Maneja envío SMTP con validación de NIT en asunto y gestión de estados
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr
from typing import List, Tuple, Dict
from app.utils.validator import Validator
from app.utils.logger import get_logger
from app.database.models import Database


class EmailSender:
    """Envía correos electrónicos por SMTP"""
    
    def __init__(self, smtp_config, db_manager=None, logger=None):
        """
        Inicializa el enviador de correos
        
        Args:
            smtp_config: Diccionario con configuración SMTP
            db_manager: Instancia de Database (opcional)
            logger: Instancia del logger (opcional)
        """
        self.smtp_config = smtp_config
        self.db_manager = db_manager or Database()
        self.logger = logger or get_logger()
        
        # Estadísticas de envío
        self.stats = {
            'enviados': 0,
            'errores': 0,
            'rebotados': 0,
            'bloqueados': 0,
            'inexistentes': 0
        }
    
    def _validar_configuracion(self):
        """
        Valida la configuración SMTP
        
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        return Validator.validar_configuracion_smtp(
            self.smtp_config.get('server', ''),
            self.smtp_config.get('port', 0),
            self.smtp_config.get('username', ''),
            self.smtp_config.get('password', '')
        )
    
    def _conectar_smtp(self):
        """
        Establece conexión con el servidor SMTP
        
        Returns:
            Tupla (conexion, mensaje_error)
        """
        try:
            # Crear conexión SMTP
            if self.smtp_config.get('use_tls', True):
                server = smtplib.SMTP(
                    self.smtp_config['server'],
                    self.smtp_config['port'],
                    timeout=30
                )
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(
                    self.smtp_config['server'],
                    self.smtp_config['port'],
                    timeout=30
                )
            
            # Login
            server.login(
                self.smtp_config['username'],
                self.smtp_config['password']
            )
            
            self.logger.debug("Conexión SMTP establecida", modulo="EmailSender")
            return server, None
        
        except smtplib.SMTPAuthenticationError:
            mensaje = "Error de autenticación SMTP. Verifica usuario y contraseña"
            self.logger.error(mensaje, modulo="EmailSender")
            return None, mensaje
        
        except smtplib.SMTPConnectError:
            mensaje = "No se pudo conectar al servidor SMTP"
            self.logger.error(mensaje, modulo="EmailSender")
            return None, mensaje
        
        except Exception as e:
            mensaje = f"Error al conectar SMTP: {str(e)}"
            self.logger.error(mensaje, modulo="EmailSender", exc_info=True)
            return None, mensaje
    
    def _construir_asunto(self, nit, nombre_cliente, prefijo="Comprobante - NIT: "):
        """
        Construye el asunto del correo con el NIT
        
        Args:
            nit: NIT del cliente
            nombre_cliente: Nombre del cliente
            prefijo: Prefijo del asunto
            
        Returns:
            Asunto completo
        """
        asunto = f"{prefijo}{nit} - {nombre_cliente}"
        
        # Validar que el asunto contenga el NIT
        es_valido, _ = Validator.validar_asunto_con_nit(asunto, nit)
        
        if not es_valido:
            # Forzar inclusión del NIT si no está
            asunto = f"NIT: {nit} - {asunto}"
        
        return asunto
    
    def _construir_mensaje(self, destinatario, nit, nombre_cliente, archivos_adjuntos, 
                          emails_copia=None, prefijo_asunto="Comprobante - NIT: "):
        """
        Construye el mensaje de correo completo
        
        Args:
            destinatario: Email del destinatario
            nit: NIT del cliente
            nombre_cliente: Nombre del cliente
            archivos_adjuntos: Lista de rutas a archivos adjuntos
            emails_copia: Lista de emails en copia (CC)
            prefijo_asunto: Prefijo del asunto
            
        Returns:
            Objeto MIMEMultipart con el mensaje completo
        """
        # Crear mensaje
        msg = MIMEMultipart()
        
        # Configurar remitente
        from_name = self.smtp_config.get('from_name', 'Sistema de Comprobantes')
        msg['From'] = formataddr((from_name, self.smtp_config['username']))
        
        # Destinatario
        msg['To'] = destinatario
        
        # Copias (CC)
        if emails_copia:
            msg['Cc'] = ', '.join(emails_copia)
        
        # Asunto (OBLIGATORIO con NIT)
        msg['Subject'] = self._construir_asunto(nit, nombre_cliente, prefijo_asunto)
        
        # Cuerpo del mensaje
        cantidad_archivos = len(archivos_adjuntos)
        cuerpo = f"""
Estimado/a {nombre_cliente},

Adjuntamos {cantidad_archivos} comprobante(s) correspondiente(s) a su NIT: {nit}.

Por favor, conserve estos documentos para su registro contable.

Saludos cordiales,
{from_name}

---
Este es un correo automático, por favor no responder.
"""
        
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
        
        # Adjuntar archivos
        for archivo in archivos_adjuntos:
            try:
                with open(archivo, 'rb') as f:
                    adjunto = MIMEApplication(f.read(), _subtype='pdf')
                    adjunto.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=os.path.basename(archivo)
                    )
                    msg.attach(adjunto)
            except Exception as e:
                self.logger.error(f"Error al adjuntar {archivo}: {e}", 
                                modulo="EmailSender", exc_info=True)
        
        return msg
    
    def _clasificar_error(self, excepcion):
        """
        Clasifica el tipo de error de envío
        
        Args:
            excepcion: Excepción capturada
            
        Returns:
            Estado del envío (REBOTADO, BLOQUEADO, INEXISTENTE, ERROR)
        """
        mensaje_error = str(excepcion).lower()
        
        # Correo inexistente
        if any(x in mensaje_error for x in ['user unknown', 'recipient rejected', 
                                             'address rejected', 'no such user',
                                             '550', 'mailbox not found']):
            return 'INEXISTENTE'
        
        # Correo bloqueado
        if any(x in mensaje_error for x in ['blocked', 'blacklisted', 'spam',
                                            '554', 'refused', 'denied']):
            return 'BLOQUEADO'
        
        # Rebote
        if any(x in mensaje_error for x in ['bounce', 'delivery failed',
                                            '552', '553', 'mailbox full']):
            return 'REBOTADO'
        
        # Error genérico
        return 'ERROR'
    
    def enviar_correo(self, nit, nombre_cliente, email_destino, archivos_adjuntos,
                     emails_copia=None, prefijo_asunto="Comprobante - NIT: ",
                     modo_prueba=False, usuario_operativa=None):
        """
        Envía un correo a un cliente
        
        Args:
            nit: NIT del cliente
            nombre_cliente: Nombre del cliente
            email_destino: Email principal del destinatario
            archivos_adjuntos: Lista de rutas a archivos PDF
            emails_copia: Lista de emails en copia (CC)
            prefijo_asunto: Prefijo del asunto
            modo_prueba: Si es True, simula el envío sin enviar realmente
            usuario_operativa: Usuario que realiza el envío
            
        Returns:
            Tupla (exito, estado, mensaje)
        """
        # Validar configuración
        es_valido, mensaje = self._validar_configuracion()
        if not es_valido:
            self.logger.error(f"Configuración SMTP inválida: {mensaje}", 
                            modulo="EmailSender")
            return False, 'ERROR', mensaje
        
        # Validar destinatario
        es_valido, mensaje = Validator.validar_email(email_destino)
        if not es_valido:
            self.logger.error(f"Email inválido: {mensaje}", modulo="EmailSender")
            return False, 'ERROR', mensaje
        
        # Validar archivos
        if not archivos_adjuntos:
            mensaje = f"No hay archivos para enviar al cliente {nombre_cliente} (NIT: {nit})"
            self.logger.warning(mensaje, modulo="EmailSender")
            return False, 'ERROR', mensaje
        
        # Verificar que los archivos existan
        archivos_validos = []
        for archivo in archivos_adjuntos:
            if os.path.exists(archivo):
                archivos_validos.append(archivo)
            else:
                self.logger.warning(f"Archivo no encontrado: {archivo}", 
                                  modulo="EmailSender")
        
        if not archivos_validos:
            mensaje = f"Ningún archivo válido para enviar"
            return False, 'ERROR', mensaje
        
        # Modo prueba: solo simular
        if modo_prueba:
            self.logger.info(
                f"[MODO PRUEBA] Simulando envío a {nombre_cliente} ({nit}) - {email_destino}",
                modulo="EmailSender"
            )
            
            # Registrar en base de datos como prueba
            if self.db_manager:
                self.db_manager.registrar_envio(
                    nit, nombre_cliente, email_destino,
                    ', '.join(emails_copia) if emails_copia else '',
                    len(archivos_validos),
                    ', '.join([os.path.basename(a) for a in archivos_validos]),
                    'ENVIADO',
                    None,
                    usuario_operativa,
                    modo_prueba=True
                )
            
            self.stats['enviados'] += 1
            return True, 'ENVIADO', 'Envío simulado en modo prueba'
        
        # Envío real
        try:
            # Conectar a SMTP
            server, error = self._conectar_smtp()
            if not server:
                self.stats['errores'] += 1
                return False, 'ERROR', error
            
            # Construir mensaje
            msg = self._construir_mensaje(
                email_destino, nit, nombre_cliente,
                archivos_validos, emails_copia, prefijo_asunto
            )
            
            # Lista de destinatarios (To + CC)
            destinatarios = [email_destino]
            if emails_copia:
                destinatarios.extend(emails_copia)
            
            # Enviar
            server.send_message(msg)
            server.quit()
            
            # Éxito
            self.logger.log_envio(nit, nombre_cliente, email_destino, 'ENVIADO')
            self.stats['enviados'] += 1
            
            # Registrar en base de datos
            if self.db_manager:
                self.db_manager.registrar_envio(
                    nit, nombre_cliente, email_destino,
                    ', '.join(emails_copia) if emails_copia else '',
                    len(archivos_validos),
                    ', '.join([os.path.basename(a) for a in archivos_validos]),
                    'ENVIADO',
                    None,
                    usuario_operativa
                )
            
            return True, 'ENVIADO', 'Correo enviado exitosamente'
        
        except smtplib.SMTPRecipientsRefused as e:
            estado = self._clasificar_error(e)
            mensaje = f"Destinatario rechazado: {str(e)}"
            self.logger.log_envio(nit, nombre_cliente, email_destino, estado, mensaje)
            self.stats[estado.lower()] += 1
            
            # Registrar en base de datos
            if self.db_manager:
                self.db_manager.registrar_envio(
                    nit, nombre_cliente, email_destino,
                    ', '.join(emails_copia) if emails_copia else '',
                    len(archivos_validos),
                    ', '.join([os.path.basename(a) for a in archivos_validos]),
                    estado,
                    mensaje,
                    usuario_operativa
                )
            
            return False, estado, mensaje
        
        except Exception as e:
            estado = self._clasificar_error(e)
            mensaje = f"Error al enviar: {str(e)}"
            self.logger.log_envio(nit, nombre_cliente, email_destino, estado, mensaje)
            self.stats['errores'] += 1
            
            # Registrar en base de datos
            if self.db_manager:
                self.db_manager.registrar_envio(
                    nit, nombre_cliente, email_destino,
                    ', '.join(emails_copia) if emails_copia else '',
                    len(archivos_validos),
                    ', '.join([os.path.basename(a) for a in archivos_validos]),
                    estado,
                    mensaje,
                    usuario_operativa
                )
            
            return False, estado, mensaje
    
    def enviar_lote(self, clientes_con_archivos, emails_copia=None, 
                   modo_prueba=False, usuario_operativa=None, callback_progreso=None):
        """
        Envía correos a un lote de clientes
        
        Args:
            clientes_con_archivos: Lista de diccionarios con formato:
                {'nit': str, 'nombre': str, 'email': str, 'archivos': [list]}
            emails_copia: Lista de emails en copia (CC)
            modo_prueba: Si es True, simula los envíos
            usuario_operativa: Usuario que realiza el envío
            callback_progreso: Función a llamar después de cada envío
                Recibe: (indice, total, cliente, exito, estado, mensaje)
        
        Returns:
            Diccionario con resultados del lote
        """
        total = len(clientes_con_archivos)
        resultados = []
        
        self.logger.info(f"Iniciando envío de lote: {total} clientes", 
                       modulo="EmailSender")
        
        for i, cliente in enumerate(clientes_con_archivos, 1):
            nit = cliente['nit']
            nombre = cliente['nombre']
            email = cliente['email']
            archivos = cliente['archivos']
            
            # Enviar correo
            exito, estado, mensaje = self.enviar_correo(
                nit, nombre, email, archivos,
                emails_copia, modo_prueba=modo_prueba,
                usuario_operativa=usuario_operativa
            )
            
            # Guardar resultado
            resultado = {
                'nit': nit,
                'nombre': nombre,
                'email': email,
                'exito': exito,
                'estado': estado,
                'mensaje': mensaje,
                'cantidad_archivos': len(archivos)
            }
            resultados.append(resultado)
            
            # Callback de progreso
            if callback_progreso:
                callback_progreso(i, total, cliente, exito, estado, mensaje)
        
        # Resumen final
        resumen = {
            'total': total,
            'enviados': self.stats['enviados'],
            'errores': self.stats['errores'],
            'rebotados': self.stats['rebotados'],
            'bloqueados': self.stats['bloqueados'],
            'inexistentes': self.stats['inexistentes'],
            'resultados': resultados
        }
        
        self.logger.info(
            f"Lote completado: {self.stats['enviados']}/{total} enviados exitosamente",
            modulo="EmailSender"
        )
        
        return resumen
    
    def probar_conexion(self):
        """
        Prueba la conexión SMTP
        
        Returns:
            Tupla (exito, mensaje)
        """
        es_valido, mensaje = self._validar_configuracion()
        if not es_valido:
            return False, mensaje
        
        server, error = self._conectar_smtp()
        if not server:
            return False, error
        
        try:
            server.quit()
            return True, "Conexión SMTP exitosa"
        except:
            return True, "Conexión establecida (no se pudo cerrar correctamente)"
    
    def obtener_estadisticas(self):
        """
        Obtiene las estadísticas de envío
        
        Returns:
            Diccionario con estadísticas
        """
        return self.stats.copy()
    
    def reiniciar_estadisticas(self):
        """Reinicia las estadísticas de envío"""
        self.stats = {
            'enviados': 0,
            'errores': 0,
            'rebotados': 0,
            'bloqueados': 0,
            'inexistentes': 0
        }