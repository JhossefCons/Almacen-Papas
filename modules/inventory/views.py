"""
Vista para el módulo de inventario de papa
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta

from modules.inventory.controller import InventoryController

class InventoryView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth_manager = auth_manager
        self.controller = InventoryController(database, auth_manager)
        
        self.setup_ui()
        self.load_inventory()
        self.update_stock_summary()
    
    def setup_ui(self):
        """Configurar la interfaz de usuario del módulo de inventario"""
        # Frame principal con paneles divididos
        main_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Panel izquierdo para formulario y resumen
        left_frame = ttk.Frame(main_paned, padding=10)
        main_paned.add(left_frame, weight=1)
        
        # Panel derecho para la lista de movimientos
        right_frame = ttk.Frame(main_paned, padding=10)
        main_paned.add(right_frame, weight=2)
        
        # Formulario para nuevo movimiento
        form_frame = ttk.LabelFrame(left_frame, text="Nuevo Movimiento", padding=10)
        form_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(form_frame, text="Fecha:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.date_entry = DateEntry(form_frame, date_pattern='yyyy-mm-dd')
        self.date_entry.set_date(datetime.now())
        self.date_entry.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Tipo Papa:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.potato_type = ttk.Combobox(form_frame, state="readonly", width=18)
        self.potato_type['values'] = self.controller.potato_types
        self.potato_type.set('parda')
        self.potato_type.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        self.potato_type.bind('<<ComboboxSelected>>', self.update_quality_options)
        
        ttk.Label(form_frame, text="Calidad:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.quality = ttk.Combobox(form_frame, state="readonly", width=18)
        self.update_quality_options()
        self.quality.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Operación:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.operation = ttk.Combobox(form_frame, state="readonly", width=18)
        self.operation['values'] = ('entry', 'exit')
        self.operation.set('entry')
        self.operation.grid(row=3, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Cantidad (costales):").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.quantity_entry = ttk.Entry(form_frame)
        self.quantity_entry.grid(row=4, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Precio Unitario:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.unit_price_entry = ttk.Entry(form_frame)
        self.unit_price_entry.grid(row=5, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Proveedor/Cliente:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.supplier_entry = ttk.Entry(form_frame)
        self.supplier_entry.grid(row=6, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(form_frame, text="Notas:").grid(row=7, column=0, sticky=tk.W, pady=2)
        self.notes_entry = ttk.Entry(form_frame)
        self.notes_entry.grid(row=7, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=8, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Agregar", command=self.add_inventory_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Limpiar", command=self.clear_form).pack(side=tk.LEFT, padx=5)
        
        # Resumen de stock
        stock_frame = ttk.LabelFrame(left_frame, text="Stock Actual", padding=10)
        stock_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Treeview para stock actual
        columns = ('type', 'quality', 'stock')
        self.stock_tree = ttk.Treeview(stock_frame, columns=columns, show='headings', height=8)
        
        self.stock_tree.heading('type', text='Tipo')
        self.stock_tree.heading('quality', text='Calidad')
        self.stock_tree.heading('stock', text='Stock (costales)')
        
        self.stock_tree.column('type', width=80)
        self.stock_tree.column('quality', width=80)
        self.stock_tree.column('stock', width=100)
        
        self.stock_tree.pack(fill=tk.BOTH, expand=True)
        
        # Alertas de stock
        alerts_frame = ttk.LabelFrame(left_frame, text="Alertas de Stock", padding=10)
        alerts_frame.pack(fill=tk.X)
        
        self.alerts_text = tk.Text(alerts_frame, height=4, width=30)
        self.alerts_text.pack(fill=tk.BOTH, expand=True)
        self.alerts_text.config(state=tk.DISABLED)
        
        ttk.Button(alerts_frame, text="Actualizar Alertas", command=self.update_alerts).pack(pady=5)
        
        # Filtros para movimientos
        filter_frame = ttk.LabelFrame(right_frame, text="Filtros", padding=10)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Desde:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.start_date = DateEntry(filter_frame, date_pattern='yyyy-mm-dd')
        self.start_date.set_date(datetime.now() - timedelta(days=30))
        self.start_date.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(filter_frame, text="Hasta:").grid(row=0, column=2, sticky=tk.W, pady=2, padx=(10, 0))
        self.end_date = DateEntry(filter_frame, date_pattern='yyyy-mm-dd')
        self.end_date.set_date(datetime.now())
        self.end_date.grid(row=0, column=3, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(filter_frame, text="Tipo:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.type_filter = ttk.Combobox(filter_frame, state="readonly", width=15)
        self.type_filter['values'] = ('',) + tuple(self.controller.potato_types)
        self.type_filter.set('')
        self.type_filter.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(filter_frame, text="Calidad:").grid(row=1, column=2, sticky=tk.W, pady=2, padx=(10, 0))
        self.quality_filter = ttk.Combobox(filter_frame, state="readonly", width=15)
        self.quality_filter['values'] = ('',) + tuple(self.controller.qualities)
        self.quality_filter.set('')
        self.quality_filter.grid(row=1, column=3, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Label(filter_frame, text="Operación:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.operation_filter = ttk.Combobox(filter_frame, state="readonly", width=15)
        self.operation_filter['values'] = ('', 'entry', 'exit')
        self.operation_filter.set('')
        self.operation_filter.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        
        ttk.Button(filter_frame, text="Aplicar Filtros", command=self.apply_filters).grid(row=2, column=2, columnspan=2, pady=10, padx=(10, 0))
        
        # Lista de movimientos
        list_frame = ttk.Frame(right_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview para movimientos
        columns = ('id', 'date', 'type', 'quality', 'operation', 'quantity', 'unit_price', 'total', 'supplier', 'user')
        self.inventory_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        self.inventory_tree.heading('id', text='ID')
        self.inventory_tree.heading('date', text='Fecha')
        self.inventory_tree.heading('type', text='Tipo')
        self.inventory_tree.heading('quality', text='Calidad')
        self.inventory_tree.heading('operation', text='Operación')
        self.inventory_tree.heading('quantity', text='Cantidad')
        self.inventory_tree.heading('unit_price', text='Precio Unit.')
        self.inventory_tree.heading('total', text='Total')
        self.inventory_tree.heading('supplier', text='Proveedor/Cliente')
        self.inventory_tree.heading('user', text='Usuario')
        
        self.inventory_tree.column('id', width=40)
        self.inventory_tree.column('date', width=80)
        self.inventory_tree.column('type', width=70)
        self.inventory_tree.column('quality', width=70)
        self.inventory_tree.column('operation', width=70)
        self.inventory_tree.column('quantity', width=70)
        self.inventory_tree.column('unit_price', width=80)
        self.inventory_tree.column('total', width=80)
        self.inventory_tree.column('supplier', width=120)
        self.inventory_tree.column('user', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.inventory_tree.yview)
        self.inventory_tree.configure(yscrollcommand=scrollbar.set)
        
        self.inventory_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botones de acción
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=(5, 0))
        
        if self.auth_manager.has_permission('admin'):
            ttk.Button(action_frame, text="Editar", command=self.edit_record).pack(side=tk.LEFT, padx=5)
            ttk.Button(action_frame, text="Eliminar", command=self.delete_record).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(action_frame, text="Actualizar", command=self.load_inventory).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Reporte", command=self.show_report).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Análisis Costos", command=self.show_cost_analysis).pack(side=tk.RIGHT, padx=5)
        
        # Configurar pesos de grid
        form_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(3, weight=1)
        
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
        self.inventory_tree.bind('<Double-1>', self.on_item_double_click)
        
        # Actualizar alertas
        self.update_alerts()
    
    def update_quality_options(self, event=None):
        """Actualizar las opciones de calidad según el tipo seleccionado"""
        selected_type = self.potato_type.get()
        if selected_type in self.controller.allowed_combinations:
            self.quality['values'] = self.controller.allowed_combinations[selected_type]
            self.quality.set(self.controller.allowed_combinations[selected_type][0])
    
    def load_inventory(self):
        """Cargar movimientos de inventario en el treeview"""
        # Limpiar treeview
        for item in self.inventory_tree.get_children():
            self.inventory_tree.delete(item)
        
        # Obtener movimientos
        records = self.controller.get_inventory_records()
        
        # Agregar movimientos al treeview
        for record in records:
            # Determinar color según operación
            tags = ()
            if record['operation'] == 'entry':
                tags = ('entry',)
            else:
                tags = ('exit',)
            
            self.inventory_tree.insert('', 'end', values=(
                record['id'],
                record['date'],
                record['potato_type'],
                record['quality'],
                'Entrada' if record['operation'] == 'entry' else 'Salida',
                f"{record['quantity']} costales",
                f"${float(record['unit_price']):.2f}",
                f"${float(record['total_value']):.2f}",
                record['supplier_customer'] or '',
                record['username'] or ''
            ), tags=tags)
        
        # Configurar colores para diferentes operaciones
        self.inventory_tree.tag_configure('entry', background='#ccffcc')  # Verde claro para entradas
        self.inventory_tree.tag_configure('exit', background='#ffcccc')   # Rojo claro para salidas
        
        # Actualizar resumen de stock
        self.update_stock_summary()
    
    def update_stock_summary(self):
        """Actualizar el resumen de stock actual"""
        # Limpiar treeview de stock
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        
        # Obtener stock actual
        current_stock = self.controller.get_current_stock()
        
        # Agregar stock al treeview
        for item in current_stock:
            self.stock_tree.insert('', 'end', values=(
                item['potato_type'],
                item['quality'],
                f"{item['current_stock']} costales"
            ))
    
    def apply_filters(self):
        """Aplicar filtros a los movimientos de inventario"""
        start_date = self.start_date.get_date().strftime('%Y-%m-%d')
        end_date = self.end_date.get_date().strftime('%Y-%m-%d')
        type_filter = self.type_filter.get() or None
        quality_filter = self.quality_filter.get() or None
        operation_filter = self.operation_filter.get() or None
        
        # Limpiar treeview
        for item in self.inventory_tree.get_children():
            self.inventory_tree.delete(item)
        
        # Obtener movimientos filtrados
        records = self.controller.get_inventory_records(
            start_date, end_date, type_filter, quality_filter, operation_filter
        )
        
        # Agregar movimientos al treeview
        for record in records:
            tags = ()
            if record['operation'] == 'entry':
                tags = ('entry',)
            else:
                tags = ('exit',)
            
            self.inventory_tree.insert('', 'end', values=(
                record['id'],
                record['date'],
                record['potato_type'],
                record['quality'],
                'Entrada' if record['operation'] == 'entry' else 'Salida',
                f"{record['quantity']} costales",
                f"${float(record['unit_price']):.2f}",
                f"${float(record['total_value']):.2f}",
                record['supplier_customer'] or '',
                record['username'] or ''
            ), tags=tags)
    
    def add_inventory_record(self):
        """Agregar un nuevo registro de inventario"""
        try:
            date = self.date_entry.get_date().strftime('%Y-%m-%d')
            potato_type = self.potato_type.get()
            quality = self.quality.get()
            operation = self.operation.get()
            quantity = int(self.quantity_entry.get())
            unit_price = float(self.unit_price_entry.get())
            supplier = self.supplier_entry.get()
            notes = self.notes_entry.get()
            
            if quantity <= 0:
                messagebox.showerror("Error", "La cantidad debe ser mayor a cero")
                return
            
            if unit_price <= 0:
                messagebox.showerror("Error", "El precio unitario debe ser mayor a cero")
                return
            
            # Para salidas, verificar que haya stock suficiente
            if operation == 'exit':
                current_stock = self.controller.get_current_stock(potato_type, quality)
                available = 0
                for item in current_stock:
                    if item['potato_type'] == potato_type and item['quality'] == quality:
                        available = item['current_stock']
                        break
                
                if quantity > available:
                    messagebox.showerror("Error", 
                        f"Stock insuficiente. Disponible: {available} costales, Solicitado: {quantity} costales")
                    return
            
            # Agregar registro
            self.controller.add_inventory_record(
                date, potato_type, quality, operation, quantity, unit_price, supplier, notes
            )
            
            messagebox.showinfo("Éxito", "Registro agregado correctamente")
            self.clear_form()
            self.load_inventory()
            self.update_alerts()
            
        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar el registro: {str(e)}")
    
    def clear_form(self):
        """Limpiar el formulario"""
        self.date_entry.set_date(datetime.now())
        self.potato_type.set('parda')
        self.update_quality_options()
        self.operation.set('entry')
        self.quantity_entry.delete(0, tk.END)
        self.unit_price_entry.delete(0, tk.END)
        self.supplier_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)
    
    def on_item_double_click(self, event):
        """Manejar doble clic en un registro"""
        if self.auth_manager.has_permission('admin'):
            self.edit_record()
    
    def edit_record(self):
        """Editar registro seleccionado"""
        selection = self.inventory_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un registro para editar")
            return
        
        item = self.inventory_tree.item(selection[0])
        record_id = item['values'][0]
        
        # Obtener información del registro
        # (Implementación similar a la del módulo de préstamos)
        messagebox.showinfo("Editar", f"Editando registro ID: {record_id}")
        # La implementación completa sería similar a edit_loan() en el módulo de préstamos
    
    def delete_record(self):
        """Eliminar registro seleccionado"""
        selection = self.inventory_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione un registro para eliminar")
            return
        
        item = self.inventory_tree.item(selection[0])
        record_id = item['values'][0]
        record_type = item['values'][2]
        record_quality = item['values'][3]
        
        if messagebox.askyesno("Confirmar", 
            f"¿Está seguro de eliminar el registro de {record_type} {record_quality}?"):
            try:
                self.controller.delete_inventory_record(record_id)
                messagebox.showinfo("Éxito", "Registro eliminado correctamente")
                self.load_inventory()
                self.update_alerts()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el registro: {str(e)}")
    
    def update_alerts(self):
        """Actualizar las alertas de stock bajo"""
        stock_alerts = self.controller.get_stock_alerts()
        
        self.alerts_text.config(state=tk.NORMAL)
        self.alerts_text.delete(1.0, tk.END)
        
        if not stock_alerts:
            self.alerts_text.insert(tk.END, "No hay alertas de stock bajo")
        else:
            self.alerts_text.insert(tk.END, "ALERTAS DE STOCK BAJO:\n\n")
            for alert in stock_alerts:
                self.alerts_text.insert(tk.END, 
                    f"{alert['potato_type']} {alert['quality']}: {alert['current_stock']} costales\n")
        
        self.alerts_text.config(state=tk.DISABLED)
    
    def show_report(self):
        """Mostrar reporte de inventario"""
        # Crear ventana de reporte
        report_window = tk.Toplevel(self.parent)
        report_window.title("Reporte de Inventario")
        report_window.geometry("800x500")
        report_window.transient(self.parent)
        
        # Marco principal
        main_frame = ttk.Frame(report_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Fecha Inicio:").grid(row=0, column=0, sticky=tk.W, pady=5)
        start_date = DateEntry(main_frame, date_pattern='yyyy-mm-dd')
        start_date.set_date(datetime.now() - timedelta(days=30))
        start_date.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Fecha Fin:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(10, 0))
        end_date = DateEntry(main_frame, date_pattern='yyyy-mm-dd')
        end_date.set_date(datetime.now())
        end_date.grid(row=0, column=3, sticky=tk.EW, pady=5, padx=(5, 0))
        
        # Treeview para reporte
        columns = ('type', 'quality', 'entries', 'exits', 'stock', 'entry_value', 'exit_value', 'avg_cost')
        report_tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=20)
        
        report_tree.heading('type', text='Tipo')
        report_tree.heading('quality', text='Calidad')
        report_tree.heading('entries', text='Entradas')
        report_tree.heading('exits', text='Salidas')
        report_tree.heading('stock', text='Stock Actual')
        report_tree.heading('entry_value', text='Valor Entradas')
        report_tree.heading('exit_value', text='Valor Salidas')
        report_tree.heading('avg_cost', text='Costo Promedio')
        
        report_tree.column('type', width=80)
        report_tree.column('quality', width=80)
        report_tree.column('entries', width=70)
        report_tree.column('exits', width=70)
        report_tree.column('stock', width=90)
        report_tree.column('entry_value', width=100)
        report_tree.column('exit_value', width=100)
        report_tree.column('avg_cost', width=100)
        
        report_tree.grid(row=1, column=0, columnspan=4, sticky=tk.NSEW, pady=10)
        
        def generate_report():
            start = start_date.get_date().strftime('%Y-%m-%d')
            end = end_date.get_date().strftime('%Y-%m-%d')
            
            # Limpiar treeview
            for item in report_tree.get_children():
                report_tree.delete(item)
            
            # Generar reporte
            report_data = self.controller.get_inventory_report(start, end)
            
            # Agregar datos al treeview
            for item in report_data:
                report_tree.insert('', 'end', values=(
                    item['potato_type'],
                    item['quality'],
                    f"{item['total_entries']} costales",
                    f"{item['total_exits']} costales",
                    f"{item['current_stock']} costales",
                    f"${float(item['total_entry_value']):.2f}",
                    f"${float(item['total_exit_value']):.2f}",
                    f"${float(item['avg_cost_price'] or 0):.2f}" if item['avg_cost_price'] else "N/A"
                ))
        
        ttk.Button(main_frame, text="Generar Reporte", command=generate_report).grid(
            row=2, column=0, columnspan=4, pady=10)
        
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(3, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Generar reporte inicial
        generate_report()
    
    def show_cost_analysis(self):
        """Mostrar análisis de costos"""
        # Crear ventana de análisis
        analysis_window = tk.Toplevel(self.parent)
        analysis_window.title("Análisis de Costos")
        analysis_window.geometry("600x400")
        analysis_window.transient(self.parent)
        
        # Marco principal
        main_frame = ttk.Frame(analysis_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Tipo Papa:").grid(row=0, column=0, sticky=tk.W, pady=5)
        type_combo = ttk.Combobox(main_frame, state="readonly", width=15)
        type_combo['values'] = ('',) + tuple(self.controller.potato_types)
        type_combo.set('')
        type_combo.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(5, 0))
        
        ttk.Label(main_frame, text="Calidad:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(10, 0))
        quality_combo = ttk.Combobox(main_frame, state="readonly", width=15)
        quality_combo['values'] = ('',) + tuple(self.controller.qualities)
        quality_combo.set('')
        quality_combo.grid(row=0, column=3, sticky=tk.EW, pady=5, padx=(5, 0))
        
        # Treeview para análisis
        columns = ('type', 'quality', 'avg_price', 'min_price', 'max_price', 'transactions')
        analysis_tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=15)
        
        analysis_tree.heading('type', text='Tipo')
        analysis_tree.heading('quality', text='Calidad')
        analysis_tree.heading('avg_price', text='Precio Promedio')
        analysis_tree.heading('min_price', text='Precio Mínimo')
        analysis_tree.heading('max_price', text='Precio Máximo')
        analysis_tree.heading('transactions', text='Transacciones')
        
        analysis_tree.column('type', width=80)
        analysis_tree.column('quality', width=80)
        analysis_tree.column('avg_price', width=100)
        analysis_tree.column('min_price', width=100)
        analysis_tree.column('max_price', width=100)
        analysis_tree.column('transactions', width=90)
        
        analysis_tree.grid(row=1, column=0, columnspan=4, sticky=tk.NSEW, pady=10)
        
        def generate_analysis():
            potato_type = type_combo.get() or None
            quality = quality_combo.get() or None
            
            # Limpiar treeview
            for item in analysis_tree.get_children():
                analysis_tree.delete(item)
            
            # Generar análisis
            analysis_data = self.controller.get_cost_analysis(potato_type, quality)
            
            # Agregar datos al treeview
            for item in analysis_data:
                analysis_tree.insert('', 'end', values=(
                    item['potato_type'],
                    item['quality'],
                    f"${float(item['avg_price'] or 0):.2f}",
                    f"${float(item['min_price'] or 0):.2f}",
                    f"${float(item['max_price'] or 0):.2f}",
                    item['transactions']
                ))
        
        ttk.Button(main_frame, text="Generar Análisis", command=generate_analysis).grid(
            row=2, column=0, columnspan=4, pady=10)
        
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(3, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Generar análisis inicial
        generate_analysis()