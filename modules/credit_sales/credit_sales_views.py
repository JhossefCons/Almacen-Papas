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
from typing import Optional 

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

PAY_TO_CODE = {"Efectivo": "cash", "Transferencia": "transfer"}
CODE_TO_PAY = {"cash": "Efectivo", "transfer": "Transferencia"}

class CreditSalesView:
    def __init__(self, parent, database, auth_manager, cash_controller):
        self.parent = parent
        self.db = database
        self.auth = auth_manager
        self.controller = CreditSalesController(database, auth_manager, cash_controller)
        
        self.products_data = {} 
        self.items_list = []     
        self.selected_sale_id = None 
        self.selected_sale_summary = {} 
        self.current_status_filter_es = "Pendientes" # Para PDF

        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=8)
        container.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(container, width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False) 

        right_panel = ttk.Frame(container)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_left_panel_new_sale(left_panel)
        self._build_left_panel_payment(left_panel)
        left_panel.rowconfigure(0, weight=0)
        left_panel.rowconfigure(1, weight=1) 
        left_panel.columnconfigure(0, weight=1)
        self._build_right_panel_history(right_panel)

    def _build_left_panel_new_sale(self, parent):
        lf_new_sale = ttk.LabelFrame(parent, text="Nueva Venta a Crédito", padding=10)
        lf_new_sale.grid(row=0, column=0, sticky="new", pady=(0, 10))

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
        
        cols = ('product', 'qty', 'price', 'total')
        self.items_tree = ttk.Treeview(lf_new_sale, columns=cols, show='headings', height=4)
        self.items_tree.heading('product', text='Producto'); self.items_tree.heading('qty', text='Cant.'); self.items_tree.heading('price', text='P.U.'); self.items_tree.heading('total', text='Subtotal')
        self.items_tree.column('product', width=120); self.items_tree.column('qty', width=40, anchor=tk.CENTER); self.items_tree.column('price', width=60, anchor=tk.E); self.items_tree.column('total', width=70, anchor=tk.E)
        self.items_tree.grid(row=4, column=0, columnspan=3, sticky=tk.EW, pady=5)
        
        self.remove_item_btn = ttk.Button(lf_new_sale, text="Quitar Item", command=self._remove_item_from_list)
        self.remove_item_btn.grid(row=5, column=2, sticky=tk.E, padx=5)
        
        self.total_label = ttk.Label(lf_new_sale, text="TOTAL: S/ 0.00", font=('Segoe UI', 9, 'bold'))
        self.total_label.grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5)

        ttk.Label(lf_new_sale, text="Notas Venta:").grid(row=6, column=0, sticky=tk.W, pady=(5,2))
        self.notes_entry = ttk.Entry(lf_new_sale)
        self.notes_entry.grid(row=6, column=1, columnspan=2, sticky=tk.EW, padx=5)

        self.save_sale_btn = ttk.Button(lf_new_sale, text="Guardar Venta a Crédito", command=self._save_sale)
        self.save_sale_btn.grid(row=7, column=0, columnspan=2, pady=10, sticky=tk.EW) 

        lf_new_sale.columnconfigure(1, weight=1)

    def _build_left_panel_payment(self, parent):
        
        self.lf_payment = ttk.LabelFrame(parent, text="Registrar Pago (Seleccione una venta)", padding=10)
        self.lf_payment.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        
        self.selected_sale_label = ttk.Label(self.lf_payment, text="Venta: N/A", font=('Segoe UI', 9, 'bold'))
        self.selected_sale_label.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(5, 10))

        ttk.Label(self.lf_payment, text="Fecha Pago:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.pay_date_entry = DateEntry(self.lf_payment, date_pattern='yyyy-mm-dd', width=12)
        self.pay_date_entry.set_date(datetime.now())
        self.pay_date_entry.grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(self.lf_payment, text="Monto:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.pay_amount_entry = ttk.Entry(self.lf_payment)
        self.pay_amount_entry.grid(row=2, column=1, sticky=tk.EW, padx=5)
        
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
        self.register_payment_btn.grid(row=5, column=0, columnspan=3, pady=10, sticky=tk.EW)
        self.lf_payment.columnconfigure(1, weight=1) 
        self.lf_payment.columnconfigure(2, weight=0)
        self._toggle_payment_form(False)

    def _build_right_panel_history(self, parent):
        filters = ttk.LabelFrame(parent, text="Historial de Cuentas", padding=8)
        filters.pack(fill=tk.X)
        
        ttk.Label(filters, text="Desde:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.start_de = DateEntry(filters, date_pattern='yyyy-mm-dd', width=12)
        self.start_de.set_date(datetime.now() - timedelta(days=30))
        self.start_de.grid(row=0, column=1, sticky=tk.W, padx=(4, 12))
        self.start_de.bind("<<DateEntrySelected>>", lambda e: self._load_credit_sales_list())
        ttk.Label(filters, text="Hasta:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.end_de = DateEntry(filters, date_pattern='yyyy-mm-dd', width=12)
        self.end_de.set_date(datetime.now())
        self.end_de.grid(row=0, column=3, sticky=tk.W, padx=(4, 12))
        self.end_de.bind("<<DateEntrySelected>>", lambda e: self._load_credit_sales_list())
        ttk.Label(filters, text="Estado:").grid(row=0, column=4, sticky=tk.W, pady=2)
        self.status_cb = ttk.Combobox(filters, state="readonly", width=14, 
                                      values=["Todas", "Pendientes", "Pagadas"])
        self.status_cb.set("Pendientes")
        self.status_cb.grid(row=0, column=5, sticky=tk.W, padx=(4, 12))
        self.status_cb.bind("<<ComboboxSelected>>", lambda e: self._load_credit_sales_list())
        self.apply_filter_btn = ttk.Button(filters, text="Buscar", command=self._load_credit_sales_list)
        self.apply_filter_btn.grid(row=0, column=6, padx=(8, 4))
        self.edit_sale_btn = ttk.Button(filters, text="Editar Venta", command=self._open_edit_dialog)
        self.edit_sale_btn.grid(row=0, column=7, padx=4)
        self.delete_sale_btn = ttk.Button(filters, text="Eliminar Venta", command=self._delete_sale)
        self.delete_sale_btn.grid(row=0, column=8, padx=4)
        self.export_pdf_btn = ttk.Button(filters, text="Exportar PDF", command=self._export_pdf)
        self.export_pdf_btn.grid(row=0, column=9, padx=4, sticky=tk.E) 
        filters.columnconfigure(9, weight=1) 

        tree_frame = ttk.Frame(parent, padding=(0, 10, 0, 0))
        tree_frame.pack(fill=tk.BOTH, expand=True)
        columns = ('id', 'date', 'customer', 'due_date', 'total', 'paid', 'balance', 'status', 'notes')
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
            'total': 'Total', 'paid': 'Pagado', 'balance': 'Saldo', 'status': 'Estado', 'notes': 'Notas de Venta'
        }
        widths = {
            'id': 40, 'date': 90, 'customer': 180, 'due_date': 90, 'total': 100,
            'paid': 100, 'balance': 100, 'status': 80, 'notes': 200 
        }
        for c in columns:
            anchor = tk.W
            if c in ('total', 'paid', 'balance'): anchor = tk.E
            elif c in ('id', 'date', 'due_date', 'status'): anchor = tk.CENTER
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor=anchor, stretch=True)
        self.tree.tag_configure("paid_status", foreground="red", font=('Segoe UI', 9, 'bold'))
        self.tree.tag_configure("unpaid_status", foreground="#006400")
        self.tree.tag_configure("oddrow", background="#f5f5f5")
        self.tree.bind("<<TreeviewSelect>>", self._on_main_tree_select)
        self.tree.bind("<Double-1>", self._on_main_tree_double_click)

    def refresh_all(self):
        try:
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
        for item in self.tree.get_children(): self.tree.delete(item)
        try:
            start = self.start_de.get_date().strftime('%Y-%m-%d')
            end = self.end_de.get_date().strftime('%Y-%m-%d')
            status_map = {"Pendientes": "unpaid", "Pagadas": "paid", "Todas": "all"}
            self.current_status_filter_es = self.status_cb.get()
            status = status_map.get(self.current_status_filter_es, "all")
            sales = self.controller.get_all_credit_sales(start, end, status)
            for i, sale in enumerate(sales):
                summary = self.controller.get_credit_sale_summary(sale['id'])
                status_text = "Pagada" if sale['status'] == 'paid' else "Pendiente"
                tag = "paid_status" if sale['status'] == 'paid' else "unpaid_status"
                tags = (tag, "oddrow") if i % 2 else (tag,)
                self.tree.insert("", tk.END, iid=sale['id'], values=(
                    sale['id'], sale['date_issued'], sale['customer_name'],
                    sale['due_date'] or 'N/A', f"S/ {summary['total']:.2f}",
                    f"S/ {summary['paid']:.2f}", f"S/ {summary['balance']:.2f}",
                    status_text, sale['notes'] or ''
                ), tags=tags)
        except Exception as e:
            messagebox.showerror("Error al cargar ventas", str(e))

    def _on_product_select(self, _=None):
        selected_product = self.product_cb.get()
        qualities = self.products_data.get(selected_product, [])
        self.quality_cb['values'] = qualities
        if qualities: self.quality_cb.set(qualities[0])
        else: self.quality_cb.set("")
        self._auto_fill_price()

    def _auto_fill_price(self, _=None):
        t = (self.product_cb.get() or "").lower()
        q = (self.quality_cb.get() or "").lower()
        if not t or not q: return
        price = self.controller.inv.get_reference_price(t, q)
        self.price_entry.delete(0, tk.END)
        if price is not None: self.price_entry.insert(0, f"{price:.2f}")

    def _add_item_to_list(self):
        try:
            product = self.product_cb.get()
            quality = self.quality_cb.get()
            qty_str = self.qty_entry.get().strip()
            price_str = self.price_entry.get().strip()
            if not product or not quality: raise ValueError("Seleccione producto y calidad.")
            if not qty_str: raise ValueError("Ingrese la 'Cantidad'.")
            if not price_str: raise ValueError("Ingrese el 'Precio U:'.")
            try: qty = int(qty_str)
            except ValueError: raise ValueError("La 'Cantidad' debe ser un número entero.")
            try: price = float(price_str)
            except ValueError: raise ValueError("El 'Precio U:' debe ser un número.")
            if qty <= 0 or price < 0: raise ValueError("Cantidad y precio deben ser positivos.")
            item_data = {
                'product_name': product, 'quality': quality, 'quantity': qty,
                'unit_price': price, 'total_value': round(qty * price, 2)
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
        selected = self.items_tree.selection()
        if not selected: return
        selected_index = self.items_tree.index(selected[0])
        self.items_tree.delete(selected[0])
        del self.items_list[selected_index]
        self._update_total_label()
        
    def _update_due_date(self, event=None):
        try:
            emission_date = self.date_entry.get_date()
            due_date = emission_date + timedelta(days=7)
            self.due_date_entry.set_date(due_date)
        except Exception:
            self.date_entry.set_date(datetime.now())
            self.due_date_entry.set_date(datetime.now() + timedelta(days=7))
        
    def _update_total_label(self):
        total = sum(item['total_value'] for item in self.items_list)
        self.total_label.config(text=f"TOTAL: S/ {total:.2f}")

    def _clear_sale_form(self):
        self.customer_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)
        self._update_due_date()
        self.price_entry.delete(0, tk.END)
        self.qty_entry.delete(0, tk.END)
        for item in self.items_tree.get_children(): self.items_tree.delete(item)
        self.items_list = []
        self._update_total_label()
        if self.product_cb['values']:
            self.product_cb.set(self.product_cb['values'][0])
            self._on_product_select()

    def _save_sale(self):
        try:
            customer = self.customer_entry.get().strip()
            if not customer: raise ValueError("Debe ingresar un nombre de 'Cliente'.")
            date = self.date_entry.get_date().strftime('%Y-%m-%d')
            due_date_str = self.due_date_entry.get()
            due_date = self.due_date_entry.get_date().strftime('%Y-%m-%d') if due_date_str else None
            notes = self.notes_entry.get().strip()
            if not self.items_list:
                raise ValueError("Debe agregar al menos un producto a la venta.")

            self.controller.create_credit_sale(
                customer_name=customer, date_issued=date,
                due_date=due_date, notes=notes, items=self.items_list
            )
            messagebox.showinfo("Éxito", "Venta a crédito creada. El inventario ha sido descontado.")
            self._clear_sale_form()
            self._load_credit_sales_list() 
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error de validación", str(e))
        except Exception as e:
            messagebox.showerror("Error inesperado", f"No se pudo crear la venta: {e}")

    def _on_main_tree_select(self, _=None):
        selected = self.tree.selection()
        if not selected:
            self._clear_payment_form()
            self._toggle_payment_form(False)
            return
        self.selected_sale_id = selected[0]
        try:
            item_values = self.tree.item(self.selected_sale_id, 'values')
            customer_name = item_values[2]
            status = item_values[7] 
            self.selected_sale_summary = self.controller.get_credit_sale_summary(self.selected_sale_id)
            balance = self.selected_sale_summary['balance']
            self.lf_payment.config(text=f"Pagar Venta ID: {self.selected_sale_id}")
            self.selected_sale_label.config(text=f"Cliente: {customer_name}")
            self.pay_amount_entry.delete(0, tk.END)
            self.pay_amount_entry.insert(0, f"{balance:.2f}")
            if status == "Pendiente" and balance > 0.009:
                self._toggle_payment_form(True)
            else:
                self._toggle_payment_form(False)
                self.lf_payment.config(text="Venta Pagada")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el resumen de pago: {e}")
            self._clear_payment_form()
            self._toggle_payment_form(False)

    def _on_main_tree_double_click(self, _=None):
        if self.selected_sale_id:
            item_values = self.tree.item(self.selected_sale_id, 'values')
            status = item_values[7]
            if status == "Pendiente":
                self.pay_amount_entry.focus()
                self.pay_amount_entry.select_range(0, tk.END)

    def _toggle_payment_form(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for child in self.lf_payment.winfo_children():
            if not isinstance(child, ttk.Label):
                child.config(state=state)

    def _clear_payment_form(self):
        self.selected_sale_id = None
        self.selected_sale_summary = {}
        self.lf_payment.config(text="Registrar Pago (Seleccione una venta)")
        self.selected_sale_label.config(text="Venta: N/A")
        self.pay_amount_entry.delete(0, tk.END)
        self.pay_notes_entry.delete(0, tk.END)
        self.pay_method_cb.set("Efectivo")
        self._toggle_payment_form(False)

    def _fill_balance(self):
        balance = self.selected_sale_summary.get('balance', 0.0)
        self.pay_amount_entry.delete(0, tk.END)
        self.pay_amount_entry.insert(0, f"{balance:.2f}")

    def _register_payment(self):
        if not self.selected_sale_id:
            messagebox.showwarning("Sin selección", "No hay una venta seleccionada para pagar.")
            return
        try:
            date = self.pay_date_entry.get_date().strftime('%Y-%m-%d')
            amount_str = self.pay_amount_entry.get().strip()
            if not amount_str: raise ValueError("El 'Monto' no puede estar vacío.")
            try: amount = float(amount_str)
            except ValueError: raise ValueError("El 'Monto' debe ser un número válido.")
            if amount <= 0:
                raise ValueError("El monto del pago debe ser positivo.")
            method = PAY_TO_CODE[self.pay_method_cb.get()]
            notes = self.pay_notes_entry.get().strip()
            self.controller.add_payment(self.selected_sale_id, date, amount, method, notes)
            messagebox.showinfo("Éxito", "Pago registrado. La caja ha sido actualizada.")
            self._clear_payment_form()
            self._load_credit_sales_list() 
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error de validación", str(e), parent=self.parent)
        except Exception as e:
            messagebox.showerror("Error inesperado", f"No se pudo registrar el pago: {e}", parent=self.parent)

    def _get_selected_sale_id(self):
        if not self.selected_sale_id:
            selected = self.tree.selection()
            if not selected:
                messagebox.showwarning("Sin selección", "Por favor, seleccione una venta de la lista.")
                return None
            self.selected_sale_id = selected[0]
        return self.selected_sale_id

    def _open_edit_dialog(self):
        sale_id = self._get_selected_sale_id()
        if not sale_id: return
        try:
            sale_data = self.controller.get_credit_sale(sale_id)
            if not sale_data:
                messagebox.showerror("Error", "No se pudo cargar la venta seleccionada.")
                return
            EditSaleDialog(self.parent, self.controller, sale_data, self.refresh_all)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el editor: {e}")

    def _delete_sale(self):
        sale_id = self._get_selected_sale_id()
        if not sale_id: return
        summary = self.controller.get_credit_sale_summary(sale_id)
        if summary['paid'] > 0:
            messagebox.showerror("Acción denegada", "No se puede eliminar una venta que ya tiene pagos registrados.")
            return
        if messagebox.askyesno("Confirmar Eliminación", 
            f"¿Está seguro de eliminar la venta a crédito ID {sale_id}?\n\n"
            "¡ADVERTENCIA!\n"
            "Esta acción REVERTIRÁ el inventario (los productos y costales 'volverán' al stock)."):
            try:
                self.controller.delete_credit_sale(sale_id)
                messagebox.showinfo("Éxito", "Venta eliminada y stock revertido.")
                self.refresh_all()
            except Exception as e:
                messagebox.showerror("Error al eliminar", str(e))

    def _export_pdf(self):
        if not REPORTLAB_OK:
            messagebox.showerror("Error", "La librería ReportLab no está instalada.\n\nInstálala con: pip install reportlab")
            return
        try:
            start = self.start_de.get_date().strftime('%Y-%m-%d')
            end = self.end_de.get_date().strftime('%Y-%m-%d')
            status_map = {"Pendientes": "unpaid", "Pagadas": "paid", "Todas": "all"}
            status_filter_es = self.current_status_filter_es
            status_filter_en = status_map.get(status_filter_es, "all")
            sales = self.controller.get_all_credit_sales(start, end, status_filter_en)
            default_name = f"reporte_ventas_credito_{start.replace('-','')}_{end.replace('-','')}.pdf"
            path = filedialog.asksaveasfilename(
                title="Guardar Reporte PDF",
                initialfile=default_name,
                defaultextension=".pdf",
                filetypes=[("PDF Files", "*.pdf")]
            )
            if not path: return 
            doc = SimpleDocTemplate(
                path, pagesize=landscape(A4),
                leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=20*mm
            )
            story = []
            styles = getSampleStyleSheet()
            title = Paragraph("<b>Reporte de Ventas a Crédito</b>", styles['Title'])
            meta_text = (
                f"Período: <b>{start}</b> a <b>{end}</b> | "
                f"Estado: <b>{status_filter_es}</b> | "
                f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            meta = Paragraph(meta_text, styles['Normal'])
            story += [title, Spacer(1, 4*mm), meta, Spacer(1, 6*mm)]
            headers = ["ID", "Fecha", "Cliente", "Vencimiento", "Total", "Pagado", "Saldo", "Estado", "Notas"]
            table_data = [headers]
            total_deuda = 0.0
            total_pagado = 0.0
            total_saldo = 0.0
            if not sales:
                table_data.append(["(Sin registros para este período)", "", "", "", "", "", "", "", ""])
            else:
                for sale in sales:
                    summary = self.controller.get_credit_sale_summary(sale['id'])
                    status_text = "Pagada" if sale['status'] == 'paid' else "Pendiente"
                    total = summary['total']; paid = summary['paid']; balance = summary['balance']
                    total_deuda += total; total_pagado += paid; total_saldo += balance
                    table_data.append([
                        sale['id'],
                        sale['date_issued'],
                        sale['customer_name'],
                        sale['due_date'] or 'N/A',
                        f"S/ {total:,.2f}",
                        f"S/ {paid:,.2f}",
                        f"S/ {balance:,.2f}",
                        status_text,
                        sale['notes'] or ''
                    ])
            table_data.append([
                "TOTALES", "", "", "",
                f"S/ {total_deuda:,.2f}",
                f"S/ {total_pagado:,.2f}",
                f"S/ {total_saldo:,.2f}",
                "", ""
            ])
            colWidths = [12*mm, 22*mm, 45*mm, 22*mm, 30*mm, 30*mm, 30*mm, 20*mm, 54*mm]
            tbl = Table(table_data, colWidths=colWidths, repeatRows=1)
            style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,0), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.whitesmoke, colors.transparent]),
                ('ALIGN', (0,1), (1,-1), 'CENTER'),
                ('ALIGN', (3,1), (3,-1), 'CENTER'),
                ('ALIGN', (4,1), (6,-1), 'RIGHT'),
                ('ALIGN', (7,1), (7,-1), 'CENTER'),
                ('ALIGN', (2,1), (2,-1), 'LEFT'),
                ('ALIGN', (8,1), (8,-1), 'LEFT'),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                ('BACKGROUND', (0,-1), (-1,-1), colors.lightblue),
                ('ALIGN', (4,-1), (6,-1), 'RIGHT'),
            ])
            tbl.setStyle(style)
            story.append(tbl)
            def footer(canvas, doc):
                canvas.saveState()
                canvas.setFont('Helvetica', 9)
                canvas.drawRightString(doc.pagesize[0] - 15*mm, 10*mm, f"Página {doc.page}")
                canvas.restoreState()
            doc.build(story, onFirstPage=footer, onLaterPages=footer)
            messagebox.showinfo("Exportar PDF", f"PDF generado correctamente:\n{path}")
        except Exception as e:
            messagebox.showerror("Error al Exportar PDF", f"No se pudo generar el PDF:\n{e}")

