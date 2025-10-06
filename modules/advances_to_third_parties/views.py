"""
Vista de Anticipos a Terceros (Ventas a Crédito) - Tkinter + ttk
- Registrar venta a crédito (impacta inventario genérico)
- Historial de ventas a crédito
- Registrar pagos (impacta Caja)
- Historial de pagos
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime, timedelta

from modules.advances_to_third_parties.controller import AdvancesToThirdPartiesController

PAY_TO_CODE = {"Efectivo": "cash", "Transferencia": "transfer"}
CODE_TO_PAY = {"cash": "Efectivo", "transfer": "Transferencia"}


class AdvancesToThirdPartiesView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth = auth_manager
        self.controller = AdvancesToThirdPartiesController(database, auth_manager)

        self._build_ui()
        self._load_credit_sales()
        self._load_payments()

    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=8)
        container.pack(fill=tk.BOTH, expand=True)

        # Notebook para pestañas: Ventas a Crédito y Pagos
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Pestaña 1: Ventas a Crédito
        sales_tab = ttk.Frame(self.notebook)
        self.notebook.add(sales_tab, text="Ventas a Crédito")

        self._build_sales_tab(sales_tab)

        # Pestaña 2: Pagos
        payments_tab = ttk.Frame(self.notebook)
        self.notebook.add(payments_tab, text="Pagos")

        self._build_payments_tab(payments_tab)

    def _build_sales_tab(self, parent):
        # Panel izquierdo: Nueva venta a crédito
        left = ttk.LabelFrame(parent, text="Nueva venta a crédito", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        # Panel derecho: Historial
        right = ttk.Frame(parent)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ---- Formulario ----
        row = 0
        ttk.Label(left, text="Fecha:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.date_entry = DateEntry(left, date_pattern="yyyy-mm-dd")
        self.date_entry.set_date(datetime.now())
        self.date_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Producto:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.product_cb = ttk.Combobox(left, state="readonly")
        self._load_product_options()
        self.product_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Calidad:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.quality_entry = ttk.Entry(left)
        self.quality_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Cantidad:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.qty_entry = ttk.Entry(left)
        self.qty_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Precio unitario:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.unit_price_entry = ttk.Entry(left)
        self.unit_price_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Cliente:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.customer_entry = ttk.Entry(left)
        self.customer_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Notas:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.notes_entry = ttk.Entry(left)
        self.notes_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Button(left, text="Registrar venta", command=self._create_credit_sale).grid(row=row, column=0, columnspan=2, pady=8)

        for c in (0, 1):
            left.grid_columnconfigure(c, weight=1)

        # ---- Historial ----
        hist_frame = ttk.LabelFrame(right, text="Historial de ventas a crédito", padding=(6, 6, 6, 6))
        hist_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('date', 'customer', 'product', 'quality', 'qty', 'unit', 'total', 'status', 'user', 'notes')
        self.sales_tree = ttk.Treeview(hist_frame, columns=columns, show='headings', height=15)

        ysb = ttk.Scrollbar(hist_frame, orient=tk.VERTICAL, command=self.sales_tree.yview)
        self.sales_tree.configure(yscrollcommand=ysb.set)

        self.sales_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)

        headers = {
            'date': 'Fecha', 'customer': 'Cliente', 'product': 'Producto', 'quality': 'Calidad',
            'qty': 'Cantidad', 'unit': 'Precio U.', 'total': 'Total', 'status': 'Estado',
            'user': 'Usuario', 'notes': 'Notas'
        }
        widths = {
            'date': 100, 'customer': 120, 'product': 120, 'quality': 80,
            'qty': 80, 'unit': 100, 'total': 100, 'status': 80, 'user': 100, 'notes': 200
        }

        for c in columns:
            self.sales_tree.heading(c, text=headers[c])
            self.sales_tree.column(c, width=widths[c], anchor=tk.W, stretch=False)

    def _build_payments_tab(self, parent):
        # Panel izquierdo: Nuevo pago
        left = ttk.LabelFrame(parent, text="Registrar pago", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        # Panel derecho: Historial de pagos
        right = ttk.Frame(parent)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ---- Formulario pago ----
        row = 0
        ttk.Label(left, text="ID Venta:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.sale_id_entry = ttk.Entry(left)
        self.sale_id_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Fecha de pago:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.pay_date_entry = DateEntry(left, date_pattern="yyyy-mm-dd")
        self.pay_date_entry.set_date(datetime.now())
        self.pay_date_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Monto:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.amount_entry = ttk.Entry(left)
        self.amount_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Método de pago:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.pay_method_cb = ttk.Combobox(left, state="readonly", values=tuple(PAY_TO_CODE.keys()))
        self.pay_method_cb.set("Efectivo")
        self.pay_method_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Notas:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.pay_notes_entry = ttk.Entry(left)
        self.pay_notes_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Button(left, text="Registrar pago", command=self._add_payment).grid(row=row, column=0, columnspan=2, pady=8)

        for c in (0, 1):
            left.grid_columnconfigure(c, weight=1)

        # ---- Historial pagos ----
        hist_frame = ttk.LabelFrame(right, text="Historial de pagos", padding=(6, 6, 6, 6))
        hist_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('sale_id', 'customer', 'pay_date', 'amount', 'method', 'user', 'notes')
        self.payments_tree = ttk.Treeview(hist_frame, columns=columns, show='headings', height=15)

        ysb = ttk.Scrollbar(hist_frame, orient=tk.VERTICAL, command=self.payments_tree.yview)
        self.payments_tree.configure(yscrollcommand=ysb.set)

        self.payments_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)

        headers = {
            'sale_id': 'ID Venta', 'customer': 'Cliente', 'pay_date': 'Fecha Pago',
            'amount': 'Monto', 'method': 'Método', 'user': 'Usuario', 'notes': 'Notas'
        }
        widths = {
            'sale_id': 80, 'customer': 120, 'pay_date': 100, 'amount': 100,
            'method': 100, 'user': 100, 'notes': 200
        }

        for c in columns:
            self.payments_tree.heading(c, text=headers[c])
            self.payments_tree.column(c, width=widths[c], anchor=tk.W, stretch=False)

    def _load_product_options(self):
        try:
            rows = self.db.execute_query("SELECT DISTINCT potato_type FROM potato_inventory ORDER BY potato_type")
            products = [r['potato_type'] for r in rows] if rows else []
            self.product_cb["values"] = tuple(products)
            if products:
                self.product_cb.set(products[0])
        except Exception as e:
            self.product_cb["values"] = ()
            print(f"Error loading products: {e}")

    def _create_credit_sale(self):
        try:
            date = self.date_entry.get_date().strftime("%Y-%m-%d")
            product = self.product_cb.get().strip()
            quality = self.quality_entry.get().strip()
            qty = int(self.qty_entry.get().strip())
            unit_price = float(self.unit_price_entry.get().strip())
            customer = self.customer_entry.get().strip()
            notes = self.notes_entry.get().strip()

            if not product or not quality or not customer:
                raise ValueError("Producto, calidad y cliente son obligatorios.")

            self.controller.create_credit_sale(
                date=date,
                customer_name=customer,
                product_name=product,
                quality=quality,
                quantity=qty,
                unit_price=unit_price,
                notes=notes,
            )

            messagebox.showinfo("Venta a Crédito", "Venta registrada correctamente.")
            self._reset_sale_form()
            self._load_credit_sales()
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _reset_sale_form(self):
        self.quality_entry.delete(0, tk.END)
        self.qty_entry.delete(0, tk.END)
        self.unit_price_entry.delete(0, tk.END)
        self.customer_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)

    def _load_credit_sales(self):
        for i in self.sales_tree.get_children():
            self.sales_tree.delete(i)

        try:
            sales = self.controller.list_credit_sales()
            for s in sales:
                self.sales_tree.insert('', 'end', values=(
                    s['date'], s['customer_name'], s['product_name'], s['quality'],
                    s['quantity'], f"${s['unit_price']:.2f}", f"${s['total_amount']:.2f}",
                    s['status'], s.get('username', ''), s.get('notes', '')
                ))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar ventas: {e}")

    def _add_payment(self):
        try:
            sale_id = int(self.sale_id_entry.get().strip())
            pay_date = self.pay_date_entry.get_date().strftime("%Y-%m-%d")
            amount = float(self.amount_entry.get().strip())
            method = PAY_TO_CODE[self.pay_method_cb.get()]
            notes = self.pay_notes_entry.get().strip()

            self.controller.add_payment(
                credit_sale_id=sale_id,
                payment_date=pay_date,
                amount=amount,
                payment_method=method,
                notes=notes,
            )

            messagebox.showinfo("Pago", "Pago registrado correctamente.")
            self._reset_payment_form()
            self._load_payments()
            self._load_credit_sales()  # refrescar estados
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _reset_payment_form(self):
        self.sale_id_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)
        self.pay_notes_entry.delete(0, tk.END)
        self.pay_method_cb.set("Efectivo")

    def _load_payments(self):
        for i in self.payments_tree.get_children():
            self.payments_tree.delete(i)

        try:
            payments = self.controller.get_payments()
            for p in payments:
                self.payments_tree.insert('', 'end', values=(
                    p['credit_sale_id'], p['customer_name'], p['payment_date'],
                    f"${p['amount']:.2f}", CODE_TO_PAY.get(p['payment_method'], p['payment_method']),
                    p.get('username', ''), p.get('notes', '')
                ))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar pagos: {e}")

    def refresh_all(self):
        self._load_product_options()
        self._load_credit_sales()
        self._load_payments()
