"""
Ventana principal de la aplicación - Versión con módulo de Ventas y responsabilidades separadas
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading
from tkinter import messagebox
import sys
from utils.notifications import NotificationSystem, NotificationCenter
from utils.scrollframe import ScrollFrame
from PIL import Image, ImageTk


class MainWindow:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth_manager = auth_manager
        self.root = tk.Tk()
        
        # 👉 Agregar icono a la ventana
        try:
            icon_image = Image.open("assets/icons/iconoPapa.png")
            # Redimensionar manteniendo proporción
            w, h = icon_image.size
            max_size = 64  # tamaño máximo recomendado para íconos
            scale = min(max_size / w, max_size / h)
            new_w, new_h = int(w * scale), int(h * scale)
            icon_image = icon_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.icon_photo = ImageTk.PhotoImage(icon_image)
            self.root.iconphoto(False, self.icon_photo)
        except Exception as e:
            print(f"No se pudo cargar el icono de la ventana: {e}")

        # Sistema de notificaciones
        self.notification_center = NotificationCenter(self.root)
        self.notification_system = NotificationSystem(database, self.notification_center)



        self.setup_window()
        
    def setup_window(self):
        """Configurar la ventana principal"""
        self.root.title("Sistema de Gestión Integral - PapaSoft")
        self.root.geometry("1200x700")
        self.root.configure(bg='#f0f0f0')
        
        # Configurar icono (si existe)
        try:
            self.root.iconbitmap("assets/iconoPapa.ico")
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
        
        # Acerca de
        menubar.add_command(label="Acerca de PapaSoft", command=self.show_about)
    
    def setup_toolbar(self):
        """Configurar la barra de herramientas"""
        toolbar = ttk.Frame(self.root, relief=tk.RAISED, borderwidth=1)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # Botones de la toolbar
        ttk.Button(toolbar, text="Actualizar", command=self.refresh_all).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Button(toolbar, text="Notificaciones", command=self.show_notifications).pack(side=tk.LEFT, padx=2, pady=2)
        
        # Separador
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
    
    def setup_notebook(self):
        """Configurar el notebook con pestañas para cada módulo (con scroll)."""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        try:
            # Import dinámico de vistas disponibles
            from modules.cash_register.views import CashRegisterView
        except Exception:
            CashRegisterView = None
        try:
            from modules.sales.views import SalesView
        except Exception:
            SalesView = None
        try:
            from modules.loans.views import LoansView
        except Exception:
            LoansView = None
        try:
            from modules.inventory.views import InventoryView
        except Exception:
            InventoryView = None
        try:
            from modules.employees.views import EmployeesView
        except Exception:
            EmployeesView = None
        try:
            from modules.payroll.views import PayrollReportView
        except Exception:
            PayrollReportView = None

        # Helper para crear pestañas con scroll y montar la vista
        def _add_tab(title, ViewClass, attr_name, *extra_args):
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=title)
            if ViewClass is None:
                ttk.Label(frame, text=f"{title} - No disponible (módulo no encontrado)").pack(pady=20)
                return
            scroll = ScrollFrame(frame, fit_width=True)
            scroll.pack(fill=tk.BOTH, expand=True)
            parent_for_view = scroll.body  # aquí la vista puede usar pack/grid sin restricciones
            view = ViewClass(parent_for_view, self.db, self.auth_manager, *extra_args)
            setattr(self, attr_name, view)

        # Crea pestañas
        _add_tab("Módulo de Caja", CashRegisterView, "cash_view")
        if SalesView:
            try:
                from modules.cash_register.controller import CashRegisterController
                self.cash_controller = CashRegisterController(self.db, self.auth_manager)
                _add_tab("Ventas", SalesView, "sales_view", self.cash_controller)
            except Exception:
                _add_tab("Ventas", SalesView, "sales_view")
        _add_tab("Inventario de Papa", InventoryView, "inventory_view")
        _add_tab("Préstamos a Empleados", LoansView, "loans_view")
        _add_tab("Empleados", EmployeesView, "employees_view")
        _add_tab("Nómina", PayrollReportView, "payroll_view")

        # refresco al cambiar de pestaña (si ya tienes uno, mantén el tuyo)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.root.bind("<F5>", lambda e: self.refresh_current_tab())
        
        # 🔔 Escuchar ventas creadas para refrescar Inventario en caliente
        self.root.bind("<<SaleCreated>>", lambda e: self._on_sale_created())

    def _on_sale_created(self):
        try:
            # Refrescar Inventario enseguida
            if hasattr(self, "inventory_view") and self.inventory_view:
                if hasattr(self.inventory_view, "refresh_all"):
                    self.inventory_view.refresh_all()
                else:
                    # fallbacks
                    if hasattr(self.inventory_view, "refresh_stock_table"):
                        self.inventory_view.refresh_stock_table()
                    if hasattr(self.inventory_view, "refresh_valuation_table"):
                        self.inventory_view.refresh_valuation_table()
                    if hasattr(self.inventory_view, "refresh_sacks_label"):
                        self.inventory_view.refresh_sacks_label()
            # Opcional: también refrescar indicadores en la vista de ventas
            if hasattr(self, "sales_view") and self.sales_view:
                if hasattr(self.sales_view, "_refresh_stock_labels"):
                    self.sales_view._refresh_stock_labels()
                if hasattr(self.sales_view, "_auto_fill_price"):
                    self.sales_view._auto_fill_price()
        except Exception as ex:
            print("No se pudo refrescar tras venta:", ex)

    
    def _refresh_view_safely(self, view):
        """Intenta llamar el método de refresco que exista en la vista."""
        if not view:
            return
        for name in (
            "refresh_all", "reload", "refresh", "load", "load_data",
            "load_transactions", "load_loans", "load_inventory", "load_sales"
        ):
            if hasattr(view, name):
                try:
                    getattr(view, name)()
                except Exception as e:
                    from tkinter import messagebox
                    messagebox.showerror("Error", f"No se pudo refrescar el módulo: {e}")
                break  # encontró un método válido

    def _on_tab_changed(self, event):
        """Se dispara al cambiar de pestaña: refresca solo ese módulo."""
        try:
            tab_text = event.widget.tab(event.widget.select(), "text").lower()
            if "venta" in tab_text and hasattr(self, "sales_view"):
                self._refresh_view_safely(self.sales_view)
            elif "caja" in tab_text and hasattr(self, "cash_view"):
                self._refresh_view_safely(self.cash_view)
            elif ("préstamo" in tab_text or "prestamo" in tab_text) and hasattr(self, "loans_view"):
                self._refresh_view_safely(self.loans_view)
            elif "inventario" in tab_text and hasattr(self, "inventory_view"):
                self._refresh_view_safely(self.inventory_view)
            elif "emplead" in tab_text and hasattr(self, "employees_view"):
                self._refresh_view_safely(self.employees_view)
            elif "nómina" in tab_text or "nomina" in tab_text:
                if hasattr(self, "payroll_view"):
                    self._refresh_view_safely(self.payroll_view)
            else:
                # Si no reconoce la pestaña, como fallback refresca todo
                self.refresh_all()
        except Exception:
            pass

    def refresh_current_tab(self):
        """Refresca la pestaña activa (atajo para F5 y para usar donde quieras)."""
        self._on_tab_changed(type("E", (object,), {"widget": self.notebook})())

    
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
        
        # Cambiar color si hay notificaciones no leídas
        if count > 0:
            self.notification_indicator.config(foreground="red", font=('Arial', 9, 'bold'))
        else:
            self.notification_indicator.config(foreground="blue", font=('Arial', 9))
        
        self.root.after(30000, self.update_notification_count)  # Actualizar cada 30 segundos
    
    def refresh_all(self):
        """Actualizar todos los módulos (sin romper compatibilidad con distintas vistas)"""
        try:
            # Caja
            if hasattr(self, 'cash_view'):
                if hasattr(self.cash_view, 'load_transactions'):
                    self.cash_view.load_transactions()
                elif hasattr(self.cash_view, 'refresh'):
                    self.cash_view.refresh()
            
            # Préstamos
            if hasattr(self, 'loans_view'):
                if hasattr(self.loans_view, 'load_loans'):
                    self.loans_view.load_loans()
                elif hasattr(self.loans_view, 'refresh'):
                    self.loans_view.refresh()
            
            # Inventario (nueva vista usa refresh_table)
            if hasattr(self, 'inventory_view'):
                if hasattr(self.inventory_view, 'refresh_all'):
                    self.inventory_view.refresh_all()
                else:
                    # fallback por si en algún momento cambiaste nombres
                    if hasattr(self.inventory_view, 'refresh_stock_table'):
                        self.inventory_view.refresh_stock_table()
                    if hasattr(self.inventory_view, 'refresh_valuation_table'):
                        self.inventory_view.refresh_valuation_table()
                    if hasattr(self.inventory_view, 'refresh_sacks_label'):
                        self.inventory_view.refresh_sacks_label()
            
            # Ventas (refrescar stocks y precio sugerido)
            if hasattr(self, 'sales_view'):
                if hasattr(self.sales_view, '_refresh_stock_labels'):
                    self.sales_view._refresh_stock_labels()
                if hasattr(self.sales_view, '_auto_fill_price'):
                    self.sales_view._auto_fill_price()
            
            messagebox.showinfo("Actualizado", "Todos los módulos han sido actualizados")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron actualizar los módulos: {str(e)}")
    
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
            # Detener sistema de notificaciones
            self.notification_system.stop()

            # Cerrar base de datos
            if hasattr(self.db, 'close'):
                self.db.close()

            sys.exit(0)
    
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
