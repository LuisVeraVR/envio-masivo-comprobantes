"""
Script para ejecutar la aplicación
"""

import sys
import os

# Agregar directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar y ejecutar
from app.main import main

if __name__ == "__main__":
    main()