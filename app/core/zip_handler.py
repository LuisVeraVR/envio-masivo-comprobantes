"""
Manejador de archivos ZIP
Extrae PDFs y los asocia con clientes por NIT
"""

import os
import zipfile
import shutil
from typing import List, Dict, Tuple
from pathlib import Path
from app.utils.validator import Validator
from app.utils.logger import get_logger


class ZipHandler:
    """Maneja archivos ZIP con comprobantes PDF"""
    
    def __init__(self, logger=None):
        """
        Inicializa el manejador de ZIP
        
        Args:
            logger: Instancia del logger (opcional)
        """
        self.logger = logger or get_logger()
        self.archivos_extraidos = []
        self.archivos_por_nit = {}  # {nit: [lista_rutas_pdf]}
        self.temp_dir = None
    
    def _crear_directorio_temporal(self):
        """
        Crea un directorio temporal para extraer archivos
        
        Returns:
            Ruta al directorio temporal
        """
        import time
        timestamp = int(time.time())
        temp_dir = f"temp/zip_extract_{timestamp}"
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    def _extraer_nit_de_nombre(self, nombre_archivo):
        """
        Extrae el NIT del nombre de un archivo PDF
        NO calcula dígito verificador - usa el número tal cual aparece
        
        Ejemplos:
        - _NIT._ 900059238 MAKRO... → 900059238
        - _NIT._ 901495289 MD... → 901495289
        
        Args:
            nombre_archivo: Nombre del archivo
            
        Returns:
            NIT extraído (solo números, sin guion ni verificador)
        """
        nombre = os.path.splitext(os.path.basename(nombre_archivo))[0]
        
        import re
        
        # Buscar "NIT._" o "NIT._ " CERCA DEL INICIO
        patron_nit_punto = r'^[_\s]*NIT\._?\s*(\d{8,10})'
        match = re.search(patron_nit_punto, nombre, re.IGNORECASE)
        
        if match:
            nit_numeros = match.group(1)
            
            # FILTRO: Rechazar cédulas muy cortas (7 dígitos o menos)
            if len(nit_numeros) <= 7:
                return None
            
            # FILTRO: Si el número aparece cerca de "ORF_" o "F_" es factura
            if re.search(r'[FO]R?F[_\s]+0*' + nit_numeros + r'\b', nombre):
                return None
            
            # Retornar solo el número, SIN calcular verificador
            return nit_numeros
        
        # Patrón 2: NIT con guion (quitar el guion)
        patron_con_guion = r'\b(\d{8,10})-\d\b'
        match = re.search(patron_con_guion, nombre)
        if match:
            contexto = nombre[max(0, match.start()-15):match.end()+5]
            if 'ORF' not in contexto.upper():
                return match.group(1)  # Solo la parte antes del guion
        
        return None
    
    def _calcular_digito_verificador(self, numero):
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
    
    def procesar_zip(self, ruta_zip, temp_dir=None):
        """
        Procesa un archivo ZIP y extrae los PDFs
        
        Args:
            ruta_zip: Ruta al archivo ZIP
            temp_dir: Directorio temporal (opcional, se crea automáticamente)
            
        Returns:
            Tupla (exito, mensaje, archivos_por_nit)
        """
        self.archivos_extraidos = []
        self.archivos_por_nit = {}
        
        # Validar ZIP
        es_valido, mensaje = Validator.validar_archivo_zip(ruta_zip)
        if not es_valido:
            self.logger.error(f"Archivo ZIP inválido: {mensaje}", modulo="ZipHandler")
            return False, mensaje, {}
        
        # Crear directorio temporal
        if temp_dir:
            self.temp_dir = temp_dir
        else:
            self.temp_dir = self._crear_directorio_temporal()
        
        try:
            self.logger.info(f"Procesando archivo ZIP: {os.path.basename(ruta_zip)}", 
                           modulo="ZipHandler")
            
            # Extraer ZIP
            with zipfile.ZipFile(ruta_zip, 'r') as zip_ref:
                # Obtener lista de archivos PDF
                archivos = [f for f in zip_ref.namelist() 
                           if f.lower().endswith('.pdf') and not f.startswith('__MACOSX')]
                
                if not archivos:
                    mensaje = "No se encontraron archivos PDF en el ZIP"
                    self.logger.warning(mensaje, modulo="ZipHandler")
                    return False, mensaje, {}
                
                self.logger.info(f"Encontrados {len(archivos)} archivos PDF", modulo="ZipHandler")
                
                # Extraer cada PDF
                pdfs_sin_nit = []
                
                for archivo in archivos:
                    try:
                        # Extraer archivo
                        zip_ref.extract(archivo, self.temp_dir)
                        ruta_extraida = os.path.join(self.temp_dir, archivo)
                        
                        self.archivos_extraidos.append(ruta_extraida)
                        
                        # Intentar extraer NIT del nombre
                        nit = self._extraer_nit_de_nombre(archivo)
                        
                        if nit:
                            # Agregar a diccionario por NIT
                            if nit not in self.archivos_por_nit:
                                self.archivos_por_nit[nit] = []
                            
                            self.archivos_por_nit[nit].append(ruta_extraida)
                            
                            self.logger.debug(
                                f"PDF asociado: {os.path.basename(archivo)} -> NIT {nit}",
                                modulo="ZipHandler"
                            )
                        else:
                            pdfs_sin_nit.append(archivo)
                            self.logger.warning(
                                f"No se pudo extraer NIT de: {archivo}",
                                modulo="ZipHandler"
                            )
                    
                    except Exception as e:
                        self.logger.error(
                            f"Error al extraer {archivo}: {e}",
                            modulo="ZipHandler",
                            exc_info=True
                        )
            
            # Log del procesamiento
            self.logger.log_procesamiento_zip(
                os.path.basename(ruta_zip),
                len(self.archivos_extraidos)
            )
            
            # Construir mensaje de resultado
            mensaje_partes = []
            mensaje_partes.append(f"Extraídos {len(self.archivos_extraidos)} archivos PDF")
            mensaje_partes.append(f"Agrupados en {len(self.archivos_por_nit)} NITs diferentes")
            
            if pdfs_sin_nit:
                mensaje_partes.append(f"⚠️ {len(pdfs_sin_nit)} archivos sin NIT identificable")
            
            mensaje = "\n".join(mensaje_partes)
            
            # Advertencia si no se agruparon archivos
            if not self.archivos_por_nit:
                return False, "No se pudieron asociar archivos a ningún NIT", {}
            
            return True, mensaje, self.archivos_por_nit
        
        except Exception as e:
            mensaje = f"Error al procesar ZIP: {str(e)}"
            self.logger.error(mensaje, modulo="ZipHandler", exc_info=True)
            return False, mensaje, {}
    
    def obtener_archivos_por_nit(self, nit):
        """
        Obtiene la lista de archivos asociados a un NIT
        Usa comparación flexible ignorando el dígito verificador
        
        Args:
            nit: NIT del cliente
            
        Returns:
            Lista de rutas a archivos PDF
        """
        from app.utils.validator import Validator
        
        nit_normalizado = Validator.normalizar_nit(nit)
        
        # Primero buscar coincidencia exacta
        if nit_normalizado in self.archivos_por_nit:
            return self.archivos_por_nit[nit_normalizado]
        
        # Buscar coincidencia flexible (ignorando dígito verificador)
        for nit_archivo, archivos in self.archivos_por_nit.items():
            if Validator.nits_coinciden(nit_normalizado, nit_archivo):
                return archivos
        
        return []
    
    def buscar_archivos_por_nit_flexible(self, nit_buscado, nombre_cliente=None):
        """
        Busca archivos por NIT de forma flexible
        Si no encuentra por NIT, busca por nombre de empresa
        
        Args:
            nit_buscado: NIT a buscar
            nombre_cliente: Nombre del cliente (opcional, para buscar por nombre)
            
        Returns:
            Lista de rutas a archivos PDF que coinciden
        """
        nit_normalizado = Validator.normalizar_nit(nit_buscado)
        nit_sin_guion = nit_normalizado.replace('-', '')
        
        # 1. Buscar coincidencia exacta
        if nit_normalizado in self.archivos_por_nit:
            return self.archivos_por_nit[nit_normalizado]
        
        # 2. Buscar coincidencia flexible por NIT en diccionario
        for nit_archivo, archivos in self.archivos_por_nit.items():
            if Validator.nits_coinciden(nit_normalizado, nit_archivo):
                return archivos
        
        # 3. Buscar en nombres de archivos
        archivos_encontrados = []
        for ruta_archivo in self.archivos_extraidos:
            nombre = os.path.basename(ruta_archivo)
            if nit_normalizado in nombre or nit_sin_guion in nombre:
                archivos_encontrados.append(ruta_archivo)
        
        if archivos_encontrados:
            return archivos_encontrados
        
        # 4. NUEVO: Buscar por nombre de empresa
        if nombre_cliente:
            archivos_encontrados = self._buscar_por_nombre_empresa(nombre_cliente)
            if archivos_encontrados:
                self.logger.info(
                    f"Archivo encontrado por nombre: {nombre_cliente[:40]}... -> {os.path.basename(archivos_encontrados[0])}",
                    modulo="ZipHandler"
                )
                return archivos_encontrados
        
        return []
    
    def _buscar_por_nombre_empresa(self, nombre_cliente):
        """
        Busca archivos por similitud en el nombre de la empresa
        
        Args:
            nombre_cliente: Nombre del cliente a buscar
            
        Returns:
            Lista de archivos que coinciden
        """
        if not nombre_cliente:
            return []
        
        # Normalizar nombre
        nombre_norm = self._normalizar_texto(nombre_cliente)
        
        # Extraer palabras significativas (>= 4 caracteres, no comunes)
        palabras_ignorar = {
            'sas', 's.a.s', 'sa', 's.a', 'ltda', 'limitada',
            'sociedad', 'por', 'acciones', 'simplificada',
            'comercializadora', 'distribuidora', 'inversiones',
            'productos', 'servicios', 'empresa', 'compania',
            'cia', 'de', 'del', 'la', 'el', 'y', 'e', 'los', 'las'
        }
        
        palabras = [p for p in nombre_norm.split() if len(p) >= 4 and p not in palabras_ignorar]
        
        if not palabras:
            palabras = nombre_norm.split()[:3]
        
        # Buscar archivos con coincidencias
        candidatos = []
        for ruta in self.archivos_extraidos:
            nombre_archivo = self._normalizar_texto(os.path.basename(ruta))
            
            # Contar coincidencias
            score = sum(1 for p in palabras if p in nombre_archivo)
            
            # Si al menos 50% de palabras coinciden
            if score >= len(palabras) * 0.5:
                candidatos.append((ruta, score))
        
        # Ordenar por score
        candidatos.sort(key=lambda x: x[1], reverse=True)
        
        return [archivo for archivo, _ in candidatos]
    
    def _normalizar_texto(self, texto):
        """Normaliza texto para comparación"""
        import re
        import unicodedata
        
        if not texto:
            return ""
        
        texto = str(texto).lower()
        texto = unicodedata.normalize('NFKD', texto)
        texto = texto.encode('ASCII', 'ignore').decode('ASCII')
        texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto)
        
        return texto.strip()
    
    def obtener_todos_los_nits(self):
        """
        Obtiene la lista de todos los NITs encontrados
        
        Returns:
            Lista de NITs
        """
        return list(self.archivos_por_nit.keys())
    
    def validar_archivos_contra_clientes(self, lista_clientes):
        """
        Valida que los archivos del ZIP coincidan con los clientes del Excel
        Usa comparación flexible ignorando el dígito verificador
        
        Args:
            lista_clientes: Lista de diccionarios con datos de clientes
            
        Returns:
            Diccionario con estadísticas de coincidencias
        """
        from app.utils.validator import Validator
        
        nits_excel = [Validator.normalizar_nit(cliente['nit']) for cliente in lista_clientes]
        nits_zip = list(self.obtener_todos_los_nits())
        
        # Encontrar coincidencias flexibles
        nits_coincidentes = []
        clientes_sin_archivos = []  # Guardar datos completos del cliente
        
        for cliente in lista_clientes:
            nit_excel = Validator.normalizar_nit(cliente['nit'])
            encontrado = False
            
            for nit_zip in nits_zip:
                if Validator.nits_coinciden(nit_excel, nit_zip):
                    encontrado = True
                    if nit_excel not in nits_coincidentes:
                        nits_coincidentes.append(nit_excel)
                    break
            
            if not encontrado:
                clientes_sin_archivos.append({
                    'nit': cliente['nit'],
                    'nombre': cliente['nombre'],
                    'email': cliente['email']
                })
        
        # Encontrar archivos sin cliente (con nombre completo del archivo)
        archivos_sin_cliente = []
        for nit_zip in nits_zip:
            encontrado = False
            for nit_excel in nits_excel:
                if Validator.nits_coinciden(nit_excel, nit_zip):
                    encontrado = True
                    break
            
            if not encontrado:
                # Buscar el nombre completo del archivo
                archivos_nit = self.archivos_por_nit.get(nit_zip, [])
                for archivo in archivos_nit:
                    nombre_archivo = os.path.basename(archivo)
                    archivos_sin_cliente.append({
                        'nit': nit_zip,
                        'archivo': nombre_archivo
                    })
        
        resultado = {
            'total_excel': len(nits_excel),
            'total_zip': len(nits_zip),
            'coincidentes': len(nits_coincidentes),
            'sin_archivos': clientes_sin_archivos,
            'sin_cliente': archivos_sin_cliente
        }
        
        # Log detallado
        if clientes_sin_archivos:
            self.logger.warning(
                f"=== {len(clientes_sin_archivos)} CLIENTES SIN ARCHIVOS ===",
                modulo="ZipHandler"
            )
            for i, cliente in enumerate(clientes_sin_archivos[:20], 1):  # Primeros 20
                self.logger.warning(
                    f"  {i}. NIT: {cliente['nit']} | Nombre: {cliente['nombre'][:50]} | Email: {cliente['email']}",
                    modulo="ZipHandler"
                )
            if len(clientes_sin_archivos) > 20:
                self.logger.warning(
                    f"  ... y {len(clientes_sin_archivos) - 20} más",
                    modulo="ZipHandler"
                )
        
        if archivos_sin_cliente:
            self.logger.warning(
                f"=== {len(archivos_sin_cliente)} ARCHIVOS SIN CLIENTE ===",
                modulo="ZipHandler"
            )
            for i, info in enumerate(archivos_sin_cliente[:20], 1):  # Primeros 20
                self.logger.warning(
                    f"  {i}. NIT: {info['nit']} | Archivo: {info['archivo']}",
                    modulo="ZipHandler"
                )
            if len(archivos_sin_cliente) > 20:
                self.logger.warning(
                    f"  ... y {len(archivos_sin_cliente) - 20} más",
                    modulo="ZipHandler"
                )
        
        return resultado
    
    def limpiar_temporales(self):
        """Elimina los archivos temporales extraídos"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.logger.debug(f"Directorio temporal eliminado: {self.temp_dir}", 
                                modulo="ZipHandler")
                self.temp_dir = None
            except Exception as e:
                self.logger.error(f"Error al eliminar temporales: {e}", 
                                modulo="ZipHandler")
    
    def obtener_resumen(self):
        """
        Genera un resumen del procesamiento
        
        Returns:
            Diccionario con estadísticas
        """
        total_archivos = sum(len(archivos) for archivos in self.archivos_por_nit.values())
        
        # Encontrar NIT con más archivos
        nit_con_mas_archivos = None
        max_archivos = 0
        
        for nit, archivos in self.archivos_por_nit.items():
            if len(archivos) > max_archivos:
                max_archivos = len(archivos)
                nit_con_mas_archivos = nit
        
        return {
            'total_archivos': total_archivos,
            'total_nits': len(self.archivos_por_nit),
            'promedio_archivos_por_nit': total_archivos / len(self.archivos_por_nit) if self.archivos_por_nit else 0,
            'nit_con_mas_archivos': nit_con_mas_archivos,
            'max_archivos_por_nit': max_archivos
        }
    
    def __del__(self):
        """Destructor: limpia archivos temporales al eliminar el objeto"""
        self.limpiar_temporales()