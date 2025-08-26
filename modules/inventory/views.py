"""
Vista de Inventario de Papas (Tkinter + ttk)
- Un solo TreeView (evita “doble carga”)
- Checkbox “Registrar en Caja”
- Método de pago (cash/transfer)
- Auto-registro en Caja por venta/compra
- Gráfico mensual compras vs ventas
"""

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime

# Controladores
from modules.inventory.controller import InventoryController
from modules.cash_register.controller import CashRegisterController

# Si usas matplotlib para el gráfico mensual:
import matplotlib
matplotlib.use("TkAgg")
from matplotlib import pyplot as plt


class InventoryView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth = auth_manager

        self.controller = InventoryController(database, auth_manager)
        self.cash = CashRegisterController(database, auth_manager)

        self._build_ui()
        self.refresh_table()

    # ---------------------------------
    # UI
    # ---------------------------------
    def _build_ui(self):
        container = ttk.Frame(self.parent)
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left = ttk.LabelFrame(container, text="Movimiento")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        right = ttk.Frame(container)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Formulario ---
        row = 0
        ttk.Label(left, text="Fecha:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.date_entry = DateEntry(left, date_pattern="yyyy-mm-dd")
        self.date_entry.set_date(datetime.now())
        self.date_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Tipo Papa:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.type_entry = ttk.Entry(left)
        self.type_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Calidad:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.quality_entry = ttk.Entry(left)
        self.quality_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Operación:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.operation = ttk.Combobox(left, state="readonly", values=("entry", "exit"), width=14)
        self.operation.set("entry")
        self.operation.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Cantidad (bultos):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.qty_entry = ttk.Entry(left)
        self.qty_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Precio Unitario:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.unit_price_entry = ttk.Entry(left)
        self.unit_price_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Método Pago:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.payment_method = ttk.Combobox(left, state="readonly", values=("cash", "transfer"))
        self.payment_method.set("cash")
        self.payment_method.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        self.add_to_cash = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="Registrar en Caja", variable=self.add_to_cash).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(6, 2)
        )
        row += 1

        ttk.Label(left, text="Proveedor/Cliente:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.supplier_entry = ttk.Entry(left)
        self.supplier_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Notas:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.notes_entry = ttk.Entry(left)
        self.notes_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        btn = ttk.Frame(left)
        btn.grid(row=row, column=0, columnspan=2, pady=8)
        ttk.Button(btn, text="Guardar movimiento", command=self.add_inventory_record).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn, text="Gráfico mensual", command=self.show_monthly_chart).pack(side=tk.LEFT)

        for c in (0, 1):
            left.grid_columnconfigure(c, weight=1)

        # --- Tabla (un solo TreeView) ---
        cols = (
            "id",
            "date",
            "potato_type",
            "quality",
            "operation",
            "quantity",
            "unit_price",
            "total_value",
            "supplier_customer",
            "notes",
            "created_by",
        )
        self.inventory_tree = ttk.Treeview(right, columns=cols, show="headings", height=18)
        self.inventory_tree.pack(fill=tk.BOTH, expand=True)

        headings = {
            "id": "ID",
            "date": "Fecha",
            "potato_type": "Tipo",
            "quality": "Calidad",
            "operation": "Operación",
            "quantity": "Bultos",
            "unit_price": "Precio U.",
            "total_value": "Total",
            "supplier_customer": "Proveedor/Cliente",
            "notes": "Notas",
            "created_by": "Usuario",
        }
        widths = {
            "id": 60,
            "date": 90,
            "potato_type": 110,
            "quality": 90,
            "operation": 90,
            "quantity": 80,
            "unit_price": 90,
            "total_value": 90,
            "supplier_customer": 160,
            "notes": 180,
            "created_by": 100,
        }

        for c in cols:
            self.inventory_tree.heading(c, text=headings[c])
            self.inventory_tree.column(c, width=widths[c], anchor=tk.CENTER if c in ("id", "quantity") else tk.W)

    # ---------------------------------
    # Acciones
    # ---------------------------------
    def add_inventory_record(self):
        try:
            date = self.date_entry.get_date().strftime("%Y-%m-%d")
            potato_type = self.type_entry.get().strip()
            quality = self.quality_entry.get().strip()
            operation = self.operation.get()
            quantity = int(self.qty_entry.get())
            unit_price = float(self.unit_price_entry.get())
            supplier = self.supplier_entry.get().strip()
            notes = self.notes_entry.get().strip()

            # Insertar en inventario
            self.controller.add_inventory_record(
                date, potato_type, quality, operation, quantity, unit_price, supplier, notes
            )

            # Reflejar en Caja (si aplica)
            if self.add_to_cash.get():
                total = round(quantity * unit_price, 2)
                pay = self.payment_method.get()
                if operation == "exit":
                    desc = f"Venta {potato_type} {quality} ({quantity} bultos)"
                    # income
                    self.cash.add_transaction(date, "income", desc, total, pay, "venta")
                else:
                    desc = f"Compra {potato_type} {quality} ({quantity} bultos)"
                    # expense
                    self.cash.add_transaction(date, "expense", desc, total, pay, "compra_inventario")

            messagebox.showinfo("Éxito", "Movimiento registrado correctamente")
            self.refresh_table()

        except ValueError:
            messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh_table(self):
        for item in self.inventory_tree.get_children():
            self.inventory_tree.delete(item)

        rows = self.controller.get_inventory_records(limit=500)
        for r in rows:
            values = (
                r.get("id"),
                r.get("date"),
                r.get("potato_type"),
                r.get("quality"),
                r.get("operation"),
                r.get("quantity"),
                r.get("unit_price"),
                r.get("total_value"),
                r.get("supplier_customer"),
                r.get("notes"),
                r.get("created_by"),
            )
            self.inventory_tree.insert("", tk.END, values=values)

    # ---------------------------------
    # Gráfico
    # ---------------------------------
    def show_monthly_chart(self):
        data = self.controller.get_monthly_summary()
        if not data:
            messagebox.showinfo("Gráfico mensual", "No hay datos para el año seleccionado.")
            return

        months = [d["month"] for d in data]
        incomes = [float(d["total_income"] or 0) for d in data]
        expenses = [float(d["total_expense"] or 0) for d in data]

        # Gráfico simple de barras
        plt.figure()
        x = list(range(len(months)))
        plt.bar([i - 0.2 for i in x], incomes, width=0.4, label="Ingresos (ventas)")
        plt.bar([i + 0.2 for i in x], expenses, width=0.4, label="Egresos (compras)")
        plt.xticks(x, months, rotation=45, ha="right")
        plt.title("Resumen mensual")
        plt.xlabel("Mes")
        plt.ylabel("Monto")
        plt.legend()
        plt.tight_layout()
        plt.show()
