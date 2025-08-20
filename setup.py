"""
Script de instalación y empaquetado para PapaSoft
"""
import os
import sys
import shutil
from cx_Freeze import setup, Executable

def create_directory_structure():
    """Crear la estructura de directorios necesaria"""
    directories = [
        'backups',
        'logs',
        'reports',
        'assets'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Directorio creado: {directory}")

def create_config_file():
    """Crear archivo de configuración inicial"""
    config_content = """[database]
path = papasoft.db

[application]
name = PapaSoft
version = 1.0.0
company = Tu Empresa

[notifications]
check_interval = 300
low_stock_threshold = 20

[backup]
auto_backup = True
backup_interval = 86400  # 24 horas en segundos
max_backups = 30
"""
    
    if not os.path.exists('config.ini'):
        with open('config.ini', 'w', encoding='utf-8') as f:
            f.write(config_content)
        print("Archivo de configuración creado: config.ini")

def create_start_script():
    """Crear script de inicio para diferentes plataformas"""
    # Script para Windows
    if sys.platform == 'win32':
        bat_content = """@echo off
echo Iniciando PapaSoft...
python main.py
pause
"""
        with open('start_papasoft.bat', 'w') as f:
            f.write(bat_content)
        print("Script de inicio creado: start_papasoft.bat")
    
    # Script para Linux/Mac
    else:
        sh_content = """#!/bin/bash
echo "Iniciando PapaSoft..."
python3 main.py
"""
        with open('start_papasoft.sh', 'w') as f:
            f.write(sh_content)
        os.chmod('start_papasoft.sh', 0o755)
        print("Script de inicio creado: start_papasoft.sh")

def create_requirements_file():
    """Crear archivo requirements.txt"""
    requirements = """tkinter
tkcalendar
matplotlib
cx_Freeze
"""
    with open('requirements.txt', 'w') as f:
        f.write(requirements)
    print("Archivo de requirements creado: requirements.txt")

def setup_application():
    """Configurar la aplicación"""
    print("Configurando PapaSoft...")
    
    create_directory_structure()
    create_config_file()
    create_start_script()
    create_requirements_file()
    
    print("Configuración completada. Puede ejecutar 'python main.py' para iniciar.")

def build_installer():
    """Crear instalador ejecutable"""
    print("Construyendo instalador...")
    
    # Configuración para cx_Freeze
    build_exe_options = {
        "packages": ["tkinter", "sqlite3", "matplotlib"],
        "excludes": ["test"],
        "include_files": [
            "database/",
            "modules/", 
            "auth/",
            "ui/",
            "utils/",
            "help/",
            "assets/",
            "config.ini"
        ],
        "optimize": 2
    }
    
    base = None
    if sys.platform == "win32":
        base = "Win32GUI"
    
    setup(
        name="PapaSoft",
        version="1.0.0",
        description="Sistema de Gestión Integral para Negocios de Papa",
        options={"build_exe": build_exe_options},
        executables=[Executable("main.py", base=base, icon="assets/icon.ico")]
    )
    
    print("Instalador creado en directorio build/")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        build_installer()
    else:
        setup_application()