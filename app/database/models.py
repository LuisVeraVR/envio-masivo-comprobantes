"""
Modelos de base de datos para el sistema de envío de comprobantes
"""

from datetime import datetime
import sqlite3
import os

class Database:
    """Manejador de base de datos SQLite"""
    
    def __init__(self, db_path="data/comprobantes.db"):
        """
        Inicializa la base de datos
        
        Args:
            db_path: Ruta al archivo de base de datos
        """
        self.db_path = db_path
        self._ensure_directory()
        self._create_tables()
    
    def _ensure_directory(self):
        """Crea el directorio de la base de datos si no existe"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _create_tables(self):
        """Crea las tablas necesarias en la base de datos"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabla de envíos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS envios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    nit TEXT NOT NULL,
                    nombre_cliente TEXT NOT NULL,
                    email_destino TEXT NOT NULL,
                    emails_copia TEXT,
                    cantidad_archivos INTEGER NOT NULL,
                    archivos_adjuntos TEXT,
                    estado TEXT NOT NULL,
                    mensaje_error TEXT,
                    asunto TEXT NOT NULL,
                    usuario_operativa TEXT,
                    modo_prueba BOOLEAN DEFAULT 0
                )
            """)
            
            # Tabla de estados de correos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS estados_correo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    envio_id INTEGER NOT NULL,
                    estado TEXT NOT NULL,
                    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    detalle TEXT,
                    FOREIGN KEY (envio_id) REFERENCES envios(id)
                )
            """)
            
            # Tabla de logs del sistema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs_sistema (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    nivel TEXT NOT NULL,
                    modulo TEXT NOT NULL,
                    mensaje TEXT NOT NULL,
                    detalle TEXT
                )
            """)
            
            # Índices para mejorar rendimiento
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_envios_nit 
                ON envios(nit)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_envios_fecha 
                ON envios(fecha_envio)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_envios_estado 
                ON envios(estado)
            """)
            
            conn.commit()
    
    def registrar_envio(self, nit, nombre_cliente, email_destino, emails_copia,
                       cantidad_archivos, archivos_adjuntos, estado, 
                       mensaje_error=None, usuario_operativa=None, modo_prueba=False):
        """
        Registra un nuevo envío en la base de datos
        
        Args:
            nit: NIT del cliente
            nombre_cliente: Nombre del cliente
            email_destino: Email principal del destinatario
            emails_copia: Lista de emails en copia (CC) separados por coma
            cantidad_archivos: Número de archivos adjuntos
            archivos_adjuntos: Nombres de archivos separados por coma
            estado: Estado del envío (ENVIADO, ERROR, REBOTADO, etc.)
            mensaje_error: Mensaje de error si aplica
            usuario_operativa: Usuario que realizó el envío
            modo_prueba: Si el envío fue en modo prueba
            
        Returns:
            ID del envío registrado
        """
        asunto = f"Comprobante - NIT: {nit} - {nombre_cliente}"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO envios (
                    nit, nombre_cliente, email_destino, emails_copia,
                    cantidad_archivos, archivos_adjuntos, estado, mensaje_error,
                    asunto, usuario_operativa, modo_prueba
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nit, nombre_cliente, email_destino, emails_copia,
                cantidad_archivos, archivos_adjuntos, estado, mensaje_error,
                asunto, usuario_operativa, modo_prueba
            ))
            conn.commit()
            return cursor.lastrowid
    
    def actualizar_estado_envio(self, envio_id, nuevo_estado, detalle=None):
        """
        Actualiza el estado de un envío y registra el cambio
        
        Args:
            envio_id: ID del envío
            nuevo_estado: Nuevo estado del envío
            detalle: Detalle adicional del cambio
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Actualizar estado en tabla envios
            cursor.execute("""
                UPDATE envios 
                SET estado = ?
                WHERE id = ?
            """, (nuevo_estado, envio_id))
            
            # Registrar cambio de estado
            cursor.execute("""
                INSERT INTO estados_correo (envio_id, estado, detalle)
                VALUES (?, ?, ?)
            """, (envio_id, nuevo_estado, detalle))
            
            conn.commit()
    
    def obtener_envios_por_estado(self, estado, fecha_inicio=None, fecha_fin=None):
        """
        Obtiene envíos filtrados por estado y rango de fechas
        
        Args:
            estado: Estado a filtrar (ENVIADO, REBOTADO, BLOQUEADO, INEXISTENTE)
            fecha_inicio: Fecha inicio del filtro (opcional)
            fecha_fin: Fecha fin del filtro (opcional)
            
        Returns:
            Lista de envíos
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM envios WHERE estado = ?"
            params = [estado]
            
            if fecha_inicio:
                query += " AND fecha_envio >= ?"
                params.append(fecha_inicio)
            
            if fecha_fin:
                query += " AND fecha_envio <= ?"
                params.append(fecha_fin)
            
            query += " ORDER BY fecha_envio DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def obtener_estadisticas(self, fecha_inicio=None, fecha_fin=None):
        """
        Obtiene estadísticas de envíos
        
        Args:
            fecha_inicio: Fecha inicio del filtro (opcional)
            fecha_fin: Fecha fin del filtro (opcional)
            
        Returns:
            Diccionario con estadísticas
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    estado,
                    COUNT(*) as cantidad,
                    SUM(cantidad_archivos) as total_archivos
                FROM envios
                WHERE 1=1
            """
            params = []
            
            if fecha_inicio:
                query += " AND fecha_envio >= ?"
                params.append(fecha_inicio)
            
            if fecha_fin:
                query += " AND fecha_envio <= ?"
                params.append(fecha_fin)
            
            query += " GROUP BY estado"
            
            cursor.execute(query, params)
            
            estadisticas = {}
            for row in cursor.fetchall():
                estado, cantidad, total_archivos = row
                estadisticas[estado] = {
                    "cantidad": cantidad,
                    "total_archivos": total_archivos
                }
            
            return estadisticas
    
    def registrar_log(self, nivel, modulo, mensaje, detalle=None):
        """
        Registra un log del sistema
        
        Args:
            nivel: Nivel del log (INFO, WARNING, ERROR, CRITICAL)
            modulo: Módulo que genera el log
            mensaje: Mensaje del log
            detalle: Detalle adicional
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO logs_sistema (nivel, modulo, mensaje, detalle)
                VALUES (?, ?, ?, ?)
            """, (nivel, modulo, mensaje, detalle))
            conn.commit()
    
    def limpiar_logs_antiguos(self, dias=30):
        """
        Elimina logs más antiguos que X días
        
        Args:
            dias: Número de días a mantener
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM logs_sistema 
                WHERE fecha < datetime('now', '-' || ? || ' days')
            """, (dias,))
            conn.commit()
    
    def obtener_historial_cliente(self, nit):
        """
        Obtiene el historial de envíos de un cliente por NIT
        
        Args:
            nit: NIT del cliente
            
        Returns:
            Lista de envíos del cliente
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM envios 
                WHERE nit = ?
                ORDER BY fecha_envio DESC
            """, (nit,))
            return [dict(row) for row in cursor.fetchall()]