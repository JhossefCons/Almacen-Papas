"""
Vista de Nómina mensual
- Seleccionar año/mes
- Ver por empleado: salario bruto, deducción préstamos, neto (calc.), neto en Caja, diferencia, #préstamos
- Exportar PDF
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime
from modules.payroll.controller import PayrollController

PAY_TO_CODE = {"Efectivo": "cash", "Transferencia": "transfer"}


class PayrollReportView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth = auth_manager
        self.controller = PayrollController(database, auth_manager)

        self._build_ui()
        self.refresh_report()
        self._load_employees_combo()


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
        ttk.Button(top, text="Exportar PDF", command=self.export_pdf).pack(side=tk.LEFT, padx=(6,0))

        pay_frame = ttk.LabelFrame(container, text="Pago de salario", padding=8)
        pay_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(pay_frame, text="Empleado:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.emp_cb = ttk.Combobox(pay_frame, state="readonly", width=28)
        self.emp_cb.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 12))

        ttk.Label(pay_frame, text="Fecha pago:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.pay_date = DateEntry(pay_frame, date_pattern='yyyy-mm-dd')
        self.pay_date.set_date(datetime.now())
        self.pay_date.grid(row=0, column=3, sticky=tk.EW, pady=2, padx=(5, 12))

        ttk.Label(pay_frame, text="Método:").grid(row=0, column=4, sticky=tk.W, pady=2)
        self.pay_method = ttk.Combobox(pay_frame, state="readonly", values=tuple(PAY_TO_CODE.keys()), width=16)
        self.pay_method.set("Efectivo")
        self.pay_method.grid(row=0, column=5, sticky=tk.EW, pady=2, padx=(5, 0))

        self.chk_register_cash = tk.BooleanVar(value=True)
        ttk.Checkbutton(pay_frame, text="Registrar en Caja", variable=self.chk_register_cash)\
            .grid(row=1, column=0, columnspan=2, sticky=tk.W)

        self.chk_with_deduction = tk.BooleanVar(value=True)
        ttk.Checkbutton(pay_frame, text="Deducir préstamos del empleado", variable=self.chk_with_deduction)\
            .grid(row=1, column=2, columnspan=2, sticky=tk.W)

        ttk.Button(pay_frame, text="Pagar salario", command=self._do_pay_salary)\
            .grid(row=1, column=5, sticky=tk.E, padx=(8, 0))

        for c in (1,3,5):
            pay_frame.columnconfigure(c, weight=1)

        # Tabla
        columns = ("name","gross","deduct","net_calc","loans_count")
        headers = {
            "name":"Empleado", "gross":"Salario bruto", "deduct":"Deducción préstamos",
            "net_calc":"Neto (calc.)", "loans_count":"#Préstamos"
        }
        widths = {"name":220,"gross":120,"deduct":150,"net_calc":110,"loans_count":100}

        # 1) Crear Treeview
        self.tree = ttk.Treeview(container, columns=columns, show="headings", height=12)

        # 2) Configurar headings/columns
        for c in columns:
            self.tree.heading(c, text=headers[c])
            anchor = tk.W if c == "name" else (tk.CENTER if c == "loans_count" else tk.E)
            self.tree.column(c, width=widths[c], anchor=anchor)

        # 3) Scrollbars
        ysb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        # 4) Empaquetar
        self.tree.pack(fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        xsb.pack(fill=tk.X)

        self.total_lbl = ttk.Label(container, text="Totales: ", font=('Segoe UI', 9, 'bold'))
        self.total_lbl.pack(anchor=tk.E, pady=(6,0))

        self.status_lbl = ttk.Label(container, text="", foreground="#555")
        self.status_lbl.pack(anchor=tk.W, pady=(2,0))

        self.tree.tag_configure("mismatch", background="#fff1c1")  # amarillo suave

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
        try:
            year = int(self.year_cb.get())
        except Exception:
            year = datetime.now().year
        try:
            month = int((self.month_cb.get() or "01").split(" - ",1)[0])
        except Exception:
            month = datetime.now().month
        return year, month

    def _set_status(self, text):
        self.status_lbl.config(text=text)

    def refresh_report(self):
        # limpiar tabla
        for i in self.tree.get_children():
            self.tree.delete(i)

        year, month = self._parse_year_month()
        ym_str = f"{year}-{month:02d}"

        try:
            data, totals = self.controller.get_month_report(year, month)

            if not data:
                self.total_lbl.config(text="Totales: (sin empleados)")
                self._set_status(f"No hay empleados para mostrar en {ym_str}.")
                # 5 columnas
                self.tree.insert("", tk.END, values=("— Sin empleados —","","","",""))
                return

            any_rows = False
            for d in data:
                any_rows = True
                # Ya no existe 'diff' en la vista
                self.tree.insert("", tk.END, values=(
                    d["name"],
                    f"${float(d['gross']):.2f}",
                    f"${float(d['deduct']):.2f}",
                    f"${float(d['net_calc']):.2f}",
                    d["loans_count"]
                ))

            if not any_rows:
                self.tree.insert("", tk.END, values=("— Sin datos —","","","",""))
                self._set_status(f"Sin datos de nómina para {ym_str}.")

            self.total_lbl.config(
                text=(
                    f"Totales: Bruto=${float(totals['gross']):.2f} | "
                    f"Deducciones=${float(totals['deduct']):.2f} | "
                    f"Neto(calc)=${float(totals['net_calc']):.2f}"
                )
            )
            self._set_status(f"Reporte generado para {ym_str}. Empleados: {len(data)}.")

        except Exception as e:
            messagebox.showerror("Nómina", f"Ocurrió un error al generar el reporte:\n{e}")
            self.tree.insert("", tk.END, values=("— Error —","","","",""))
            self.total_lbl.config(text="Totales: (error)")
            self._set_status("No se pudo generar el reporte.")


    def export_pdf(self):
        """Exporta a PDF el reporte del mes seleccionado."""
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            messagebox.showerror("Falta dependencia", "Para generar PDF necesitas instalar reportlab:\n\npip install reportlab")
            return

        # Tomar datos actuales del controlador para evitar depender de lo que esté renderizado
        year, month = self._parse_year_month()
        data, totals = self.controller.get_month_report(year, month)

        if not data:
            messagebox.showwarning("Nómina", "No hay datos para exportar en el período seleccionado.")
            return

        default_name = f"reporte_nomina_{year}{month:02d}.pdf"
        path = filedialog.asksaveasfilename(
            title="Guardar reporte como",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF","*.pdf")]
        )
        if not path:
            return

        try:
            doc = SimpleDocTemplate(
                path, pagesize=landscape(A4),
                leftMargin=18, rightMargin=18, topMargin=18, bottomMargin=22
            )
            styles = getSampleStyleSheet()
            title = Paragraph("<b>Reporte de Nómina</b>", styles['Title'])
            meta = Paragraph(
                f"Período: <b>{year}-{month:02d}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                styles['Normal']
            )

            table_data = [["Empleado","Salario Bruto","Deducción Préstamos","Neto (calc.)","#Préstamos"]]
            for r in data:
                table_data.append([
                    r["name"],
                    f"${float(r['gross']):,.2f}",
                    f"${float(r['deduct']):,.2f}",
                    f"${float(r['net_calc']):,.2f}",
                    str(r["loans_count"])
                ])



            table_data.append(
                    ["Totales", 
                    f"${totals['gross']:,.2f}", 
                    f"${totals['deduct']:,.2f}",
                    f"${totals['net_calc']:,.2f}", ""])

            tbl = Table(table_data, repeatRows=1)
            tbl.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0f0f0')),
                # Alinear numéricas: columnas 1..3 (RIGHT)
                ('ALIGN', (1,1), (3,-2), 'RIGHT'),
                # Alinear #Préstamos: columna 4 (CENTER)
                ('ALIGN', (4,1), (4,-2), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor('#cccccc')),
                ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#fbfbfb')]),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e3f2fd')),
            ]))


            story = [title, Spacer(0,8), meta, Spacer(0,10), tbl]

            def _footer(canvas, doc):
                canvas.saveState()
                canvas.setFont("Helvetica", 9)
                canvas.drawRightString(doc.pagesize[0]-18, 12, f"Página {doc.page}")
                canvas.restoreState()

            doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
            messagebox.showinfo("Nómina", f"PDF generado correctamente:\n{path}")

        except Exception as e:
            messagebox.showerror("Nómina", f"No se pudo generar el PDF:\n{e}")
            
    def _load_employees_combo(self):
        try:
            emps = self.controller.list_employees(only_active=True)
        except Exception:
            emps = []
        values = [f"{e['id']} - {e['first_name']} {e['last_name']}" for e in emps]
        self.emp_cb['values'] = values
        if values:
            self.emp_cb.set(values[0])

    def _parse_emp_id(self):
        val = (self.emp_cb.get() or "").strip()
        if " - " not in val:
            return None
        return int(val.split(" - ",1)[0])

    def _do_pay_salary(self):
        try:
            emp_id = self._parse_emp_id()
            if not emp_id:
                messagebox.showerror("Nómina", "Seleccione un empleado")
                return
            date = self.pay_date.get_date().strftime('%Y-%m-%d')
            method = PAY_TO_CODE[self.pay_method.get()]
            reg = self.chk_register_cash.get()
            with_ded = self.chk_with_deduction.get()

            res = self.controller.process_salary_payment(
                emp_id, date, payment_method=method,
                register_in_cash=reg, with_loan_deduction=with_ded
            )
            msg = (f"Empleado: {res['employee']}\n"
                   f"Salario bruto: ${res['gross_salary']:.2f}\n"
                   f"Deducido a préstamos: ${res['total_deducted']:.2f}\n"
                   f"Pagado (neto): ${res['net_paid']:.2f}")
            messagebox.showinfo("Nómina", msg)
            self.refresh_report()
        except Exception as e:
            messagebox.showerror("Nómina", str(e))

