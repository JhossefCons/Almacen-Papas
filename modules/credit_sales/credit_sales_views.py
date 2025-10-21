# modules/credit_sales/credit_sales_views.py
"""
Vista para Cuentas por Cobrar (Ventas a Crédito)
- Diseño de panel dividido (similar a 'Ventas') sin ventanas emergentes.
- Panel izquierdo: Crear ventas (con multi-item) y Registrar pagos.
- Panel derecho: Historial filtrable de cuentas por cobrar.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime, timedelta
from modules.credit_sales.credit_sales_controller import CreditSalesController

PAY_TO_CODE = {"Efectivo": "cash", "Transferencia": "transfer"}
CODE_TO_PAY = {"cash": "Efectivo", "transfer": "Transferencia"}

class CreditSalesView:
    def __init__(self, parent, database, auth_manager, cash_controller):
        self.parent = parent
        self.db = database
        self.auth = auth_manager
        self.controller = CreditSalesController(database, auth_manager, cash_controller)
        
        self.products_data = {}  # Para los combobox de productos
        self.items_list = []     # Lista temporal de items para la nueva venta
        self.selected_sale_id = None # ID de la venta seleccionada en el árbol
        self.selected_sale_summary = {} # Resumen de la venta seleccionada

        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=8)
        container.pack(fill=tk.BOTH, expand=True)

        # --- Panel Izquierdo (Formularios) ---
        left_panel = ttk.Frame(container, width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False) # Evita que el panel se encoja

        # --- Panel Derecho (Historial) ---
        right_panel = ttk.Frame(container)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Contenido Panel Izquierdo ---
        self._build_left_panel_new_sale(left_panel)
        self._build_left_panel_payment(left_panel)
        
        # --- Contenido Panel Derecho ---
        self._build_right_panel_history(right_panel)

    def _build_left_panel_new_sale(self, parent):
        """Construye el formulario de 'Nueva Venta a Crédito' en el panel izquierdo."""
        lf_new_sale = ttk.LabelFrame(parent, text="Nueva Venta a Crédito", padding=10)
        lf_new_sale.pack(fill=tk.X, expand=False, pady=(0, 10))

        # --- Datos Cliente ---
        ttk.Label(lf_new_sale, text="Cliente:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.customer_entry = ttk.Entry(lf_new_sale)
        self.customer_entry.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5)

        ttk.Label(lf_new_sale, text="Fecha Emisión:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.date_entry = DateEntry(lf_new_sale, date_pattern='yyyy-mm-dd', width=12)
        self.date_entry.bind("<<DateEntrySelected>>", self._update_due_date)
        self.date_entry.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(lf_new_sale, text="Vencimiento (Opc):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.due_date_entry = DateEntry(lf_new_sale, date_pattern='yyyy-mm-dd', width=12)
        self.due_date_entry.grid(row=2, column=1, sticky=tk.W, padx=5)
        self._update_due_date()

        # --- Formulario de Items ---
        item_frame = ttk.LabelFrame(lf_new_sale, text="Agregar Productos")
        item_frame.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=5)
        
        ttk.Label(item_frame, text="Producto:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.product_cb = ttk.Combobox(item_frame, state="readonly", width=15)
        self.product_cb.grid(row=1, column=0, padx=5, pady=(0,5))
        self.product_cb.bind("<<ComboboxSelected>>", self._on_product_select)

        ttk.Label(item_frame, text="Calidad:").grid(row=0, column=1, sticky=tk.W, padx=5)
        self.quality_cb = ttk.Combobox(item_frame, state="readonly", width=12)
        self.quality_cb.grid(row=1, column=1, padx=5, pady=(0,5))
        self.quality_cb.bind("<<ComboboxSelected>>", self._auto_fill_price)

        ttk.Label(item_frame, text="Precio U:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.price_entry = ttk.Entry(item_frame, width=15)
        self.price_entry.grid(row=3, column=0, padx=5, pady=(0,5))
        
        ttk.Label(item_frame, text="Cantidad:").grid(row=2, column=1, sticky=tk.W, padx=5)
        self.qty_entry = ttk.Entry(item_frame, width=12)
        self.qty_entry.grid(row=3, column=1, padx=5, pady=(0,5))

        self.add_item_btn = ttk.Button(item_frame, text="Agregar Item", command=self._add_item_to_list)
        self.add_item_btn.grid(row=3, column=2, padx=5, sticky=tk.W, pady=(0,5))

        item_frame.columnconfigure(2, weight=1)
        
        # --- Mini-árbol de items ---
        cols = ('product', 'qty', 'price', 'total')
        self.items_tree = ttk.Treeview(lf_new_sale, columns=cols, show='headings', height=4)
        self.items_tree.heading('product', text='Producto')
        self.items_tree.heading('qty', text='Cant.')
        self.items_tree.heading('price', text='P.U.')
        self.items_tree.heading('total', text='Subtotal')
        self.items_tree.column('product', width=120)
        self.items_tree.column('qty', width=40, anchor=tk.CENTER)
        self.items_tree.column('price', width=60, anchor=tk.E)
        self.items_tree.column('total', width=70, anchor=tk.E)
        self.items_tree.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=5)
        
        self.remove_item_btn = ttk.Button(lf_new_sale, text="Quitar Item", command=self._remove_item_from_list)
        self.remove_item_btn.grid(row=5, column=2, sticky=tk.E, padx=5)
        
        self.total_label = ttk.Label(lf_new_sale, text="TOTAL: S/ 0.00", font=('Segoe UI', 9, 'bold'))
        self.total_label.grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5)

        ttk.Label(lf_new_sale, text="Notas Venta:").grid(row=6, column=0, sticky=tk.W, pady=(5,2))
        self.notes_entry = ttk.Entry(lf_new_sale)
        self.notes_entry.grid(row=6, column=1, columnspan=2, sticky=tk.EW, padx=5)

        self.save_sale_btn = ttk.Button(lf_new_sale, text="Guardar Venta a Crédito", command=self._save_sale)
        self.save_sale_btn.grid(row=7, column=0, columnspan=3, pady=10)

        lf_new_sale.columnconfigure(1, weight=1)

    def _build_left_panel_payment(self, parent):
        """Construye el formulario de 'Registrar Pago' en el panel izquierdo."""
        self.lf_payment = ttk.LabelFrame(parent, text="Registrar Pago (Seleccione una venta)", padding=10)
        self.lf_payment.pack(fill=tk.X, expand=False)
        
        self.selected_sale_label = ttk.Label(self.lf_payment, text="Venta: N/A", font=('Segoe UI', 9, 'bold'))
        self.selected_sale_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        ttk.Label(self.lf_payment, text="Fecha Pago:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.pay_date_entry = DateEntry(self.lf_payment, date_pattern='yyyy-mm-dd', width=12)
        self.pay_date_entry.set_date(datetime.now())
        self.pay_date_entry.grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(self.lf_payment, text="Monto:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.pay_amount_entry = ttk.Entry(self.lf_payment, width=14)
        self.pay_amount_entry.grid(row=2, column=1, sticky=tk.W, padx=5)
        
        self.fill_balance_btn = ttk.Button(self.lf_payment, text="Saldar", command=self._fill_balance, width=6)
        self.fill_balance_btn.grid(row=2, column=2, padx=5, sticky=tk.W)

        ttk.Label(self.lf_payment, text="Método:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.pay_method_cb = ttk.Combobox(self.lf_payment, state="readonly", values=list(PAY_TO_CODE.keys()), width=12)
        self.pay_method_cb.set("Efectivo")
        self.pay_method_cb.grid(row=3, column=1, sticky=tk.W, padx=5)

        ttk.Label(self.lf_payment, text="Notas Pago:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.pay_notes_entry = ttk.Entry(self.lf_payment)
        self.pay_notes_entry.grid(row=4, column=1, columnspan=2, sticky=tk.EW, padx=5)
        
        self.register_payment_btn = ttk.Button(self.lf_payment, text="Registrar Pago", command=self._register_payment)
        self.register_payment_btn.grid(row=5, column=0, columnspan=3, pady=10)
        
        self.lf_payment.columnconfigure(1, weight=1)
        self._toggle_payment_form(False) # Deshabilitado al inicio

    def _build_right_panel_history(self, parent):
        """Construye el historial (filtros y árbol) en el panel derecho."""
        # --- Filtros ---
        filters = ttk.LabelFrame(parent, text="Historial de Cuentas", padding=8)
        filters.pack(fill=tk.X)

        ttk.Label(filters, text="Desde:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.start_de = DateEntry(filters, date_pattern='yyyy-mm-dd', width=12)
        self.start_de.set_date(datetime.now() - timedelta(days=30))
        self.start_de.grid(row=0, column=1, sticky=tk.W, padx=(4, 12))

        ttk.Label(filters, text="Hasta:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.end_de = DateEntry(filters, date_pattern='yyyy-mm-dd', width=12)
        self.end_de.set_date(datetime.now())
        self.end_de.grid(row=0, column=3, sticky=tk.W, padx=(4, 12))

        ttk.Label(filters, text="Estado:").grid(row=0, column=4, sticky=tk.W, pady=2)
        self.status_cb = ttk.Combobox(filters, state="readonly", width=14, 
                                      values=["Todas", "Pendientes", "Pagadas"])
        self.status_cb.set("Pendientes")
        self.status_cb.grid(row=0, column=5, sticky=tk.W, padx=(4, 12))
        
        self.apply_filter_btn = ttk.Button(filters, text="Buscar", command=self._load_credit_sales_list)
        self.apply_filter_btn.grid(row=0, column=6, padx=(8, 4))
        
        self.export_pdf_btn = ttk.Button(filters, text="Exportar PDF", command=self._export_pdf)
        self.export_pdf_btn.grid(row=0, column=7, padx=4)

        self.delete_sale_btn = ttk.Button(filters, text="Eliminar Venta", command=self._delete_sale)
        self.delete_sale_btn.grid(row=0, column=8, padx=4)


        # --- Tabla Principal ---
        tree_frame = ttk.Frame(parent, padding=(0, 10, 0, 0))
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('id', 'date', 'customer', 'due_date', 'total', 'paid', 'balance', 'status')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=18)
        
        ysb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        xsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        headers = {
            'id': 'ID', 'date': 'Fecha', 'customer': 'Cliente', 'due_date': 'Vencimiento',
            'total': 'Total', 'paid': 'Pagado', 'balance': 'Saldo', 'status': 'Estado'
        }
        widths = {
            'id': 40, 'date': 90, 'customer': 200, 'due_date': 90,
            'total': 100, 'paid': 100, 'balance': 100, 'status': 80
        }
        
        for c in columns:
            anchor = tk.W if c == 'customer' else tk.E
            if c in ('id', 'date', 'due_date', 'status'):
                anchor = tk.CENTER
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor=anchor, stretch=True)

        # --- Definir Estilos (Tags) ---
        self.tree.tag_configure("paid_status", foreground="red", font=('Segoe UI', 9, 'bold')) # Pagado en ROJO
        self.tree.tag_configure("unpaid_status", foreground="#006400") # Pendiente en Verde oscuro
        self.tree.tag_configure("oddrow", background="#f5f5f5")
        
        self.tree.bind("<<TreeviewSelect>>", self._on_main_tree_select)
        self.tree.bind("<Double-1>", self._on_main_tree_double_click)

    # --- Métodos de Lógica de UI ---

    def refresh_all(self):
        """Método público para refrescar toda la pestaña."""
        try:
            # Cargar productos para el formulario de nueva venta
            self.products_data = self.controller.inv.get_all_products()
            product_names = sorted(list(self.products_data.keys()))
            self.product_cb['values'] = product_names
            if product_names:
                self.product_cb.set(product_names[0])
                self._on_product_select()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los productos: {e}")
            self.products_data = {}
        
        self._clear_sale_form()
        self._clear_payment_form()
        self._load_credit_sales_list()

    def _load_credit_sales_list(self):
        """Recarga la lista principal de ventas a crédito."""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            start = self.start_de.get_date().strftime('%Y-%m-%d')
            end = self.end_de.get_date().strftime('%Y-%m-%d')
            status_map = {"Pendientes": "unpaid", "Pagadas": "paid", "Todas": "all"}
            status = status_map.get(self.status_cb.get(), "all")
            
            sales = self.controller.get_all_credit_sales(start, end, status)
            
            for i, sale in enumerate(sales):
                summary = self.controller.get_credit_sale_summary(sale['id'])
                
                status_text = "Pagada" if sale['status'] == 'paid' else "Pendiente"
                tag = "paid_status" if sale['status'] == 'paid' else "unpaid_status"
                tags = (tag, "oddrow") if i % 2 else (tag,)

                self.tree.insert("", tk.END, iid=sale['id'], values=(
                    sale['id'],
                    sale['date_issued'],
                    sale['customer_name'],
                    sale['due_date'] or 'N/A',
                    f"S/ {summary['total']:.2f}",
                    f"S/ {summary['paid']:.2f}",
                    f"S/ {summary['balance']:.2f}",
                    status_text
                ), tags=tags)
        except Exception as e:
            messagebox.showerror("Error al cargar ventas", str(e))

    def _on_product_select(self, _=None):
        selected_product = self.product_cb.get()
        qualities = self.products_data.get(selected_product, [])
        self.quality_cb['values'] = qualities
        if qualities:
            self.quality_cb.set(qualities[0])
        else:
            self.quality_cb.set("")
        self._auto_fill_price()

    def _auto_fill_price(self, _=None):
        t = (self.product_cb.get() or "").lower()
        q = (self.quality_cb.get() or "").lower()
        if not t or not q: return
        
        price = self.controller.inv.get_reference_price(t, q)
        self.price_entry.delete(0, tk.END)
        if price is not None:
            self.price_entry.insert(0, f"{price:.2f}")

    def _add_item_to_list(self):
        """Agrega un producto al mini-árbol de la nueva venta."""
        try:
            product = self.product_cb.get()
            quality = self.quality_cb.get()
            qty = int(self.qty_entry.get())
            price = float(self.price_entry.get())
            
            if not product or not quality: raise ValueError("Seleccione producto y calidad.")
            if qty <= 0 or price < 0: raise ValueError("Cantidad y precio deben ser positivos.")
                
            item_data = {
                'product_name': product,
                'quality': quality,
                'quantity': qty,
                'unit_price': price,
                'total_value': round(qty * price, 2)
            }
            
            self.items_list.append(item_data)
            self.items_tree.insert("", tk.END, values=(
                f"{product} ({quality})", qty, f"{price:.2f}", f"{item_data['total_value']:.2f}"
            ))
            self._update_total_label()
            self.qty_entry.delete(0, tk.END)
        except (ValueError, TypeError) as e:
            messagebox.showerror("Error de datos", str(e))

    def _remove_item_from_list(self):
        """Quita un producto del mini-árbol."""
        selected = self.items_tree.selection()
        if not selected: return
        
        selected_index = self.items_tree.index(selected[0])
        self.items_tree.delete(selected[0])
        del self.items_list[selected_index]
        self._update_total_label()
        
    def _update_due_date(self, event=None):
        """
        Actualiza la fecha de vencimiento para que sea 7 días después 
        de la fecha de emisión seleccionada.
        """
        try:
            # 1. Obtener la fecha de emisión
            emission_date = self.date_entry.get_date()
            
            # 2. Calcular la nueva fecha de vencimiento (emisión + 7 días)
            due_date = emission_date + timedelta(days=7)
            
            # 3. Establecer la fecha de vencimiento
            self.due_date_entry.set_date(due_date)
        except Exception:
            # Si la fecha de emisión está vacía o es inválida, limpia el vencimiento
            self.date_entry.set_date(datetime.now())
            self.due_date_entry.set_date(datetime.now() + timedelta(days=7))
        
    def _update_total_label(self):
        total = sum(item['total_value'] for item in self.items_list)
        self.total_label.config(text=f"TOTAL: S/ {total:.2f}")

    def _clear_sale_form(self):
        """Limpia el formulario de nueva venta."""
        self.customer_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)
        self._update_due_date()
        self.price_entry.delete(0, tk.END)
        self.qty_entry.delete(0, tk.END)
        
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        self.items_list = []
        self._update_total_label()
        
        if self.product_cb['values']:
            self.product_cb.set(self.product_cb['values'][0])
            self._on_product_select()

    def _save_sale(self):
        """Guarda la nueva venta a crédito."""
        try:
            customer = self.customer_entry.get().strip()
            date = self.date_entry.get_date().strftime('%Y-%m-%d')
            due_date_str = self.due_date_entry.get()
            due_date = self.due_date_entry.get_date().strftime('%Y-%m-%d') if due_date_str else None
            notes = self.notes_entry.get().strip()
            
            if not self.items_list:
                raise ValueError("Debe agregar al menos un producto a la venta.")
            if not customer:
                raise ValueError("Debe ingresar un nombre de cliente.")

            # Esta llamada DESCUENTA INVENTARIO Y COSTALES
            self.controller.create_credit_sale(
                customer_name=customer, date_issued=date,
                due_date=due_date, notes=notes, items=self.items_list
            )
            
            messagebox.showinfo("Éxito", "Venta a crédito creada. El inventario ha sido descontado.")
            self._clear_sale_form()
            self._load_credit_sales_list() # Recargar el historial
            self.parent.event_generate("<<SaleCreated>>", when="tail") # Notificar a otros módulos
            
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error de validación", str(e))
        except Exception as e:
            messagebox.showerror("Error inesperado", f"No se pudo crear la venta: {e}")

    # --- Métodos del Formulario de Pago ---

    def _on_main_tree_select(self, _=None):
        """Se activa al seleccionar una fila en el árbol principal de la derecha."""
        selected = self.tree.selection()
        if not selected:
            self._clear_payment_form()
            self._toggle_payment_form(False)
            return

        self.selected_sale_id = selected[0]
        try:
            # Obtener datos de la fila
            item_values = self.tree.item(self.selected_sale_id, 'values')
            customer_name = item_values[2]
            status = item_values[7]

            self.selected_sale_summary = self.controller.get_credit_sale_summary(self.selected_sale_id)
            balance = self.selected_sale_summary['balance']
            
            # Actualizar formulario de pago
            self.lf_payment.config(text=f"Pagar Venta ID: {self.selected_sale_id}")
            self.selected_sale_label.config(text=f"Cliente: {customer_name}")
            self.pay_amount_entry.delete(0, tk.END)
            self.pay_amount_entry.insert(0, f"{balance:.2f}")

            # Activar o desactivar formulario
            if status == "Pendiente" and balance > 0:
                self._toggle_payment_form(True)
            else:
                self._toggle_payment_form(False)
                self.lf_payment.config(text="Venta Pagada")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el resumen de pago: {e}")
            self._clear_payment_form()
            self._toggle_payment_form(False)

    def _on_main_tree_double_click(self, _=None):
        """Al hacer doble clic, enfoca el campo de monto."""
        if self.selected_sale_id:
            self.pay_amount_entry.focus()
            self.pay_amount_entry.select_range(0, tk.END)

    def _toggle_payment_form(self, enabled: bool):
        """Activa o desactiva todos los widgets en el frame de pago."""
        state = "normal" if enabled else "disabled"
        for child in self.lf_payment.winfo_children():
            # No deshabilitar las etiquetas
            if isinstance(child, (ttk.Entry, ttk.Combobox, ttk.Button, DateEntry)):
                child.config(state=state)

    def _clear_payment_form(self):
        """Limpia el formulario de pago."""
        self.selected_sale_id = None
        self.selected_sale_summary = {}
        self.lf_payment.config(text="Registrar Pago (Seleccione una venta)")
        self.selected_sale_label.config(text="Venta: N/A")
        self.pay_amount_entry.delete(0, tk.END)
        self.pay_notes_entry.delete(0, tk.END)
        self.pay_method_cb.set("Efectivo")
        self._toggle_payment_form(False)

    def _fill_balance(self):
        """Rellena el campo de monto con el saldo pendiente."""
        balance = self.selected_sale_summary.get('balance', 0.0)
        self.pay_amount_entry.delete(0, tk.END)
        self.pay_amount_entry.insert(0, f"{balance:.2f}")

    def _register_payment(self):
        """Guarda el pago en la BD y actualiza la 'Caja'."""
        if not self.selected_sale_id:
            messagebox.showwarning("Sin selección", "No hay una venta seleccionada para pagar.")
            return

        try:
            date = self.pay_date_entry.get_date().strftime('%Y-%m-%d')
            amount = float(self.pay_amount_entry.get())
            method = PAY_TO_CODE[self.pay_method_cb.get()]
            notes = self.pay_notes_entry.get().strip()

            # Esta llamada REGISTRA INGRESO EN CAJA
            self.controller.add_payment(self.selected_sale_id, date, amount, method, notes)
            
            messagebox.showinfo("Éxito", "Pago registrado. La caja ha sido actualizada.")
            
            self._clear_payment_form()
            self._load_credit_sales_list() # Recargar el historial
            
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error de validación", str(e))
        except Exception as e:
            messagebox.showerror("Error inesperado", f"No se pudo registrar el pago: {e}")

    # --- Otros Métodos ---

    def _get_selected_sale_id(self):
        """Obtiene el ID de la fila seleccionada en el árbol principal."""
        if not self.selected_sale_id:
            # Probar a leer la selección actual si self.selected_sale_id está vacío
            selected = self.tree.selection()
            if not selected:
                messagebox.showwarning("Sin selección", "Por favor, seleccione una venta de la lista.")
                return None
            self.selected_sale_id = selected[0]
        return self.selected_sale_id

    def _delete_sale(self):
        """Elimina la venta seleccionada, revirtiendo el inventario."""
        sale_id = self._get_selected_sale_id()
        if not sale_id:
            return
            
        summary = self.controller.get_credit_sale_summary(sale_id)
        if summary['paid'] > 0:
            messagebox.showerror("Acción denegada", "No se puede eliminar una venta que ya tiene pagos registrados.")
            return

        if messagebox.askyesno("Confirmar Eliminación", 
            f"¿Está seguro de eliminar la venta a crédito ID {sale_id}?\n\n"
            "¡ADVERTENCIA!\n"
            "Esta acción REVERTIRÁ el inventario (los productos y costales 'volverán' al stock)."):
            
            try:
                # Esta llamada REVIERTE INVENTARIO
                self.controller.delete_credit_sale(sale_id)
                messagebox.showinfo("Éxito", "Venta eliminada y stock revertido.")
                self.refresh_all()
            except Exception as e:
                messagebox.showerror("Error al eliminar", str(e))

    def _export_pdf(self):
        """Exporta la vista actual a un PDF."""
        messagebox.showinfo("Exportar PDF", "Función de exportar PDF aún no implementada.")