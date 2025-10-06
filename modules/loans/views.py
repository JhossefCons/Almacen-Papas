# modules/loans/views.py
"""
Vista para el módulo de préstamos a empleados
Novedades:
- Gestión de empleados (crear y seleccionar en préstamos)
- Préstamo: método de pago + "Registrar en Caja"
- Pago préstamo: método de pago + "Registrar en Caja"
- Pago de salario con deducción automática y registro en Caja
- Reporte con totales y exportación a PDF
"""

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import datetime, timedelta

from modules.loans.controller import LoansController

PAY_TO_CODE = {"Efectivo": "cash", "Transferencia": "transfer"}


class LoansView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth_manager = auth_manager
        self.controller = LoansController(database, auth_manager)

        self.setup_ui()
        self.load_employees()
        self.load_loans()

    # -----------------------------
    # UI
    # -----------------------------
    def setup_ui(self):
        main_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left = ttk.Frame(main_paned, padding=10)
        main_paned.add(left, weight=1)

        right = ttk.Frame(main_paned, padding=10)
        main_paned.add(right, weight=2)

        # --- EMPLEADOS ---
        emp_frame = ttk.LabelFrame(left, text="Empleado", padding=10)
        emp_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(emp_frame, text="Nombre:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.emp_first = ttk.Entry(emp_frame)
        self.emp_first.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        ttk.Label(emp_frame, text="Apellido:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.emp_last = ttk.Entry(emp_frame)
        self.emp_last.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        ttk.Label(emp_frame, text="Salario:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.emp_salary = ttk.Entry(emp_frame)
        self.emp_salary.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        ttk.Button(emp_frame, text="Crear empleado", command=self.create_employee).grid(row=3, column=0, columnspan=2, pady=6)

        emp_frame.columnconfigure(1, weight=1)

        # --- NUEVO PRÉSTAMO ---
        loan_frame = ttk.LabelFrame(left, text="Nuevo Préstamo", padding=10)
        loan_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(loan_frame, text="Empleado:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.employee_cb = ttk.Combobox(loan_frame, state="readonly", width=28)
        self.employee_cb.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        ttk.Label(loan_frame, text="Monto:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.amount_entry = ttk.Entry(loan_frame)
        self.amount_entry.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        ttk.Label(loan_frame, text="Fecha préstamo:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.date_issued_entry = DateEntry(loan_frame, date_pattern='yyyy-mm-dd')
        self.date_issued_entry.set_date(datetime.now())
        self.date_issued_entry.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        ttk.Label(loan_frame, text="Vence:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.due_date_entry = DateEntry(loan_frame, date_pattern='yyyy-mm-dd')
        self.due_date_entry.set_date(datetime.now() + timedelta(days=30))
        self.due_date_entry.grid(row=3, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        ttk.Label(loan_frame, text="Interés (%):").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.interest_entry = ttk.Entry(loan_frame)
        self.interest_entry.insert(0, "0")
        self.interest_entry.grid(row=4, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        ttk.Label(loan_frame, text="Notas:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.notes_entry = ttk.Entry(loan_frame)
        self.notes_entry.grid(row=5, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        # caja en préstamo
        self.loan_register_cash = tk.BooleanVar(value=True)
        ttk.Checkbutton(loan_frame, text="Registrar en Caja", variable=self.loan_register_cash).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        ttk.Label(loan_frame, text="Método pago:").grid(row=7, column=0, sticky=tk.W, pady=2)
        self.loan_pay_method = ttk.Combobox(loan_frame, state="readonly", values=tuple(PAY_TO_CODE.keys()), width=18)
        self.loan_pay_method.set("Efectivo")
        self.loan_pay_method.grid(row=7, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        btns = ttk.Frame(loan_frame)
        btns.grid(row=8, column=0, columnspan=2, pady=8)
        ttk.Button(
            btns, text="Agregar", command=self.add_loan,
            state=("normal" if self.auth_manager.has_permission('admin') else "disabled")
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Limpiar", command=self.clear_loan_form).pack(side=tk.LEFT, padx=5)

        loan_frame.columnconfigure(1, weight=1)

        # --- NÓMINA ---
        payroll = ttk.LabelFrame(left, text="Pago de salario (con deducción de préstamos)", padding=10)
        payroll.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(payroll, text="Empleado:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.payroll_emp_cb = ttk.Combobox(payroll, state="readonly", width=28)
        self.payroll_emp_cb.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        ttk.Label(payroll, text="Fecha pago:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.payroll_date = DateEntry(payroll, date_pattern='yyyy-mm-dd')
        self.payroll_date.set_date(datetime.now())
        self.payroll_date.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        ttk.Label(payroll, text="Método:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.payroll_method = ttk.Combobox(payroll, state="readonly", values=tuple(PAY_TO_CODE.keys()), width=18)
        self.payroll_method.set("Efectivo")
        self.payroll_method.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=(5, 0))

        self.payroll_register_cash = tk.BooleanVar(value=True)
        ttk.Checkbutton(payroll, text="Registrar en Caja", variable=self.payroll_register_cash).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))

        ttk.Button(payroll, text="Pagar salario", command=self.pay_salary).grid(row=4, column=0, columnspan=2, pady=8)

        payroll.columnconfigure(1, weight=1)

        # ----------------- LISTA / ACCIONES -----------------
        list_frame = ttk.Frame(right)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('id', 'employee', 'amount', 'issued', 'due', 'interest', 'status', 'user')
        self.loans_tree = ttk.Treeview(list_frame, columns=columns, show='headings')

        for h, txt, w in (
            ('id', 'ID', 40),
            ('employee', 'Empleado', 180),
            ('amount', 'Monto', 90),
            ('issued', 'Fecha Préstamo', 100),
            ('due', 'Fecha Vencimiento', 110),
            ('interest', 'Interés %', 80),
            ('status', 'Estado', 80),
            ('user', 'Usuario', 100),
        ):
            self.loans_tree.heading(h, text=txt)
            self.loans_tree.column(h, width=w, anchor=tk.W if h in ('employee',) else tk.CENTER)

        ysb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.loans_tree.yview)
        self.loans_tree.configure(yscrollcommand=ysb.set)
        self.loans_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)

        action = ttk.Frame(right)
        action.pack(fill=tk.X, pady=(6, 0))

        if self.auth_manager.has_permission('admin'):
            ttk.Button(action, text="Editar", command=self.edit_loan).pack(side=tk.LEFT, padx=5)
            ttk.Button(action, text="Eliminar", command=self.delete_loan).pack(side=tk.LEFT, padx=5)

        ttk.Button(action, text="Ver Detalles", command=self.show_loan_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            action, text="Registrar Pago", command=self.show_payment_dialog,
            state=("normal" if self.auth_manager.has_permission('admin') else "disabled")
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(action, text="Actualizar", command=self.load_loans).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action, text="Reporte", command=self.show_report).pack(side=tk.RIGHT, padx=5)

        self.loans_tree.bind('<Double-1>', self.on_loan_double_click)

        # Filtros (sencillos)
        filters = ttk.LabelFrame(right, text="Filtros", padding=8)
        filters.pack(fill=tk.X, pady=(8, 0))

        ttk.Label(filters, text="Estado:").pack(side=tk.LEFT)
        self.status_filter = ttk.Combobox(filters, state="readonly", values=("", "active", "paid", "overdue"), width=12)
        self.status_filter.set("")
        self.status_filter.pack(side=tk.LEFT, padx=6)

        ttk.Label(filters, text="Empleado:").pack(side=tk.LEFT)
        self.employee_filter = ttk.Entry(filters, width=20)
        self.employee_filter.pack(side=tk.LEFT, padx=6)

        ttk.Button(filters, text="Aplicar", command=self.apply_filters).pack(side=tk.LEFT, padx=6)

        # Alertas
        alerts = ttk.LabelFrame(right, text="Alertas de Vencimiento", padding=8)
        alerts.pack(fill=tk.BOTH, expand=False, pady=(8, 0))
        self.alerts_text = tk.Text(alerts, height=6)
        self.alerts_text.pack(fill=tk.BOTH, expand=True)
        self.alerts_text.config(state=tk.DISABLED)

        ttk.Button(alerts, text="Actualizar Alertas", command=self.update_alerts).pack(pady=4)

    # públicos (lo llama MainWindow al cambiar de pestaña/F5)
    def refresh_all(self):
        self.load_loans()
        self.load_employees()
        self.update_alerts()

    # -----------------------------
    # EMPLEADOS
    # -----------------------------
    def load_employees(self):
        self.employees = self.controller.list_employees()
        names = [f"{e['id']} - {e['first_name']} {e['last_name']} (Sal: {e['salary']})" for e in self.employees]
        self.employee_cb['values'] = names
        self.payroll_emp_cb['values'] = [f"{e['id']} - {e['first_name']} {e['last_name']}" for e in self.employees]

        if names:
            self.employee_cb.set(names[0])
            self.payroll_emp_cb.set(self.payroll_emp_cb['values'][0])

    def create_employee(self):
        try:
            first = self.emp_first.get().strip()
            last = self.emp_last.get().strip()
            salary = float((self.emp_salary.get() or "0").strip())
            self.controller.add_employee(first, last, salary)
            messagebox.showinfo("Empleado", "Empleado creado correctamente.")
            self.emp_first.delete(0, tk.END)
            self.emp_last.delete(0, tk.END)
            self.emp_salary.delete(0, tk.END)
            self.load_employees()
        except ValueError:
            messagebox.showerror("Error", "Salario debe ser un número.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _get_selected_employee_id_from_combo(self, combo):
        val = (combo.get() or "").strip()
        if not val or " - " not in val:
            return None
        return int(val.split(" - ", 1)[0])

    # -----------------------------
    # PRÉSTAMOS
    # -----------------------------
    def load_loans(self, status_filter=None, employee_filter=None):
        for i in self.loans_tree.get_children():
            self.loans_tree.delete(i)
        loans = self.controller.get_loans(status_filter, employee_filter)
        for L in loans:
            tags = ()
            if L['status'] == 'overdue':
                tags = ('overdue',)
            elif L['status'] == 'paid':
                tags = ('paid',)
            self.loans_tree.insert('', 'end', values=(
                L['id'],
                L['employee_display'],
                f"${float(L['amount']):.2f}",
                L['date_issued'],
                L['due_date'],
                f"{float(L['interest_rate']):.1f}%",
                self._translate_status(L['status']),
                L.get('username') or ''
            ), tags=tags)
        self.loans_tree.tag_configure('overdue', background='#ffcccc')
        self.loans_tree.tag_configure('paid', background='#ccffcc')

    def _translate_status(self, status):
        return {'active': 'Activo', 'paid': 'Pagado', 'overdue': 'Vencido'}.get(status, status)

    def apply_filters(self):
        st = self.status_filter.get() or None
        emp = self.employee_filter.get() or None
        self.load_loans(st, emp)

    def clear_loan_form(self):
        self.amount_entry.delete(0, tk.END)
        self.date_issued_entry.set_date(datetime.now())
        self.due_date_entry.set_date(datetime.now() + timedelta(days=30))
        self.interest_entry.delete(0, tk.END); self.interest_entry.insert(0, "0")
        self.notes_entry.delete(0, tk.END)
        if self.employee_cb['values']:
            self.employee_cb.set(self.employee_cb['values'][0])
        self.loan_register_cash.set(True)
        self.loan_pay_method.set("Efectivo")

    def add_loan(self):
        try:
            emp_id = self._get_selected_employee_id_from_combo(self.employee_cb)
            if not emp_id:
                messagebox.showerror("Error", "Seleccione un empleado")
                return
            amount = float(self.amount_entry.get())
            date_issued = self.date_issued_entry.get_date().strftime('%Y-%m-%d')
            due_date = self.due_date_entry.get_date().strftime('%Y-%m-%d')
            interest = float(self.interest_entry.get() or "0")
            notes = self.notes_entry.get()
            reg_cash = self.loan_register_cash.get()
            pay_method = PAY_TO_CODE[self.loan_pay_method.get()]

            self.controller.add_loan(emp_id, amount, date_issued, due_date, interest, notes,
                                     register_in_cash=reg_cash, payment_method=pay_method)
            messagebox.showinfo("Préstamo", "Préstamo agregado correctamente.")
            self.clear_loan_form()
            self.load_loans()
            self.update_alerts()
        except ValueError:
            messagebox.showerror("Error", "Monto/Interés inválidos.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # -----------------------------
    # DETALLES / PAGOS
    # -----------------------------
    def on_loan_double_click(self, _):
        self.show_loan_details()

    def show_loan_details(self):
        sel = self.loans_tree.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Seleccione un préstamo")
            return
        loan_id = self.loans_tree.item(sel[0])['values'][0]
        s = self.controller.get_loan_summary(loan_id)
        if not s:
            messagebox.showerror("Error", "No se pudo cargar el préstamo")
            return

        win = tk.Toplevel(self.parent)
        win.title(f"Detalles - {s['loan']['employee_display']}")
        win.geometry("620x420")
        win.transient(self.parent)
        win.grab_set()

        main = ttk.Frame(win, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        info = ttk.LabelFrame(main, text="Información", padding=8)
        info.pack(fill=tk.X, pady=(0, 8))

        text = (f"Empleado: {s['loan']['employee_display']}\n"
                f"Monto original: ${float(s['loan']['amount']):.2f}\n"
                f"Interés: {float(s['loan']['interest_rate']):.1f}%\n"
                f"Total a pagar: ${float(s['total_due']):.2f}\n"
                f"Fecha préstamo: {s['loan']['date_issued']} | Vence: {s['loan']['due_date']} | Estado: {self._translate_status(s['loan']['status'])}\n"
                f"Pagado: ${float(s['total_paid']):.2f} | Saldo: ${float(s['balance']):.2f}")
        ttk.Label(info, text=text, justify=tk.LEFT).pack(anchor=tk.W)

        pays_frame = ttk.LabelFrame(main, text="Pagos", padding=8)
        pays_frame.pack(fill=tk.BOTH, expand=True)

        cols = ('date', 'amount', 'notes', 'user')
        tree = ttk.Treeview(pays_frame, columns=cols, show='headings', height=8)
        for c, txt, w in (('date','Fecha',100), ('amount','Monto',90), ('notes','Notas',260), ('user','Usuario',120)):
            tree.heading(c, text=txt)
            tree.column(c, width=w, anchor=tk.W if c == 'notes' else tk.CENTER)
        for p in s['payments']:
            tree.insert('', 'end', values=(p['payment_date'], f"${float(p['amount']):.2f}", p['notes'] or '', p.get('username') or ''))
        ysb = ttk.Scrollbar(pays_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=ysb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)

    def show_payment_dialog(self):
        sel = self.loans_tree.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Seleccione un préstamo para registrar pago")
            return
        loan_id = self.loans_tree.item(sel[0])['values'][0]
        employee = self.loans_tree.item(sel[0])['values'][1]

        win = tk.Toplevel(self.parent)
        win.title(f"Registrar Pago - {employee}")
        win.geometry("420x260")
        win.transient(self.parent)
        win.grab_set()

        main = ttk.Frame(win, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="Fecha Pago:").grid(row=0, column=0, sticky=tk.W, pady=4)
        date_entry = DateEntry(main, date_pattern='yyyy-mm-dd')
        date_entry.set_date(datetime.now())
        date_entry.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main, text="Monto:").grid(row=1, column=0, sticky=tk.W, pady=4)
        amount_entry = ttk.Entry(main)
        amount_entry.grid(row=1, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main, text="Notas:").grid(row=2, column=0, sticky=tk.W, pady=4)
        notes_entry = ttk.Entry(main)
        notes_entry.grid(row=2, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        reg_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main, text="Registrar en Caja", variable=reg_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        ttk.Label(main, text="Método:").grid(row=4, column=0, sticky=tk.W, pady=4)
        method_cb = ttk.Combobox(main, state="readonly", values=tuple(PAY_TO_CODE.keys()), width=18)
        method_cb.set("Efectivo")
        method_cb.grid(row=4, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        def do_register():
            try:
                date = date_entry.get_date().strftime('%Y-%m-%d')
                amount = float(amount_entry.get())
                notes = notes_entry.get()
                reg = reg_var.get()
                method = PAY_TO_CODE[method_cb.get()]
                self.controller.add_payment(loan_id, date, amount, notes, register_in_cash=reg, payment_method=method)
                messagebox.showinfo("Pago", "Pago registrado.")
                win.destroy()
                self.load_loans()
                self.update_alerts()
            except ValueError:
                messagebox.showerror("Error", "Monto inválido")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        btns = ttk.Frame(main)
        btns.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Registrar", command=do_register).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Cancelar", command=win.destroy).pack(side=tk.LEFT, padx=5)

        main.columnconfigure(1, weight=1)

    # -----------------------------
    # NÓMINA
    # -----------------------------
    def pay_salary(self):
        try:
            emp_id = self._get_selected_employee_id_from_combo(self.payroll_emp_cb)
            if not emp_id:
                messagebox.showerror("Error", "Seleccione empleado")
                return
            date = self.payroll_date.get_date().strftime('%Y-%m-%d')
            method = PAY_TO_CODE[self.payroll_method.get()]
            reg = self.payroll_register_cash.get()
            res = self.controller.process_payroll_payment(emp_id, date, payment_method=method, register_in_cash=reg)
            msg = (f"Empleado: {res['employee']}\n"
                   f"Salario bruto: ${res['gross_salary']:.2f}\n"
                   f"Deducido a préstamos: ${res['total_deducted']:.2f}\n"
                   f"Pagado (neto): ${res['net_paid']:.2f}")
            messagebox.showinfo("Nómina", msg)
            self.load_loans()
            self.update_alerts()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # -----------------------------
    # ALERTAS
    # -----------------------------
    def update_alerts(self):
        o = self.controller.get_overdue_loans()
        self.alerts_text.config(state=tk.NORMAL)
        self.alerts_text.delete(1.0, tk.END)
        if not o:
            self.alerts_text.insert(tk.END, "No hay préstamos vencidos")
        else:
            self.alerts_text.insert(tk.END, "PRÉSTAMOS VENCIDOS:\n\n")
            for L in o:
                days = (datetime.now().date() - datetime.strptime(L['due_date'], '%Y-%m-%d').date()).days
                name = L.get("employee_display") or "—"
                self.alerts_text.insert(tk.END, f"{name}: ${float(L['amount']):.2f} - {days} días de retraso\n")
        self.alerts_text.config(state=tk.DISABLED)

    # -----------------------------
    # REPORTE (con PDF)
    # -----------------------------
    def show_report(self):
        """Diálogo de Reporte de Préstamos con generación de PDF."""
        from tkinter import filedialog
        try:
            import reportlab  # solo para dar un mensaje claro si no está
        except Exception:
            reportlab = None

        # Crear ventana
        report_window = tk.Toplevel(self.parent)
        report_window.title("Reporte de Préstamos")
        report_window.geometry("820x520")
        report_window.transient(self.parent)
        report_window.grab_set()

        # Marco principal
        main_frame = ttk.Frame(report_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Filtros
        ttk.Label(main_frame, text="Fecha Inicio:").grid(row=0, column=0, sticky=tk.W, pady=4)
        start_date = DateEntry(main_frame, date_pattern='yyyy-mm-dd')
        start_date.set_date(datetime.now() - timedelta(days=30))
        start_date.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(5, 12))

        ttk.Label(main_frame, text="Fecha Fin:").grid(row=0, column=2, sticky=tk.W, pady=4)
        end_date = DateEntry(main_frame, date_pattern='yyyy-mm-dd')
        end_date.set_date(datetime.now())
        end_date.grid(row=0, column=3, sticky=tk.EW, pady=4, padx=(5, 12))

        ttk.Label(main_frame, text="Estado:").grid(row=0, column=4, sticky=tk.W, pady=4)
        status_filter = ttk.Combobox(main_frame, state="readonly", width=16)
        status_filter['values'] = ('Todos', 'Activo', 'Pagado', 'Vencido')
        status_filter.set('Todos')
        status_filter.grid(row=0, column=5, sticky=tk.EW, pady=4, padx=(5, 0))

        # Botones
        btns = ttk.Frame(main_frame)
        btns.grid(row=1, column=0, columnspan=6, sticky=tk.W, pady=(6, 10))
        ttk.Button(btns, text="Generar PDF", command=lambda: generate_and_export_pdf()).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btns, text="Cerrar", command=report_window.destroy).pack(side=tk.LEFT)

        # Tabla de vista previa
        columns = ('employee', 'amount', 'issued', 'due', 'status', 'paid', 'balance')
        report_tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=16)

        report_tree.heading('employee', text='Empleado')
        report_tree.heading('amount', text='Monto')
        report_tree.heading('issued', text='Fecha Préstamo')
        report_tree.heading('due', text='Fecha Vencimiento')
        report_tree.heading('status', text='Estado')
        report_tree.heading('paid', text='Pagado')
        report_tree.heading('balance', text='Saldo')

        report_tree.column('employee', width=220, anchor=tk.W)
        report_tree.column('amount', width=100, anchor=tk.E)
        report_tree.column('issued', width=120, anchor=tk.CENTER)
        report_tree.column('due', width=130, anchor=tk.CENTER)
        report_tree.column('status', width=90, anchor=tk.CENTER)
        report_tree.column('paid', width=100, anchor=tk.E)
        report_tree.column('balance', width=100, anchor=tk.E)

        ysb = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=report_tree.yview)
        xsb = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=report_tree.xview)
        report_tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        report_tree.grid(row=2, column=0, columnspan=6, sticky=tk.NSEW, pady=6)
        ysb.grid(row=2, column=6, sticky=tk.NS, pady=6)
        xsb.grid(row=3, column=0, columnspan=6, sticky=tk.EW)

        # Totales + estado
        totals_lbl = ttk.Label(main_frame, text="Totales: —", font=('Segoe UI', 9, 'bold'))
        totals_lbl.grid(row=4, column=0, columnspan=6, sticky=tk.E, pady=(8, 0))

        status_lbl = ttk.Label(main_frame, text="", foreground="#666")
        status_lbl.grid(row=5, column=0, columnspan=6, sticky=tk.W, pady=(4, 0))

        # Colores para estados
        report_tree.tag_configure('overdue', background='#ffefef')  # vencido
        report_tree.tag_configure('paid', background='#eefeef')     # pagado

        # Pesos de grid
        for c in range(6):
            main_frame.columnconfigure(c, weight=1)
        main_frame.rowconfigure(2, weight=1)

        def _status_map_to_internal(label_es: str):
            return {
                'Activo': 'active',
                'Pagado': 'paid',
                'Vencido': 'overdue',
                'Todos': None,
                '': None
            }.get(label_es, None)

        def _translate_status_en_to_es(st: str):
            return {'active': 'Activo', 'paid': 'Pagado', 'overdue': 'Vencido'}.get(st, st or '—')

        def _format_money(val):
            try:
                return f"${float(val):,.2f}"
            except Exception:
                return "$0.00"

        def _load_preview():
            """Carga/recarga la vista previa en pantalla (tabla) y devuelve (data, totals)."""
            # Limpia
            for i in report_tree.get_children():
                report_tree.delete(i)
            totals_lbl.config(text="Totales: —")
            status_lbl.config(text="")

            start = start_date.get_date().strftime('%Y-%m-%d')
            end = end_date.get_date().strftime('%Y-%m-%d')
            status_internal = _status_map_to_internal(status_filter.get())

            data = self.controller.get_loans_report(start, end, status_internal) or []

            total_amount = total_paid = total_balance = 0.0

            if not data:
                report_tree.insert('', 'end', values=("— Sin datos —", "", "", "", "", "", ""))
                status_lbl.config(text="No hay préstamos para el período seleccionado.")
                return [], {"amount": 0.0, "paid": 0.0, "balance": 0.0}

            for loan in data:
                employee = loan.get('employee_display') or loan.get('employee_name') or '—'
                amount = float(loan.get('amount') or 0)
                paid = float(loan.get('total_paid') or 0)
                balance = float(loan.get('balance') or 0)
                issued = loan.get('date_issued') or ''
                due = loan.get('due_date') or ''
                st = _translate_status_en_to_es(loan.get('status'))

                tags = ()
                if loan.get('status') == 'overdue':
                    tags = ('overdue',)
                elif loan.get('status') == 'paid':
                    tags = ('paid',)

                report_tree.insert('', 'end', values=(
                    employee, _format_money(amount), issued, due, st,
                    _format_money(paid), _format_money(balance)
                ), tags=tags)

                total_amount += amount
                total_paid += paid
                total_balance += balance

            totals_lbl.config(
                text=f"Totales: Monto={_format_money(total_amount)} | "
                     f"Pagado={_format_money(total_paid)} | Saldo={_format_money(total_balance)}"
            )
            status_lbl.config(text=f"Registros: {len(data)}")
            return data, {"amount": total_amount, "paid": total_paid, "balance": total_balance}

        def generate_and_export_pdf():
            """Genera el PDF con los datos actuales del filtro."""
            # Cargar/actualizar preview y tomar los datos
            try:
                data, totals = _load_preview()
            except Exception as e:
                messagebox.showerror("Reporte de Préstamos", f"Error obteniendo datos: {e}")
                return

            # Si no hay datos, no generamos
            if not data:
                return

            # Elegir ruta de guardado
            from tkinter import filedialog
            default_name = f"reporte_prestamos_{start_date.get_date().strftime('%Y%m%d')}_{end_date.get_date().strftime('%Y%m%d')}.pdf"
            save_path = filedialog.asksaveasfilename(
                title="Guardar reporte como",
                defaultextension=".pdf",
                initialfile=default_name,
                filetypes=[("PDF", "*.pdf")]
            )
            if not save_path:
                return

            # Intentar importar reportlab
            try:
                from reportlab.lib.pagesizes import A4, landscape
                from reportlab.lib import colors
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
            except ImportError:
                messagebox.showerror(
                    "Falta dependencia",
                    "Para generar PDF necesitas instalar reportlab:\n\npip install reportlab"
                )
                return

            try:
                # Documento
                doc = SimpleDocTemplate(
                    save_path,
                    pagesize=landscape(A4),
                    leftMargin=18, rightMargin=18, topMargin=18, bottomMargin=22
                )

                styles = getSampleStyleSheet()
                title = Paragraph("<b>Reporte de Préstamos a Empleados</b>", styles['Title'])

                # Subtítulo: periodo y estado
                st_map = {None: "Todos", "active": "Activo", "paid": "Pagado", "overdue": "Vencido"}
                start_str = start_date.get_date().strftime('%Y-%m-%d')
                end_str = end_date.get_date().strftime('%Y-%m-%d')
                status_internal = _status_map_to_internal(status_filter.get())
                status_str = st_map.get(status_internal, "Todos")

                meta = Paragraph(
                    f"Período: <b>{start_str}</b> a <b>{end_str}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"Estado: <b>{status_str}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
                    f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    styles['Normal']
                )

                # Tabla
                table_data = [
                    ["Empleado", "Monto", "Fecha Préstamo", "Fecha Vencimiento", "Estado", "Pagado", "Saldo"]
                ]
                for loan in data:
                    employee = loan.get('employee_display') or loan.get('employee_name') or '—'
                    amount = float(loan.get('amount') or 0)
                    paid = float(loan.get('total_paid') or 0)
                    balance = float(loan.get('balance') or 0)
                    issued = loan.get('date_issued') or ''
                    due = loan.get('due_date') or ''
                    st_es = _translate_status_en_to_es(loan.get('status'))
                    table_data.append([
                        employee, _format_money(amount), issued, due, st_es,
                        _format_money(paid), _format_money(balance)
                    ])

                # Totales
                table_data.append([
                    "Totales", _format_money(totals["amount"]), "", "", "",
                    _format_money(totals["paid"]), _format_money(totals["balance"])
                ])

                tbl = Table(table_data, repeatRows=1)
                tbl.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (1, 1), (1, -2), 'RIGHT'),   # Monto
                    ('ALIGN', (5, 1), (6, -2), 'RIGHT'),   # Pagado, Saldo
                    ('ALIGN', (2, 1), (3, -2), 'CENTER'),  # Fechas
                    ('ALIGN', (4, 1), (4, -2), 'CENTER'),  # Estado
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cccccc')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#fbfbfb')]),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e9')),
                ]))

                story = [title, Spacer(0, 8), meta, Spacer(0, 10), tbl]

                # Footer con número de página
                def _footer(canvas, doc):
                    canvas.saveState()
                    footer = f"Página {doc.page}"
                    canvas.setFont("Helvetica", 9)
                    canvas.drawRightString(doc.pagesize[0] - 18, 12, footer)
                    canvas.restoreState()

                doc.build(story, onFirstPage=_footer, onLaterPages=_footer)

                messagebox.showinfo("Reporte de Préstamos", f"PDF generado correctamente:\n{save_path}")

            except Exception as e:
                messagebox.showerror("Reporte de Préstamos", f"No se pudo generar el PDF:\n{e}")

        # Generar una vista previa inicial
        try:
            _load_preview()
        except Exception as e:
            messagebox.showerror("Reporte de Préstamos", f"Error inicial: {e}")

    # -----------------------------
    # EDICIÓN / ELIMINACIÓN
    # -----------------------------
    def edit_loan(self):
        """Editar préstamo seleccionado (solo admin)."""
        if not self.auth_manager.has_permission('admin'):
            messagebox.showerror("Permisos", "Solo los administradores pueden editar préstamos")
            return

        sel = self.loans_tree.selection()
        if not sel:
            messagebox.showwarning("Seleccionar", "Seleccione un préstamo para editar")
            return

        loan_id = self.loans_tree.item(sel[0])['values'][0]
        loan = self.controller.get_loan_by_id(loan_id)
        if not loan:
            messagebox.showerror("Error", "No se pudo obtener la información del préstamo")
            return

        # Dialogo
        win = tk.Toplevel(self.parent)
        win.title(f"Editar Préstamo #{loan_id}")
        win.geometry("420x360")
        win.transient(self.parent)
        win.grab_set()

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        # Empleado (combobox con empleados activos/inactivos)
        ttk.Label(frm, text="Empleado:").grid(row=0, column=0, sticky=tk.W, pady=4)
        try:
            employees = self.controller.list_employees(only_active=False)
        except Exception:
            employees = []
        emp_display_to_id = {}
        emp_values = []
        current_emp_id = loan.get('employee_id')
        current_emp_display = loan.get('employee_display') or loan.get('employee_name') or "—"

        for e in (employees or []):
            disp = f"{e['first_name']} {e['last_name']} (ID {e['id']})"
            emp_display_to_id[disp] = e['id']
            emp_values.append(disp)

        emp_cb = ttk.Combobox(frm, values=emp_values, state="readonly", width=30)
        # preseleccionar
        if current_emp_id and employees:
            for disp, _id in emp_display_to_id.items():
                if _id == current_emp_id:
                    emp_cb.set(disp)
                    break
        else:
            emp_cb.set(current_emp_display)
        emp_cb.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(6, 0))

        # Monto
        ttk.Label(frm, text="Monto:").grid(row=1, column=0, sticky=tk.W, pady=4)
        amount_e = ttk.Entry(frm)
        amount_e.insert(0, str(loan.get('amount') or "0"))
        amount_e.grid(row=1, column=1, sticky=tk.EW, pady=4, padx=(6, 0))

        # Fechas
        ttk.Label(frm, text="Fecha Préstamo:").grid(row=2, column=0, sticky=tk.W, pady=4)
        issued_de = DateEntry(frm, date_pattern='yyyy-mm-dd')
        try:
            issued_de.set_date(datetime.strptime(loan.get('date_issued'), '%Y-%m-%d'))
        except Exception:
            pass
        issued_de.grid(row=2, column=1, sticky=tk.EW, pady=4, padx=(6, 0))

        ttk.Label(frm, text="Fecha Vencimiento:").grid(row=3, column=0, sticky=tk.W, pady=4)
        due_de = DateEntry(frm, date_pattern='yyyy-mm-dd')
        try:
            due_de.set_date(datetime.strptime(loan.get('due_date'), '%Y-%m-%d'))
        except Exception:
            pass
        due_de.grid(row=3, column=1, sticky=tk.EW, pady=4, padx=(6, 0))

        # Interés
        ttk.Label(frm, text="Interés (%):").grid(row=4, column=0, sticky=tk.W, pady=4)
        interest_e = ttk.Entry(frm)
        interest_e.insert(0, str(loan.get('interest_rate') or "0"))
        interest_e.grid(row=4, column=1, sticky=tk.EW, pady=4, padx=(6, 0))

        # Notas
        ttk.Label(frm, text="Notas:").grid(row=5, column=0, sticky=tk.W, pady=4)
        notes_e = ttk.Entry(frm)
        notes_e.insert(0, (loan.get('notes') or ""))
        notes_e.grid(row=5, column=1, sticky=tk.EW, pady=4, padx=(6, 0))

        # Botones
        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=2, pady=12)

        def _save():
            try:
                # employee_id desde combobox (si eligió uno)
                emp_disp = emp_cb.get()
                emp_id = current_emp_id
                if emp_disp in emp_display_to_id:
                    emp_id = emp_display_to_id[emp_disp]

                amount = float(amount_e.get())
                if amount <= 0:
                    messagebox.showerror("Error", "El monto debe ser mayor a cero")
                    return

                issued = issued_de.get_date().strftime('%Y-%m-%d')
                due = due_de.get_date().strftime('%Y-%m-%d')
                if due <= issued:
                    messagebox.showerror("Error", "La fecha de vencimiento debe ser posterior a la fecha de préstamo")
                    return

                interest = float(interest_e.get())
                if interest < 0:
                    messagebox.showerror("Error", "La tasa de interés no puede ser negativa")
                    return

                notes = notes_e.get()

                self.controller.update_loan(
                    loan_id=loan_id,
                    employee_id=emp_id,
                    amount=amount,
                    date_issued=issued,
                    due_date=due,
                    interest_rate=interest,
                    notes=notes
                )
                messagebox.showinfo("Éxito", "Préstamo actualizado correctamente")
                win.destroy()
                self.load_loans()
                self.update_alerts()
            except ValueError:
                messagebox.showerror("Error", "Ingrese valores numéricos válidos")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el préstamo:\n{e}")

        ttk.Button(btns, text="Guardar", command=_save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancelar", command=win.destroy).pack(side=tk.LEFT, padx=6)

        frm.columnconfigure(1, weight=1)

    def delete_loan(self):
        """Eliminar préstamo seleccionado (solo admin)."""
        if not self.auth_manager.has_permission('admin'):
            messagebox.showerror("Permisos", "Solo los administradores pueden eliminar préstamos")
            return

        sel = self.loans_tree.selection()
        if not sel:
            messagebox.showwarning("Seleccionar", "Seleccione un préstamo para eliminar")
            return

        loan_id = self.loans_tree.item(sel[0])['values'][0]
        employee = self.loans_tree.item(sel[0])['values'][1]
        if messagebox.askyesno("Confirmar", f"¿Eliminar el préstamo de '{employee}'? Se borrarán sus pagos."):
            try:
                self.controller.delete_loan(loan_id)
                messagebox.showinfo("Éxito", "Préstamo eliminado")
                self.load_loans()
                self.update_alerts()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar: {e}")
