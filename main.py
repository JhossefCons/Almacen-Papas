#!/usr/bin/env python3
"""
Punto de entrada principal para la aplicación PapaSoft
"""
import sys
import os

# Agregar las rutas de los módulos al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'auth'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'ui'))

from ui.main_window import MainWindow
from auth.auth_manager import AuthManager
from database.database import Database

class PapaSoftApp:
    def __init__(self):
        # Inicializar componentes principales
        self.db = Database()
        self.auth_manager = AuthManager(self.db)
        
        # Inicializar la interfaz después de la autenticación
        self.main_window = None
        
    def run(self):
        """Ejecutar la aplicación"""
        # Verificar si hay que crear usuario admin por primera vez
        if not self.auth_manager.has_admin_user():
            self.auth_manager.create_default_admin()
            
        # Mostrar ventana de login
        if self.auth_manager.show_login():
            # Si el login es exitoso, mostrar ventana principal
            self.main_window = MainWindow(self.db, self.auth_manager)
            self.main_window.run()
        else:
            # Si el login falla, salir
            sys.exit(0)

if __name__ == "__main__":
    app = PapaSoftApp()
    app.run()