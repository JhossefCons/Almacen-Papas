"""
Vista para el módulo de préstamos a empleados
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta

from modules.loans.controller import LoansController

class LoansView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth_manager = auth_manager
        self.controller = LoansController(database, auth_manager)
        
        self.setup_ui()
        self.load_loans()
    
    def setup_ui(self):
        """Configurar la interfaz de usuario del módulo de préstamos"""
        # Frame principal con paneles divididos
        main_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Panel izquierdo para formulario y filtros
        left_frame = ttk.Frame(main_paned, padding=10)
        main_paned.add(left_frame, weight=1)
        
        # Panel derecho para la lista de préstamos
        right_frame = ttk.Frame(main_paned, padding=10)
        main_paned.add(right_frame, weight=2)
        
        # Formulario para nuevo préstamo
        form_frame = ttk.LabelFrame(left_frame, text="Nuevo Préstamo", padding=10)
        form_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(form_frame, text="Empleado:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.employee_entry = ttk.Entry(form_frame)
        self.employee_entry.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Monto:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.amount_entry = ttk.Entry(form_frame)
        self.amount_entry.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Fecha Préstamo:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.date_issued_entry = DateEntry(form_frame, date_pattern='yyyy-mm-dd')
        self.date_issued_entry.set_date(datetime.now())
        self.date_issued_entry.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Fecha Vencimiento:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.due_date_entry = DateEntry(form_frame, date_pattern='yyyy-mm-dd')
        self.due_date_entry.set_date(datetime.now() + timedelta(days=30))
        self.due_date_entry.grid(row=3, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Tasa Interés (%):").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.interest_entry = ttk.Entry(form_frame)
        self.interest_entry.insert(0, "0")
        self.interest_entry.grid(row=4, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Notas:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.notes_entry = ttk.Entry(form_frame)
        self.notes_entry.grid(row=5, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Agregar", command=self.add_loan).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Limpiar", command=self.clear_form).pack(side=tk.LEFT, padx=5)
        
        # Filtros
        filter_frame = ttk.LabelFrame(left_frame, text="Filtros", padding=10)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Estado:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.status_filter = ttk.Combobox(filter_frame, state="readonly", width=18)
        self.status_filter['values'] = ('', 'active', 'paid', 'overdue')
        self.status_filter.set('')
        self.status_filter.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(filter_frame, text="Empleado:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.employee_filter = ttk.Entry(filter_frame)
        self.employee_filter.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Button(filter_frame, text="Aplicar Filtros", command=self.apply_filters).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Alertas de vencimientos
        alerts_frame = ttk.LabelFrame(left_frame, text="Alertas de Vencimiento", padding=10)
        alerts_frame.pack(fill=tk.X)
        
        self.alerts_text = tk.Text(alerts_frame, height=6, width=30)
        self.alerts_text.pack(fill=tk.BOTH, expand=True)
        self.alerts_text.config(state=tk.DISABLED)
        
        ttk.Button(alerts_frame, text="Actualizar Alertas", command=self.update_alerts).pack(pady=5)
        
        # Lista de préstamos
        list_frame = ttk.Frame(right_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview para mostrar préstamos
        columns = ('id', 'employee', 'amount', 'issued', 'due', 'interest', 'status', 'user')
        self.loans_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        # Definir columnas
        self.loans_tree.heading('id', text='ID')
        self.loans_tree.heading('employee', text='Empleado')
        self.loans_tree.heading('amount', text='Monto')
        self.loans_tree.heading('issued', text='Fecha Préstamo')
        self.loans_tree.heading('due', text='Fecha Vencimiento')
        self.loans_tree.heading('interest', text='Interés %')
        self.loans_tree.heading('status', text='Estado')
        self.loans_tree.heading('user', text='Usuario')
        
        # Ajustar anchos de columnas
        self.loans_tree.column('id', width=40)
        self.loans_tree.column('employee', width=100)
        self.loans_tree.column('amount', width=80)
        self.loans_tree.column('issued', width=90)
        self.loans_tree.column('due', width=90)
        self.loans_tree.column('interest', width=70)
        self.loans_tree.column('status', width=80)
        self.loans_tree.column('user', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.loans_tree.yview)
        self.loans_tree.configure(yscrollcommand=scrollbar.set)
        
        self.loans_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botones de acción para préstamos
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=(5, 0))
        
        if self.auth_manager.has_permission('admin'):
            ttk.Button(action_frame, text="Editar", command=self.edit_loan).pack(side=tk.LEFT, padx=5)
            ttk.Button(action_frame, text="Eliminar", command=self.delete_loan).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(action_frame, text="Ver Detalles", command=self.show_loan_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Registrar Pago", command=self.show_payment_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Actualizar", command=self.load_loans).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Reporte", command=self.show_report).pack(side=tk.RIGHT, padx=5)
        
        # Configurar pesos de grid
        form_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(1, weight=1)
        
        # Bind eventos
        self.loans_tree.bind('<Double-1>', self.on_loan_double_click)
        
        # Actualizar alertas
        self.update_alerts()
    
    def load_loans(self):
        """Cargar préstamos en el treeview"""
        # Limpiar treeview
        for item in self.loans_tree.get_children():
            self.loans_tree.delete(item)
        
        # Obtener préstamos
        loans = self.controller.get_loans()
        
        # Agregar préstamos al treeview
        for loan in loans:
            # Determinar color según estado
            tags = ()
            if loan['status'] == 'overdue':
                tags = ('overdue',)
            elif loan['status'] == 'paid':
                tags = ('paid',)
            
            self.loans_tree.insert('', 'end', values=(
                loan['id'],
                loan['employee_name'],
                f"${float(loan['amount']):.2f}",
                loan['date_issued'],
                loan['due_date'],
                f"{float(loan['interest_rate']):.1f}%",
                self._translate_status(loan['status']),
                loan['username'] or ''
            ), tags=tags)
        
        # Configurar colores para diferentes estados
        self.loans_tree.tag_configure('overdue', background='#ffcccc')  # Rojo claro para vencidos
        self.loans_tree.tag_configure('paid', background='#ccffcc')     # Verde claro para pagados
    
    def _translate_status(self, status):
        """Traducir estados al español"""
        translations = {
            'active': 'Activo',
            'paid': 'Pagado',
            'overdue': 'Vencido'
        }
        return translations.get(status, status)
    
    def apply_filters(self):
        """Aplicar filtros a los préstamos"""
        status_filter = self.status_filter.get() or None
        employee_filter = self.employee_filter.get() or None
        
        # Limpiar treeview
        for item in self.loans_tree.get_children():
            self.loans_tree.delete(item)
        
        # Obtener préstamos filtrados
        loans = self.controller.get_loans(status_filter, employee_filter)
        
        # Agregar préstamos al treeview
        for loan in loans:
            tags = ()
            if loan['status'] == 'overdue':
                tags = ('overdue',)
            elif loan['status'] == 'paid':
                tags = ('paid',)
            
            self.loans_tree.insert('', 'end', values=(
                loan['id'],
                loan['employee_name'],
                f"${float(loan['amount']):.2f}",
                loan['date_issued'],
                loan['due_date'],
                f"{float(loan['interest_rate']):.1f}%",
                self._translate_status(loan['status']),
                loan['username'] or ''
            ), tags=tags)
    
    def add_loan(self):
        """Agregar un nuevo préstamo"""
        try:
            employee = self.employee_entry.get()
            amount = float(self.amount_entry.get())
            date_issued = self.date_issued_entry.get_date().strftime('%Y-%m-%d')
            due_date = self.due_date_entry.get_date().strftime('%Y-%m-%d')
            interest_rate = float(self.interest_entry.get())
            notes = self.notes_entry.get()
            
            if not employee:
                messagebox.showerror("Error", "El nombre del empleado es obligatorio")
                return
            
            if amount <= 0:
                messagebox.showerror("Error", "El monto debe ser mayor a cero")
                return
            
            if interest_rate < 0:
                messagebox.showerror("Error", "La tasa de interés no puede ser negativa")
                return
            
            # Verificar que la fecha de vencimiento sea posterior a la fecha de préstamo
            if due_date <= date_issued:
                messagebox.showerror("Error", "La fecha de vencimiento debe ser posterior a la fecha de préstamo")
                return
            
            # Agregar préstamo
            self.controller.add_loan(employee, amount, date_issued, due_date, interest_rate, notes)
            
            messagebox.showinfo("Éxito", "Préstamo agregado correctamente")
            self.clear_form()
            self.load_loans()
            self.update_alerts()
            
        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar el préstamo: {str(e)}")
    
    def clear_form(self):
        """Limpiar el formulario"""
        self.employee_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)
        self.date_issued_entry.set_date(datetime.now())
        self.due_date_entry.set_date(datetime.now() + timedelta(days=30))
        self.interest_entry.delete(0, tk.END)
        self.interest_entry.insert(0, "0")
        self.notes_entry.delete(0, tk.END)
    
    def on_loan_double_click(self, event):
        """Manejar doble clic en un préstamo"""
        self.show_loan_details()
    
    def show_loan_details(self):
        """Mostrar detalles del préstamo seleccionado"""
        selection = self.loans_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un préstamo para ver detalles")
            return
        
        item = self.loans_tree.item(selection[0])
        loan_id = item['values'][0]
        
        # Obtener detalles del préstamo
        loan_summary = self.controller.get_loan_summary(loan_id)
        if not loan_summary:
            messagebox.showerror("Error", "No se pudo obtener la información del préstamo")
            return
        
        # Crear ventana de detalles
        details_window = tk.Toplevel(self.parent)
        details_window.title(f"Detalles del Préstamo - {loan_summary['loan']['employee_name']}")
        details_window.geometry("600x400")
        details_window.transient(self.parent)
        details_window.grab_set()
        
        # Marco principal
        main_frame = ttk.Frame(details_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Información del préstamo
        info_frame = ttk.LabelFrame(main_frame, text="Información del Préstamo", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = f"""
