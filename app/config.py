"""
Manejador de configuración de la aplicación
Gestiona config.json y encriptación de contraseñas
"""

import json
import os
from pathlib import Path
from cryptography.fernet import Fernet
import base64


class ConfigManager:
    """Gestiona la configuración de la aplicación"""
    
    def __init__(self, config_file="config.json"):
        """
        Inicializa el manejador de configuración
        
        Args:
            config_file: Ruta al archivo de configuración
        """
        self.config_file = config_file
        self.config = self._load_config()
        self._ensure_directories()
        self._ensure_encryption_key()
    
    def _get_encryption_key(self):
        """
        Obtiene o genera la clave de encriptación
        Almacenada en un archivo oculto local
        """
        key_file = ".key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generar nueva clave
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # Hacer el archivo oculto en Windows
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(key_file, 2)
            except:
                pass
            
            return key
    
    def _ensure_encryption_key(self):
        self.cipher = Fernet(self._get_encryption_key())
    
    def _encrypt_password(self, password):
        """
        Encripta una contraseña
        
        Args:
            password: Contraseña en texto plano
            
        Returns:
            Contraseña encriptada en base64
        """
        if not password:
            return ""
        
        encrypted = self.cipher.encrypt(password.encode())
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_password(self, encrypted_password):
        """
        Desencripta una contraseña
        
        Args:
            encrypted_password: Contraseña encriptada
            
        Returns:
            Contraseña en texto plano
        """
        if not encrypted_password:
            return ""
        
        try:
            encrypted = base64.b64decode(encrypted_password.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception:
            return ""
    
    def _load_config(self):
        """Carga la configuración desde el archivo JSON"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self._default_config()
        else:
            config = self._default_config()
            self.save_config()
            return config
    
    def _default_config(self):
        """Retorna configuración por defecto"""
        from app.version import __version__
        
        return {
            "version": __version__,
            "smtp": {
                "server": "",
                "port": 587,
                "use_tls": True,
                "username": "",
                "password_encrypted": ""
            },
            "email": {
                "from_name": "Sistema de Comprobantes",
                "subject_prefix": "Comprobante - NIT: ",
                "emails_copia": [] 
            },
            "update": {
                "check_on_startup": True,
                "update_url": ""
            },
            "paths": {
                "logs": "logs/",
                "reports": "reportes/",
                "temp": "temp/",
                "data": "data/"
            },
            "test_mode": {
                "enabled": False,
                "test_email": ""
            },
            "ui": {
                "remember_last_files": True,
                "last_excel_path": "",
                "last_zip_path": ""
            }
        }
    
    def _ensure_directories(self):
        """Crea los directorios necesarios si no existen"""
        paths = self.config.get("paths", {})
        for path in paths.values():
            Path(path).mkdir(parents=True, exist_ok=True)
    
    def save_config(self):
        """Guarda la configuración actual al archivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error al guardar configuración: {e}")
            return False
    
    def get(self, key, default=None):
        """
        Obtiene un valor de configuración usando notación de punto
        
        Args:
            key: Clave en formato "seccion.subseccion.valor"
            default: Valor por defecto si no existe
            
        Returns:
            Valor de la configuración
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
            
            if value is default:
                break
        
        return value
    
    def set(self, key, value):
        """
        Establece un valor de configuración usando notación de punto
        
        Args:
            key: Clave en formato "seccion.subseccion.valor"
            value: Valor a establecer
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        
        config[keys[-1]] = value
        self.save_config()
    
    # Métodos específicos para SMTP
    
    def get_smtp_config(self):
        """
        Obtiene la configuración SMTP completa
        
        Returns:
            Diccionario con configuración SMTP (contraseña desencriptada)
        """
        smtp = self.config.get("smtp", {}).copy()
        
        # Desencriptar contraseña
        encrypted_password = smtp.get("password_encrypted", "")
        smtp["password"] = self._decrypt_password(encrypted_password)
        
        return smtp
    
    def set_smtp_config(self, server, port, username, password, use_tls=True):
        """
        Guarda la configuración SMTP
        
        Args:
            server: Servidor SMTP
            port: Puerto SMTP
            username: Usuario SMTP
            password: Contraseña (será encriptada)
            use_tls: Usar TLS
        """
        self.config["smtp"] = {
            "server": server,
            "port": port,
            "use_tls": use_tls,
            "username": username,
            "password_encrypted": self._encrypt_password(password)
        }
        self.save_config()
    
    def get_smtp_password(self):
        """Obtiene la contraseña SMTP desencriptada"""
        encrypted = self.get("smtp.password_encrypted", "")
        return self._decrypt_password(encrypted)
    
    # Métodos específicos para emails en copia (CC)
    
    def get_emails_copia(self):
        """
        Obtiene la lista de emails en copia
        
        Returns:
            Lista de emails
        """
        return self.get("email.emails_copia", [])
    
    def set_emails_copia(self, emails):
        """
        Guarda la lista de emails en copia
        
        Args:
            emails: Lista de emails o string separado por comas
        """
        if isinstance(emails, str):
            # Separar por coma o punto y coma
            emails = [e.strip() for e in emails.replace(';', ',').split(',') if e.strip()]
        
        self.set("email.emails_copia", emails)
    
    def add_email_copia(self, email):
        """
        Agrega un email a la lista de copia
        
        Args:
            email: Email a agregar
        """
        emails = self.get_emails_copia()
        if email not in emails:
            emails.append(email)
            self.set_emails_copia(emails)
    
    def remove_email_copia(self, email):
        """
        Elimina un email de la lista de copia
        
        Args:
            email: Email a eliminar
        """
        emails = self.get_emails_copia()
        if email in emails:
            emails.remove(email)
            self.set_emails_copia(emails)
    
    # Métodos específicos para modo de pruebas
    
    def is_test_mode(self):
        """Verifica si está en modo prueba"""
        return self.get("test_mode.enabled", False)
    
    def set_test_mode(self, enabled, test_email=""):
        """
        Activa/desactiva el modo de pruebas
        
        Args:
            enabled: True para activar, False para desactivar
            test_email: Email de prueba
        """
        self.set("test_mode.enabled", enabled)
        if test_email:
            self.set("test_mode.test_email", test_email)
    
    def get_test_email(self):
        """Obtiene el email de prueba"""
        return self.get("test_mode.test_email", "")
    
    # Métodos de validación
    
    def is_smtp_configured(self):
        """Verifica si SMTP está configurado"""
        smtp = self.get_smtp_config()
        return all([
            smtp.get("server"),
            smtp.get("username"),
            smtp.get("password")
        ])
    
    def validate_config(self):
        """
        Valida la configuración actual
        
        Returns:
            Tupla (es_valido, lista_errores)
        """
        errors = []
        
        # Validar SMTP
        if not self.is_smtp_configured():
            errors.append("Configuración SMTP incompleta")
        
        # Validar emails en copia
        from app.utils.validator import Validator
        
        emails_copia = self.get_emails_copia()
        for email in emails_copia:
            es_valido, mensaje = Validator.validar_email(email)
            if not es_valido:
                errors.append(f"Email en copia inválido: {email}")
        
        # Validar modo de pruebas
        if self.is_test_mode():
            test_email = self.get_test_email()
            if not test_email:
                errors.append("Modo de pruebas activado pero sin email de prueba")
            else:
                es_valido, mensaje = Validator.validar_email(test_email)
                if not es_valido:
                    errors.append(f"Email de prueba inválido: {mensaje}")
        
        return len(errors) == 0, errors
    
    # Métodos de UI
    
    def remember_file_path(self, file_type, path):
        """
        Recuerda la ruta del último archivo usado
        
        Args:
            file_type: 'excel' o 'zip'
            path: Ruta del archivo
        """
        if self.get("ui.remember_last_files", True):
            self.set(f"ui.last_{file_type}_path", path)
    
    def get_last_file_path(self, file_type):
        """
        Obtiene la última ruta de archivo usada
        
        Args:
            file_type: 'excel' o 'zip'
            
        Returns:
            Ruta del último archivo o string vacío
        """
        return self.get(f"ui.last_{file_type}_path", "")
    
    # Métodos de actualización
    
    def should_check_updates(self):
        """Verifica si debe buscar actualizaciones al iniciar"""
        return self.get("update.check_on_startup", True)
    
    def get_update_url(self):
        """Obtiene la URL de actualizaciones"""
        return self.get("update.update_url", "")
    
    def set_update_url(self, url):
        """Establece la URL de actualizaciones"""
        self.set("update.update_url", url)