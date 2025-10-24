"""
Sistema de logging profesional para la aplicación
Registra logs en archivo y en base de datos
"""

import logging
import os
from datetime import datetime
from pathlib import Path

class AppLogger:
    """Manejador de logs de la aplicación"""
    
    def __init__(self, log_dir="logs", db_manager=None):
        """
        Inicializa el sistema de logging
        
        Args:
            log_dir: Directorio donde se guardarán los logs
            db_manager: Instancia de Database para logs en BD
        """
        self.log_dir = log_dir
        self.db_manager = db_manager
        self._ensure_log_directory()
        self._setup_logger()
    
    def _ensure_log_directory(self):
        """Crea el directorio de logs si no existe"""
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
    
    def _setup_logger(self):
        """Configura el logger de Python"""
        # Nombre del archivo de log con fecha
        log_filename = f"app_{datetime.now().strftime('%Y%m%d')}.log"
        log_path = os.path.join(self.log_dir, log_filename)
        
        # Configurar el logger
        self.logger = logging.getLogger("ComprobantesApp")
        self.logger.setLevel(logging.DEBUG)
        
        # Limpiar handlers existentes
        self.logger.handlers = []
        
        # Handler para archivo
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formato de los logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _log_to_db(self, nivel, modulo, mensaje, detalle=None):
        """
        Registra el log en la base de datos
        
        Args:
            nivel: Nivel del log
            modulo: Módulo que genera el log
            mensaje: Mensaje del log
            detalle: Detalle adicional
        """
        if self.db_manager:
            try:
                self.db_manager.registrar_log(nivel, modulo, mensaje, detalle)
            except Exception as e:
                # Si falla el log a BD, solo loguear en archivo
                self.logger.error(f"Error al registrar log en BD: {e}")
    
    def info(self, mensaje, modulo="General", detalle=None):
        """
        Registra un log de nivel INFO
        
        Args:
            mensaje: Mensaje del log
            modulo: Módulo que genera el log
            detalle: Detalle adicional
        """
        self.logger.info(f"[{modulo}] {mensaje}")
        self._log_to_db("INFO", modulo, mensaje, detalle)
    
    def warning(self, mensaje, modulo="General", detalle=None):
        """
        Registra un log de nivel WARNING
        
        Args:
            mensaje: Mensaje del log
            modulo: Módulo que genera el log
            detalle: Detalle adicional
        """
        self.logger.warning(f"[{modulo}] {mensaje}")
        self._log_to_db("WARNING", modulo, mensaje, detalle)
    
    def error(self, mensaje, modulo="General", detalle=None, exc_info=False):
        """
        Registra un log de nivel ERROR
        
        Args:
            mensaje: Mensaje del log
            modulo: Módulo que genera el log
            detalle: Detalle adicional
            exc_info: Si debe incluir información de excepción
        """
        self.logger.error(f"[{modulo}] {mensaje}", exc_info=exc_info)
        self._log_to_db("ERROR", modulo, mensaje, detalle)
    
    def critical(self, mensaje, modulo="General", detalle=None, exc_info=False):
        """
        Registra un log de nivel CRITICAL
        
        Args:
            mensaje: Mensaje del log
            modulo: Módulo que genera el log
            detalle: Detalle adicional
            exc_info: Si debe incluir información de excepción
        """
        self.logger.critical(f"[{modulo}] {mensaje}", exc_info=exc_info)
        self._log_to_db("CRITICAL", modulo, mensaje, detalle)
    
    def debug(self, mensaje, modulo="General"):
        """
        Registra un log de nivel DEBUG (solo en archivo, no en BD)
        
        Args:
            mensaje: Mensaje del log
            modulo: Módulo que genera el log
        """
        self.logger.debug(f"[{modulo}] {mensaje}")
    
    def log_envio(self, nit, nombre_cliente, email, estado, detalle=None):
        """
        Log específico para envíos de correo
        
        Args:
            nit: NIT del cliente
            nombre_cliente: Nombre del cliente
            email: Email destino
            estado: Estado del envío
            detalle: Detalle adicional
        """
        mensaje = f"Envío a {nombre_cliente} ({nit}) - {email} - Estado: {estado}"
        
        if estado in ["ERROR", "REBOTADO", "BLOQUEADO", "INEXISTENTE"]:
            self.error(mensaje, modulo="EmailSender", detalle=detalle)
        else:
            self.info(mensaje, modulo="EmailSender", detalle=detalle)
    
    def log_procesamiento_excel(self, archivo, registros_procesados, errores=0):
        """
        Log específico para procesamiento de Excel
        
        Args:
            archivo: Nombre del archivo Excel
            registros_procesados: Número de registros procesados
            errores: Número de errores encontrados
        """
        mensaje = f"Excel procesado: {archivo} - {registros_procesados} registros, {errores} errores"
        
        if errores > 0:
            self.warning(mensaje, modulo="ExcelProcessor")
        else:
            self.info(mensaje, modulo="ExcelProcessor")
    
    def log_procesamiento_zip(self, archivo, archivos_extraidos):
        """
        Log específico para procesamiento de ZIP
        
        Args:
            archivo: Nombre del archivo ZIP
            archivos_extraidos: Número de archivos extraídos
        """
        mensaje = f"ZIP procesado: {archivo} - {archivos_extraidos} archivos extraídos"
        self.info(mensaje, modulo="ZipHandler")
    
    def limpiar_logs_antiguos(self, dias=30):
        """
        Elimina archivos de log más antiguos que X días
        
        Args:
            dias: Número de días a mantener
        """
        try:
            from datetime import timedelta
            fecha_limite = datetime.now() - timedelta(days=dias)
            
            for archivo in Path(self.log_dir).glob("app_*.log"):
                # Extraer fecha del nombre del archivo
                try:
                    fecha_str = archivo.stem.split('_')[1]  # app_YYYYMMDD.log
                    fecha_archivo = datetime.strptime(fecha_str, '%Y%m%d')
                    
                    if fecha_archivo < fecha_limite:
                        archivo.unlink()
                        self.info(f"Log antiguo eliminado: {archivo.name}", modulo="Maintenance")
                except Exception as e:
                    self.warning(f"Error al procesar archivo de log {archivo}: {e}", modulo="Maintenance")
            
            # También limpiar logs de BD
            if self.db_manager:
                self.db_manager.limpiar_logs_antiguos(dias)
                self.info(f"Logs de BD más antiguos que {dias} días eliminados", modulo="Maintenance")
        
        except Exception as e:
            self.error(f"Error al limpiar logs antiguos: {e}", modulo="Maintenance", exc_info=True)


# Singleton global del logger
_logger_instance = None

def get_logger(log_dir="logs", db_manager=None):
    """
    Obtiene la instancia singleton del logger
    
    Args:
        log_dir: Directorio de logs
        db_manager: Instancia de Database
        
    Returns:
        Instancia de AppLogger
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = AppLogger(log_dir, db_manager)
    return _logger_instance