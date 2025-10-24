"""
Validadores para datos de entrada del sistema
"""

import re
from typing import Tuple, List


class Validator:
    """Clase para validar datos de entrada"""
    
    # Expresión regular para validar emails
    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    # Expresión regular para validar NIT colombiano
    # Formato: 8-9 dígitos + guion + dígito verificador (ej: 12345678-9 o 123456789-0)
    NIT_REGEX = re.compile(r'^\d{8,10}-?\d$')
    
    @staticmethod
    def validar_email(email: str) -> Tuple[bool, str]:
        """
        Valida un email
        
        Args:
            email: Email a validar
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        if not email:
            return False, "El email no puede estar vacío"
        
        email = email.strip()
        
        if not Validator.EMAIL_REGEX.match(email):
            return False, f"Email inválido: {email}"
        
        return True, ""
    
    @staticmethod
    def validar_lista_emails(emails: str) -> Tuple[bool, str, List[str]]:
        """
        Valida una lista de emails separados por coma o punto y coma
        
        Args:
            emails: String con emails separados por coma o punto y coma
            
        Returns:
            Tupla (es_valido, mensaje_error, lista_emails_validos)
        """
        if not emails:
            return True, "", []
        
        # Separar por coma o punto y coma
        separadores = [',', ';']
        lista_emails = [emails]
        
        for sep in separadores:
            nueva_lista = []
            for email in lista_emails:
                nueva_lista.extend(email.split(sep))
            lista_emails = nueva_lista
        
        # Limpiar espacios
        lista_emails = [email.strip() for email in lista_emails if email.strip()]
        
        # Validar cada email
        emails_invalidos = []
        emails_validos = []
        
        for email in lista_emails:
            es_valido, mensaje = Validator.validar_email(email)
            if es_valido:
                emails_validos.append(email)
            else:
                emails_invalidos.append(email)
        
        if emails_invalidos:
            return False, f"Emails inválidos: {', '.join(emails_invalidos)}", emails_validos
        
        return True, "", emails_validos
    
    @staticmethod
    def validar_nit(nit: str, validar_digito: bool = False) -> Tuple[bool, str]:
        """
        Valida un NIT colombiano
        
        Args:
            nit: NIT a validar
            validar_digito: Si True, valida el dígito verificador (opcional)
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        if not nit:
            return False, "El NIT no puede estar vacío"
        
        nit = str(nit).strip()
        
        # Aceptar NITs con 8, 9 o 10 dígitos (con o sin guion)
        import re
        if '-' in nit:
            # Formato con guion: 12345678-9 o 123456789-0
            if not re.match(r'^\d{8,9}-\d$', nit):
                return False, f"NIT con guion inválido: {nit}"
            
            # Si validar_digito es True, validar el verificador
            if validar_digito:
                partes = nit.split('-')
                numero = partes[0]
                digito_verificador_dado = int(partes[1])
                
                # Calcular verificador
                digito_calculado = Validator._calcular_digito_verificador(numero)
                if int(digito_calculado) != digito_verificador_dado:
                    return False, f"NIT inválido: dígito verificador incorrecto"
        else:
            # Sin guion: debe tener 8, 9 o 10 dígitos
            if not re.match(r'^\d{8,10}$', nit):
                return False, f"NIT debe tener entre 8 y 10 dígitos: {nit}"
        
        return True, ""
    
    @staticmethod
    def _calcular_digito_verificador(numero: str) -> str:
        """
        Calcula el dígito verificador de un NIT colombiano
        
        Args:
            numero: Número del NIT (8 o 9 dígitos)
            
        Returns:
            Dígito verificador calculado
        """
        pesos = [71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3]
        pesos_ajustados = pesos[-len(numero):]
        
        suma = sum(int(d) * p for d, p in zip(numero, pesos_ajustados))
        residuo = suma % 11
        
        if residuo in [0, 1]:
            return str(residuo)
        else:
            return str(11 - residuo)
    
    @staticmethod
    def nits_coinciden(nit1: str, nit2: str) -> bool:
        """
        Compara dos NITs (solo los números, sin guion ni verificador)
        
        Args:
            nit1: Primer NIT
            nit2: Segundo NIT
            
        Returns:
            True si los NITs coinciden
        """
        if not nit1 or not nit2:
            return False
        
        # Normalizar ambos (solo números)
        nit1_norm = Validator.normalizar_nit(nit1)
        nit2_norm = Validator.normalizar_nit(nit2)
        
        # Comparar directamente
        return nit1_norm == nit2_norm
    
    @staticmethod
    def normalizar_nit(nit: str) -> str:
        """
        Normaliza un NIT quitando guiones y caracteres no numéricos.
        NO elimina el último dígito salvo que haya evidencia de que es DV (guion).
        """
        import re
        if not nit:
            return ""
        nit = str(nit).strip()
    
        # Si tiene guion, tomar solo la parte antes del guion (asumimos DV después del guion)
        if '-' in nit:
            nit = nit.split('-')[0]
    
        # Quitar todo excepto dígitos
        nit = re.sub(r'\D', '', nit)
    
        # Ya NO quitamos el último dígito automáticamente cuando hay 10
        return nit

    
    @staticmethod
    def validar_archivo_excel(ruta_archivo: str) -> Tuple[bool, str]:
        """
        Valida que un archivo sea un Excel válido
        
        Args:
            ruta_archivo: Ruta al archivo
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        import os
        
        if not ruta_archivo:
            return False, "No se proporcionó ruta de archivo"
        
        if not os.path.exists(ruta_archivo):
            return False, f"El archivo no existe: {ruta_archivo}"
        
        extensiones_validas = ['.xlsx', '.xls', '.xlsm']
        extension = os.path.splitext(ruta_archivo)[1].lower()
        
        if extension not in extensiones_validas:
            return False, f"Extensión de archivo inválida: {extension}. Extensiones válidas: {', '.join(extensiones_validas)}"
        
        return True, ""
    
    @staticmethod
    def validar_archivo_zip(ruta_archivo: str) -> Tuple[bool, str]:
        """
        Valida que un archivo sea un ZIP válido
        
        Args:
            ruta_archivo: Ruta al archivo
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        import os
        import zipfile
        
        if not ruta_archivo:
            return False, "No se proporcionó ruta de archivo"
        
        if not os.path.exists(ruta_archivo):
            return False, f"El archivo no existe: {ruta_archivo}"
        
        extension = os.path.splitext(ruta_archivo)[1].lower()
        
        if extension != '.zip':
            return False, f"El archivo no es un ZIP: {extension}"
        
        # Verificar que el ZIP no esté corrupto
        try:
            with zipfile.ZipFile(ruta_archivo, 'r') as zip_ref:
                # Intentar listar los archivos
                zip_ref.namelist()
            return True, ""
        except zipfile.BadZipFile:
            return False, "El archivo ZIP está corrupto"
        except Exception as e:
            return False, f"Error al validar ZIP: {str(e)}"
    
    @staticmethod
    def validar_nombre_archivo_pdf(nombre_archivo: str, nit_esperado: str = None) -> Tuple[bool, str]:
        """
        Valida que un nombre de archivo PDF sea válido y coincida con el NIT esperado
        
        Args:
            nombre_archivo: Nombre del archivo
            nit_esperado: NIT que debería estar en el nombre (opcional)
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        import os
        
        if not nombre_archivo:
            return False, "Nombre de archivo vacío"
        
        # Verificar extensión
        extension = os.path.splitext(nombre_archivo)[1].lower()
        if extension != '.pdf':
            return False, f"El archivo no es un PDF: {nombre_archivo}"
        
        # Si se proporciona NIT esperado, verificar que esté en el nombre
        if nit_esperado:
            nit_normalizado = Validator.normalizar_nit(nit_esperado)
            nit_sin_guion = nit_normalizado.replace('-', '')
            
            # Buscar el NIT en el nombre del archivo (con o sin guion)
            if nit_normalizado not in nombre_archivo and nit_sin_guion not in nombre_archivo:
                return False, f"El archivo {nombre_archivo} no contiene el NIT {nit_esperado}"
        
        return True, ""
    
    @staticmethod
    def validar_asunto_con_nit(asunto: str, nit: str) -> Tuple[bool, str]:
        """
        Valida que un asunto de correo contenga el NIT
        
        Args:
            asunto: Asunto del correo
            nit: NIT que debe estar en el asunto
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        if not asunto:
            return False, "El asunto no puede estar vacío"
        
        if not nit:
            return False, "El NIT no puede estar vacío"
        
        nit_normalizado = Validator.normalizar_nit(nit)
        nit_sin_guion = nit_normalizado.replace('-', '')
        
        # Verificar que el NIT esté en el asunto (con o sin guion)
        if nit_normalizado not in asunto and nit_sin_guion not in asunto:
            return False, f"El asunto debe contener el NIT: {nit_normalizado}"
        
        return True, ""
    
    @staticmethod
    def validar_configuracion_smtp(servidor: str, puerto: int, usuario: str, password: str) -> Tuple[bool, str]:
        """s
        Valida la configuración SMTP
        
        Args:
            servidor: Servidor SMTP
            puerto: Puerto SMTP
            usuario: Usuario SMTP
            password: Contraseña SMTP
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        if not servidor:
            return False, "El servidor SMTP no puede estar vacío"
        
        if not puerto or puerto <= 0:
            return False, "El puerto SMTP debe ser un número positivo"
        
        if not usuario:
            return False, "El usuario SMTP no puede estar vacío"
        
        if not password:
            return False, "La contraseña SMTP no puede estar vacía"
        
        # Validar que el usuario sea un email válido
        es_valido, mensaje = Validator.validar_email(usuario)
        if not es_valido:
            return False, f"El usuario SMTP debe ser un email válido: {mensaje}"
        
        return True, ""