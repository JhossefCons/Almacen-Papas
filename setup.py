"""
Script de instalación y empaquetado para PapaSoft
Versión mejorada con soporte para base de datos embebida
"""
import os
import sys
import shutil
import sqlite3
import configparser
from cx_Freeze import setup, Executable

def create_directory_structure():
    """Crear la estructura de directorios necesaria"""
    directories = [
        'backups',
        'logs',
        'reports',
        'assets',
        'temp'
    ]

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Directorio creado: {directory}")

def create_config_file():
    """Crear archivo de configuración inicial"""
    config_content = """[database]
path = papasoft.db
backup_path = backups/
auto_backup_days = 7

[application]
name = PapaSoft
version = 1.0.0
company = Tu Empresa
language = es
theme = default

[notifications]
check_interval = 300
low_stock_threshold = 20
loan_alert_days = 7
cash_closure_reminder = 17:00

[backup]
auto_backup = True
backup_interval = 86400
max_backups = 30
compress_backups = True

[security]
password_min_length = 6
password_require_special = False
session_timeout = 3600
max_login_attempts = 5

[reports]
default_currency = $
date_format = %Y-%m-%d
number_format = %.2f

[inventory]
default_potato_type = parda
default_quality = primera
measurement_unit = costales
"""

    if not os.path.exists('config.ini'):
        with open('config.ini', 'w', encoding='utf-8') as f:
            f.write(config_content)
        print("✓ Archivo de configuración creado: config.ini")

def initialize_database():
    """Inicializar la base de datos si no existe"""
    db_path = 'papasoft.db'

    if not os.path.exists(db_path):
        print("✓ Creando base de datos...")
        from database.database import Database
        db = Database()
        db.initialize_database()
        print("✓ Base de datos inicializada correctamente")
    else:
        print("✓ Base de datos ya existe")

def create_start_script():
    """Crear script de inicio para diferentes plataformas"""
    # Script para Windows
    if sys.platform == 'win32':
        bat_content = """@echo off
echo ====================================
echo     SISTEMA PAPASOFT v1.0.0
echo ====================================
echo Iniciando aplicacion...
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Error al ejecutar la aplicacion
    echo Presione cualquier tecla para continuar...
    pause > nul
)
"""
        with open('start_papasoft.bat', 'w', encoding='utf-8') as f:
            f.write(bat_content)
        print("✓ Script de inicio creado: start_papasoft.bat")

    # Script para Linux/Mac
    else:
        sh_content = """#!/bin/bash
echo "===================================="
echo "    SISTEMA PAPASOFT v1.0.0"
echo "===================================="
echo "Iniciando aplicacion..."
cd "$(dirname "$0")"
python3 main.py
if [ $? -ne 0 ]; then
    echo ""
    echo "Error al ejecutar la aplicacion"
    read -p "Presione Enter para continuar..."
fi
"""
        with open('start_papasoft.sh', 'w', encoding='utf-8') as f:
            f.write(sh_content)
        os.chmod('start_papasoft.sh', 0o755)
        print("✓ Script de inicio creado: start_papasoft.sh")

def create_requirements_file():
    """Crear archivo requirements.txt con todas las dependencias"""
    requirements = """# Dependencias principales
tkinter>=8.6
tkcalendar>=1.6.1
matplotlib>=3.5.0
Pillow>=9.0.0

# Para desarrollo y empaquetado
cx_Freeze>=6.14
setuptools>=65.0.0

# Opcionales para funcionalidades avanzadas
requests>=2.28.0
openpyxl>=3.0.0
"""
    with open('requirements.txt', 'w', encoding='utf-8') as f:
        f.write(requirements)
    print("✓ Archivo de requirements creado: requirements.txt")

def create_installer_script():
    """Crear script de instalación automática"""
    installer_content = """#!/bin/bash
# Script de instalación automática para PapaSoft
# Compatible con Linux y macOS

echo "===================================="
echo "  INSTALADOR PAPASOFT v1.0.0"
echo "===================================="
echo ""

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado. Instálalo primero."
    exit 1
fi

echo "✓ Python 3 detectado"

# Instalar dependencias
echo "Instalando dependencias..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Dependencias instaladas correctamente"
else
    echo "❌ Error al instalar dependencias"
    exit 1
fi

# Configurar aplicación
echo "Configurando aplicación..."
python3 setup.py

# Crear acceso directo
echo "Creando acceso directo..."
chmod +x start_papasoft.sh

echo ""
echo "===================================="
echo "  INSTALACIÓN COMPLETADA"
echo "===================================="
echo ""
echo "Para ejecutar PapaSoft:"
echo "  ./start_papasoft.sh"
echo ""
echo "O directamente:"
echo "  python3 main.py"
echo ""
"""

    with open('install.sh', 'w', encoding='utf-8') as f:
        f.write(installer_content)
    os.chmod('install.sh', 0o755)
    print("✓ Script de instalación creado: install.sh")

def create_uninstaller():
    """Crear script de desinstalación"""
    uninstaller_content = """#!/bin/bash
# Script de desinstalación para PapaSoft

echo "===================================="
echo " DESINSTALADOR PAPASOFT v1.0.0"
echo "===================================="
echo ""

read -p "¿Está seguro de que desea desinstalar PapaSoft? (s/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Desinstalación cancelada."
    exit 0
fi

echo "Eliminando archivos de aplicación..."
rm -f papasoft.db
rm -f config.ini
rm -rf backups/
rm -rf logs/
rm -rf reports/
rm -rf temp/

echo "✓ Archivos eliminados"
echo ""
echo "Nota: Los archivos de configuración y datos han sido eliminados."
echo "Si desea conservar los datos, haga un backup antes de desinstalar."
"""

    with open('uninstall.sh', 'w', encoding='utf-8') as f:
        f.write(uninstaller_content)
    os.chmod('uninstall.sh', 0o755)
    print("✓ Script de desinstalación creado: uninstall.sh")

