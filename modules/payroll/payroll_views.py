# modules/payroll/payroll_views.py
"""
Vista de Nómina (Historial de Pagos)
- Muestra historial de pagos con filtros de fecha.
- Permite iniciar el proceso de pago de salario con confirmación/edición de montos.
- Exporta el historial filtrado a PDF.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime, timedelta
from modules.payroll.payroll_controller import PayrollController
from typing import List, Dict, Tuple, Optional


PAY_TO_CODE = {"Efectivo": "cash", "Transferencia": "transfer"}
CODE_TO_PAY = {v: k for k, v in PAY_TO_CODE.items()} # Inverso para mostrar

class PayrollReportView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth = auth_manager
        self.controller = PayrollController(database, auth_manager)
        self.employee_list_cache = [] # Cache para el combobox de empleados

        self._build_ui()
        self._load_employees_combo() # Cargar empleados una vez al inicio
        self.refresh_report() # Cargar historial inicial

    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        # --- Filtros y Acciones Superiores ---
        top_frame = ttk.Frame(container)
        top_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(top_frame, text="Desde:").pack(side=tk.LEFT)
        self.start_date_entry = DateEntry(top_frame, date_pattern='yyyy-mm-dd', width=12)
        self.start_date_entry.set_date(datetime.now().replace(day=1)) # Inicio del mes actual
        self.start_date_entry.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(top_frame, text="Hasta:").pack(side=tk.LEFT)
        self.end_date_entry = DateEntry(top_frame, date_pattern='yyyy-mm-dd', width=12)
        self.end_date_entry.set_date(datetime.now()) # Fecha actual
        self.end_date_entry.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Button(top_frame, text="Buscar Historial", command=self.refresh_report).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Exportar PDF", command=self.export_pdf).pack(side=tk.LEFT, padx=(6,0))

        # --- Formulario para Iniciar Pago ---
        pay_frame = ttk.LabelFrame(container, text="Iniciar Pago de Salario", padding=8)
        pay_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(pay_frame, text="Empleado:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.emp_cb = ttk.Combobox(pay_frame, state="readonly", width=30)
        self.emp_cb.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 12))

        ttk.Label(pay_frame, text="Fecha Pago:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.pay_date = DateEntry(pay_frame, date_pattern='yyyy-mm-dd', width=12)
        self.pay_date.set_date(datetime.now())
        self.pay_date.grid(row=0, column=3, sticky=tk.EW, pady=2, padx=(5, 12))

        ttk.Label(pay_frame, text="Método:").grid(row=0, column=4, sticky=tk.W, pady=2)
        self.pay_method = ttk.Combobox(pay_frame, state="readonly", values=tuple(PAY_TO_CODE.keys()), width=16)
        self.pay_method.set("Efectivo")
        self.pay_method.grid(row=0, column=5, sticky=tk.EW, pady=2, padx=(5, 0))

        self.chk_register_cash = tk.BooleanVar(value=True)
        ttk.Checkbutton(pay_frame, text="Registrar en Caja", variable=self.chk_register_cash)\
            .grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(4,0))

        # El botón ahora abre el diálogo de confirmación
        ttk.Button(pay_frame, text="Iniciar Proceso de Pago", command=self._open_payment_confirmation)\
            .grid(row=1, column=5, sticky=tk.E, padx=(8, 0), pady=(4,0))

        for c in (1,3,5): pay_frame.columnconfigure(c, weight=1)

        # --- Tabla de Historial ---
        table_container = ttk.Frame(container)
        table_container.pack(fill=tk.BOTH, expand=True)

        columns = ("payment_date", "name", "gross", "deduct", "net_paid", "user", "id")
        headers = {
            "payment_date": "Fecha Pago", "name": "Empleado", "gross": "Salario Bruto Pagado",
            "deduct": "Deducción Préstamos", "net_paid": "Neto Pagado", "user": "Usuario Reg.", "id": "ID Pago"
        }
        widths = {"payment_date": 100, "name": 200, "gross": 140, "deduct": 150,
                  "net_paid": 120, "user": 100, "id": 60}

        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", height=15)

        for c in columns:
            self.tree.heading(c, text=headers[c])
            anchor = tk.W if c == "name" else (tk.CENTER if c in ("payment_date", "id") else tk.E)
            self.tree.column(c, width=widths[c], anchor=anchor)

        ysb = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        # --- Totales ---
        self.total_lbl = ttk.Label(container, text="Totales del período: ", font=('Segoe UI', 9, 'bold'))
        self.total_lbl.pack(anchor=tk.E, pady=(6,0))

        # --- Estado ---
        self.status_lbl = ttk.Label(container, text="", foreground="#555")
        self.status_lbl.pack(anchor=tk.W, pady=(2,0))

    # --- Métodos Públicos y de Carga ---
    def refresh_all(self):
        """Refresca toda la vista (llamado por main_window)."""
        self._load_employees_combo() # Recarga por si hubo cambios
        self.refresh_report()

    def refresh_report(self):
        """Carga el historial de pagos según el filtro de fechas."""
        for i in self.tree.get_children(): self.tree.delete(i)
        self.total_lbl.config(text="Totales del período: ")
        self.status_lbl.config(text="")

        try:
            start_date = self.start_date_entry.get_date().strftime('%Y-%m-%d')
            end_date = self.end_date_entry.get_date().strftime('%Y-%m-%d')

            history_list, totals = self.controller.get_payroll_history(start_date, end_date)

            if not history_list:
                self.tree.insert("", tk.END, values=("— Sin pagos en este período —", "", "", "", "", "", ""))
                self.status_lbl.config(text=f"No se encontraron pagos entre {start_date} y {end_date}.")
                return

            for payment in history_list:
                self.tree.insert("", tk.END, values=(
                    payment["payment_date"],
                    payment["employee_name"],
                    f"${float(payment['gross_salary_paid']):,.2f}",
                    f"${float(payment['loan_deductions']):,.2f}",
                    f"${float(payment['net_paid']):,.2f}",
                    payment.get('username') or 'N/A',
                    payment['id']
                ))

            self.total_lbl.config(text=(
                f"Totales del período ({totals['count']} pagos): "
                f"Bruto=${totals['gross']:,.2f} | "
                f"Deducciones=${totals['deductions']:,.2f} | "
                f"Neto Pagado=${totals['net']:,.2f}"
            ))
            self.status_lbl.config(text=f"Mostrando pagos entre {start_date} y {end_date}.")

        except Exception as e:
            messagebox.showerror("Error al Cargar Historial", f"Ocurrió un error:\n{e}")
            self.tree.insert("", tk.END, values=("— Error al cargar datos —", "", "", "", "", "", ""))
            self.status_lbl.config(text="Error al cargar historial.")

    def _load_employees_combo(self):
        """Carga la lista de empleados activos en el combobox."""
        try:
            # Guardamos la lista para usarla en el diálogo sin recargar
            self.employee_list_cache = self.controller.list_employees(only_active=True)
            values = [f"{e['id']} - {e['first_name']} {e['last_name']}" for e in self.employee_list_cache]
            self.emp_cb['values'] = values
            if values:
                self.emp_cb.set(values[0])
            else:
                self.emp_cb.set("")
        except Exception as e:
            messagebox.showerror("Error Empleados", f"No se pudo cargar la lista de empleados:\n{e}")
            self.emp_cb['values'] = []
            self.emp_cb.set("")

    def _get_selected_employee_id_from_combo(self) -> Optional[int]:
        """Obtiene el ID del empleado seleccionado en el combobox principal."""
        val = (self.emp_cb.get() or "").strip()
        if " - " not in val: return None
        try: return int(val.split(" - ",1)[0])
        except ValueError: return None

    # --- Lógica de Pago ---
    def _open_payment_confirmation(self):
        """Abre el diálogo para confirmar/ajustar y ejecutar el pago."""
        try:
            employee_id = self._get_selected_employee_id_from_combo()
            if not employee_id:
                messagebox.showwarning("Selección Requerida", "Por favor, seleccione un empleado.")
                return

            # Buscar detalles del empleado seleccionado en la cache
            employee_data = next((emp for emp in self.employee_list_cache if emp['id'] == employee_id), None)
            if not employee_data:
                messagebox.showerror("Error", "No se encontraron los datos del empleado seleccionado.")
                return

            payment_date = self.pay_date.get_date().strftime('%Y-%m-%d')
            suggested_gross = float(employee_data.get('salary', 0.0))

            # Calcular deducciones sugeridas
            total_deducted, deduction_details = self.controller.calculate_deductions_for_payroll(employee_id, suggested_gross)
            suggested_net = round(suggested_gross - total_deducted, 2)

            # Crear y mostrar el diálogo
            PaymentConfirmationDialog(
                parent=self.parent,
                controller=self.controller,
                employee_id=employee_id,
                employee_name=f"{employee_data['first_name']} {employee_data['last_name']}",
                payment_date=payment_date,
                suggested_gross=suggested_gross,
                suggested_deduction=total_deducted,
                deduction_details=deduction_details,
                suggested_net=suggested_net,
                payment_method=PAY_TO_CODE[self.pay_method.get()],
                register_in_cash=self.chk_register_cash.get(),
                refresh_callback=self.refresh_report # Para actualizar historial tras pagar
            )

        except Exception as e:
            messagebox.showerror("Error al Iniciar Pago", f"Ocurrió un error:\n{e}")

    # --- Exportar PDF ---
    def export_pdf(self):
        """Exporta el historial actualmente filtrado a PDF."""
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import mm
        except ImportError:
            messagebox.showerror("Falta dependencia", "Para generar PDF necesitas instalar reportlab:\n\npip install reportlab")
            return

        start_date = self.start_date_entry.get_date().strftime('%Y-%m-%d')
        end_date = self.end_date_entry.get_date().strftime('%Y-%m-%d')

        # Obtener los datos directamente del controlador con los filtros actuales
        history_list, totals = self.controller.get_payroll_history(start_date, end_date)

        default_name = f"reporte_nomina_{start_date.replace('-','')}_{end_date.replace('-','')}.pdf"
        path = filedialog.asksaveasfilename(
            title="Guardar reporte como", defaultextension=".pdf", initialfile=default_name, filetypes=[("PDF","*.pdf")]
        )
        if not path: return

        try:
            doc = SimpleDocTemplate(
                path, pagesize=landscape(A4),
                leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=20*mm
            )
            styles = getSampleStyleSheet()
            story = []

            title = Paragraph("<b>Historial de Pagos de Nómina</b>", styles['Title'])
            meta = Paragraph(
                f"Período: <b>{start_date}</b> a <b>{end_date}</b> | Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                styles['Normal']
            )
            story += [title, Spacer(1, 4*mm), meta, Spacer(1, 6*mm)]

            # --- Tabla ---
            headers = ["Fecha Pago", "Empleado", "Salario Bruto", "Deducción Préstamos", "Neto Pagado", "Usuario"]
            table_data = [headers]

            if not history_list:
                # --- CAMBIO: Generar PDF vacío si no hay datos ---
                table_data.append(["(Sin registros para este período)", "", "", "", "", ""])
            else:
                for p in history_list:
                    table_data.append([
                        p["payment_date"],
                        p["employee_name"],
                        f"${float(p['gross_salary_paid']):,.2f}",
                        f"${float(p['loan_deductions']):,.2f}",
                        f"${float(p['net_paid']):,.2f}",
                        p.get('username') or 'N/A'
                    ])
                # Añadir fila de totales
                table_data.append([
                    "TOTALES", "",
                    f"${totals['gross']:,.2f}",
                    f"${totals['deductions']:,.2f}",
                    f"${totals['net']:,.2f}",
                    f"({totals['count']} pagos)"
                ])

            colWidths = [25*mm, 55*mm, 35*mm, 40*mm, 35*mm, 30*mm] # Ajustar anchos
            tbl = Table(table_data, colWidths=colWidths, repeatRows=1)

            style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'), # Centrar todo por defecto
                ('ALIGN', (1,1), (1,-1), 'LEFT'), # Empleado a la izquierda
                ('ALIGN', (2,1), (4,-1), 'RIGHT'), # Montos a la derecha
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'), # Totales en negrita
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.whitesmoke, colors.transparent]),
                ('BACKGROUND', (0,-1), (-1,-1), colors.lightblue), # Fondo fila totales
            ])
            tbl.setStyle(style)
            story.append(tbl)

            # --- Resumen de Totales (opcional, ya están en la tabla) ---
            # story.append(Spacer(1, 6*mm))
            # summary_text = f"Total Bruto: ${totals['gross']:,.2f} | Total Deducciones: ${totals['deductions']:,.2f} | Total Neto Pagado: ${totals['net']:,.2f}"
            # story.append(Paragraph(summary_text, styles['Normal']))

            def footer(canvas, doc):
                canvas.saveState()
                canvas.setFont('Helvetica', 9)
                canvas.drawRightString(doc.pagesize[0] - 15*mm, 10*mm, f"Página {doc.page}")
                canvas.restoreState()

            doc.build(story, onFirstPage=footer, onLaterPages=footer)
            messagebox.showinfo("Exportar PDF", f"PDF generado correctamente:\n{path}")

        except Exception as e:
            messagebox.showerror("Error al Exportar PDF", f"No se pudo generar el PDF:\n{e}")


# --- NUEVA CLASE: Diálogo de Confirmación de Pago ---
class PaymentConfirmationDialog:
    def __init__(self, parent, controller, employee_id, employee_name, payment_date,
                 suggested_gross, suggested_deduction, deduction_details, suggested_net,
                 payment_method, register_in_cash, refresh_callback):

        self.controller: PayrollController = controller
        self.employee_id = employee_id
        self.employee_name = employee_name
        self.payment_date = payment_date
        self.deduction_details = deduction_details # Guardar para enviar al controller
        self.payment_method = payment_method
        self.register_in_cash = register_in_cash
        self.refresh_callback = refresh_callback

        self.top = tk.Toplevel(parent)
        self.top.title(f"Confirmar Pago - {employee_name}")
        self.top.geometry("450x350")
        self.top.transient(parent)
        self.top.grab_set()

        # Variables de Tkinter para los Entry
        self.gross_var = tk.StringVar(value=f"{suggested_gross:.2f}")
        self.deduction_var = tk.StringVar(value=f"{suggested_deduction:.2f}")
        self.net_var = tk.StringVar(value=f"{suggested_net:.2f}")

        self._build_ui()
        # Vincular cambios en Bruto para recalcular Neto
        self.gross_entry.bind("<KeyRelease>", self._recalculate_net)

    def _build_ui(self):
        main_frame = ttk.Frame(self.top, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=f"Empleado: {self.employee_name}", font=('Segoe UI', 10, 'bold'))\
            .grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        ttk.Label(main_frame, text="Fecha de Pago:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Label(main_frame, text=self.payment_date).grid(row=1, column=1, sticky=tk.W, pady=4, padx=(5,0))

        # --- CAMBIO: Texto de la etiqueta modificado ---
        ttk.Label(main_frame, text="Salario Base (Editar actualiza Empleado):").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.gross_entry = ttk.Entry(main_frame, textvariable=self.gross_var, width=15)
        self.gross_entry.grid(row=2, column=1, sticky=tk.EW, pady=4, padx=(5,0))

        ttk.Label(main_frame, text="Deducción por Préstamos:").grid(row=3, column=0, sticky=tk.W, pady=4)
        # La deducción no es editable directamente, se calcula basada en el bruto
        ttk.Label(main_frame, textvariable=self.deduction_var)\
            .grid(row=3, column=1, sticky=tk.W, pady=4, padx=(5,0))

        ttk.Label(main_frame, text="Neto a Pagar (Editable):").grid(row=4, column=0, sticky=tk.W, pady=4)
        self.net_entry = ttk.Entry(main_frame, textvariable=self.net_var, width=15)
        self.net_entry.grid(row=4, column=1, sticky=tk.EW, pady=4, padx=(5,0))

        # Información adicional (opcional)
        if self.deduction_details:
             ttk.Label(main_frame, text="(Deducción aplicada a préstamos activos)", foreground="gray")\
                 .grid(row=5, column=1, sticky=tk.W, pady=(0, 10))

        ttk.Label(main_frame, text="Método de Pago:").grid(row=6, column=0, sticky=tk.W, pady=4)
        ttk.Label(main_frame, text=CODE_TO_PAY.get(self.payment_method, self.payment_method))\
            .grid(row=6, column=1, sticky=tk.W, pady=4, padx=(5,0))

        ttk.Label(main_frame, text="Registrar en Caja:").grid(row=7, column=0, sticky=tk.W, pady=4)
        ttk.Label(main_frame, text="Sí" if self.register_in_cash else "No")\
            .grid(row=7, column=1, sticky=tk.W, pady=4, padx=(5,0))


        footer = ttk.Frame(main_frame)
        footer.grid(row=8, column=0, columnspan=2, pady=(20,0))

        self.confirm_btn = ttk.Button(footer, text="Confirmar y Pagar", command=self._confirm_payment)
        self.confirm_btn.pack(side=tk.RIGHT, padx=5)
        self.cancel_btn = ttk.Button(footer, text="Cancelar", command=self.top.destroy)
        self.cancel_btn.pack(side=tk.RIGHT)

        main_frame.columnconfigure(1, weight=1)
        self.gross_entry.focus() # Enfocar el primer campo editable
        self.gross_entry.select_range(0, tk.END)

    def _recalculate_net(self, event=None):
        """Recalcula deducciones y neto cuando cambia el Salario Bruto."""
        try:
            current_gross = float(self.gross_var.get())
            if current_gross < 0: current_gross = 0.0

            # Volver a calcular deducciones con el nuevo bruto
            new_deduction, self.deduction_details = self.controller.calculate_deductions_for_payroll(
                self.employee_id, current_gross
            )
            new_net = round(current_gross - new_deduction, 2)

            # Actualizar las variables de Tkinter
            self.deduction_var.set(f"{new_deduction:.2f}")
            self.net_var.set(f"{new_net:.2f}")

        except ValueError:
            # Si el bruto no es un número válido, no hacer nada o limpiar
            self.deduction_var.set("0.00")
            self.net_var.set("0.00")
            self.deduction_details = []

    def _confirm_payment(self):
        """Valida y procesa el pago llamando al controlador."""
        try:
            # Obtener valores finales confirmados/editados por el usuario
            final_gross = float(self.gross_var.get())
            final_net = float(self.net_var.get())
            # La deducción se toma de la variable recalculada
            final_deduction = float(self.deduction_var.get())

            # Validaciones básicas
            if final_gross < 0 or final_net < 0:
                raise ValueError("Los montos no pueden ser negativos.")
            # Podríamos añadir más validaciones si es necesario

            # Llamar al controlador para procesar el pago
            self.controller.process_payroll_payment(
                employee_id=self.employee_id,
                payment_date=self.payment_date,
                gross_salary_paid=final_gross,
                net_amount_paid=final_net,
                loan_deductions_applied=final_deduction,
                deduction_details=self.deduction_details,
                payment_method=self.payment_method,
                register_in_cash=self.register_in_cash
            )

            messagebox.showinfo("Pago Exitoso", f"Pago de nómina para {self.employee_name} procesado correctamente.", parent=self.top)
            self.refresh_callback() # Actualizar la tabla de historial en la vista principal
            self.top.destroy()

        except ValueError as ve:
            messagebox.showerror("Error de Datos", str(ve), parent=self.top)
        except Exception as e:
            messagebox.showerror("Error al Procesar Pago", f"Ocurrió un error:\n{e}", parent=self.top)