#!/usr/bin/env python3
"""
Script de actualización automática de versión
Actualiza el número de versión en todos los archivos del proyecto
"""

import re
import sys
import argparse
from pathlib import Path
from datetime import datetime


class VersionBumper:
    """Manejador de actualización de versiones"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.version_file = project_root / "app" / "version.py"
        self.init_file = project_root / "app" / "__init__.py"
        self.package_bat = project_root / "package.bat"

    def read_current_version(self) -> str:
        """Lee la versión actual desde app/version.py"""
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                content = f.read()

            match = re.search(r'__version__\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', content)
            if match:
                return match.group(1)
            else:
                raise ValueError("No se encontró la versión en version.py")
        except Exception as e:
            print(f"Error leyendo versión actual: {e}")
            return "1.0.0"

    def parse_version(self, version: str) -> tuple:
        """Parsea una versión en formato semver (major.minor.patch)"""
        parts = version.split('.')
        if len(parts) != 3:
            raise ValueError(f"Versión inválida: {version}")
        return tuple(map(int, parts))

    def bump_version(self, version: str, bump_type: str = "patch") -> str:
        """Incrementa la versión según el tipo especificado"""
        major, minor, patch = self.parse_version(version)

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Tipo de bump inválido: {bump_type}")

        return f"{major}.{minor}.{patch}"

    def update_version_py(self, new_version: str) -> bool:
        """Actualiza app/version.py con la nueva versión"""
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Actualizar __version__
            content = re.sub(
                r'(__version__\s*=\s*["\'])[0-9]+\.[0-9]+\.[0-9]+(["\'])',
                rf'\g<1>{new_version}\g<2>',
                content
            )

            with open(self.version_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✓ Actualizado {self.version_file.relative_to(self.project_root)}")
            return True
        except Exception as e:
            print(f"✗ Error actualizando version.py: {e}")
            return False

    def update_init_py(self, new_version: str) -> bool:
        """Actualiza app/__init__.py con la nueva versión"""
        try:
            with open(self.init_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Actualizar __version__
            content = re.sub(
                r'(__version__\s*=\s*["\'])[0-9]+\.[0-9]+\.[0-9]+(["\'])',
                rf'\g<1>{new_version}\g<2>',
                content
            )

            with open(self.init_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✓ Actualizado {self.init_file.relative_to(self.project_root)}")
            return True
        except Exception as e:
            print(f"✗ Error actualizando __init__.py: {e}")
            return False

    def update_package_bat(self, new_version: str) -> bool:
        """Actualiza package.bat con la nueva versión"""
        try:
            if not self.package_bat.exists():
                print(f"⚠ {self.package_bat.name} no existe, saltando...")
                return True

            with open(self.package_bat, 'r', encoding='utf-8') as f:
                content = f.read()

            # Actualizar VERSION=
            content = re.sub(
                r'(set\s+VERSION\s*=\s*)[0-9]+\.[0-9]+\.[0-9]+',
                rf'\g<1>{new_version}',
                content,
                flags=re.IGNORECASE
            )

            with open(self.package_bat, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✓ Actualizado {self.package_bat.relative_to(self.project_root)}")
            return True
        except Exception as e:
            print(f"✗ Error actualizando package.bat: {e}")
            return False

    def add_version_history_entry(self, new_version: str, message: str = None) -> bool:
        """Agrega una entrada al historial de versiones en version.py"""
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Buscar VERSION_HISTORY
            history_match = re.search(r'VERSION_HISTORY\s*=\s*\{', content)
            if not history_match:
                print("⚠ No se encontró VERSION_HISTORY, saltando historial...")
                return True

            # Crear entrada de historial
            date_str = datetime.now().strftime("%Y-%m-%d")
            if message:
                entry = f'    "{new_version}": [\n        "{message}",\n        "Fecha: {date_str}"\n    ],\n'
            else:
                entry = f'    "{new_version}": [\n        "Actualización automática de versión",\n        "Fecha: {date_str}"\n    ],\n'

            # Insertar después de la apertura del diccionario
            insert_pos = history_match.end()
            content = content[:insert_pos] + '\n' + entry + content[insert_pos:]

            with open(self.version_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✓ Agregada entrada en VERSION_HISTORY para v{new_version}")
            return True
        except Exception as e:
            print(f"✗ Error actualizando VERSION_HISTORY: {e}")
            return False

    def update_all(self, bump_type: str = "patch", message: str = None) -> str:
        """Actualiza la versión en todos los archivos"""
        print("=" * 60)
        print("ACTUALIZADOR AUTOMÁTICO DE VERSIÓN")
        print("=" * 60)

        # Leer versión actual
        current_version = self.read_current_version()
        print(f"\nVersión actual: {current_version}")

        # Calcular nueva versión
        new_version = self.bump_version(current_version, bump_type)
        print(f"Nueva versión: {new_version} ({bump_type})")
        print()

        # Actualizar archivos
        success = True
        success &= self.update_version_py(new_version)
        success &= self.update_init_py(new_version)
        success &= self.update_package_bat(new_version)
        success &= self.add_version_history_entry(new_version, message)

        print()
        if success:
            print(f"✓ Versión actualizada exitosamente a {new_version}")
        else:
            print("✗ Hubo errores durante la actualización")
        print("=" * 60)

        return new_version


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Actualiza automáticamente el número de versión del proyecto'
    )
    parser.add_argument(
        '--type',
        choices=['major', 'minor', 'patch'],
        default='patch',
        help='Tipo de incremento de versión (default: patch)'
    )
    parser.add_argument(
        '--message',
        type=str,
        help='Mensaje para el historial de versiones'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Solo mostrar la versión actual sin modificar'
    )

    args = parser.parse_args()

    # Obtener el directorio raíz del proyecto
    project_root = Path(__file__).parent.absolute()

    bumper = VersionBumper(project_root)

    if args.check:
        current_version = bumper.read_current_version()
        print(f"Versión actual: {current_version}")
        return 0

    try:
        new_version = bumper.update_all(args.type, args.message)
        return 0
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
