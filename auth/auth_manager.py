"""
Módulo para la gestión de autenticación y usuarios
"""
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox
from ui.login_window import LoginWindow

class AuthManager:
    def __init__(self, database):
        self.db = database
        self.current_user = None
        self.user_role = None
        
    def hash_password(self, password):
        """Hashear una contraseña"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_login(self, username, password):
        """Verificar credenciales de usuario"""
        query = "SELECT id, username, role, full_name FROM users WHERE username=? AND password=? AND is_active=1"
        hashed_password = self.hash_password(password)
        
        result = self.db.execute_query(query, (username, hashed_password))
        return result[0] if result else None
    
    def has_admin_user(self):
        """Verificar si existe al menos un usuario administrador"""
        query = "SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1"
        result = self.db.execute_query(query)
        return result[0][0] > 0 if result else False
    
    def create_default_admin(self):
        """Crear usuario administrador por defecto"""
        hashed_password = self.hash_password("admin123")
        query = "INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)"
        self.db.execute_query(query, ('admin', hashed_password, 'admin', 'Administrador Principal'))
        
    def show_login(self):
        """Mostrar ventana de login y retornar si fue exitoso"""
        login_window = LoginWindow(self)
        return login_window.result
    
    def get_current_user_info(self):
        """Obtener información del usuario actual"""
        if not self.current_user:
            return None
            
        query = "SELECT id, username, role, full_name FROM users WHERE id=?"
        result = self.db.execute_query(query, (self.current_user,))
        return result[0] if result else None
    
    def has_permission(self, required_role):
        """Verificar si el usuario actual tiene los permisos requeridos"""
        if not self.current_user:
            return False
            
        user_info = self.get_current_user_info()
        if not user_info:
            return False
            
        # Los administradores tienen todos los permisos
        if user_info['role'] == 'admin':
            return True
            
        # Verificar permisos específicos
        return user_info['role'] == required_role