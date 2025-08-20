"""
Vista para la gestión de usuarios (solo para administradores)
"""
import tkinter as tk
from tkinter import ttk, messagebox

from auth.user_manager import UserManager

class UserManagementView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth_manager = auth_manager
        self.user_manager = UserManager(database)
        
        self.setup_ui()
        self.load_users()
    
    def setup_ui(self):
        """Configurar la interfaz de usuario de gestión de usuarios"""
        # Frame principal
        main_frame = ttk.Frame(self.parent, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Botones superiores
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, text="Nuevo Usuario", command=self.show_new_user_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Actualizar", command=self.load_users).pack(side=tk.LEFT, padx=5)
        
        # Treeview para usuarios
        columns = ('id', 'username', 'role', 'full_name', 'status', 'created')
        self.users_tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=15)
        
        self.users_tree.heading('id', text='ID')
        self.users_tree.heading('username', text='Usuario')
        self.users_tree.heading('role', text='Rol')
        self.users_tree.heading('full_name', text='Nombre Completo')
        self.users_tree.heading('status', text='Estado')
        self.users_tree.heading('created', text='Creado')
        
        self.users_tree.column('id', width=40)
        self.users_tree.column('username', width=100)
        self.users_tree.column('role', width=80)
        self.users_tree.column('full_name', width=150)
        self.users_tree.column('status', width=80)
        self.users_tree.column('created', width=120)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=scrollbar.set)
        
        self.users_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botones de acción
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(action_frame, text="Editar", command=self.edit_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Cambiar Contraseña", command=self.change_password).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Eliminar", command=self.delete_user).pack(side=tk.LEFT, padx=5)
        
        # Estadísticas
        stats_frame = ttk.LabelFrame(main_frame, text="Estadísticas", padding=10)
        stats_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.stats_label = ttk.Label(stats_frame, text="Cargando estadísticas...")
        self.stats_label.pack(anchor=tk.W)
        
        # Bind eventos
        self.users_tree.bind('<Double-1>', self.on_user_double_click)
    
    def load_users(self):
        """Cargar usuarios en el treeview"""
        # Limpiar treeview
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        # Obtener usuarios
        users = self.user_manager.get_all_users()
        
        # Agregar usuarios al treeview
        for user in users:
            status = "Activo" if user['is_active'] else "Inactivo"
            created_date = user['created_at'][:10] if user['created_at'] else "N/A"
            
            # Determinar color según estado
            tags = ()
            if not user['is_active']:
                tags = ('inactive',)
            elif user['role'] == 'admin':
                tags = ('admin',)
            
            self.users_tree.insert('', 'end', values=(
                user['id'],
                user['username'],
                'Administrador' if user['role'] == 'admin' else 'Empleado',
                user['full_name'],
                status,
                created_date
            ), tags=tags)
        
        # Configurar colores
        self.users_tree.tag_configure('inactive', foreground='gray')
        self.users_tree.tag_configure('admin', foreground='darkblue', font=('Arial', 9, 'bold'))
        
        # Actualizar estadísticas
        self.update_stats()
    
    def update_stats(self):
        """Actualizar estadísticas de usuarios"""
        active_count = self.user_manager.get_active_users_count()
        users_by_role = self.user_manager.get_users_by_role()
        
        admin_count = users_by_role.get('admin', 0)
        employee_count = users_by_role.get('employee', 0)
        
        stats_text = f"Usuarios activos: {active_count} | Administradores: {admin_count} | Empleados: {employee_count}"
        self.stats_label.config(text=stats_text)
    
    def on_user_double_click(self, event):
        """Manejar doble clic en un usuario"""
        self.edit_user()
    
    def show_new_user_dialog(self):
        """Mostrar diálogo para crear nuevo usuario"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Nuevo Usuario")
        dialog.geometry("400x300")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Marco principal
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Usuario:").grid(row=0, column=0, sticky=tk.W, pady=5)
        username_entry = ttk.Entry(main_frame, width=25)
        username_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Contraseña:").grid(row=1, column=0, sticky=tk.W, pady=5)
        password_entry = ttk.Entry(main_frame, width=25, show="*")
        password_entry.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Confirmar:").grid(row=2, column=0, sticky=tk.W, pady=5)
        confirm_entry = ttk.Entry(main_frame, width=25, show="*")
        confirm_entry.grid(row=2, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Rol:").grid(row=3, column=0, sticky=tk.W, pady=5)
        role_var = tk.StringVar(value="employee")
        role_combo = ttk.Combobox(main_frame, textvariable=role_var, state="readonly", width=22)
        role_combo['values'] = ('employee', 'admin')
        role_combo.grid(row=3, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Nombre Completo:").grid(row=4, column=0, sticky=tk.W, pady=5)
        fullname_entry = ttk.Entry(main_frame, width=25)
        fullname_entry.grid(row=4, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=15)
        
        def create_user():
            username = username_entry.get()
            password = password_entry.get()
            confirm = confirm_entry.get()
            role = role_var.get()
            full_name = fullname_entry.get()
            
            if not all([username, password, confirm, full_name]):
                messagebox.showerror("Error", "Todos los campos son obligatorios")
                return
            
            if password != confirm:
                messagebox.showerror("Error", "Las contraseñas no coinciden")
                return
            
            # Validar fortaleza de contraseña
            is_valid, message = self.user_manager.validate_password_strength(password)
            if not is_valid:
                messagebox.showerror("Error", message)
                return
            
            try:
                self.user_manager.create_user(username, password, role, full_name)
                messagebox.showinfo("Éxito", "Usuario creado correctamente")
                dialog.destroy()
                self.load_users()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear el usuario: {str(e)}")
        
        ttk.Button(button_frame, text="Crear", command=create_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
        username_entry.focus()
    
    def edit_user(self):
        """Editar usuario seleccionado"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un usuario para editar")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        
        # Obtener información del usuario
        user = self.user_manager.get_user_by_id(user_id)
        if not user:
            messagebox.showerror("Error", "No se pudo obtener la información del usuario")
            return
        
        dialog = tk.Toplevel(self.parent)
        dialog.title("Editar Usuario")
        dialog.geometry("400x250")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Marco principal
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Usuario:").grid(row=0, column=0, sticky=tk.W, pady=5)
        username_entry = ttk.Entry(main_frame, width=25)
        username_entry.insert(0, user['username'])
        username_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Rol:").grid(row=1, column=0, sticky=tk.W, pady=5)
        role_var = tk.StringVar(value=user['role'])
        role_combo = ttk.Combobox(main_frame, textvariable=role_var, state="readonly", width=22)
        role_combo['values'] = ('employee', 'admin')
        role_combo.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Nombre Completo:").grid(row=2, column=0, sticky=tk.W, pady=5)
        fullname_entry = ttk.Entry(main_frame, width=25)
        fullname_entry.insert(0, user['full_name'])
        fullname_entry.grid(row=2, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Estado:").grid(row=3, column=0, sticky=tk.W, pady=5)
        status_var = tk.BooleanVar(value=bool(user['is_active']))
        status_check = ttk.Checkbutton(main_frame, text="Activo", variable=status_var)
        status_check.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=15)
        
        def save_changes():
            username = username_entry.get()
            role = role_var.get()
            full_name = fullname_entry.get()
            is_active = status_var.get()
            
            if not all([username, full_name]):
                messagebox.showerror("Error", "Usuario y nombre completo son obligatorios")
                return
            
            try:
                self.user_manager.update_user(user_id, username, role, full_name, is_active)
                messagebox.showinfo("Éxito", "Usuario actualizado correctamente")
                dialog.destroy()
                self.load_users()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el usuario: {str(e)}")
        
        ttk.Button(button_frame, text="Guardar", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
        username_entry.focus()
    
    def change_password(self):
        """Cambiar contraseña de usuario seleccionado"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un usuario para cambiar contraseña")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        
        dialog = tk.Toplevel(self.parent)
        dialog.title(f"Cambiar Contraseña - {username}")
        dialog.geometry("400x200")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Marco principal
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Nueva Contraseña:").grid(row=0, column=0, sticky=tk.W, pady=5)
        password_entry = ttk.Entry(main_frame, width=25, show="*")
        password_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Confirmar:").grid(row=1, column=0, sticky=tk.W, pady=5)
        confirm_entry = ttk.Entry(main_frame, width=25, show="*")
        confirm_entry.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=15)
        
        def save_password():
            password = password_entry.get()
            confirm = confirm_entry.get()
            
            if not password:
                messagebox.showerror("Error", "La contraseña es obligatoria")
                return
            
            if password != confirm:
                messagebox.showerror("Error", "Las contraseñas no coinciden")
                return
            
            # Validar fortaleza de contraseña
            is_valid, message = self.user_manager.validate_password_strength(password)
            if not is_valid:
                messagebox.showerror("Error", message)
                return
            
            try:
                self.user_manager.update_user_password(user_id, password)
                messagebox.showinfo("Éxito", "Contraseña actualizada correctamente")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cambiar la contraseña: {str(e)}")
        
        ttk.Button(button_frame, text="Cambiar", command=save_password).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
        password_entry.focus()
    
    def delete_user(self):
        """Eliminar usuario seleccionado"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un usuario para eliminar")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        
        if messagebox.askyesno("Confirmar", 
            f"¿Está seguro de eliminar al usuario '{username}'? Esta acción no se puede deshacer."):
            try:
                self.user_manager.delete_user(user_id)
                messagebox.showinfo("Éxito", "Usuario eliminado correctamente")
                self.load_users()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el usuario: {str(e)}")