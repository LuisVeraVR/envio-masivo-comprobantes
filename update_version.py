#!/usr/bin/env python3
"""
Script para actualizar automáticamente la versión de la aplicación

Uso:
    python update_version.py 1.2.3                    # Actualiza a versión 1.2.3
    python update_version.py 1.2.3 --tag              # Actualiza y crea tag en git
    python update_version.py 1.2.3 --tag --push       # Actualiza, crea tag y hace push
    python update_version.py --show                   # Muestra versión actual
    python update_version.py --patch                  # Incrementa versión patch (1.1.2 -> 1.1.3)
    python update_version.py --minor                  # Incrementa versión minor (1.1.2 -> 1.2.0)
    python update_version.py --major                  # Incrementa versión major (1.1.2 -> 2.0.0)

Características:
    - Actualiza app/version.py (fuente única de verdad)
    - Valida formato semántico de versión (X.Y.Z)
    - Crea tags de git automáticamente (opcional)
    - Push automático a repositorio (opcional)
    - Modo interactivo para agregar notas de versión
"""

import sys
import re
import argparse
import subprocess
from pathlib import Path


VERSION_FILE = Path(__file__).parent / "app" / "version.py"


def get_current_version():
    """Lee la versión actual desde app/version.py"""
    if not VERSION_FILE.exists():
        print(f"❌ Error: No se encontró {VERSION_FILE}")
        sys.exit(1)

    content = VERSION_FILE.read_text(encoding='utf-8')
    match = re.search(r'__version__\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', content)

    if not match:
        print(f"❌ Error: No se pudo leer la versión desde {VERSION_FILE}")
        sys.exit(1)

    return match.group(1)


def parse_version(version_str):
    """Parsea una versión en formato X.Y.Z"""
    parts = version_str.split('.')
    if len(parts) != 3:
        return None
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def increment_version(version_str, part='patch'):
    """Incrementa una versión según el tipo (major, minor, patch)"""
    major, minor, patch = parse_version(version_str)

    if part == 'major':
        return f"{major + 1}.0.0"
    elif part == 'minor':
        return f"{major}.{minor + 1}.0"
    elif part == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Tipo de incremento inválido: {part}")


def validate_version(version_str):
    """Valida que la versión tenga formato X.Y.Z"""
    pattern = r'^[0-9]+\.[0-9]+\.[0-9]+$'
    return re.match(pattern, version_str) is not None


def update_version_file(new_version, release_notes=None):
    """Actualiza el archivo app/version.py con la nueva versión"""
    content = VERSION_FILE.read_text(encoding='utf-8')

    # Actualizar __version__
    content = re.sub(
        r'(__version__\s*=\s*["\'])[0-9]+\.[0-9]+\.[0-9]+(["\'])',
        rf'\g<1>{new_version}\g<2>',
        content
    )

    # Agregar entrada en VERSION_HISTORY si se proporcionan notas
    if release_notes:
        # Buscar el cierre del diccionario VERSION_HISTORY
        history_match = re.search(r'(VERSION_HISTORY\s*=\s*\{)(.*?)(\n\})', content, re.DOTALL)
        if history_match:
            notes_list = ',\n        '.join(f'"{note}"' for note in release_notes)
            new_entry = f',\n    "{new_version}": [\n        {notes_list}\n    ]'

            # Insertar antes del cierre del diccionario
            content = (
                content[:history_match.end(2)] +
                new_entry +
                content[history_match.end(2):]
            )

    VERSION_FILE.write_text(content, encoding='utf-8')
    print(f"✅ Versión actualizada en {VERSION_FILE}")


def create_git_tag(version, push=False):
    """Crea un tag de git para la versión"""
    tag_name = f"v{version}"

    try:
        # Verificar si hay cambios sin commitear
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout.strip():
            print("⚠️  Hay cambios sin commitear. Comiteando cambios...")
            subprocess.run(['git', 'add', str(VERSION_FILE)], check=True)
            subprocess.run(
                ['git', 'commit', '-m', f'chore: Bump version to {version}'],
                check=True
            )
            print(f"✅ Commit creado: 'Bump version to {version}'")

        # Crear tag
        subprocess.run(
            ['git', 'tag', '-a', tag_name, '-m', f'Release {version}'],
            check=True
        )
        print(f"✅ Tag creado: {tag_name}")

        # Push si se solicita
        if push:
            # Push commit
            subprocess.run(['git', 'push'], check=True)
            print("✅ Cambios pusheados al repositorio")

            # Push tag
            subprocess.run(['git', 'push', 'origin', tag_name], check=True)
            print(f"✅ Tag {tag_name} pusheado al repositorio")
        else:
            print("ℹ️  Recuerda hacer push del tag: git push origin " + tag_name)

    except subprocess.CalledProcessError as e:
        print(f"❌ Error al crear tag de git: {e}")
        sys.exit(1)


