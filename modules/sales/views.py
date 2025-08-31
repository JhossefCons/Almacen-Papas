"""
Vista de Ventas (Tkinter + ttk)
- Selección de tipo/calidad, cantidad
- Precio unitario (autollenado con último precio; editable opcional)
- Método de pago
- Cliente y notas
- Impacta inventario y costales; registra ingreso en caja
"""

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime

from modules.sales.controller import SalesController
from modules.inventory.controller import VALID_COMBOS

PAY_TO_CODE = {"Efectivo": "cash", "Transferencia": "transfer"}
CODE_TO_PAY = {"cash": "Efectivo", "transfer": "Transferencia"}


class SalesView:
    def __init__(self, parent, database, auth_manager, cash_controller):
        self.parent = parent
        self.db = database
        self.auth = auth_manager
        self.controller = SalesController(database, auth_manager, cash_controller)

        self._build_ui()
        self._auto_fill_price()
        self._refresh_stock_labels()

    # ---------------------------
    # UI
    # ---------------------------
    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=8)
        container.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(container, text="Nueva venta")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        right = ttk.LabelFrame(container, text="Disponibilidad")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        row = 0
        ttk.Label(left, text="Fecha:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.date_entry = DateEntry(left, date_pattern="yyyy-mm-dd")
        self.date_entry.set_date(datetime.now())
        self.date_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Tipo de papa:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.type_cb = ttk.Combobox(left, state="readonly", values=tuple(VALID_COMBOS.keys()))
        self.type_cb.set("parda")
        self.type_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        self.type_cb.bind("<<ComboboxSelected>>", self._on_combo_change)
        row += 1

        ttk.Label(left, text="Calidad:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.quality_cb = ttk.Combobox(left, state="readonly")
        self._reload_quality_options("parda")
        self.quality_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        self.quality_cb.bind("<<ComboboxSelected>>", self._on_combo_change)
        row += 1

        ttk.Label(left, text="Cantidad (bultos):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.qty_entry = ttk.Entry(left)
        self.qty_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Precio unitario:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.unit_price_entry = ttk.Entry(left)
        self.unit_price_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        self.manual_price = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            left, text="Editar precio manualmente", variable=self.manual_price,
            command=self._on_manual_price_toggle
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))
        row += 1

        ttk.Label(left, text="Método de pago:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.payment_cb = ttk.Combobox(left, state="readonly", values=tuple(PAY_TO_CODE.keys()))
        self.payment_cb.set("Efectivo")
        self.payment_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        self.add_to_cash = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="Registrar en Caja", variable=self.add_to_cash).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 6)
        )
        row += 1

        ttk.Label(left, text="Cliente:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.customer_entry = ttk.Entry(left)
        self.customer_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Notas:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.notes_entry = ttk.Entry(left)
        self.notes_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        btnf = ttk.Frame(left)
        btnf.grid(row=row, column=0, columnspan=2, pady=8, sticky=tk.W)
        ttk.Button(btnf, text="Registrar venta", command=self._create_sale).pack(side=tk.LEFT)
        row += 1

        # Panel derecha: disponibilidad
        self.stock_label = ttk.Label(right, text="Stock seleccionado: -")
        self.stock_label.pack(anchor=tk.W, pady=(6, 2), padx=8)

        self.sacks_label = ttk.Label(right, text="Costales disponibles: -")
        self.sacks_label.pack(anchor=tk.W, pady=(0, 8), padx=8)

        for c in (0, 1):
            left.grid_columnconfigure(c, weight=1)

        # Por defecto el precio es autollenado (campo bloqueado)
        self._apply_price_state(disable_when_auto=True)

    # ---------------------------
    # Helpers
    # ---------------------------
    def _reload_quality_options(self, potato_type: str):
        values = VALID_COMBOS.get(potato_type.lower(), [])
        self.quality_cb["values"] = tuple(values)
        self.quality_cb.set(values[0] if values else "")

    def _on_combo_change(self, _evt=None):
        self._auto_fill_price()
        self._refresh_stock_labels()

    def _apply_price_state(self, disable_when_auto: bool):
        if disable_when_auto and not self.manual_price.get():
            self.unit_price_entry.config(state="disabled")
        else:
            self.unit_price_entry.config(state="normal")

    def _auto_fill_price(self):
        if self.manual_price.get():
            return
        t = self.type_cb.get().strip().lower()
        q = self.quality_cb.get().strip().lower()
        price = self.controller.get_last_sale_price(t, q)

        self.unit_price_entry.config(state="normal")
        self.unit_price_entry.delete(0, tk.END)
        if price is not None:
            self.unit_price_entry.insert(0, str(price))
        else:
            self.unit_price_entry.insert(0, "")
        self._apply_price_state(disable_when_auto=True)

    def _on_manual_price_toggle(self):
        if self.manual_price.get():
            self._apply_price_state(disable_when_auto=False)
            self.unit_price_entry.focus()
            self.unit_price_entry.select_range(0, tk.END)
        else:
            self._auto_fill_price()

    def _refresh_stock_labels(self):
        try:
            t = self.type_cb.get().strip().lower()
            q = self.quality_cb.get().strip().lower()
            stock = self.controller.get_stock(t, q)
            sacks = self.controller.get_sacks()
            self.stock_label.config(text=f"Stock seleccionado: {stock} bultos")
            self.sacks_label.config(text=f"Costales disponibles: {sacks}")
        except Exception as e:
            self.stock_label.config(text=f"Stock seleccionado: ? ({e})")

    def _reset_form(self):
        self.qty_entry.delete(0, tk.END)
        self.customer_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)
        self.payment_cb.set("Efectivo")
        self.add_to_cash.set(True)
        self.manual_price.set(False)
        self._auto_fill_price()
        self._apply_price_state(disable_when_auto=True)

    # ---------------------------
    # Acción
    # ---------------------------
    def _create_sale(self):
        try:
            date = self.date_entry.get_date().strftime("%Y-%m-%d")
            t = self.type_cb.get().strip().lower()
            q = self.quality_cb.get().strip().lower()

            qty_str = self.qty_entry.get().strip()
            if not qty_str:
                raise ValueError("Ingrese la cantidad.")
            qty = int(qty_str)

            price_str = self.unit_price_entry.get().strip()
            if price_str == "":
                raise ValueError("Ingrese el precio unitario (o desmarque 'Editar precio' para autollenar).")
            price = float(price_str)

            pay = PAY_TO_CODE[self.payment_cb.get()]
            customer = self.customer_entry.get().strip()
            notes = self.notes_entry.get().strip()
            register_cash = self.add_to_cash.get()

            self.controller.create_sale(
                date=date,
                potato_type=t,
                quality=q,
                quantity=qty,
                sale_unit_price=price,
                payment_method=pay,
                customer=customer,
                notes=notes,
                register_cash=register_cash,
            )

            messagebox.showinfo("Venta", "Venta registrada correctamente.")
            self._refresh_stock_labels()
            self._reset_form()
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", str(e))
