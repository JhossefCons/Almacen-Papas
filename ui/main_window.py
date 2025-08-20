"""
Ventana principal de la aplicación - Versión Final
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading
from tkinter import messagebox
from utils.notifications import NotificationSystem, NotificationCenter
from help.help_system import HelpSystem, QuickHelp

class MainWindow:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth_manager = auth_manager
        self.root = tk.Tk()
        
        # Sistema de notificaciones
        self.notification_system = NotificationSystem(database)
        self.notification_center = NotificationCenter(self.root)
        
        # Sistema de ayuda
        self.help_system = HelpSystem(self.root)
        
        self.setup_window()
        
    def setup_window(self):
        """Configurar la ventana principal"""
        self.root.title("Sistema de Gestión Integral - PapaSoft")
        self.root.geometry("1200x700")
        self.root.configure(bg='#f0f0f0')
        
        # Configurar icono (si existe)
        try:
            self.root.iconbitmap("assets/icon.ico")
        except:
            pass
        
        # Configurar la barra de menú
        self.setup_menu()
        
        # Configurar la barra de herramientas
        self.setup_toolbar()
        
        # Configurar el notebook (pestañas)
        self.setup_notebook()
        
        # Configurar la barra de estado
        self.setup_status_bar()
        
        # Iniciar sistema de notificaciones
        self.notification_system.start()
        
        # Configurar cierre seguro
        self.root.protocol("WM_DELETE_WINDOW", self.safe_exit)
    
    def setup_menu(self):
        """Configurar la barra de menú"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menú Archivo
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Cerrar Sesión", command=self.logout)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.safe_exit)
        
        # Menú Edición
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edición", menu=edit_menu)
        edit_menu.add_command(label="Preferencias", command=self.show_preferences)
        
        # Menú Ver
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ver", menu=view_menu)
        view_menu.add_command(label="Notificaciones", command=self.show_notifications)
        view_menu.add_command(label="Actualizar", command=self.refresh_all)
        
        # Menú Administración (solo para admins)
        if self.auth_manager.has_permission('admin'):
            admin_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Administración", menu=admin_menu)
            admin_menu.add_command(label="Gestión de Usuarios", command=self.show_user_management)
            admin_menu.add_command(label="Backup Base de Datos", command=self.backup_database)
            admin_menu.add_command(label="Restaurar Backup", command=self.restore_backup)
        
        # Menú Ayuda
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        help_menu.add_command(label="Contenido de Ayuda", command=lambda: self.help_system.show_help())
        help_menu.add_command(label="Manual de Usuario", command=lambda: self.help_system.show_help('manual'))
        help_menu.add_separator()
        help_menu.add_command(label="Acerca de PapaSoft", command=self.show_about)
    
    def setup_toolbar(self):
        """Configurar la barra de herramientas"""
        toolbar = ttk.Frame(self.root, relief=tk.RAISED, borderwidth=1)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # Botones de la toolbar
        ttk.Button(toolbar, text="Actualizar", command=self.refresh_all).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar, text="Notificaciones", command=self.show_notifications).pack(side=tk.LEFT, padx=2, pady=2)
        
        # Separador
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        # Botones de ayuda contextual
        ttk.Button(toolbar, text="Ayuda Caja", 
                  command=lambda: self.help_system.show_help('caja')).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar, text="Ayuda Préstamos", 
                  command=lambda: self.help_system.show_help('prestamos')).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar, text="Ayuda Inventario", 
                  command=lambda: self.help_system.show_help('inventario')).pack(side=tk.LEFT, padx=2, pady=2)
    
    def setup_notebook(self):
        """Configurar el notebook con pestañas para cada módulo"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Importar las vistas de cada módulo
        try:
            from modules.cash_register.views import CashRegisterView
            from modules.loans.views import LoansView
            from modules.inventory.views import InventoryView
            
            # Crear pestaña para módulo de caja
            cash_frame = ttk.Frame(self.notebook)
            self.notebook.add(cash_frame, text="Módulo de Caja")
            self.cash_view = CashRegisterView(cash_frame, self.db, self.auth_manager)
            
            # Crear pestaña para módulo de préstamos
            loans_frame = ttk.Frame(self.notebook)
            self.notebook.add(loans_frame, text="Préstamos a Empleados")
            self.loans_view = LoansView(loans_frame, self.db, self.auth_manager)
            
            # Crear pestaña para módulo de inventario
            inventory_frame = ttk.Frame(self.notebook)
            self.notebook.add(inventory_frame, text="Inventario de Papa")
            self.inventory_view = InventoryView(inventory_frame, self.db, self.auth_manager)
            
        except ImportError as e:
            # Placeholder en caso de error
            for tab_name in ["Módulo de Caja", "Préstamos a Empleados", "Inventario de Papa"]:
                frame = ttk.Frame(self.notebook)
                self.notebook.add(frame, text=tab_name)
                label = ttk.Label(frame, text=f"{tab_name} - Error al cargar: {str(e)}")
                label.pack(pady=20)
    
    def setup_status_bar(self):
        """Configurar la barra de estado"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        user_info = self.auth_manager.get_current_user_info()
        user_text = f"Usuario: {user_info['username']} ({user_info['role']})"
        
        self.status_user = ttk.Label(status_frame, text=user_text)
        self.status_user.pack(side=tk.LEFT, padx=10)
        
        # Indicador de notificaciones
        self.notification_indicator = ttk.Label(status_frame, text="Notificaciones: 0", 
                                               foreground="blue", cursor="hand2")
        self.notification_indicator.pack(side=tk.LEFT, padx=10)
        self.notification_indicator.bind("<Button-1>", lambda e: self.show_notifications())
        
        self.status_time = ttk.Label(status_frame, text="")
        self.status_time.pack(side=tk.RIGHT, padx=10)
        
        self.update_clock()
        self.update_notification_count()
    
    def update_clock(self):
        """Actualizar el reloj en la barra de estado"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_time.config(text=now)
        self.root.after(1000, self.update_clock)
    
    def update_notification_count(self):
        """Actualizar contador de notificaciones"""
        count = self.notification_center.get_unread_count()
        self.notification_indicator.config(text=f"Notificaciones: {count}")
        
        # Cambiar color si hay notificaciones no leídas
        if count > 0:
            self.notification_indicator.config(foreground="red", font=('Arial', 9, 'bold'))
        else:
            self.notification_indicator.config(foreground="blue", font=('Arial', 9))
        
        self.root.after(30000, self.update_notification_count)  # Actualizar cada 30 segundos
    
    def refresh_all(self):
        """Actualizar todos los módulos"""
        try:
            if hasattr(self, 'cash_view'):
                self.cash_view.load_transactions()
            if hasattr(self, 'loans_view'):
                self.loans_view.load_loans()
            if hasattr(self, 'inventory_view'):
                self.inventory_view.load_inventory()
            
            messagebox.showinfo("Actualizado", "Todos los módulos han sido actualizados")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron actualizar los módulos: {str(e)}")
    
    def show_notifications(self):
        """Mostrar centro de notificaciones"""
        self.notification_center.show_notification_center()
    
    def show_preferences(self):
        """Mostrar diálogo de preferencias"""
        # Implementación básica de preferencias
        dialog = tk.Toplevel(self.root)
        dialog.title("Preferencias - PapaSoft")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Preferencias de la Aplicación", 
                 font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0, 20))
        
        # Aquí puedes agregar más opciones de configuración
        ttk.Label(main_frame, text="Opciones de notificación:").pack(anchor=tk.W, pady=(0, 5))
        
        # Ejemplo: Checkbox para notificaciones
        notif_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="Activar notificaciones", 
                       variable=notif_var).pack(anchor=tk.W, pady=2)
        
        ttk.Button(main_frame, text="Guardar", 
                  command=dialog.destroy).pack(pady=20)
    
    def show_about(self):
        """Mostrar diálogo Acerca de"""
        about_text = """
        PapaSoft - Sistema de Gestión Integral
        
        Versión: 1.0.0
        Desarrollado por: Tu Empresa
        
        Características:
        • Gestión de Caja
        • Control de Préstamos
        • Inventario de Papa
        • Reportes y Gráficos
        • Sistema de Notificaciones
        
        © 2024 Tu Empresa. Todos los derechos reservados.
        """
        
        messagebox.showinfo("Acerca de PapaSoft", about_text)
    
    def safe_exit(self):
        """Cierre seguro de la aplicación"""
        if messagebox.askokcancel("Salir", "¿Está seguro de que desea salir de PapaSoft?"):
            # Detener sistema de notificaciones
            self.notification_system.stop()
            
            # Cerrar base de datos
            if hasattr(self.db, 'close'):
                self.db.close()
            
            self.root.quit()
    
    def logout(self):
        """Cerrar sesión y volver a la ventana de login"""
        if messagebox.askokcancel("Cerrar Sesión", "¿Está seguro de que desea cerrar sesión?"):
            # Detener sistema de notificaciones
            self.notification_system.stop()
            
            self.auth_manager.current_user = None
            self.auth_manager.user_role = None
            self.root.destroy()
    
    def show_user_management(self):
        """Mostrar gestión de usuarios (solo admin)"""
        self.auth_manager.show_user_management(self.root)
    
    def backup_database(self):
        """Realizar backup de la base de datos"""
        import shutil
        import os
        from datetime import datetime
        
        try:
            # Crear directorio de backups si no existe
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            # Generar nombre de archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"papasoft_backup_{timestamp}.db")
            
            # Copiar archivo de base de datos
            shutil.copy2("papasoft.db", backup_file)
            
            messagebox.showinfo("Backup Exitoso", f"Backup creado en: {backup_file}")
            
            # Agregar notificación
            self.notification_center.add_notification(
                "Backup Realizado",
                f"Se creó un backup de la base de datos: {backup_file}",
                "info"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear el backup: {str(e)}")
    
    def restore_backup(self):
        """Restaurar backup de la base de datos"""
        import shutil
        import os
        from tkinter import filedialog
        
        try:
            # Seleccionar archivo de backup
            backup_file = filedialog.askopenfilename(
                title="Seleccionar archivo de backup",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")]
            )
            
            if not backup_file:
                return
            
            if messagebox.askyesno("Confirmar", 
                "¿Está seguro de restaurar este backup? Se sobrescribirán todos los datos actuales."):
                
                # Cerrar conexión actual
                if hasattr(self.db, 'close'):
                    self.db.close()
                
                # Restaurar backup
                shutil.copy2(backup_file, "papasoft.db")
                
                # Reconectar
                if hasattr(self.db, 'connect'):
                    self.db.connect()
                
                messagebox.showinfo("Restauración Exitosa", "Backup restaurado correctamente")
                
                # Agregar notificación
                self.notification_center.add_notification(
                    "Backup Restaurado",
                    f"Se restauró la base de datos desde: {os.path.basename(backup_file)}",
                    "warning"
                )
                
                # Recargar todos los módulos
                self.refresh_all()
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo restaurar el backup: {str(e)}")
    
    def run(self):
        """Ejecutar la ventana principal"""
        # Centrar ventana en la pantalla
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        self.root.mainloop()