def prompt_release_notes():
    """Solicita notas de la versión de forma interactiva"""
    print("\n📝 Ingrese las notas de la versión (una por línea, línea vacía para terminar):")
    notes = []
    while True:
        line = input("   - ").strip()
        if not line:
            break
        notes.append(line)
    return notes if notes else None


def main():
    parser = argparse.ArgumentParser(
        description='Actualiza la versión de la aplicación automáticamente',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s 1.2.3                     Actualiza a versión 1.2.3
  %(prog)s 1.2.3 --tag               Actualiza y crea tag en git
  %(prog)s 1.2.3 --tag --push        Actualiza, crea tag y hace push
  %(prog)s --show                    Muestra versión actual
  %(prog)s --patch                   Incrementa versión patch
  %(prog)s --minor                   Incrementa versión minor
  %(prog)s --major                   Incrementa versión major
  %(prog)s --patch --notes           Incrementa patch y solicita notas
        """
    )

    parser.add_argument('version', nargs='?', help='Nueva versión (formato: X.Y.Z)')
    parser.add_argument('--show', action='store_true', help='Mostrar versión actual')
    parser.add_argument('--patch', action='store_true', help='Incrementar versión patch')
    parser.add_argument('--minor', action='store_true', help='Incrementar versión minor')
    parser.add_argument('--major', action='store_true', help='Incrementar versión major')
    parser.add_argument('--tag', action='store_true', help='Crear tag de git')
    parser.add_argument('--push', action='store_true', help='Pushear cambios y tag a repositorio')
    parser.add_argument('--notes', action='store_true', help='Agregar notas de versión interactivamente')

    args = parser.parse_args()

    # Mostrar versión actual
    if args.show:
        current = get_current_version()
        print(f"📦 Versión actual: {current}")
        return

    # Determinar nueva versión
    current_version = get_current_version()
    new_version = None

    if args.patch or args.minor or args.major:
        if args.patch:
            new_version = increment_version(current_version, 'patch')
        elif args.minor:
            new_version = increment_version(current_version, 'minor')
        elif args.major:
            new_version = increment_version(current_version, 'major')
    elif args.version:
        new_version = args.version
    else:
        parser.print_help()
        return

    # Validar versión
    if not validate_version(new_version):
        print(f"❌ Error: Versión inválida '{new_version}'. Formato esperado: X.Y.Z")
        sys.exit(1)

    # Verificar que sea mayor que la actual
    current_parsed = parse_version(current_version)
    new_parsed = parse_version(new_version)

    if new_parsed <= current_parsed:
        print(f"❌ Error: La nueva versión {new_version} debe ser mayor que la actual {current_version}")
        sys.exit(1)

    # Solicitar notas si se requiere
    release_notes = None
    if args.notes:
        release_notes = prompt_release_notes()

    # Confirmar cambio
    print(f"\n🔄 Actualización de versión:")
    print(f"   Actual: {current_version}")
    print(f"   Nueva:  {new_version}")

    if release_notes:
        print(f"\n📝 Notas de la versión:")
        for note in release_notes:
            print(f"   - {note}")

    if args.tag:
        print(f"\n🏷️  Se creará tag: v{new_version}")
        if args.push:
            print(f"📤 Se hará push al repositorio")

    response = input("\n¿Continuar? [s/N]: ").strip().lower()
    if response not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Operación cancelada")
        return

    # Actualizar versión
    update_version_file(new_version, release_notes)

    # Crear tag si se solicita
    if args.tag:
        create_git_tag(new_version, args.push)

    print(f"\n✨ Versión actualizada exitosamente a {new_version}")
    print("\n📋 Próximos pasos:")
    if not args.tag:
        print("   1. Revisar los cambios: git diff app/version.py")
        print("   2. Commitear: git commit -am 'chore: Bump version to " + new_version + "'")
        print("   3. Crear tag: git tag -a v" + new_version + " -m 'Release " + new_version + "'")
        print("   4. Push: git push && git push origin v" + new_version)
    else:
        if not args.push:
            print("   1. Push del tag: git push origin v" + new_version)
        print("   2. Crear release en GitHub con el tag v" + new_version)


if __name__ == '__main__':
    main()
