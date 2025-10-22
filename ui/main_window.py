"""
Ventana principal de la aplicación - Versión con módulo de Ventas y responsabilidades separadas
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from tkinter import messagebox
import sys

from utils.notifications import NotificationSystem, NotificationCenter
from utils.scrollframe import ScrollFrame
from PIL import Image, ImageTk

# --- VISTAS DE MÓDULOS ---
from modules.cash_register.cash_register_views import CashRegisterView
from modules.sales.sales_views import SalesView
from modules.inventory.inventory_views import InventoryView
from modules.products.products_views import ProductsView
from modules.loans.loans_views import LoansView
from modules.employees.employees_views import EmployeesView
from modules.payroll.payroll_views import PayrollReportView
from modules.credit_sales.credit_sales_views import CreditSalesView
from modules.supplier_advances.supplier_advances_views import SupplierAdvancesView

# --- CONTROLADORES NECESARIOS ---
from modules.cash_register.cash_register_controller import CashRegisterController

class MainWindow:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth_manager = auth_manager
        self.root = tk.Tk()
        
        try:
            icon_image = Image.open("assets/icons/iconoPapa.png")
            w, h = icon_image.size
            max_size = 64
            scale = min(max_size / w, max_size / h)
            new_w, new_h = int(w * scale), int(h * scale)
            icon_image = icon_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.icon_photo = ImageTk.PhotoImage(icon_image)
            self.root.iconphoto(False, self.icon_photo)
        except Exception as e:
            print(f"No se pudo cargar el icono de la ventana: {e}")

        self.notification_center = NotificationCenter(self.root)
        self.notification_system = NotificationSystem(database, self.notification_center)
        self.setup_window()
        
    def setup_window(self):
        self.root.title("Sistema de Gestión Integral - PapaSoft")
        self.root.geometry("1200x700")
        self.root.configure(bg='#f0f0f0')
        self.setup_menu()
        # self.setup_toolbar() # ELIMINADO según tu solicitud
        self.setup_notebook()
        self.setup_status_bar()
        self.notification_system.start()
        self.root.protocol("WM_DELETE_WINDOW", self.safe_exit)
    
    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Cerrar Sesión", command=self.logout)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.safe_exit)
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ver", menu=view_menu)
        view_menu.add_command(label="Actualizar Pestaña", command=self.refresh_current_tab)
        if self.auth_manager.has_permission('admin'):
            admin_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Administración", menu=admin_menu)
            admin_menu.add_command(label="Gestión de Usuarios", command=self.show_user_management)
    
    # --- setup_toolbar() ELIMINADO COMPLETAMENTE ---
    
    def setup_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.views = {} # Diccionario para guardar referencias a las vistas

        def _add_tab(title, ViewClass, attr_name, *extra_args):
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=title)
            if not ViewClass:
                ttk.Label(frame, text=f"{title} - No disponible").pack(pady=20)
                return
            scroll = ScrollFrame(frame, fit_width=True)
            scroll.pack(fill=tk.BOTH, expand=True)
            view = ViewClass(scroll.body, self.db, self.auth_manager, *extra_args)
            self.views[attr_name] = view # Guardar la instancia de la vista

        try:
            self.cash_controller = CashRegisterController(self.db, self.auth_manager)
        except Exception as e:
            messagebox.showerror("Error Crítico", f"No se pudo iniciar el controlador de Caja: {e}")
            self.cash_controller = None

        # 2. Añade las pestañas (EL ORDEN AQUÍ DEBE COINCIDIR CON 'view_map' ABAJO)
        _add_tab("Módulo de Caja", CashRegisterView, "cash_view") # Índice 0

        if self.cash_controller:
            _add_tab("Ventas", SalesView, "sales_view", self.cash_controller) # Índice 1
            _add_tab("Ventas a Crédito", CreditSalesView, "credit_sales_view", self.cash_controller) # Índice 2
            _add_tab("Anticipos Proveedores", SupplierAdvancesView, "advances_view", self.cash_controller) # Índice 3
        else:
            _add_tab("Ventas", None, "sales_view")
            _add_tab("Ventas a Crédito", None, "credit_sales_view")
            _add_tab("Anticipos Proveedores", None, "advances_view")

        _add_tab("Inventario", InventoryView, "inventory_view") # Índice 4
        _add_tab("Productos", ProductsView, "products_view") # Índice 5
        _add_tab("Préstamos a Empleados", LoansView, "loans_view") # Índice 6
        _add_tab("Empleados", EmployeesView, "employees_view") # Índice 7
        _add_tab("Nómina", PayrollReportView, "payroll_view") # Índice 8

        # Esta es la única vinculación necesaria.
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
    
    # --- MÉTODOS DE COMUNICACIÓN Y REFRESCO ---
    # (ESTA SECCIÓN HA SIDO COMPLETAMENTE LIMPIADA Y CORREGIDA)

    def _on_tab_changed(self, event):
        """
        SOLUCIÓN DEFINITIVA: Se llama CADA VEZ que el usuario cambia de pestaña.
        Refresca la vista que acaba de ser seleccionada.
        """
        self.refresh_current_tab()
    
    def refresh_current_tab(self):
        """
        Llama al método 'refresh_all' de la vista actualmente visible,
        forzando a que cargue los datos frescos desde la base de datos.
        """
        try:
            selected_tab_index = self.notebook.index(self.notebook.select())
            
            # Este mapa DEBE coincidir con el orden en que añades las pestañas
            # en setup_notebook()
            view_map = {
                0: "cash_view",
                1: "sales_view",
                2: "credit_sales_view",
                3: "advances_view",
                4: "inventory_view",
                5: "products_view",
                6: "loans_view",
                7: "employees_view",
                8: "payroll_view"
            }
            
            view_key = view_map.get(selected_tab_index)
            
            if view_key and self.views.get(view_key):
                # ¡Esta es la línea clave!
                # Llama a la función 'refresh_all()' de la pestaña seleccionada.
                self.views[view_key].refresh_all()
                
        except Exception as e:
            # Esta excepción es normal si la pestaña aún no se ha cargado
            # print(f"No se pudo refrescar la pestaña actual (Índice: {selected_tab_index}): {e}")
            pass
            
    # --- FIN DE LA SECCIÓN DE REFRESCO ---

    def setup_status_bar(self):
        """Configurar la barra de estado"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        user_info = self.auth_manager.get_current_user_info()
        if user_info:
            user_text = f"Usuario: {user_info['username']} ({user_info['role']})"
        else:
            user_text = "Usuario: -"
        
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
        
        if count > 0:
            self.notification_indicator.config(foreground="red", font=('Arial', 9, 'bold'))
        else:
            self.notification_indicator.config(foreground="blue", font=('Arial', 9))
        
        self.root.after(30000, self.update_notification_count)  # Actualizar cada 30 segundos
    
    def show_notifications(self):
        """Mostrar centro de notificaciones"""
        self.notification_center.show_notification_center()
    
    def show_preferences(self):
        """Mostrar diálogo de preferencias"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Preferencias - PapaSoft")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Preferencias de la Aplicación", 
                 font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0, 20))
        
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
        Desarrollado por: JHOSSEF NICOLAS CONSTAIN NIEVES
        Numero: 3233585649
        Correo: niconstain@gmail.com
        
        Características:
        • Gestión de Caja
        • Control de Préstamos
        • Inventario de Papa
        • Ventas
        • Reportes y Gráficos
        • Sistema de Notificaciones
        """
        messagebox.showinfo("Acerca de PapaSoft", about_text)
    
    def safe_exit(self):
        """Cierre seguro de la aplicación"""
        if messagebox.askokcancel("Salir", "¿Está seguro de que desea salir de PapaSoft?"):
            self.notification_system.stop()
            if hasattr(self.db, 'close'):
                self.db.close()
            sys.exit(0)
    
    def logout(self):
        """Cerrar sesión y volver a la ventana de login"""
        if messagebox.askokcancel("Cerrar Sesión", "¿Está seguro de que desea cerrar sesión?"):
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
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"papasoft_backup_{timestamp}.db")
            
            shutil.copy2("papasoft.db", backup_file)
            messagebox.showinfo("Backup Exitoso", f"Backup creado en: {backup_file}")
            
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
            backup_file = filedialog.askopenfilename(
                title="Seleccionar archivo de backup",
                filetypes=[("Database files", "*.db"), ("All files", "*.*")]
            )
            
            if not backup_file:
                return
            
            if messagebox.askyesno("Confirmar", 
                "¿Está seguro de restaurar este backup? Se sobrescribirán todos los datos actuales."):
                
                if hasattr(self.db, 'close'):
                    self.db.close()
                
                shutil.copy2(backup_file, "papasoft.db")
                
                if hasattr(self.db, 'connect'):
                    self.db.connect()
                
                messagebox.showinfo("Restauración Exitosa", "Backup restaurado correctamente")
                
                self.notification_center.add_notification(
                    "Backup Restaurado",
                    f"Se restauró la base de datos desde: {os.path.basename(backup_file)}",
                    "warning"
                )
                
                # Forzar recarga de la pestaña actual
                self.refresh_current_tab()
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo restaurar el backup: {str(e)}")
    
    def run(self):
        """Ejecutar la ventana principal"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Forzar una carga inicial de la primera pestaña
        self.refresh_current_tab() 
        
        self.root.mainloop()