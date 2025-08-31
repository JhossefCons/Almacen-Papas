# modules/inventory/views.py
"""
Inventario de Papas (stock + entradas)
- Formulario de ENTRADAS con Precio de compra (costo) + Precio de venta (referencia).
- Si se registra en Caja, usa el precio de compra.
- Tabla superior: STOCK actual (incluye 0) con Precio ref.
- Tabla inferior: VALORIZACIÓN del inventario (costo promedio, valor a costo, valor potencial, margen).
- Edición admin: ajustar precio ref. y stock total (como antes).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime

from modules.inventory.controller import InventoryController, VALID_COMBOS
from modules.cash_register.controller import CashRegisterController

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

        self._build_ui()
        self.refresh_stock_table()
        self.refresh_valuation_table()
        self.refresh_sacks_label()
        self._auto_fill_prices()  # inicial

    # ------------------------------
    # UI
    # ------------------------------
    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=(6, 6, 6, 6))
        container.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(container, text="Entrada de inventario", padding=(8, 8, 8, 8))
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        right = ttk.LabelFrame(container, text="Stock actual y valorización", padding=(8, 8, 8, 8))
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        row = 0
        ttk.Label(left, text="Fecha:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.date_entry = DateEntry(left, date_pattern="yyyy-mm-dd", width=14)
        self.date_entry.set_date(datetime.now())
        self.date_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Tipo de papa:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.type_cb = ttk.Combobox(left, state="readonly", values=tuple(VALID_COMBOS.keys()), width=18)
        self.type_cb.set("parda")
        self.type_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        self.type_cb.bind("<<ComboboxSelected>>", self._on_combo_change)
        row += 1

        ttk.Label(left, text="Calidad:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.quality_cb = ttk.Combobox(left, state="readonly", width=18)
        self._reload_quality_options("parda")
        self.quality_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        self.quality_cb.bind("<<ComboboxSelected>>", self._on_combo_change)
        row += 1

        ttk.Label(left, text="Cantidad (bultos):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.qty_entry = ttk.Entry(left)
        self.qty_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        # -------- Precios --------
        ttk.Label(left, text="Precio de compra (costo):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.purchase_price_entry = ttk.Entry(left)
        self.purchase_price_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Precio de venta (referencia):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.sale_price_entry = ttk.Entry(left)
        self.sale_price_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        # Registrar compras en caja (OPCIONAL)
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
        ttk.Button(btn, text="Gráfico mensual", command=self.show_monthly_chart).pack(side=tk.LEFT)
        row += 1

        # ----------------- Costales -----------------
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

        for c in (0, 1):
            left.grid_columnconfigure(c, weight=1)
        for c in range(5):
            lf_sacks.grid_columnconfigure(c, weight=1)

        # ----------------- Panel derecho: 2 tablas -----------------
        style = ttk.Style()
        style.configure("Inv.Treeview", rowheight=22)
        style.configure("Inv.Treeview.Heading", font=("Segoe UI", 9, "bold"))

        # STOCK
        stock_frame = ttk.LabelFrame(right, text="Stock actual")
        stock_frame.pack(fill=tk.BOTH, expand=True)
        cols = ("potato_type", "quality", "price", "stock")
        self.stock_tree = ttk.Treeview(stock_frame, columns=cols, show="headings", height=12, style="Inv.Treeview")
        self.stock_tree.pack(fill=tk.BOTH, expand=True)

        self.stock_tree.heading("potato_type", text="Tipo")
        self.stock_tree.heading("quality", text="Calidad")
        self.stock_tree.heading("price", text="Precio venta.")
        self.stock_tree.heading("stock", text="Bultos disponibles")

        self.stock_tree.column("potato_type", width=160, anchor=tk.W)
        self.stock_tree.column("quality", width=140, anchor=tk.W)
        self.stock_tree.column("price", width=110, anchor=tk.E)
        self.stock_tree.column("stock", width=150, anchor=tk.CENTER)

        self.stock_tree.tag_configure("zero", foreground="gray")
        self.stock_tree.tag_configure("odd", background="#f7f7f7")
        self.stock_tree.bind("<Double-1>", self._on_stock_dblclick)

        actions = ttk.Frame(stock_frame)
        actions.pack(fill=tk.X, pady=(6, 0))
        self.edit_btn = ttk.Button(actions, text="Editar seleccionado (admin)",
                                   command=self._edit_selected,
                                   state=("normal" if self.is_admin else "disabled"))
        self.edit_btn.pack(side=tk.LEFT)

        self.total_label = ttk.Label(stock_frame, text="Total de bultos: 0", font=("Segoe UI", 9, "bold"))
        self.total_label.pack(anchor=tk.E, pady=(6, 0))

        # VALORIZACIÓN
        val_frame = ttk.LabelFrame(right, text="Valorización del inventario")
        val_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        vcols = ("potato_type", "quality", "stock", "avg_cost", "cost_value", "ref_price",
                 "potential_revenue")
        self.valuation_tree = ttk.Treeview(val_frame, columns=vcols, show="headings", height=10, style="Inv.Treeview")
        self.valuation_tree.pack(fill=tk.BOTH, expand=True)

        headers = {
            "potato_type": "Tipo",
            "quality": "Calidad",
            "stock": "Bultos",
            "avg_cost": "Costo compra",
            "cost_value": "Costo total",
            "ref_price": "Precio venta",
            "potential_revenue": "Valor potencial"
        }
        widths = {
            "potato_type": 90, "quality": 90, "stock": 70, "avg_cost": 100, "cost_value": 120,
            "ref_price": 90, "potential_revenue": 120
        }
        for c in vcols:
            self.valuation_tree.heading(c, text=headers[c])
            self.valuation_tree.column(c, width=widths[c],
                                       anchor=tk.W if c in ("potato_type", "quality") else (tk.CENTER if c=="stock" else tk.E))

        self.valuation_tree.tag_configure("odd", background="#f7f7f7")

        ttk.Label(right,
                  text="Nota: las ventas se registran en la pestaña 'Ventas' y actualizan este stock automáticamente.",
                  foreground="gray").pack(anchor=tk.W, padx=2, pady=(6, 2))

    # ------------------------------
    # Helpers
    # ------------------------------
    def _reload_quality_options(self, potato_type: str):
        values = VALID_COMBOS.get(potato_type.lower(), [])
        self.quality_cb["values"] = tuple(values)
        self.quality_cb.set(values[0] if values else "")

    def _on_combo_change(self, _evt=None):
        self._auto_fill_prices()

    def _auto_fill_prices(self):
        """Autollenado de precios: compra (último costo) y venta (precio ref.)."""
        t = self.type_cb.get().strip().lower()
        q = self.quality_cb.get().strip().lower()
        # compra
        p_buy = self.controller.get_last_purchase_price(t, q)
        self.purchase_price_entry.delete(0, tk.END)
        if p_buy is not None:
            self.purchase_price_entry.insert(0, f"{p_buy:.2f}")
        # venta ref.
        p_sell = self.controller.get_reference_price(t, q)
        self.sale_price_entry.delete(0, tk.END)
        if p_sell is not None:
            self.sale_price_entry.insert(0, f"{p_sell:.2f}")

    # ------------------------------
    # Costales
    # ------------------------------
    def refresh_sacks_label(self):
        try:
            n = self.controller.get_sacks_count()
            self.sacks_label.config(text=f"Stock de costales: {n}")
        except Exception as e:
            self.sacks_label.config(text=f"Stock de costales: ? ({e})")

    def add_sacks_click(self):
        try:
            amount = int((self.sacks_add_entry.get() or "").strip())
            price_str = (self.sacks_price_entry.get() or "").strip()
            if amount <= 0:
                raise ValueError("La cantidad de costales debe ser positiva.")

            if self.sacks_register_cash.get():
                if not price_str:
                    raise ValueError("Ingrese el precio por costal para registrar en Caja.")
                unit_price = float(price_str)
                if unit_price < 0:
                    raise ValueError("El precio por costal no puede ser negativo.")
            else:
                unit_price = float(price_str) if price_str else 0.0
                if unit_price < 0:
                    raise ValueError("El precio por costal no puede ser negativo.")

            self.controller.add_sacks(amount)

            if self.sacks_register_cash.get():
                total = round(amount * unit_price, 2)
                pay_method = PAY_TO_CODE[self.payment_method.get()]
                date = self.date_entry.get_date().strftime("%Y-%m-%d")
                desc = f"Compra de costales ({amount} uds)"
                self.cash.add_transaction(date, "expense", desc, total, pay_method, "empaque")

            self.sacks_add_entry.delete(0, tk.END)
            self.sacks_price_entry.delete(0, tk.END)
            self.sacks_register_cash.set(False)
            self.refresh_sacks_label()
            messagebox.showinfo("Costales", "Costales agregados correctamente.")
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def set_sacks_click(self):
        if not self.is_admin:
            messagebox.showerror("Permiso denegado", "Solo el administrador puede ajustar costales.")
            return
        try:
            new_count = int(self.sacks_set_entry.get())
            self.controller.set_sacks(new_count)
            self.refresh_sacks_label()
            messagebox.showinfo("Costales", "Stock de costales ajustado.")
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número entero válido.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ------------------------------
    # Entradas & tablas
    # ------------------------------
    def _reset_form(self):
        self.qty_entry.delete(0, tk.END)
        self.purchase_price_entry.delete(0, tk.END)
        self.sale_price_entry.delete(0, tk.END)
        self.supplier_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)
        self.payment_method.set("Efectivo")
        self.add_to_cash.set(False)
        self._auto_fill_prices()

    def add_entry(self):
        try:
            date = self.date_entry.get_date().strftime("%Y-%m-%d")
            t = self.type_cb.get().strip().lower()
            q = self.quality_cb.get().strip().lower()

            qty = int((self.qty_entry.get() or "").strip())
            if qty <= 0:
                raise ValueError("Ingrese la cantidad de bultos (>0).")

            p_buy = float((self.purchase_price_entry.get() or "").strip())
            if p_buy < 0:
                raise ValueError("El precio de compra debe ser ≥ 0.")

            p_sell = float((self.sale_price_entry.get() or "").strip()) if (self.sale_price_entry.get() or "").strip() != "" else 0.0
            if p_sell < 0:
                raise ValueError("El precio de venta debe ser ≥ 0.")

            supplier = (self.supplier_entry.get() or "").strip()
            notes = (self.notes_entry.get() or "").strip()

            # Registrar ENTRADA con precio de compra
            self.controller.add_inventory_record(
                date, t, q, "entry", qty, p_buy, supplier, notes
            )

            # Actualizar precio de venta de referencia
            if self.is_admin:
                self.controller.set_reference_price(t, q, p_sell)

            # Registrar en Caja (gasto) usando precio de compra
            if self.add_to_cash.get():
                total = round(qty * p_buy, 2)
                pay = PAY_TO_CODE[self.payment_method.get()]
                desc = f"Compra {t} {q} ({qty} bultos)"
                self.cash.add_transaction(date, "expense", desc, total, pay, "compra_inventario")

            messagebox.showinfo("Inventario", "Entrada registrada correctamente.")
            self.refresh_stock_table()
            self.refresh_valuation_table()
            self._reset_form()
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh_stock_table(self):
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)

        rows = self.controller.get_stock_matrix()
        total = 0
        for idx, r in enumerate(rows):
            stock = int(r.get("stock", 0))
            price = float(r.get("price", 0) or 0)
            total += stock
            tags = []
            if stock == 0:
                tags.append("zero")
            if idx % 2 == 1:
                tags.append("odd")
            self.stock_tree.insert("", tk.END,
                                   values=(r.get("potato_type"), r.get("quality"), f"{price:.2f}", stock),
                                   tags=tuple(tags))
        self.total_label.config(text=f"Total de bultos: {total}")

    def refresh_valuation_table(self):
        for item in self.valuation_tree.get_children():
            self.valuation_tree.delete(item)

        rows = self.controller.get_inventory_valuation()
        for idx, r in enumerate(rows):
            avg_cost = r["avg_cost"]
            ref_price = r["ref_price"]
            self.valuation_tree.insert(
                "", tk.END,
                values=(
                    r["potato_type"], r["quality"], r["stock"],
                    "-" if avg_cost is None else f"{avg_cost:.2f}",
                    f"{float(r['cost_value']):.2f}",
                    "-" if ref_price is None else f"{ref_price:.2f}",
                    f"{float(r['potential_revenue']):.2f}",
                    f"{float(r['potential_margin']):.2f}"
                ),
                tags=("odd",) if idx % 2 else ()
            )

    # ------------------------------
    # Edición admin (stock / precio ref.)
    # ------------------------------
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
        potato_type, quality, price_str, stock = vals[0], vals[1], vals[2], int(vals[3])

        dlg = tk.Toplevel(self.parent)
        dlg.title(f"Editar {potato_type} - {quality}")
        dlg.geometry("360x230")
        dlg.transient(self.parent)
        dlg.grab_set()

        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Tipo:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Label(frm, text=potato_type).grid(row=0, column=1, sticky=tk.W, pady=4)

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

                self.controller.set_reference_price(potato_type, quality, new_price)
                if new_stock != stock:
                    self.controller.set_stock_by_admin(potato_type, quality, new_stock, note_var.get().strip())

                dlg.destroy()
                self.refresh_stock_table()
                self.refresh_valuation_table()
                messagebox.showinfo("Inventario", "Cambios guardados.")
            except ValueError as ve:
                messagebox.showerror("Error", str(ve))
            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(btns, text="Guardar", command=save_changes).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancelar", command=dlg.destroy).pack(side=tk.LEFT, padx=6)
        frm.columnconfigure(1, weight=1)

    # ------------------------------
    # Gráfico (compras/ventas por mes)
    # ------------------------------
    def show_monthly_chart(self):
        data = self.controller.get_monthly_summary()
        if not data:
            messagebox.showinfo("Gráfico mensual", "No hay datos para el año seleccionado.")
            return
        months = [d["month"] for d in data]
        incomes = [float(d["total_income"] or 0) for d in data]
        expenses = [float(d["total_expense"] or 0) for d in data]

        plt.figure()
        x = list(range(len(months)))
        plt.bar([i - 0.2 for i in x], incomes, width=0.4, label="Ventas (salidas)")
        plt.bar([i + 0.2 for i in x], expenses, width=0.4, label="Compras (entradas)")
        plt.xticks(x, months, rotation=45, ha="right")
        plt.title("Resumen mensual")
        plt.xlabel("Mes")
        plt.ylabel("Monto")
        plt.legend()
        plt.tight_layout()
        plt.show()
