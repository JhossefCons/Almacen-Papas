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
    Como fallback, incluye Tcl/Tk si cx_Freeze no lo resuelve solo.
    No afecta si ya está correctamente detectado.
    """
    candidates = []
    candidates.append(os.path.join(sys.base_prefix, "tcl"))
    candidates.append(os.path.join(os.path.dirname(sys.executable), "tcl"))
    for env_var in ("TCL_LIBRARY", "TK_LIBRARY"):
        path = os.environ.get(env_var)
        if path:
            tcl_root = os.path.dirname(os.path.dirname(path))
            candidates.append(tcl_root)
    valid = [p for p in candidates if p and os.path.isdir(p)]
    return [(p, "tcl") for p in valid]

# ---------- Metadatos desde config.ini ----------
cfg = read_cfg()
APP_NAME    = cfg.get("application", "name",    fallback="PapaSoft")
APP_VERSION = cfg.get("application", "version", fallback="1.0.0")
COMPANY     = cfg.get("application", "company", fallback="Tu Empresa")

# ---------- Archivos/carpetas a incluir ----------
include_files = [
    ("database/", "database/"),
    ("modules/", "modules/"),
    ("auth/", "auth/"),
    ("ui/", "ui/"),
    ("utils/", "utils/"),
    ("assets/", "assets/"),
    ("config.ini", "config.ini"),
]

# Incluir DB semilla si existe
if os.path.exists("papasoft.db"):
    include_files.append(("papasoft.db", "papasoft.db"))

# Intento de fallback para Tcl/Tk
for tcl_pair in guess_tcl_tk_dirs():
    if tcl_pair not in include_files:
        include_files.append(tcl_pair)

# ---------- Opciones de compilación ----------
build_exe_options = {
    "packages": [
        "tkinter",
        "sqlite3",
        "PIL",           # Pillow
        "tkcalendar",
        "configparser",
        "json",
        "datetime",
        "threading",
        "os",
        "sys",
    ],
    "excludes": ["unittest", "pdb", "doctest", "test"],
    "include_files": include_files,
    "optimize": 2,
    "include_msvcr": True,  # runtime VC++ en Windows
}

base = "Win32GUI" if sys.platform == "win32" else None

# Icono del EXE y accesos directos
icon_path = "assets/icons/accesoDirecto.ico"
if not os.path.exists(icon_path):
    icon_path = None  # si no existe, no rompe el build

# Dos accesos directos: Escritorio y Menú Inicio
executables = [
    Executable(
        "main.py",
        base=base,
        target_name=f"{APP_NAME}.exe",
        icon=icon_path,
        shortcut_name=APP_NAME,
        shortcut_dir="DesktopFolder",
    ),
    Executable(
        "main.py",
        base=base,
        target_name=f"{APP_NAME}.exe",
        icon=icon_path,
        shortcut_name=APP_NAME,
        shortcut_dir="ProgramMenuFolder",
    ),
]

# MSI options (puedes fijar carpeta destino por defecto en LocalAppData)
bdist_msi_options = {
    "add_to_path": False,
    # "upgrade_code": "{PUT-A-UUID-HERE-IF-YOU-WANT-STABLE-UPGRADES}",
    # "initial_target_dir": rf"[LocalAppDataFolder]\{APP_NAME}",
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