def setup_application():
    """Configurar la aplicación completa"""
    print("🔧 Configurando PapaSoft...")
    print("=" * 50)

    create_directory_structure()
    create_config_file()
    initialize_database()
    create_start_script()
    create_requirements_file()
    create_installer_script()
    create_uninstaller()

    print("=" * 50)
    print("✅ Configuración completada exitosamente!")
    print("")
    print("Para ejecutar PapaSoft:")
    if sys.platform == 'win32':
        print("  • Haga doble clic en: start_papasoft.bat")
        print("  • O ejecute: python main.py")
    else:
        print("  • Ejecute: ./start_papasoft.sh")
        print("  • O ejecute: python3 main.py")
    print("")
    print("📁 Base de datos: papasoft.db (SQLite embebida)")
    print("⚙️  Configuración: config.ini")

def build_installer():
    """Crear instalador ejecutable con cx_Freeze"""
    print("🏗️  Construyendo instalador ejecutable...")
    print("=" * 50)

    # Verificar que existe la base de datos
    if not os.path.exists('papasoft.db'):
        print("⚠️  Base de datos no encontrada. Creándola...")
        initialize_database()

    # Configuración mejorada para cx_Freeze
    build_exe_options = {
        "packages": [
            "tkinter",
            "sqlite3",
            "tkinter.ttk",
            "tkinter.messagebox",
            "tkinter.filedialog",
            "tkinter.simpledialog",
            "datetime",
            "calendar",
            "configparser",
            "threading",
            "json",
            "os",
            "sys",
            "math",
            "random"
        ],
        "excludes": [
            "test",
            "unittest",
            "pdb",
            "pydoc",
            "doctest"
        ],
        "include_files": [
            ("database/", "database/"),
            ("modules/", "modules/"),
            ("auth/", "auth/"),
            ("ui/", "ui/"),
            ("utils/", "utils/"),
            ("help/", "help/"),
            ("assets/", "assets/"),
            ("config.ini", "config.ini"),
            ("papasoft.db", "papasoft.db")
        ],
        "optimize": 2,
        "include_msvcr": True  # Incluir runtime de VC++ en Windows
    }

    base = None
    if sys.platform == "win32":
        base = "Win32GUI"  # Sin consola

    # Crear ejecutable
    setup(
        name="PapaSoft",
        version="1.0.0",
        description="Sistema de Gestión Integral para Negocios de Papa",
        author="Tu Empresa",
        author_email="info@tuempresa.com",
        url="https://tuempresa.com",
        options={"build_exe": build_exe_options},
        executables=[Executable(
            "main.py",
            base=base,
            icon="assets/icon.ico" if os.path.exists("assets/icon.ico") else None,
            shortcut_name="PapaSoft",
            shortcut_dir="DesktopFolder"
        )]
    )

    print("✅ Instalador creado exitosamente!")
    print("📁 Ubicación: build/exe.win-amd64-3.11/" if sys.platform == "win32" else "build/exe.linux-x86_64-3.11/")
    print("")
    print("Para crear un instalador MSI (Windows):")
    print("  pip install cx_Freeze --upgrade")
    print("  python setup.py bdist_msi")
    print("")
    print("Para crear un paquete DEB (Linux):")
    print("  pip install stdeb")
    print("  python setup.py --command-packages=stdeb.command bdist_deb")

def create_portable_version():
    """Crear versión portable"""
    print("📦 Creando versión portable...")

    portable_dir = "PapaSoft_Portable"
    if os.path.exists(portable_dir):
        shutil.rmtree(portable_dir)
    os.makedirs(portable_dir)

    # Copiar archivos necesarios
    files_to_copy = [
        'main.py',
        'config.ini',
        'papasoft.db',
        'requirements.txt'
    ]

    dirs_to_copy = [
        'database',
        'modules',
        'auth',
        'ui',
        'utils',
        'help',
        'assets'
    ]

    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, portable_dir)

    for dir_name in dirs_to_copy:
        if os.path.exists(dir_name):
            shutil.copytree(dir_name, os.path.join(portable_dir, dir_name))

    # Crear script de inicio portable
    if sys.platform == 'win32':
        portable_script = f"""@echo off
echo ====================================
echo     PAPASOFT PORTABLE v1.0.0
echo ====================================
cd /d "%~dp0"
python main.py
pause
"""
        with open(os.path.join(portable_dir, 'PapaSoft.bat'), 'w', encoding='utf-8') as f:
            f.write(portable_script)

    print(f"✅ Versión portable creada en: {portable_dir}/")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "build":
            build_installer()
        elif sys.argv[1] == "portable":
            create_portable_version()
        elif sys.argv[1] == "clean":
            # Limpiar archivos temporales
            dirs_to_clean = ['build', 'dist', '__pycache__']
            for dir_name in dirs_to_clean:
                if os.path.exists(dir_name):
                    shutil.rmtree(dir_name)
                    print(f"✓ Limpiado: {dir_name}")
        else:
            print("Uso: python setup.py [build|portable|clean]")
    else:
        setup_application()
