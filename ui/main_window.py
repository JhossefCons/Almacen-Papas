"""
Ventana principal de la aplicación
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime

class MainWindow:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth_manager = auth_manager
        self.root = tk.Tk()
        
        self.setup_window()
        
    def setup_window(self):
        """Configurar la ventana principal"""
        self.root.title("Sistema de Gestión Integral - PapaSoft")
        self.root.geometry("1200x700")
        self.root.configure(bg='#f0f0f0')
        
        # Configurar la barra de menú
        self.setup_menu()
        
        # Configurar el notebook (pestañas)
        self.setup_notebook()
        
        # Configurar la barra de estado
        self.setup_status_bar()
        
    def setup_menu(self):
        """Configurar la barra de menú"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menú Archivo
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Cerrar Sesión", command=self.logout)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)
        
        # Menú Administración (solo para admins)
        if self.auth_manager.has_permission('admin'):
            admin_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Administración", menu=admin_menu)
            admin_menu.add_command(label="Gestión de Usuarios", command=self.show_user_management)
        
    def setup_notebook(self):
        """Configurar el notebook con pestañas para cada módulo"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Importar las vistas de cada módulo
        try:
            from modules.cash_register.views import CashRegisterView
            from modules.loans.views import LoansView
            
            # Crear pestaña para módulo de caja
            cash_frame = ttk.Frame(self.notebook)
            self.notebook.add(cash_frame, text="Módulo de Caja")
            self.cash_view = CashRegisterView(cash_frame, self.db, self.auth_manager)
            
            # Crear pestaña para módulo de préstamos
            loans_frame = ttk.Frame(self.notebook)
            self.notebook.add(loans_frame, text="Préstamos a Empleados")
            self.loans_view = LoansView(loans_frame, self.db, self.auth_manager)
            
            # Placeholder para el módulo de inventario
            inventory_frame = ttk.Frame(self.notebook)
            self.notebook.add(inventory_frame, text="Inventario de Papa")
            inventory_label = ttk.Label(inventory_frame, text="Módulo de Inventario - En desarrollo")
            inventory_label.pack(pady=20)
            
        except ImportError as e:
            # Placeholder hasta que implementemos los módulos
            for tab_name in ["Módulo de Caja", "Préstamos a Empleados", "Inventario de Papa"]:
                frame = ttk.Frame(self.notebook)
                self.notebook.add(frame, text=tab_name)
                label = ttk.Label(frame, text=f"{tab_name} - En desarrollo")
                label.pack(pady=20)

    def setup_status_bar(self):
        """Configurar la barra de estado"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        user_info = self.auth_manager.get_current_user_info()
        user_text = f"Usuario: {user_info['username']} ({user_info['role']})"
        
        self.status_user = ttk.Label(status_frame, text=user_text)
        self.status_user.pack(side=tk.LEFT, padx=10)
        
        self.status_time = ttk.Label(status_frame, text="")
        self.status_time.pack(side=tk.RIGHT, padx=10)
        
        self.update_clock()
        
    def update_clock(self):
        """Actualizar el reloj en la barra de estado"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_time.config(text=now)
        self.root.after(1000, self.update_clock)
        
    def logout(self):
        """Cerrar sesión y volver a la ventana de login"""
        self.auth_manager.current_user = None
        self.auth_manager.user_role = None
        self.root.destroy()
        
    def show_user_management(self):
        """Mostrar gestión de usuarios (solo admin)"""
        # Se implementará más adelante
        from tkinter import messagebox
        messagebox.showinfo("Información", "Gestión de usuarios - En desarrollo")
        
    def run(self):
        """Ejecutar la ventana principal"""
        self.root.mainloop()