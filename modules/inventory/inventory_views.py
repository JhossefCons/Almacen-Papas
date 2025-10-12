# modules/inventory/inventory_views.py

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime

# Se elimina la importación de VALID_COMBOS que causaba el error
from modules.inventory.inventory_controller import InventoryController
from modules.cash_register.cash_register_controller import CashRegisterController

import matplotlib
matplotlib.use("TkAgg")
from matplotlib import pyplot as plt

PAY_TO_CODE = {"Efectivo": "cash", "Transferencia": "transfer"}

class InventoryView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth = auth_manager

        self.controller = InventoryController(database, auth_manager)
        self.cash = CashRegisterController(database, auth_manager)

        self.is_admin = self.auth.has_permission("admin")
        self.products_data = {}

        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=(6, 6, 6, 6))
        container.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(container, text="Entrada de inventario", padding=(8, 8, 8, 8))
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        right = ttk.LabelFrame(container, text="Stock y valorización", padding=(8, 8, 8, 8))
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        row = 0
        ttk.Label(left, text="Fecha:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.date_entry = DateEntry(left, date_pattern="yyyy-mm-dd", width=14)
        self.date_entry.set_date(datetime.now())
        self.date_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Producto:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.type_cb = ttk.Combobox(left, values=[], width=18, state="readonly")
        self.type_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        self.type_cb.bind("<<ComboboxSelected>>", self._on_type_selected)
        row += 1

        ttk.Label(left, text="Calidad:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.quality_cb = ttk.Combobox(left, values=[], width=18, state="readonly")
        self.quality_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        self.quality_cb.bind("<<ComboboxSelected>>", self._on_combo_change)
        row += 1

        ttk.Label(left, text="Cantidad (bultos):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.qty_entry = ttk.Entry(left)
        self.qty_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Precio de compra (costo):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.purchase_price_entry = ttk.Entry(left)
        self.purchase_price_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Precio de venta (referencia):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.sale_price_entry = ttk.Entry(left)
        self.sale_price_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        self.add_to_cash = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Registrar esta compra en Caja", variable=self.add_to_cash).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 6)
        )
        row += 1

        ttk.Label(left, text="Método de pago:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.payment_method = ttk.Combobox(left, state="readonly", values=tuple(PAY_TO_CODE.keys()), width=18)
        self.payment_method.set("Efectivo")
        self.payment_method.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Proveedor:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.supplier_entry = ttk.Entry(left)
        self.supplier_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Notas:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.notes_entry = ttk.Entry(left)
        self.notes_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        btn = ttk.Frame(left)
        btn.grid(row=row, column=0, columnspan=2, pady=8, sticky=tk.W)
        ttk.Button(btn, text="Guardar entrada", command=self.add_entry).pack(side=tk.LEFT, padx=(0, 6))
        # ttk.Button(btn, text="Gráfico mensual", command=self.show_monthly_chart).pack(side=tk.LEFT)
        row += 1

        lf_sacks = ttk.LabelFrame(left, text="Costales (empaque)", padding=(6, 6, 6, 6))
        lf_sacks.grid(row=row, column=0, columnspan=2, sticky=tk.EW, padx=0, pady=(6, 0))
        row += 1

        r2 = 0
        self.sacks_label = ttk.Label(lf_sacks, text="Stock de costales: 0")
        self.sacks_label.grid(row=r2, column=0, columnspan=5, sticky=tk.W, padx=6, pady=(6, 2))
        r2 += 1

        ttk.Label(lf_sacks, text="Agregar costales:").grid(row=r2, column=0, sticky=tk.W, padx=6, pady=2)
        self.sacks_add_entry = ttk.Entry(lf_sacks, width=10)
        self.sacks_add_entry.grid(row=r2, column=1, sticky=tk.E, padx=(0, 6), pady=2)

        ttk.Label(lf_sacks, text="Precio por costal:").grid(row=r2, column=2, sticky=tk.W, padx=6, pady=2)
        self.sacks_price_entry = ttk.Entry(lf_sacks, width=12)
        self.sacks_price_entry.grid(row=r2, column=3, sticky=tk.E, padx=(0, 6), pady=2)

        self.sacks_register_cash = tk.BooleanVar(value=False)
        ttk.Checkbutton(lf_sacks, text="Registrar compra en Caja", variable=self.sacks_register_cash)\
            .grid(row=r2, column=4, sticky=tk.W, padx=(4, 6), pady=2)
        r2 += 1

        ttk.Button(lf_sacks, text="Agregar costales", command=self.add_sacks_click)\
            .grid(row=r2, column=0, columnspan=2, sticky=tk.W, padx=6, pady=(4, 8))

        ttk.Label(lf_sacks, text="Ajustar stock a:").grid(row=r2, column=2, sticky=tk.E, padx=6, pady=(4, 8))
        self.sacks_set_entry = ttk.Entry(lf_sacks, width=10, state=("normal" if self.is_admin else "disabled"))
        self.sacks_set_entry.grid(row=r2, column=3, sticky=tk.W, padx=(0, 6), pady=(4, 8))
        ttk.Button(lf_sacks, text="Ajustar", command=self.set_sacks_click,
                   state=("normal" if self.is_admin else "disabled"))\
            .grid(row=r2, column=4, sticky=tk.W, padx=6, pady=(4, 8))

        for c in (0, 1): left.grid_columnconfigure(c, weight=1)
        for c in range(5): lf_sacks.grid_columnconfigure(c, weight=1)

        style = ttk.Style()
        style.configure("Inv.Treeview", rowheight=22)
        style.configure("Inv.Treeview.Heading", font=("Segoe UI", 9, "bold"))

        stock_frame = ttk.LabelFrame(right, text="Stock actual")
        stock_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("product_name", "quality", "price", "stock")
        self.stock_tree = ttk.Treeview(stock_frame, columns=cols, show="headings", height=12, style="Inv.Treeview")

        stock_y = ttk.Scrollbar(stock_frame, orient="vertical", command=self.stock_tree.yview)
        stock_x = ttk.Scrollbar(stock_frame, orient="horizontal", command=self.stock_tree.xview)
        self.stock_tree.configure(yscrollcommand=stock_y.set, xscrollcommand=stock_x.set)

        self.stock_tree.grid(row=0, column=0, sticky="nsew")
        stock_y.grid(row=0, column=1, sticky="ns")
        stock_x.grid(row=1, column=0, sticky="ew")

        stock_frame.grid_rowconfigure(0, weight=1)
        stock_frame.grid_columnconfigure(0, weight=1)

        self.stock_tree.heading("product_name", text="Producto")
        self.stock_tree.heading("quality", text="Calidad")
        self.stock_tree.heading("price", text="Precio ref.")
        self.stock_tree.heading("stock", text="Bultos disponibles")

        self.stock_tree.column("product_name", width=160, anchor=tk.W)
        self.stock_tree.column("quality", width=140, anchor=tk.W)
        self.stock_tree.column("price", width=110, anchor=tk.E)
        self.stock_tree.column("stock", width=150, anchor=tk.CENTER)

        self.stock_tree.tag_configure("zero", foreground="gray")
        self.stock_tree.tag_configure("odd", background="#f7f7f7")
        self.stock_tree.bind("<Double-1>", self._on_stock_dblclick)

        actions = ttk.Frame(stock_frame)
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.edit_btn = ttk.Button(actions, text="Editar seleccionado (admin)",
                                   command=self._edit_selected,
                                   state=("normal" if self.is_admin else "disabled"))
        self.edit_btn.pack(side=tk.LEFT)
        
        self.total_label = ttk.Label(stock_frame, text="Total de bultos: 0", font=("Segoe UI", 9, "bold"))
        self.total_label.grid(row=3, column=0, columnspan=2, sticky="e", pady=(6, 0))

        val_frame = ttk.LabelFrame(right, text="Valorización del inventario (simplificada)")
        val_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        vcols = ("product_name", "quality", "stock", "avg_cost", "ref_price", "gain_total")
        self.valuation_tree = ttk.Treeview(val_frame, columns=vcols, show="headings", height=10, style="Inv.Treeview")

        val_y = ttk.Scrollbar(val_frame, orient="vertical", command=self.valuation_tree.yview)
        val_x = ttk.Scrollbar(val_frame, orient="horizontal", command=self.valuation_tree.xview)
        self.valuation_tree.configure(yscrollcommand=val_y.set, xscrollcommand=val_x.set)

        self.valuation_tree.grid(row=0, column=0, sticky="nsew")
        val_y.grid(row=0, column=1, sticky="ns")
        val_x.grid(row=1, column=0, sticky="ew")

        val_frame.grid_rowconfigure(0, weight=1)
        val_frame.grid_columnconfigure(0, weight=1)

        headers = {
            "product_name": "Producto", "quality": "Calidad", "stock": "Bultos",
            "avg_cost": "Costo compra", "ref_price": "Precio venta", "gain_total": "Ganancias Totales"
        }
        widths = {"product_name": 120, "quality": 120, "stock": 80,
                  "avg_cost": 110, "ref_price": 110, "gain_total": 120}
        for c in vcols:
            self.valuation_tree.heading(c, text=headers[c])
            anchor = tk.W
            if c == "stock": anchor = tk.CENTER
            elif c not in ("product_name", "quality"): anchor = tk.E
            self.valuation_tree.column(c, width=widths[c], anchor=anchor)

        self.valuation_tree.tag_configure("odd", background="#f7f7f7")

        ttk.Label(
            right,
            text="Nota: las ventas se registran en la pestaña 'Ventas' y actualizan este stock automáticamente.",
            foreground="gray"
        ).pack(anchor=tk.W, padx=2, pady=(6, 2))

    def _load_product_list(self):
        """Carga los productos y calidades desde el controlador."""
        self.products_data = self.controller.get_all_products()
        product_names = sorted(list(self.products_data.keys()))
        self.type_cb['values'] = product_names
        if product_names:
            self.type_cb.set(product_names[0])
            self._on_type_selected()
        else:
            self.type_cb.set("")
            self.quality_cb.set("")
            self.quality_cb['values'] = []

    def _on_type_selected(self, _evt=None):
        """Al seleccionar un producto, carga sus calidades."""
        selected_product = self.type_cb.get()
        qualities = self.products_data.get(selected_product, [])
        self.quality_cb['values'] = qualities
        if qualities:
            self.quality_cb.set(qualities[0])
        else:
            self.quality_cb.set("")
        self._auto_fill_prices()

    def _on_type_key_release(self, _evt=None):
        current_text = self.type_cb.get()
        if current_text not in self.products_data:
            self.quality_cb['values'] = []
            self.quality_cb.set("")
            self._auto_fill_prices()

    def _on_combo_change(self, _evt=None):
        self._auto_fill_prices()

    def _auto_fill_prices(self):
        t = self.type_cb.get().strip().lower()
        q = self.quality_cb.get().strip().lower()
        if not t or not q: 
            self.purchase_price_entry.delete(0, tk.END)
            self.sale_price_entry.delete(0, tk.END)
            return

        p_buy = self.controller.get_last_purchase_price(t, q)
        self.purchase_price_entry.delete(0, tk.END)
        if p_buy is not None:
            self.purchase_price_entry.insert(0, f"{p_buy:.2f}")

        p_sell = self.controller.get_reference_price(t, q)
        self.sale_price_entry.delete(0, tk.END)
        if p_sell is not None:
            self.sale_price_entry.insert(0, f"{p_sell:.2f}")

    def refresh_all(self):
        self._load_product_list()
        self.refresh_stock_table()
        self.refresh_valuation_table()
        self.refresh_sacks_label()

    def refresh_sacks_label(self):
        try:
            n = self.controller.get_sacks_count()
            self.sacks_label.config(text=f"Stock de costales: {n}")
        except Exception as e:
            self.sacks_label.config(text=f"Stock de costales: ? ({e})")

    def add_sacks_click(self):
        try:
            amount_str = (self.sacks_add_entry.get() or "").strip()
            if not amount_str: raise ValueError("Ingrese la cantidad de costales a agregar.")
            amount = int(amount_str)

            price_str = (self.sacks_price_entry.get() or "").strip()
            price = float(price_str) if price_str else None

            if self.sacks_register_cash.get() and price is None:
                raise ValueError("Ingrese el precio por costal para registrar en Caja.")

            self.controller.add_sacks(amount, price)

            if self.sacks_register_cash.get():
                total = round(amount * price, 2)
                pay_method = PAY_TO_CODE[self.payment_method.get()]
                date = self.date_entry.get_date().strftime("%Y-%m-%d")
                desc = f"Compra de costales ({amount} uds)"
                self.cash.add_transaction(date, "expense", desc, total, pay_method, "empaque")

            self.sacks_add_entry.delete(0, tk.END)
            self.sacks_price_entry.delete(0, tk.END)
            self.sacks_register_cash.set(False)
            self.refresh_sacks_label()
            messagebox.showinfo("Costales", "Costales agregados correctamente.")
        except (ValueError, TypeError) as ve:
            messagebox.showerror("Error de datos", str(ve))
        except Exception as e:
            messagebox.showerror("Error inesperado", str(e))

    def set_sacks_click(self):
        if not self.is_admin:
            messagebox.showerror("Permiso denegado", "Solo el administrador puede ajustar costales.")
            return
        try:
            new_count_str = self.sacks_set_entry.get()
            if not new_count_str: raise ValueError("Ingrese un número entero válido.")
            new_count = int(new_count_str)
            self.controller.set_sacks(new_count)
            self.refresh_sacks_label()
            messagebox.showinfo("Costales", "Stock de costales ajustado.")
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número entero válido.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _reset_form(self):
        self.qty_entry.delete(0, tk.END)
        self.purchase_price_entry.delete(0, tk.END)
        self.sale_price_entry.delete(0, tk.END)
        self.supplier_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)
        self.payment_method.set("Efectivo")
        self.add_to_cash.set(False)
        self._load_product_list()

    def add_entry(self):
        try:
            date = self.date_entry.get_date().strftime("%Y-%m-%d")
            t = self.type_cb.get().strip()
            q = self.quality_cb.get().strip()

            if not t or not q: raise ValueError("Debe ingresar un producto y una calidad.")

            qty_str = (self.qty_entry.get() or "").strip()
            if not qty_str: raise ValueError("Ingrese la cantidad de bultos.")
            qty = int(qty_str)

            p_buy_str = (self.purchase_price_entry.get() or "").strip()
            if not p_buy_str: raise ValueError("Ingrese el precio de compra.")
            p_buy = float(p_buy_str)

            p_sell_str = (self.sale_price_entry.get() or "").strip()
            p_sell = float(p_sell_str) if p_sell_str else 0.0

            supplier = (self.supplier_entry.get() or "").strip()
            notes = (self.notes_entry.get() or "").strip()

            self.controller.add_inventory_record(date, t, q, "entry", qty, p_buy, supplier, notes)
            self.controller.set_reference_price(t, q, p_sell)

            if self.add_to_cash.get():
                total = round(qty * p_buy, 2)
                pay = PAY_TO_CODE[self.payment_method.get()]
                desc = f"Compra {t.capitalize()} {q.capitalize()} ({qty} bultos)"
                self.cash.add_transaction(date, "expense", desc, total, pay, "compra_inventario")

            messagebox.showinfo("Inventario", "Entrada registrada correctamente.")
            self.refresh_all()
            self._reset_form()
        except (ValueError, TypeError) as ve:
            messagebox.showerror("Error de datos", str(ve))
        except Exception as e:
            messagebox.showerror("Error inesperado", str(e))

    def refresh_stock_table(self):
        for item in self.stock_tree.get_children(): self.stock_tree.delete(item)
        rows = self.controller.get_stock_matrix()
        total = 0
        for idx, r in enumerate(rows):
            stock = int(r.get("stock", 0))
            price = float(r.get("price", 0) or 0)
            total += stock
            tags = []
            if stock == 0: tags.append("zero")
            if idx % 2 == 1: tags.append("odd")
            self.stock_tree.insert("", tk.END,
                values=(r.get("product_name"), r.get("quality"), f"{price:.2f}", stock),
                tags=tuple(tags)
            )
        self.total_label.config(text=f"Total de bultos: {total}")

    def refresh_valuation_table(self):
        for item in self.valuation_tree.get_children(): self.valuation_tree.delete(item)
        data = self.controller.get_inventory_valuation()
        for idx, r in enumerate(data):
            stock = int(r["stock"])
            avg_cost = r["avg_cost"]
            ref_price = r["ref_price"]

            if avg_cost is None or ref_price is None:
                gain_text = "-"
            else:
                sack_price = self.controller.get_sack_price()
                gain_total = stock * (ref_price - avg_cost - sack_price)
                gain_text = f"{gain_total:,.2f}"

            self.valuation_tree.insert("", tk.END,
                values=(
                    r["product_name"], r["quality"], stock,
                    "-" if avg_cost is None else f"{avg_cost:,.2f}",
                    "-" if ref_price is None else f"{ref_price:,.2f}",
                    gain_text
                ),
                tags=("odd",) if idx % 2 else ()
            )

    def _on_stock_dblclick(self, _evt):
        if self.is_admin:
            self._edit_selected()

    def _edit_selected(self):
        if not self.is_admin:
            messagebox.showerror("Permiso denegado", "Solo el administrador puede editar.")
            return
        sel = self.stock_tree.selection()
        if not sel:
            messagebox.showwarning("Inventario", "Selecciona una fila para editar.")
            return
        vals = self.stock_tree.item(sel[0], "values")
        product_name, quality, price_str, stock = vals[0], vals[1], vals[2], int(vals[3])

        dlg = tk.Toplevel(self.parent)
        dlg.title(f"Editar {product_name} - {quality}")
        dlg.geometry("360x230")
        dlg.transient(self.parent)
        dlg.grab_set()
        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Producto:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Label(frm, text=product_name).grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(frm, text="Calidad:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Label(frm, text=quality).grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(frm, text="Precio ref. (venta):").grid(row=2, column=0, sticky=tk.W, pady=4)
        price_entry = ttk.Entry(frm, width=18)
        price_entry.insert(0, price_str)
        price_entry.grid(row=2, column=1, sticky=tk.EW, pady=4)

        ttk.Label(frm, text="Bultos (stock):").grid(row=3, column=0, sticky=tk.W, pady=4)
        stock_entry = ttk.Entry(frm, width=18)
        stock_entry.insert(0, str(stock))
        stock_entry.grid(row=3, column=1, sticky=tk.EW, pady=4)

        note_var = tk.StringVar()
        ttk.Label(frm, text="Nota (opcional):").grid(row=4, column=0, sticky=tk.W, pady=4)
        note_entry = ttk.Entry(frm, textvariable=note_var)
        note_entry.grid(row=4, column=1, sticky=tk.EW, pady=4)

        btns = ttk.Frame(frm)
        btns.grid(row=5, column=0, columnspan=2, pady=(10, 0))

        def save_changes():
            try:
                new_price = float(price_entry.get())
                new_stock = int(stock_entry.get())
                if new_price < 0 or new_stock < 0:
                    raise ValueError("Precio y stock deben ser ≥ 0.")
                self.controller.set_reference_price(product_name, quality, new_price)
                if new_stock != stock:
                    self.controller.set_stock_by_admin(product_name, quality, new_stock, note_var.get().strip())
                dlg.destroy()
                self.refresh_all()
                messagebox.showinfo("Inventario", "Cambios guardados.")
            except (ValueError, TypeError) as ve:
                messagebox.showerror("Error de datos", str(ve))
            except Exception as e:
                messagebox.showerror("Error inesperado", str(e))

        ttk.Button(btns, text="Guardar", command=save_changes).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancelar", command=dlg.destroy).pack(side=tk.LEFT, padx=6)
        frm.columnconfigure(1, weight=1)

    # def show_monthly_chart(self):
    #     # La lógica de este gráfico debería adaptarse para manejar múltiples productos.
    #     # Por ahora, se puede dejar comentada para evitar errores.
    #     messagebox.showinfo("Gráfico", "Funcionalidad de gráfico en desarrollo.")
    #     pass