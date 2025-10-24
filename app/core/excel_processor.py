"""
Procesador de archivos Excel
Extrae información de clientes (NIT, Nombre, Email)
"""

import os
from typing import List, Dict, Tuple
import openpyxl
import pandas as pd
from app.utils.validator import Validator
from app.utils.logger import get_logger


class ExcelProcessor:
    """Procesa archivos Excel con datos de clientes"""
    
    # Nombres de columnas esperadas (case-insensitive)
    COLUMN_NAMES = {
        'nit': ['nit', 'nit_comprador', 'numero_identificacion', 'identificacion', 'num_id'],
        'nombre': ['nombre', 'nombre_del_comprador', 'nombre_comprador', 'nombre_cliente', 'razon_social', 'cliente', 'empresa'],
        'email': ['email', 'correos', 'correo', 'correo_electronico', 'e-mail', 'mail']
    }
    
    def __init__(self, logger=None):
        """
        Inicializa el procesador de Excel
        
        Args:
            logger: Instancia del logger (opcional)
        """
        self.logger = logger or get_logger()
        self.clientes = []
        self.errores = []
    
    def _normalizar_columna(self, nombre_columna):
        """
        Normaliza el nombre de una columna para comparación
        
        Args:
            nombre_columna: Nombre original de la columna
            
        Returns:
            Nombre normalizado
        """
        return str(nombre_columna).lower().strip().replace(' ', '_')
    
    def _detectar_columnas(self, df):
        """
        Detecta las columnas de NIT, Nombre y Email en el DataFrame
        
        Args:
            df: DataFrame de pandas
            
        Returns:
            Diccionario con los nombres de columnas detectadas
        """
        columnas_detectadas = {
            'nit': None,
            'nombre': None,
            'email': None
        }
        
        # Normalizar nombres de columnas del DataFrame
        columnas_df = {col: self._normalizar_columna(col) for col in df.columns}
        
        # Buscar cada tipo de columna
        for tipo, nombres_posibles in self.COLUMN_NAMES.items():
            for col_original, col_normalizada in columnas_df.items():
                if col_normalizada in nombres_posibles:
                    columnas_detectadas[tipo] = col_original
                    break
        
        return columnas_detectadas
    
    def _validar_columnas(self, columnas):
        """
        Valida que se hayan detectado todas las columnas necesarias
        
        Args:
            columnas: Diccionario de columnas detectadas
            
        Returns:
            Tupla (es_valido, mensaje_error)
        """
        columnas_faltantes = [tipo for tipo, col in columnas.items() if col is None]
        
        if columnas_faltantes:
            return False, f"No se encontraron las columnas: {', '.join(columnas_faltantes)}"
        
        return True, ""
    
    def procesar_archivo(self, ruta_excel):
        """
        Procesa un archivo Excel y extrae los datos de clientes
        
        Args:
            ruta_excel: Ruta al archivo Excel
            
        Returns:
            Tupla (exito, mensaje, lista_clientes)
        """
        self.clientes = []
        self.errores = []
        
        # Validar que el archivo existe y es Excel
        es_valido, mensaje = Validator.validar_archivo_excel(ruta_excel)
        if not es_valido:
            self.logger.error(f"Archivo Excel inválido: {mensaje}", modulo="ExcelProcessor")
            return False, mensaje, []
        
        try:
            # Leer Excel con pandas
            self.logger.info(f"Procesando archivo Excel: {os.path.basename(ruta_excel)}", 
                           modulo="ExcelProcessor")
            
            df = pd.read_excel(ruta_excel, engine='openpyxl')
            
            # Detectar columnas
            columnas = self._detectar_columnas(df)
            es_valido, mensaje = self._validar_columnas(columnas)
            
            if not es_valido:
                self.logger.error(mensaje, modulo="ExcelProcessor")
                return False, mensaje, []
            
            self.logger.info(f"Columnas detectadas: NIT={columnas['nit']}, "
                           f"Nombre={columnas['nombre']}, Email={columnas['email']}", 
                           modulo="ExcelProcessor")
            
            # Procesar cada fila
            registros_procesados = 0
            registros_con_error = 0
            
            for index, row in df.iterrows():
                try:
                    # Obtener valores de las columnas
                    nit_raw = row[columnas['nit']]
                    nombre_raw = row[columnas['nombre']]
                    email_raw = row[columnas['email']]
                    
                    # Convertir NIT correctamente (manejar float)
                    if pd.notna(nit_raw) and isinstance(nit_raw, (int, float)):
                        nit = str(int(nit_raw))
                    else:
                        nit = str(nit_raw).strip()
                    
                    # Convertir nombre
                    nombre = str(nombre_raw).strip() if pd.notna(nombre_raw) else ""
                    
                    # Convertir email
                    email = str(email_raw).strip() if pd.notna(email_raw) else ""
                    
                    # Saltar filas vacías
                    if not nit or nit.lower() in ['nan', 'none', '']:
                        continue
                    
                    # Validar NIT
                    es_valido_nit, mensaje_nit = Validator.validar_nit(nit)
                    if not es_valido_nit:
                        error = f"Fila {index + 2}: {mensaje_nit}"
                        self.errores.append(error)
                        registros_con_error += 1
                        continue
                    
                    # Normalizar NIT
                    nit = Validator.normalizar_nit(nit)
                    
                    # ✅ CORRECCIÓN: Validar lista de emails (soporta múltiples emails)
                    es_valido_email, mensaje_email, lista_emails = Validator.validar_lista_emails(email)
                    if not es_valido_email:
                        error = f"Fila {index + 2}: {mensaje_email}"
                        self.errores.append(error)
                        registros_con_error += 1
                        continue
                    
                    # Si hay emails válidos, reunirlos con punto y coma
                    if lista_emails:
                        email = "; ".join(lista_emails)
                    else:
                        error = f"Fila {index + 2}: No se encontraron emails válidos"
                        self.errores.append(error)
                        registros_con_error += 1
                        continue
                    
                    # Validar nombre
                    if not nombre or nombre.lower() in ['nan', 'none', '']:
                        error = f"Fila {index + 2}: Nombre de cliente vacío"
                        self.errores.append(error)
                        registros_con_error += 1
                        continue
                    
                    # Agregar cliente válido
                    cliente = {
                        'nit': nit,
                        'nombre': nombre,
                        'email': email,  # Ahora puede contener múltiples emails separados por "; "
                        'fila': index + 2  # +2 porque index empieza en 0 y hay fila de encabezados
                    }
                    
                    self.clientes.append(cliente)
                    registros_procesados += 1
                
                except Exception as e:
                    error = f"Fila {index + 2}: Error al procesar - {str(e)}"
                    self.errores.append(error)
                    registros_con_error += 1
                    self.logger.error(error, modulo="ExcelProcessor", exc_info=True)
            
            # Log del procesamiento
            self.logger.info(
                f"Procesamiento Excel completado: {os.path.basename(ruta_excel)} | "
                f"Registros procesados: {registros_procesados} | "
                f"Registros con error: {registros_con_error}",
                modulo="ExcelProcessor"
            )
            
            if registros_procesados == 0:
                mensaje = "No se encontraron registros válidos en el Excel"
                if self.errores:
                    mensaje += f"\n\nErrores encontrados:\n" + "\n".join(self.errores[:10])
                    if len(self.errores) > 10:
                        mensaje += f"\n... y {len(self.errores) - 10} errores más"
                
                return False, mensaje, []
            
            mensaje = f"Procesados {registros_procesados} clientes correctamente"
            if registros_con_error > 0:
                mensaje += f" ({registros_con_error} con errores)"
            
            return True, mensaje, self.clientes
        
        except Exception as e:
            mensaje = f"Error al leer el archivo Excel: {str(e)}"
            self.logger.error(mensaje, modulo="ExcelProcessor", exc_info=True)
            return False, mensaje, []
    
    def obtener_clientes(self):
        """
        Obtiene la lista de clientes procesados
        
        Returns:
            Lista de diccionarios con datos de clientes
        """
        return self.clientes
    
    def obtener_errores(self):
        """
        Obtiene la lista de errores encontrados
        
        Returns:
            Lista de mensajes de error
        """
        return self.errores
    
    def obtener_cliente_por_nit(self, nit):
        """
        Busca un cliente por su NIT
        
        Args:
            nit: NIT del cliente a buscar
            
        Returns:
            Diccionario con datos del cliente o None
        """
        nit_normalizado = Validator.normalizar_nit(nit)
        
        for cliente in self.clientes:
            if cliente['nit'] == nit_normalizado:
                return cliente
        
        return None
    
    def exportar_errores(self, ruta_salida):
        """
        Exporta los errores a un archivo de texto
        
        Args:
            ruta_salida: Ruta donde guardar el archivo de errores
            
        Returns:
            True si se exportó correctamente
        """
        if not self.errores:
            return False
        
        try:
            with open(ruta_salida, 'w', encoding='utf-8') as f:
                f.write("ERRORES EN PROCESAMIENTO DE EXCEL\n")
                f.write("=" * 60 + "\n\n")
                
                for i, error in enumerate(self.errores, 1):
                    f.write(f"{i}. {error}\n")
                
                f.write("\n" + "=" * 60 + "\n")
                f.write(f"Total de errores: {len(self.errores)}\n")
            
            self.logger.info(f"Errores exportados a: {ruta_salida}", modulo="ExcelProcessor")
            return True
        
        except Exception as e:
            self.logger.error(f"Error al exportar errores: {e}", modulo="ExcelProcessor")
            return False
    
    def generar_resumen(self):
        """
        Genera un resumen del procesamiento
        
        Returns:
            Diccionario con estadísticas
        """
        return {
            'total_clientes': len(self.clientes),
            'total_errores': len(self.errores),
            'nits_unicos': len(set(c['nit'] for c in self.clientes)),
            'emails_unicos': len(set(c['email'] for c in self.clientes))
        }