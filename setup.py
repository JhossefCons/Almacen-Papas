import os
import sys
import configparser
from cx_Freeze import setup, Executable

# ---------- Utilidades ----------
def read_cfg():
    cfg = configparser.ConfigParser()
    cfg.read("config.ini", encoding="utf-8")
    return cfg

def guess_tcl_tk_dirs():
    """
    Para algunas instalaciones, cx_Freeze resuelve Tcl/Tk solo.
    Aun así, probamos incluirlos si existen rutas conocidas (fallback).
    """
    candidates = []
    # 1) tcl/ al lado del Python base
    candidates.append(os.path.join(sys.base_prefix, "tcl"))
    # 2) tcl/ junto al ejecutable de Python actual
    candidates.append(os.path.join(os.path.dirname(sys.executable), "tcl"))
    # 3) variables de entorno (si existen)
    for env_var in ("TCL_LIBRARY", "TK_LIBRARY"):
        path = os.environ.get(env_var)
        if path:
            tcl_root = os.path.dirname(os.path.dirname(path))
            candidates.append(tcl_root)

    # Filtrar directorios válidos
    valid = [p for p in candidates if p and os.path.isdir(p)]
    # El formato para include_files es (fuente, destino)
    # Queremos que termine en "tcl" dentro del build
    return [(p, "tcl") for p in valid]

# ---------- Leer metadatos desde config.ini ----------
cfg = read_cfg()
APP_NAME    = cfg.get("application", "name",    fallback="PapaSoft")
APP_VERSION = cfg.get("application", "version", fallback="1.0.0")
COMPANY     = cfg.get("application", "company", fallback="Jhossef Nicolas Constain Nieves")

# ---------- Archivos/carpetas a incluir ----------
include_files = [
    ("database/", "database/"),
    ("modules/", "modules/"),
    ("auth/", "auth/"),
    ("ui/", "ui/"),
    ("utils/", "utils/"),
    ("help/", "help/"),
    ("assets/", "assets/"),
    ("config.ini", "config.ini"),
]

# Incluir DB inicial si la distribuyes vacía o semilla
if os.path.exists("papasoft.db"):
    include_files.append(("papasoft.db", "papasoft.db"))

# Intento de fallback para Tcl/Tk (no hace daño si ya está resuelto)
for tcl_pair in guess_tcl_tk_dirs():
    if tcl_pair not in include_files:
        include_files.append(tcl_pair)

# ---------- Opciones de compilación ----------
build_exe_options = {
    "packages": [
        # principales
        "tkinter",
        "sqlite3",
        "PIL",
        "tkcalendar",
        "configparser",
        "json",
        "datetime",
        "threading",
        "os",
        "sys",
        # agrega aquí cualquier otra lib que uses explícitamente
    ],
    "excludes": ["unittest", "pdb", "doctest", "test"],
    "include_files": include_files,
    "optimize": 2,
    "include_msvcr": True,  # runtime VC++ en Windows
}

base = "Win32GUI" if sys.platform == "win32" else None

# Ruta del icono .ico para el binario (instalador/atajos)
icon_path = "assets/icons/iconoPapa.ico"
if not os.path.exists(icon_path):
    icon_path = None

# Dos accesos directos: Escritorio y Menú Inicio
executables = [
    Executable(
        "main.py",
        base=base,
        target_name=f"{APP_NAME}.exe",
        icon=icon_path,
        shortcut_name=APP_NAME,
        shortcut_dir="DesktopFolder",      # acceso directo en Escritorio
    ),
    Executable(
        "main.py",
        base=base,
        target_name=f"{APP_NAME}.exe",
        icon=icon_path,
        shortcut_name=APP_NAME,
        shortcut_dir="ProgramMenuFolder",  # acceso directo en Menú Inicio
    ),
]

# Opciones del MSI (puedes añadir upgrade_code si quieres mantener updates)
bdist_msi_options = {
    "add_to_path": False,  # no tocar PATH del sistema
    # "upgrade_code": "{PUT-A-UUID-HERE-IF-YOU-WANT-STABLE-UPGRADES}",
    # "initial_target_dir": r"[LocalAppDataFolder]\PapaSoft",  # opcional
}

setup(
    name=APP_NAME,
    version=APP_VERSION,
    description="Sistema de Gestión Integral para Negocios de Papa",
    author=COMPANY,
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    executables=executables,
)
