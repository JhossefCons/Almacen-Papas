# modules/payroll/views.py
"""
Vista de Nómina mensual
- Seleccionar año/mes
- Ver por empleado: salario bruto, deducción préstamo, neto (calculado), neto en Caja, diferencia, #préstamos
- Manejo de "sin datos" y errores para que el botón Generar siempre muestre un resultado visible
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from modules.payroll.controller import PayrollController


class PayrollReportView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth = auth_manager
        self.controller = PayrollController(database, auth_manager)

        self._build_ui()
        self.refresh_report()

    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(container)
        top.pack(fill=tk.X, pady=(0, 8))

        # Año / Mes
        ttk.Label(top, text="Año:").pack(side=tk.LEFT)
        years = [str(y) for y in range(datetime.now().year - 3, datetime.now().year + 2)]
        self.year_cb = ttk.Combobox(top, state="readonly", values=years, width=6)
        self.year_cb.set(str(datetime.now().year))
        self.year_cb.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(top, text="Mes:").pack(side=tk.LEFT)
        months = [
            "01 - Enero","02 - Febrero","03 - Marzo","04 - Abril","05 - Mayo","06 - Junio",
            "07 - Julio","08 - Agosto","09 - Septiembre","10 - Octubre","11 - Noviembre","12 - Diciembre"
        ]
        self.month_cb = ttk.Combobox(top, state="readonly", values=months, width=16)
        self.month_cb.set(months[datetime.now().month-1])
        self.month_cb.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Button(top, text="Generar", command=self.refresh_report).pack(side=tk.LEFT)
        ttk.Button(top, text="Actualizar", command=self.refresh_report).pack(side=tk.LEFT, padx=(6,0))

        # Tabla
        columns = ("name","gross","deduct","net_calc","net_cash","diff","loans_count")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", height=18)
        headers = {
            "name":"Empleado", "gross":"Salario bruto", "deduct":"Deducción préstamos",
            "net_calc":"Neto (calc.)", "net_cash":"Neto en Caja", "diff":"Diferencia", "loans_count":"#Préstamos"
        }
        widths = {"name":220,"gross":120,"deduct":150,"net_calc":110,"net_cash":120,"diff":100,"loans_count":100}
        for c in columns:
            self.tree.heading(c, text=headers[c])
            anchor = tk.W if c in ("name",) else (tk.CENTER if c=="loans_count" else tk.E)
            self.tree.column(c, width=widths[c], anchor=anchor)

        ysb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        xsb.pack(fill=tk.X)

        self.total_lbl = ttk.Label(container, text="Totales: ", font=('Segoe UI', 9, 'bold'))
        self.total_lbl.pack(anchor=tk.E, pady=(6,0))

        self.status_lbl = ttk.Label(container, text="", foreground="#555")
        self.status_lbl.pack(anchor=tk.W, pady=(2,0))

        # estilo visual para diferencias
        self.tree.tag_configure("mismatch", background="#fff1c1")  # amarillo suave

    # públicos (lo llama MainWindow al cambiar de pestaña/F5)
    def refresh_all(self):
        self.refresh_report()

    def _parse_year_month(self):
        # Año
        try:
            year = int(self.year_cb.get())
        except Exception:
            year = datetime.now().year
        # Mes
        try:
            month = int((self.month_cb.get() or "01").split(" - ",1)[0])
        except Exception:
            month = datetime.now().month
        return year, month

    def _set_status(self, text):
        self.status_lbl.config(text=text)

    def refresh_report(self):
        # Limpia tabla siempre, para que haya feedback inmediato
        for i in self.tree.get_children():
            self.tree.delete(i)

        year, month = self._parse_year_month()
        ym_str = f"{year}-{month:02d}"

        try:
            data, totals = self.controller.get_month_report(year, month)

            if not data:
                # No hay empleados… informamos claramente
                self.total_lbl.config(text="Totales: (sin empleados)")
                self._set_status(f"No hay empleados para mostrar en {ym_str}.")
                # Insertamos una fila placeholder para que el usuario vea algo
                self.tree.insert("", tk.END, values=("— Sin empleados —","","","","","",""))
                return

            # Rellenar tabla
            any_rows = False
            for d in data:
                any_rows = True
                tags = ("mismatch",) if abs(d["diff"]) > 0.01 else ()
                self.tree.insert("", tk.END, values=(
                    d["name"], f"${d['gross']:.2f}", f"${d['deduct']:.2f}",
                    f"${d['net_calc']:.2f}", f"${d['net_cash']:.2f}",
                    f"${d['diff']:.2f}", d["loans_count"]
                ), tags=tags)

            if not any_rows:
                self.tree.insert("", tk.END, values=("— Sin datos —","","","","","",""))
                self._set_status(f"Sin datos de nómina para {ym_str}.")

            self.total_lbl.config(
                text=f"Totales: Bruto=${totals['gross'] :.2f} | Deducciones=${totals['deduct']:.2f} | "
                     f"Neto(calc)=${totals['net_calc']:.2f} | Neto(Caja)=${totals['net_cash']:.2f} | "
                     f"Diferencia=${totals['diff']:.2f}"
            )
            self._set_status(f"Reporte generado para {ym_str}. Empleados: {len(data)}.")

        except Exception as e:
            # Mostramos error y un placeholder
            messagebox.showerror("Nómina", f"Ocurrió un error al generar el reporte:\n{e}")
            self.tree.insert("", tk.END, values=("— Error —","","","","","",""))
            self.total_lbl.config(text="Totales: (error)")
            self._set_status("No se pudo generar el reporte.")
