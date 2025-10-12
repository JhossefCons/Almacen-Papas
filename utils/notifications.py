"""
Sistema de notificaciones y recordatorios para PapaSoft
"""
import threading
import time
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk

class NotificationSystem:
    def __init__(self, database, notification_center=None, check_interval=300):  # 5 minutos por defecto
        self.db = database
        self.notification_center = notification_center
        self.check_interval = check_interval
        self.running = False
        self.thread = None
    
    def start(self):
        """Iniciar el sistema de notificaciones"""
        self.running = True
        self.thread = threading.Thread(target=self._check_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Detener el sistema de notificaciones"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
    
    def _check_loop(self):
        """Bucle principal de verificación"""
        while self.running:
            try:
                self.check_overdue_loans()
                self.check_low_stock()
                self.check_daily_cash_balance()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Error en sistema de notificaciones: {e}")
                time.sleep(60)  # Esperar 1 minuto antes de reintentar
    
    def check_overdue_loans(self):
        """Verificar préstamos vencidos"""
        try:
            query = """
                SELECT l.*, 
                       (SELECT COALESCE(SUM(amount), 0) FROM loan_payments WHERE loan_id = l.id) as total_paid,
                       (l.amount * (1 + l.interest_rate / 100)) - 
                       (SELECT COALESCE(SUM(amount), 0) FROM loan_payments WHERE loan_id = l.id) as balance
                FROM loans l
                WHERE l.status = 'active' AND l.due_date < date('now')
            """
            
            results = self.db.execute_query(query)
            overdue_loans = [dict(row) for row in results] if results else []
            
            for loan in overdue_loans:
                if loan['balance'] > 0:
                    days_overdue = (datetime.now().date() - 
                                  datetime.strptime(loan['due_date'], '%Y-%m-%d').date()).days
                    
                    # Mostrar notificación solo una vez al día por préstamo
                    notification_key = f"overdue_{loan['id']}_{datetime.now().strftime('%Y-%m-%d')}"
                    
                    # Aquí podrías guardar en una tabla de notificaciones mostradas
                    # Por ahora mostramos directamente
                    if days_overdue % 7 == 0:  # Recordar cada 7 días
                        self.show_notification(
                            "Préstamo Vencido",
                            f"Préstamo de {loan['employee_name']} vencido hace {days_overdue} días. "
                            f"Saldo pendiente: ${loan['balance']:.2f}"
                        )
                        
        except Exception as e:
            print(f"Error verificando préstamos vencidos: {e}")
    
    def check_low_stock(self):
        """Verificar stock bajo"""
        try:
            query = """
                SELECT
                    product_name as potato_type,
                    quality,
                    SUM(CASE WHEN operation = 'entry' THEN quantity ELSE -quantity END) as current_stock
                FROM inventory_movements
                GROUP BY product_name, quality
                HAVING current_stock > 0 AND current_stock <= 20  -- Umbral de 20 costales
            """

            results = self.db.execute_query(query)
            low_stock_items = [dict(row) for row in results] if results else []

            for item in low_stock_items:
                notification_key = f"lowstock_{item['potato_type']}_{item['quality']}_{datetime.now().strftime('%Y-%m-%d')}"

                self.show_notification(
                    "Stock Bajo",
                    f"Stock bajo de {item['potato_type']} {item['quality']}: "
                    f"{item['current_stock']} costales restantes"
                )

        except Exception as e:
            print(f"Error verificando stock bajo: {e}")
    
    def check_daily_cash_balance(self):
        """Verificar balance de caja diario"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Verificar si ya se hizo el cierre de caja hoy
            query_check = "SELECT COUNT(*) FROM cash_register WHERE date = ? AND description LIKE '%CIERRE DE CAJA%'"
            result = self.db.execute_query(query_check, (today,))
            
            if result and result[0][0] == 0:
                # Obtener balance del día
                query_balance = """
                    SELECT 
                        SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                        SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense,
                        SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END) as balance
                    FROM cash_register 
                    WHERE date = ?
                """
                
                result_balance = self.db.execute_query(query_balance, (today,))
                if result_balance:
                    balance = result_balance[0]['balance'] or 0
                    
                    # Recordatorio a las 5 PM para hacer cierre de caja
                    now = datetime.now()
                    if now.hour == 17 and now.minute < 5:  # Entre 5:00 y 5:04 PM
                        self.show_notification(
                            "Cierre de Caja",
                            f"Recuerda hacer el cierre de caja del día. Balance provisional: ${balance:.2f}"
                        )
                        
        except Exception as e:
            print(f"Error verificando cierre de caja: {e}")
    
    def show_notification(self, title, message):
        """Mostrar notificación (esto se puede mejorar con un sistema de notificaciones propio)"""
        try:
            # En un entorno real, podrías usar un sistema de notificaciones más sofisticado
            print(f"NOTIFICACIÓN: {title} - {message}")

            # Agregar a la interfaz de usuario si hay un centro de notificaciones disponible
            if self.notification_center:
                self.notification_center.add_notification(title, message, "info")

        except Exception as e:
            print(f"Error mostrando notificación: {e}")

class NotificationCenter:
    """Centro de notificaciones para la interfaz de usuario"""
    def __init__(self, parent):
        self.parent = parent
        self.notifications = []
        self.window = None
    
    def add_notification(self, title, message, level="info"):
        """Agregar una notificación"""
        self.notifications.append({
            'title': title,
            'message': message,
            'level': level,
            'timestamp': datetime.now(),
            'read': False
        })
        
        # Limitar a 100 notificaciones
        if len(self.notifications) > 100:
            self.notifications = self.notifications[-100:]
    
    def show_notification_center(self):
        """Mostrar el centro de notificaciones"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
        
        self.window = tk.Toplevel(self.parent)
        self.window.title("Centro de Notificaciones - PapaSoft")
        self.window.geometry("600x400")
        self.window.transient(self.parent)
        
        # Frame principal
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Botones de acción
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, text="Marcar Todas como Leídas", 
                  command=self.mark_all_read).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Limpiar Todas", 
                  command=self.clear_all).pack(side=tk.LEFT, padx=5)
        
        # Lista de notificaciones
        columns = ('status', 'time', 'title', 'message')
        self.notif_tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=15)
        
        self.notif_tree.heading('status', text='Estado')
        self.notif_tree.heading('time', text='Hora')
        self.notif_tree.heading('title', text='Título')
        self.notif_tree.heading('message', text='Mensaje')
        
        self.notif_tree.column('status', width=80)
        self.notif_tree.column('time', width=120)
        self.notif_tree.column('title', width=150)
        self.notif_tree.column('message', width=250)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.notif_tree.yview)
        self.notif_tree.configure(yscrollcommand=scrollbar.set)
        
        self.notif_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Cargar notificaciones
        self.load_notifications()
        
        # Bind eventos
        self.notif_tree.bind('<Double-1>', self.on_notification_double_click)
        
        # Configurar cierre de ventana
        self.window.protocol("WM_DELETE_WINDOW", self.on_window_close)
    
    def load_notifications(self):
        """Cargar notificaciones en el treeview"""
        # Limpiar treeview
        for item in self.notif_tree.get_children():
            self.notif_tree.delete(item)
        
        # Agregar notificaciones
        for notif in reversed(self.notifications):  # Más recientes primero
            status = "Nueva" if not notif['read'] else "Leída"
            time_str = notif['timestamp'].strftime("%Y-%m-%d %H:%M")
            
            # Acortar mensaje si es muy largo
            message = notif['message']
            if len(message) > 50:
                message = message[:47] + "..."
            
            self.notif_tree.insert('', 'end', values=(
                status,
                time_str,
                notif['title'],
                message
            ), tags=('unread' if not notif['read'] else 'read'))
        
        # Configurar colores
        self.notif_tree.tag_configure('unread', font=('Arial', 9, 'bold'))
    
    def on_notification_double_click(self, event):
        """Manejar doble clic en notificación"""
        selection = self.notif_tree.selection()
        if not selection:
            return
        
        item = self.notif_tree.item(selection[0])
        index = len(self.notifications) - self.notif_tree.index(selection[0]) - 1
        
        if 0 <= index < len(self.notifications):
            notif = self.notifications[index]
            notif['read'] = True
            
            # Mostrar detalles
            self.show_notification_details(notif)
            
            # Actualizar lista
            self.load_notifications()
    
    def show_notification_details(self, notif):
        """Mostrar detalles de la notificación"""
        details_window = tk.Toplevel(self.window)
        details_window.title(f"Detalles de Notificación - {notif['title']}")
        details_window.geometry("500x300")
        details_window.transient(self.window)
        
        # Marco principal
        main_frame = ttk.Frame(details_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text=notif['title'], font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(main_frame, text=f"Hora: {notif['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}").pack(anchor=tk.W, pady=(0, 10))
        
        # Mensaje con scroll
        message_frame = ttk.LabelFrame(main_frame, text="Mensaje", padding=10)
        message_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        message_text = tk.Text(message_frame, wrap=tk.WORD, height=10)
        message_text.insert(tk.END, notif['message'])
        message_text.config(state=tk.DISABLED)
        
        scrollbar = ttk.Scrollbar(message_frame, orient=tk.VERTICAL, command=message_text.yview)
        message_text.configure(yscrollcommand=scrollbar.set)
        
        message_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        ttk.Button(main_frame, text="Cerrar", command=details_window.destroy).pack(pady=10)
    
    def mark_all_read(self):
        """Marcar todas las notificaciones como leídas"""
        for notif in self.notifications:
            notif['read'] = True
        self.load_notifications()
    
    def clear_all(self):
        """Limpiar todas las notificaciones"""
        self.notifications = []
        self.load_notifications()
    
    def on_window_close(self):
        """Manejar cierre de ventana"""
        self.window.destroy()
        self.window = None
    
    def get_unread_count(self):
        """Obtener conteo de notificaciones no leídas"""
        return sum(1 for notif in self.notifications if not notif['read'])