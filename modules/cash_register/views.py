"""
Vista para el módulo de caja
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta

from modules.cash_register.controller import CashRegisterController

class CashRegisterView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth_manager = auth_manager
        self.controller = CashRegisterController(database, auth_manager)
        
        self.setup_ui()
        self.load_transactions()
    
    def setup_ui(self):
        """Configurar la interfaz de usuario del módulo de caja"""
        # Frame principal con paneles divididos
        main_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Panel izquierdo para formulario y filtros
        left_frame = ttk.Frame(main_paned, padding=10)
        main_paned.add(left_frame, weight=1)
        
        # Panel derecho para la lista de transacciones
        right_frame = ttk.Frame(main_paned, padding=10)
        main_paned.add(right_frame, weight=2)
        
        # Formulario para nueva transacción
        form_frame = ttk.LabelFrame(left_frame, text="Nueva Transacción", padding=10)
        form_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(form_frame, text="Fecha:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.date_entry = DateEntry(form_frame, date_pattern='yyyy-mm-dd')
        self.date_entry.set_date(datetime.now())
        self.date_entry.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Tipo:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.type_var = tk.StringVar(value="income")
        type_combo = ttk.Combobox(form_frame, textvariable=self.type_var, state="readonly", width=18)
        type_combo['values'] = ('income', 'expense')
        type_combo.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Descripción:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.desc_entry = ttk.Entry(form_frame)
        self.desc_entry.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Monto:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.amount_entry = ttk.Entry(form_frame)
        self.amount_entry.grid(row=3, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Método Pago:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.payment_var = tk.StringVar(value="cash")
        payment_combo = ttk.Combobox(form_frame, textvariable=self.payment_var, state="readonly", width=18)
        payment_combo['values'] = ('cash', 'transfer')
        payment_combo.grid(row=4, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Categoría:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.category_entry = ttk.Entry(form_frame)
        self.category_entry.grid(row=5, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Agregar", command=self.add_transaction).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Limpiar", command=self.clear_form).pack(side=tk.LEFT, padx=5)
        
        # Filtros
        filter_frame = ttk.LabelFrame(left_frame, text="Filtros", padding=10)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Desde:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.start_date = DateEntry(filter_frame, date_pattern='yyyy-mm-dd')
        self.start_date.set_date(datetime.now() - timedelta(days=30))
        self.start_date.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(filter_frame, text="Hasta:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.end_date = DateEntry(filter_frame, date_pattern='yyyy-mm-dd')
        self.end_date.set_date(datetime.now())
        self.end_date.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(filter_frame, text="Tipo:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.filter_type = ttk.Combobox(filter_frame, state="readonly", width=18)
        self.filter_type['values'] = ('', 'income', 'expense')
        self.filter_type.set('')
        self.filter_type.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(filter_frame, text="Método:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.filter_payment = ttk.Combobox(filter_frame, state="readonly", width=18)
        self.filter_payment['values'] = ('', 'cash', 'transfer')
        self.filter_payment.set('')
        self.filter_payment.grid(row=3, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Button(filter_frame, text="Aplicar Filtros", command=self.apply_filters).grid(row=4, column=0, columnspan=2, pady=10)
        
        # Resumen
        summary_frame = ttk.LabelFrame(left_frame, text="Resumen", padding=10)
        summary_frame.pack(fill=tk.X)
        
        self.income_var = tk.StringVar(value="Ingresos: $0.00")
        self.expense_var = tk.StringVar(value="Egresos: $0.00")
        self.balance_var = tk.StringVar(value="Balance: $0.00")
        
        ttk.Label(summary_frame, textvariable=self.income_var).pack(anchor=tk.W)
        ttk.Label(summary_frame, textvariable=self.expense_var).pack(anchor=tk.W)
        ttk.Label(summary_frame, textvariable=self.balance_var).pack(anchor=tk.W)
        
        # Lista de transacciones
        list_frame = ttk.Frame(right_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview para mostrar transacciones
        columns = ('id', 'date', 'type', 'description', 'amount', 'payment', 'category', 'user')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        # Definir columnas
        self.tree.heading('id', text='ID')
        self.tree.heading('date', text='Fecha')
        self.tree.heading('type', text='Tipo')
        self.tree.heading('description', text='Descripción')
        self.tree.heading('amount', text='Monto')
        self.tree.heading('payment', text='Método')
        self.tree.heading('category', text='Categoría')
        self.tree.heading('user', text='Usuario')
        
        # Ajustar anchos de columnas
        self.tree.column('id', width=40)
        self.tree.column('date', width=80)
        self.tree.column('type', width=70)
        self.tree.column('description', width=150)
        self.tree.column('amount', width=80)
        self.tree.column('payment', width=70)
        self.tree.column('category', width=100)
        self.tree.column('user', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botones de acción para transacciones
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=(5, 0))
        
        if self.auth_manager.has_permission('admin'):
            ttk.Button(action_frame, text="Editar", command=self.edit_transaction).pack(side=tk.LEFT, padx=5)
            ttk.Button(action_frame, text="Eliminar", command=self.delete_transaction).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(action_frame, text="Actualizar", command=self.load_transactions).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Reporte", command=self.show_report).pack(side=tk.RIGHT, padx=5)
        
        # Configurar pesos de grid
        form_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(1, weight=1)
        
        # Crear notebook para dividir entre tabla y gráficos
        tab_control = ttk.Notebook(right_frame)
        tab_control.pack(fill=tk.BOTH, expand=True)

        # Pestaña de tabla
        table_frame = ttk.Frame(tab_control)
        tab_control.add(table_frame, text="Movimientos")

        # Pestaña de gráficos
        chart_frame = ttk.Frame(tab_control)
        tab_control.add(chart_frame, text="Gráficos")

        # Mover el treeview a la pestaña de tabla
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        # ... (configuración del treeview)

        # Agregar controles para gráficos en chart_frame
        ttk.Button(chart_frame, text="Generar Gráfico Mensual", 
                command=self.show_monthly_chart).pack(pady=10)
        
        # Bind eventos
        self.tree.bind('<Double-1>', self.on_item_double_click)
    
    def load_transactions(self):
        """Cargar transacciones en el treeview"""
        # Limpiar treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Obtener transacciones
        transactions = self.controller.get_transactions()
        
        # Calcular totales
        total_income = 0
        total_expense = 0
        
        # Agregar transacciones al treeview
        for trans in transactions:
            amount = float(trans['amount'])
            if trans['type'] == 'income':
                total_income += amount
            else:
                total_expense += amount
            
            self.tree.insert('', 'end', values=(
                trans['id'],
                trans['date'],
                trans['type'],
                trans['description'],
                f"${amount:.2f}",
                trans['payment_method'],
                trans['category'] or '',
                trans['username'] or ''
            ))
        
        # Actualizar resumen
        self.income_var.set(f"Ingresos: ${total_income:.2f}")
        self.expense_var.set(f"Egresos: ${total_expense:.2f}")
        self.balance_var.set(f"Balance: ${(total_income - total_expense):.2f}")
    
    def apply_filters(self):
        """Aplicar filtros a las transacciones"""
        start_date = self.start_date.get_date().strftime('%Y-%m-%d')
        end_date = self.end_date.get_date().strftime('%Y-%m-%d')
        type_filter = self.filter_type.get() or None
        payment_filter = self.filter_payment.get() or None
        
        # Limpiar treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Obtener transacciones filtradas
        transactions = self.controller.get_transactions(start_date, end_date, type_filter, payment_filter)
        
        # Calcular totales
        total_income = 0
        total_expense = 0
        
        # Agregar transacciones al treeview
        for trans in transactions:
            amount = float(trans['amount'])
            if trans['type'] == 'income':
                total_income += amount
            else:
                total_expense += amount
            
            self.tree.insert('', 'end', values=(
                trans['id'],
                trans['date'],
                trans['type'],
                trans['description'],
                f"${amount:.2f}",
                trans['payment_method'],
                trans['category'] or '',
                trans['username'] or ''
            ))
        
        # Actualizar resumen
        self.income_var.set(f"Ingresos: ${total_income:.2f}")
        self.expense_var.set(f"Egresos: ${total_expense:.2f}")
        self.balance_var.set(f"Balance: ${(total_income - total_expense):.2f}")
    
    def add_transaction(self):
        """Agregar una nueva transacción"""
        try:
            date = self.date_entry.get_date().strftime('%Y-%m-%d')
            type_val = self.type_var.get()
            description = self.desc_entry.get()
            amount = float(self.amount_entry.get())
            payment_method = self.payment_var.get()
            category = self.category_entry.get()
            
            if not description:
                messagebox.showerror("Error", "La descripción es obligatoria")
                return
            
            if amount <= 0:
                messagebox.showerror("Error", "El monto debe ser mayor a cero")
                return
            
            # Agregar transacción
            self.controller.add_transaction(date, type_val, description, amount, payment_method, category)
            
            messagebox.showinfo("Éxito", "Transacción agregada correctamente")
            self.clear_form()
            self.load_transactions()
            
        except ValueError:
            messagebox.showerror("Error", "El monto debe ser un número válido")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar la transacción: {str(e)}")
    
    def clear_form(self):
        """Limpiar el formulario"""
        self.date_entry.set_date(datetime.now())
        self.type_var.set('income')
        self.desc_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)
        self.payment_var.set('cash')
        self.category_entry.delete(0, tk.END)
    
    def on_item_double_click(self, event):
        """Manejar doble clic en un item del treeview"""
        if self.auth_manager.has_permission('admin'):
            self.edit_transaction()
    
    def edit_transaction(self):
        """Editar transacción seleccionada"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione una transacción para editar")
            return
        
        item = self.tree.item(selection[0])
        trans_id = item['values'][0]
        
        # Aquí se implementaría un diálogo de edición
        # Por ahora solo mostramos un mensaje
        messagebox.showinfo("Editar", f"Editando transacción ID: {trans_id}")
    
    def delete_transaction(self):
        """Eliminar transacción seleccionada"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione una transacción para eliminar")
            return
        
        item = self.tree.item(selection[0])
        trans_id = item['values'][0]
        desc = item['values'][3]
        
        if messagebox.askyesno("Confirmar", f"¿Está seguro de eliminar la transacción '{desc}'?"):
            try:
                self.controller.delete_transaction(trans_id)
                messagebox.showinfo("Éxito", "Transacción eliminada correctamente")
                self.load_transactions()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar la transacción: {str(e)}")
    
    def show_report(self):
        """Mostrar diálogo de reportes"""
        # Implementar diálogo de reportes
        messagebox.showinfo("Reportes", "Funcionalidad de reportes en desarrollo")