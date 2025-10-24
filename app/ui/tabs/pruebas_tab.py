"""
Pestaña de Ambiente de Pruebas
Permite realizar envíos de prueba
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QPushButton, QTextEdit, QMessageBox, QLineEdit)
from PyQt6.QtCore import Qt


class PruebasTab(QWidget):
    """Pestaña de ambiente de pruebas"""
    
    def __init__(self, config, db, logger):
        super().__init__()
        self.config = config
        self.db = db
        self.logger = logger
        
        self._crear_interfaz()
    
    def _crear_interfaz(self):
        """Crea la interfaz de la pestaña"""
        layout = QVBoxLayout(self)
        
        # Título
        titulo = QLabel("🧪 Ambiente de Pruebas")
        titulo.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(titulo)
        
        # Descripción
        desc = QLabel(
            "Use esta pestaña para realizar envíos de prueba antes de un envío masivo.\n"
            "Los envíos de prueba no envían correos reales."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("padding: 10px; background-color: #fff3cd; border-radius: 5px;")
        layout.addWidget(desc)
        
        # Grupo: Estado actual
        grupo_estado = self._crear_grupo_estado()
        layout.addWidget(grupo_estado)
        
        # Instrucciones
        instrucciones = QTextEdit()
        instrucciones.setReadOnly(True)
        instrucciones.setMaximumHeight(200)
        instrucciones.setHtml("""
<h3>📋 Instrucciones de uso:</h3>
<ol>
<li><b>Active el modo de pruebas</b> en la pestaña de Configuración</li>
<li>Opcionalmente, configure un email de prueba para recibir todos los envíos</li>
<li>Vaya a la pestaña "Envío de Comprobantes"</li>
<li>Cargue sus archivos Excel y ZIP normalmente</li>
<li>Haga clic en "Enviar Comprobantes"</li>
<li>Los envíos se simularán sin enviar correos reales</li>
<li>Revise los resultados en la base de datos y logs</li>
</ol>

<h3>✅ Ventajas del modo de pruebas:</h3>
<ul>
<li>Valida que los archivos se asocien correctamente</li>
<li>Verifica que el NIT esté en el asunto</li>
<li>Prueba la configuración sin enviar correos</li>
<li>Simula el flujo completo de envío</li>
</ul>
        """)
        layout.addWidget(instrucciones)
        
        # Botón ir a configuración
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_config = QPushButton("⚙️ Ir a Configuración")
        btn_config.setMinimumHeight(35)
        btn_config.clicked.connect(self._ir_a_configuracion)
        btn_layout.addWidget(btn_config)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
    
    def _crear_grupo_estado(self):
        """Crea el grupo de estado actual"""
        grupo = QGroupBox("Estado Actual")
        layout = QVBoxLayout()
        
        self.label_estado = QLabel()
        self._actualizar_estado()
        layout.addWidget(self.label_estado)
        
        grupo.setLayout(layout)
        return grupo
    
    def _actualizar_estado(self):
        """Actualiza el estado del modo de pruebas"""
        if self.config.is_test_mode():
            email_prueba = self.config.get_test_email()
            if email_prueba:
                texto = f"🧪 <b>Modo de pruebas ACTIVO</b><br>Email de prueba: {email_prueba}"
            else:
                texto = "🧪 <b>Modo de pruebas ACTIVO</b><br>Sin email de prueba configurado"
            
            self.label_estado.setText(texto)
            self.label_estado.setStyleSheet("""
                padding: 15px;
                background-color: #d4edda;
                border: 2px solid #28a745;
                border-radius: 5px;
                font-size: 14px;
            """)
        else:
            self.label_estado.setText(
                "⚠️ <b>Modo de pruebas DESACTIVADO</b><br>"
                "Los envíos se realizarán de forma real"
            )
            self.label_estado.setStyleSheet("""
                padding: 15px;
                background-color: #f8d7da;
                border: 2px solid #dc3545;
                border-radius: 5px;
                font-size: 14px;
            """)
    
    def _ir_a_configuracion(self):
        """Navega a la pestaña de configuración"""
        # Obtener el TabWidget padre
        tab_widget = self.parent()
        if tab_widget:
            # Buscar el índice de la pestaña de configuración
            for i in range(tab_widget.count()):
                if "Configuración" in tab_widget.tabText(i):
                    tab_widget.setCurrentIndex(i)
                    break
    
    def showEvent(self, event):
        """Se llama cuando la pestaña se muestra"""
        super().showEvent(event)
        self._actualizar_estado()