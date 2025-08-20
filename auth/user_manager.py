"""
Controlador para la gestión de usuarios
"""
from database.models import User
from database.database import Database

class UserManager:
    def __init__(self, database):
        self.db = database
    
    def get_all_users(self):
        """Obtener todos los usuarios"""
        query = "SELECT * FROM users ORDER BY username"
        results = self.db.execute_query(query)
        return [dict(row) for row in results] if results else []
    
    def get_user_by_id(self, user_id):
        """Obtener usuario por ID"""
        query = "SELECT * FROM users WHERE id = ?"
        result = self.db.execute_query(query, (user_id,))
        return dict(result[0]) if result else None
    
    def create_user(self, username, password, role, full_name):
        """Crear un nuevo usuario"""
        # Verificar si el usuario ya existe
        if self.user_exists(username):
            raise Exception("El nombre de usuario ya existe")
        
        # Validar rol
        if role not in ['admin', 'employee']:
            raise Exception("Rol inválido")
        
        # Hashear la contraseña
        hashed_password = self.hash_password(password)
        
        query = "INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)"
        user_id = self.db.execute_query(query, (username, hashed_password, role, full_name))
        return user_id
    
    def update_user(self, user_id, username, role, full_name, is_active):
        """Actualizar usuario existente"""
        # Verificar si el nuevo username ya existe (excluyendo el usuario actual)
        if self.user_exists(username, exclude_user_id=user_id):
            raise Exception("El nombre de usuario ya existe")
        
        # Validar rol
        if role not in ['admin', 'employee']:
            raise Exception("Rol inválido")
        
        query = "UPDATE users SET username = ?, role = ?, full_name = ?, is_active = ? WHERE id = ?"
        self.db.execute_query(query, (username, role, full_name, int(is_active), user_id))
        return True
    
    def update_user_password(self, user_id, new_password):
        """Actualizar contraseña de usuario"""
        hashed_password = self.hash_password(new_password)
        query = "UPDATE users SET password = ? WHERE id = ?"
        self.db.execute_query(query, (hashed_password, user_id))
        return True
    
    def delete_user(self, user_id):
        """Eliminar usuario (solo si no es el último admin)"""
        # Verificar que no sea el último administrador activo
        if self.is_last_admin(user_id):
            raise Exception("No se puede eliminar el último administrador activo")
        
        query = "DELETE FROM users WHERE id = ?"
        self.db.execute_query(query, (user_id,))
        return True
    
    def user_exists(self, username, exclude_user_id=None):
        """Verificar si un usuario existe"""
        if exclude_user_id:
            query = "SELECT COUNT(*) FROM users WHERE username = ? AND id != ?"
            result = self.db.execute_query(query, (username, exclude_user_id))
        else:
            query = "SELECT COUNT(*) FROM users WHERE username = ?"
            result = self.db.execute_query(query, (username,))
        
        return result[0][0] > 0 if result else False
    
    def is_last_admin(self, exclude_user_id=None):
        """Verificar si es el último administrador activo"""
        if exclude_user_id:
            query = "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1 AND id != ?"
            result = self.db.execute_query(query, (exclude_user_id,))
        else:
            query = "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
            result = self.db.execute_query(query)
        
        return result[0][0] == 0 if result else True
    
    def hash_password(self, password):
        """Hashear una contraseña (mismo método que en AuthManager)"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
    
    def validate_password_strength(self, password):
        """Validar fortaleza de la contraseña"""
        if len(password) < 6:
            return False, "La contraseña debe tener al menos 6 caracteres"
        
        # Puedes agregar más validaciones aquí
        return True, "Contraseña válida"
    
    def get_active_users_count(self):
        """Obtener conteo de usuarios activos"""
        query = "SELECT COUNT(*) FROM users WHERE is_active = 1"
        result = self.db.execute_query(query)
        return result[0][0] if result else 0
    
    def get_users_by_role(self):
        """Obtener conteo de usuarios por rol"""
        query = "SELECT role, COUNT(*) as count FROM users WHERE is_active = 1 GROUP BY role"
        results = self.db.execute_query(query)
        return {row['role']: row['count'] for row in results} if results else {}