Empleado: {loan_summary['loan']['employee_name']}
Monto Original: ${float(loan_summary['loan']['amount']):.2f}
Tasa de Interés: {float(loan_summary['loan']['interest_rate']):.1f}%
Monto Total a Pagar: ${loan_summary['total_due']:.2f}
Fecha de Préstamo: {loan_summary['loan']['date_issued']}
Fecha de Vencimiento: {loan_summary['loan']['due_date']}
Estado: {self._translate_status(loan_summary['loan']['status'])}
Total Pagado: ${loan_summary['total_paid']:.2f}
Saldo Pendiente: ${loan_summary['balance']:.2f}
        """
        
        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(anchor=tk.W)
        
        # Historial de pagos
        payments_frame = ttk.LabelFrame(main_frame, text="Historial de Pagos", padding=10)
        payments_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview para pagos
        columns = ('date', 'amount', 'notes', 'user')
        payments_tree = ttk.Treeview(payments_frame, columns=columns, show='headings', height=8)
        
        payments_tree.heading('date', text='Fecha')
        payments_tree.heading('amount', text='Monto')
        payments_tree.heading('notes', text='Notas')
        payments_tree.heading('user', text='Usuario')
        
        payments_tree.column('date', width=100)
        payments_tree.column('amount', width=80)
        payments_tree.column('notes', width=200)
        payments_tree.column('user', width=100)
        
        # Agregar pagos al treeview
        for payment in loan_summary['payments']:
            payments_tree.insert('', 'end', values=(
                payment['payment_date'],
                f"${float(payment['amount']):.2f}",
                payment['notes'] or '',
                payment['username'] or ''
            ))
        
        payments_tree.pack(fill=tk.BOTH, expand=True)
    
    def show_payment_dialog(self):
        """Mostrar diálogo para registrar un pago"""
        selection = self.loans_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un préstamo para registrar pago")
            return
        
        item = self.loans_tree.item(selection[0])
        loan_id = item['values'][0]
        employee = item['values'][1]
        
        # Crear ventana de pago
        payment_window = tk.Toplevel(self.parent)
        payment_window.title(f"Registrar Pago - {employee}")
        payment_window.geometry("400x250")
        payment_window.transient(self.parent)
        payment_window.grab_set()
        
        # Marco principal
        main_frame = ttk.Frame(payment_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Fecha Pago:").grid(row=0, column=0, sticky=tk.W, pady=5)
        payment_date = DateEntry(main_frame, date_pattern='yyyy-mm-dd')
        payment_date.set_date(datetime.now())
        payment_date.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Monto:").grid(row=1, column=0, sticky=tk.W, pady=5)
        amount_entry = ttk.Entry(main_frame)
        amount_entry.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Notas:").grid(row=2, column=0, sticky=tk.W, pady=5)
        notes_entry = ttk.Entry(main_frame)
        notes_entry.grid(row=2, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        def register_payment():
            try:
                date = payment_date.get_date().strftime('%Y-%m-%d')
                amount = float(amount_entry.get())
                notes = notes_entry.get()
                
                if amount <= 0:
                    messagebox.showerror("Error", "El monto debe ser mayor a cero")
                    return
                
                self.controller.add_payment(loan_id, date, amount, notes)
                messagebox.showinfo("Éxito", "Pago registrado correctamente")
                payment_window.destroy()
                self.load_loans()
                self.update_alerts()
                
            except ValueError:
                messagebox.showerror("Error", "Por favor ingrese un monto válido")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo registrar el pago: {str(e)}")
        
        ttk.Button(button_frame, text="Registrar", command=register_payment).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=payment_window.destroy).pack(side=tk.LEFT, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
    
    def edit_loan(self):
        """Editar préstamo seleccionado"""
        selection = self.loans_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un préstamo para editar")
            return
        
        item = self.loans_tree.item(selection[0])
        loan_id = item['values'][0]
        
        # Obtener información del préstamo
        loan = self.controller.get_loan_by_id(loan_id)
        if not loan:
            messagebox.showerror("Error", "No se pudo obtener la información del préstamo")
            return
        
        # Crear ventana de edición
        edit_window = tk.Toplevel(self.parent)
        edit_window.title("Editar Préstamo")
        edit_window.geometry("400x300")
        edit_window.transient(self.parent)
        edit_window.grab_set()
        
        # Marco principal
        main_frame = ttk.Frame(edit_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Empleado:").grid(row=0, column=0, sticky=tk.W, pady=5)
        employee_entry = ttk.Entry(main_frame)
        employee_entry.insert(0, loan['employee_name'])
        employee_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Monto:").grid(row=1, column=0, sticky=tk.W, pady=5)
        amount_entry = ttk.Entry(main_frame)
        amount_entry.insert(0, str(loan['amount']))
        amount_entry.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Fecha Préstamo:").grid(row=2, column=0, sticky=tk.W, pady=5)
        date_issued = DateEntry(main_frame, date_pattern='yyyy-mm-dd')
        date_issued.set_date(datetime.strptime(loan['date_issued'], '%Y-%m-%d'))
        date_issued.grid(row=2, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Fecha Vencimiento:").grid(row=3, column=0, sticky=tk.W, pady=5)
        due_date = DateEntry(main_frame, date_pattern='yyyy-mm-dd')
        due_date.set_date(datetime.strptime(loan['due_date'], '%Y-%m-%d'))
        due_date.grid(row=3, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Tasa Interés (%):").grid(row=4, column=0, sticky=tk.W, pady=5)
        interest_entry = ttk.Entry(main_frame)
        interest_entry.insert(0, str(loan['interest_rate']))
        interest_entry.grid(row=4, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Notas:").grid(row=5, column=0, sticky=tk.W, pady=5)
        notes_entry = ttk.Entry(main_frame)
        notes_entry.insert(0, loan['notes'] or '')
        notes_entry.grid(row=5, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=15)
        
        def save_changes():
            try:
                employee = employee_entry.get()
                amount = float(amount_entry.get())
                date_issued_val = date_issued.get_date().strftime('%Y-%m-%d')
                due_date_val = due_date.get_date().strftime('%Y-%m-%d')
                interest_rate = float(interest_entry.get())
                notes = notes_entry.get()
                
                if not employee:
                    messagebox.showerror("Error", "El nombre del empleado es obligatorio")
                    return
                
                if amount <= 0:
                    messagebox.showerror("Error", "El monto debe ser mayor a cero")
                    return
                
                if interest_rate < 0:
                    messagebox.showerror("Error", "La tasa de interés no puede ser negativa")
                    return
                
                if due_date_val <= date_issued_val:
                    messagebox.showerror("Error", "La fecha de vencimiento debe ser posterior a la fecha de préstamo")
                    return
                
                self.controller.update_loan(loan_id, employee, amount, date_issued_val, due_date_val, interest_rate, notes)
                messagebox.showinfo("Éxito", "Préstamo actualizado correctamente")
                edit_window.destroy()
                self.load_loans()
                self.update_alerts()
                
            except ValueError:
                messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el préstamo: {str(e)}")
        
        ttk.Button(button_frame, text="Guardar", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=edit_window.destroy).pack(side=tk.LEFT, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
    
    def delete_loan(self):
        """Eliminar préstamo seleccionado"""
        selection = self.loans_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un préstamo para eliminar")
            return
        
        item = self.loans_tree.item(selection[0])
        loan_id = item['values'][0]
        employee = item['values'][1]
        
        if messagebox.askyesno("Confirmar", f"¿Está seguro de eliminar el préstamo de '{employee}'? Se eliminarán todos los pagos asociados."):
            try:
                self.controller.delete_loan(loan_id)
                messagebox.showinfo("Éxito", "Préstamo eliminado correctamente")
                self.load_loans()
                self.update_alerts()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el préstamo: {str(e)}")
    
    def update_alerts(self):
        """Actualizar las alertas de vencimiento"""
        overdue_loans = self.controller.get_overdue_loans()
        
        self.alerts_text.config(state=tk.NORMAL)
        self.alerts_text.delete(1.0, tk.END)
        
        if not overdue_loans:
            self.alerts_text.insert(tk.END, "No hay préstamos vencidos")
        else:
            self.alerts_text.insert(tk.END, "PRÉSTAMOS VENCIDOS:\n\n")
            for loan in overdue_loans:
                days_overdue = (datetime.now().date() - datetime.strptime(loan['due_date'], '%Y-%m-%d').date()).days
                self.alerts_text.insert(tk.END, 
                    f"{loan['employee_name']}: ${loan['amount']} - {days_overdue} días de retraso\n")
        
        self.alerts_text.config(state=tk.DISABLED)
    
    def show_report(self):
        """Mostrar diálogo de reportes"""
        # Crear ventana de reportes
        report_window = tk.Toplevel(self.parent)
        report_window.title("Reportes de Préstamos")
        report_window.geometry("500x400")
        report_window.transient(self.parent)
        
        # Marco principal
        main_frame = ttk.Frame(report_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Fecha Inicio:").grid(row=0, column=0, sticky=tk.W, pady=5)
        start_date = DateEntry(main_frame, date_pattern='yyyy-mm-dd')
        start_date.set_date(datetime.now() - timedelta(days=30))
        start_date.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Fecha Fin:").grid(row=1, column=0, sticky=tk.W, pady=5)
        end_date = DateEntry(main_frame, date_pattern='yyyy-mm-dd')
        end_date.set_date(datetime.now())
        end_date.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Estado:").grid(row=2, column=0, sticky=tk.W, pady=5)
        status_filter = ttk.Combobox(main_frame, state="readonly", width=18)
        status_filter['values'] = ('', 'active', 'paid', 'overdue')
        status_filter.set('')
        status_filter.grid(row=2, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        # Treeview para reporte
        columns = ('employee', 'amount', 'issued', 'due', 'status', 'paid', 'balance')
        report_tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=15)
        
        report_tree.heading('employee', text='Empleado')
        report_tree.heading('amount', text='Monto')
        report_tree.heading('issued', text='Fecha Préstamo')
        report_tree.heading('due', text='Fecha Vencimiento')
        report_tree.heading('status', text='Estado')
        report_tree.heading('paid', text='Pagado')
        report_tree.heading('balance', text='Saldo')
        
        report_tree.column('employee', width=100)
        report_tree.column('amount', width=80)
        report_tree.column('issued', width=90)
        report_tree.column('due', width=90)
        report_tree.column('status', width=80)
        report_tree.column('paid', width=80)
        report_tree.column('balance', width=80)
        
        report_tree.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW, pady=10)
        
        def generate_report():
            start = start_date.get_date().strftime('%Y-%m-%d')
            end = end_date.get_date().strftime('%Y-%m-%d')
            status = status_filter.get() or None
            
            # Limpiar treeview
            for item in report_tree.get_children():
                report_tree.delete(item)
            
            # Generar reporte
            report_data = self.controller.get_loans_report(start, end, status)
            
            # Agregar datos al treeview
            for loan in report_data:
                tags = ()
                if loan['status'] == 'overdue':
                    tags = ('overdue',)
                elif loan['status'] == 'paid':
                    tags = ('paid',)
                
                report_tree.insert('', 'end', values=(
                    loan['employee_name'],
                    f"${float(loan['amount']):.2f}",
                    loan['date_issued'],
                    loan['due_date'],
                    self._translate_status(loan['status']),
                    f"${float(loan['total_paid']):.2f}",
                    f"${float(loan['balance']):.2f}"
                ), tags=tags)
            
            # Configurar colores
            report_tree.tag_configure('overdue', background='#ffcccc')
            report_tree.tag_configure('paid', background='#ccffcc')
        
        ttk.Button(main_frame, text="Generar Reporte", command=generate_report).grid(row=4, column=0, columnspan=2, pady=10)
        
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Generar reporte inicial
        generate_report()