class EditSaleDialog:
    def __init__(self, parent, controller, sale_data, refresh_callback):
        self.controller: CreditSalesController = controller
        self.sale = sale_data
        self.refresh_callback = refresh_callback
        self.top = tk.Toplevel(parent)
        self.top.title(f"Editar Venta a Crédito ID: {self.sale['id']}")
        self.top.geometry("450x250")
        self.top.transient(parent)
        self.top.grab_set()
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        main_frame = ttk.Frame(self.top, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main_frame, text="Cliente:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.customer_entry = ttk.Entry(main_frame, width=40)
        self.customer_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Label(main_frame, text="Fecha Vencimiento:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.due_date_entry = DateEntry(main_frame, date_pattern='yyyy-mm-dd', width=15)
        self.due_date_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(main_frame, text="Notas:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.notes_entry = ttk.Entry(main_frame, width=40)
        self.notes_entry.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Label(main_frame, text="Nota: Solo se pueden editar estos campos.\nPara cambiar productos, elimine y cree la venta de nuevo.",
                  font=('Segoe UI', 8), foreground="gray").grid(row=3, column=1, sticky=tk.W, padx=5, pady=(10,0))
        footer = ttk.Frame(main_frame)
        footer.grid(row=4, column=0, columnspan=2, pady=(20,0), sticky=tk.E)
        self.save_btn = ttk.Button(footer, text="Guardar Cambios", command=self._save_changes)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        self.cancel_btn = ttk.Button(footer, text="Cancelar", command=self.top.destroy)
        self.cancel_btn.pack(side=tk.LEFT)
        main_frame.columnconfigure(1, weight=1)

    def _load_data(self):
        self.customer_entry.insert(0, self.sale['customer_name'])
        self.notes_entry.insert(0, self.sale['notes'] or "")
        if self.sale['due_date']:
            try:
                date_obj = datetime.strptime(self.sale['due_date'], '%Y-%m-%d')
                self.due_date_entry.set_date(date_obj)
            except (ValueError, TypeError):
                self.due_date_entry.set_date(None)
        else:
            self.due_date_entry.set_date(None) 

    def _save_changes(self):
        try:
            customer = self.customer_entry.get().strip()
            due_date_str = self.due_date_entry.get()
            due_date = self.due_date_entry.get_date().strftime('%Y-%m-%d') if due_date_str else None
            notes = self.notes_entry.get().strip()
            if not customer:
                raise ValueError("El nombre del 'Cliente' no puede estar vacío.")
            self.controller.update_credit_sale_details(
                self.sale['id'], customer, due_date, notes
            )
            messagebox.showinfo("Éxito", "Venta actualizada.", parent=self.top)
            self.refresh_callback() 
            self.top.destroy()
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error de validación", str(e), parent=self.top)
        except Exception as e:
            messagebox.showerror("Error inesperado", f"No se pudo actualizar: {e}", parent=self.top)