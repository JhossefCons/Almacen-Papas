# modules/loans/views.py
"""
Vista para el módulo de préstamos a empleados
Novedades:
- Gestión de empleados (crear y seleccionar en préstamos)
- Préstamo: método de pago + "Registrar en Caja"
- Pago préstamo: método de pago + "Registrar en Caja"
- Pago de salario con deducción automática y registro en Caja
- Reporte con totales
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
        ttk.Button(btns, text="Agregar", command=self.add_loan,
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
        ttk.Button(action, text="Registrar Pago", command=self.show_payment_dialog,
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
            emp_id = self.controller.add_employee(first, last, salary)
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

        win = tk.Toplevel(self.parent); win.title(f"Detalles - {s['loan']['employee_display']}"); win.geometry("620x420"); win.transient(self.parent); win.grab_set()
        main = ttk.Frame(win, padding=10); main.pack(fill=tk.BOTH, expand=True)

        info = ttk.LabelFrame(main, text="Información", padding=8); info.pack(fill=tk.X, pady=(0, 8))
        text = (f"Empleado: {s['loan']['employee_display']}\n"
                f"Monto original: ${float(s['loan']['amount']):.2f}\n"
                f"Interés: {float(s['loan']['interest_rate']):.1f}%\n"
                f"Total a pagar: ${float(s['total_due']):.2f}\n"
                f"Fecha préstamo: {s['loan']['date_issued']} | Vence: {s['loan']['due_date']} | Estado: {self._translate_status(s['loan']['status'])}\n"
                f"Pagado: ${float(s['total_paid']):.2f} | Saldo: ${float(s['balance']):.2f}")
        ttk.Label(info, text=text, justify=tk.LEFT).pack(anchor=tk.W)

        pays_frame = ttk.LabelFrame(main, text="Pagos", padding=8); pays_frame.pack(fill=tk.BOTH, expand=True)
        cols = ('date', 'amount', 'notes', 'user')
        tree = ttk.Treeview(pays_frame, columns=cols, show='headings', height=8)
        for c, txt, w in (('date','Fecha',100), ('amount','Monto',90), ('notes','Notas',260), ('user','Usuario',120)):
            tree.heading(c, text=txt); tree.column(c, width=w, anchor=tk.W if c=='notes' else tk.CENTER)
        for p in s['payments']:
            tree.insert('', 'end', values=(p['payment_date'], f"${float(p['amount']):.2f}", p['notes'] or '', p.get('username') or ''))
        ysb = ttk.Scrollbar(pays_frame, orient=tk.VERTICAL, command=tree.yview); tree.configure(yscrollcommand=ysb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); ysb.pack(side=tk.RIGHT, fill=tk.Y)

    def show_payment_dialog(self):
        sel = self.loans_tree.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Seleccione un préstamo para registrar pago")
            return
        loan_id = self.loans_tree.item(sel[0])['values'][0]
        employee = self.loans_tree.item(sel[0])['values'][1]

        win = tk.Toplevel(self.parent); win.title(f"Registrar Pago - {employee}"); win.geometry("420x260"); win.transient(self.parent); win.grab_set()
        main = ttk.Frame(win, padding=10); main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="Fecha Pago:").grid(row=0, column=0, sticky=tk.W, pady=4)
        date_entry = DateEntry(main, date_pattern='yyyy-mm-dd'); date_entry.set_date(datetime.now())
        date_entry.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main, text="Monto:").grid(row=1, column=0, sticky=tk.W, pady=4)
        amount_entry = ttk.Entry(main); amount_entry.grid(row=1, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main, text="Notas:").grid(row=2, column=0, sticky=tk.W, pady=4)
        notes_entry = ttk.Entry(main); notes_entry.grid(row=2, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        reg_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main, text="Registrar en Caja", variable=reg_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        ttk.Label(main, text="Método:").grid(row=4, column=0, sticky=tk.W, pady=4)
        method_cb = ttk.Combobox(main, state="readonly", values=tuple(PAY_TO_CODE.keys()), width=18)
        method_cb.set("Efectivo"); method_cb.grid(row=4, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

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

        btns = ttk.Frame(main); btns.grid(row=5, column=0, columnspan=2, pady=10)
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
    # ALERTAS / REPORTES
    # -----------------------------
    def update_alerts(self):
        o = self.controller.get_overdue_loans()
        self.alerts_text.config(state=tk.NORMAL); self.alerts_text.delete(1.0, tk.END)
        if not o:
            self.alerts_text.insert(tk.END, "No hay préstamos vencidos")
        else:
            self.alerts_text.insert(tk.END, "PRÉSTAMOS VENCIDOS:\n\n")
            for L in o:
                days = (datetime.now().date() - datetime.strptime(L['due_date'], '%Y-%m-%d').date()).days
                name = L.get("employee_display") or "—"
                self.alerts_text.insert(tk.END, f"{name}: ${float(L['amount']):.2f} - {days} días de retraso\n")
        self.alerts_text.config(state=tk.DISABLED)

    def show_report(self):
        win = tk.Toplevel(self.parent); win.title("Reportes de Préstamos"); win.geometry("640x460"); win.transient(self.parent)
        main = ttk.Frame(win, padding=10); main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="Inicio:").grid(row=0, column=0, sticky=tk.W, pady=4)
        start = DateEntry(main, date_pattern='yyyy-mm-dd'); start.set_date(datetime.now() - timedelta(days=30))
        start.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main, text="Fin:").grid(row=1, column=0, sticky=tk.W, pady=4)
        end = DateEntry(main, date_pattern='yyyy-mm-dd'); end.set_date(datetime.now())
        end.grid(row=1, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main, text="Estado:").grid(row=2, column=0, sticky=tk.W, pady=4)
        status_cb = ttk.Combobox(main, state="readonly", values=('', 'active', 'paid', 'overdue'), width=14)
        status_cb.set(''); status_cb.grid(row=2, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        cols = ('employee', 'amount', 'issued', 'due', 'status', 'paid', 'balance')
        tree = ttk.Treeview(main, columns=cols, show='headings', height=14)
        headers = {'employee': 'Empleado', 'amount': 'Monto', 'issued':'Fecha Préstamo', 'due':'Fecha Vencimiento',
                   'status':'Estado', 'paid':'Pagado', 'balance':'Saldo'}
        widths = {'employee':180, 'amount':90, 'issued':110, 'due':110, 'status':80, 'paid':90, 'balance':90}
        for c in cols:
            tree.heading(c, text=headers[c])
            tree.column(c, width=widths[c], anchor=tk.W if c=='employee' else tk.CENTER)
        ysb = ttk.Scrollbar(main, orient=tk.VERTICAL, command=tree.yview); tree.configure(yscrollcommand=ysb.set)

        tree.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW, pady=(8, 0))
        ysb.grid(row=3, column=2, sticky=tk.NS, pady=(8, 0))

        totals_lbl = ttk.Label(main, text="Totales: Monto=0.00, Pagado=0.00, Saldo=0.00", font=('Segoe UI', 9, 'bold'))
        totals_lbl.grid(row=4, column=0, columnspan=2, sticky=tk.E, pady=(6, 0))

        def generate():
            s = start.get_date().strftime('%Y-%m-%d')
            e = end.get_date().strftime('%Y-%m-%d')
            st = status_cb.get() or None
            for i in tree.get_children():
                tree.delete(i)
            data = self.controller.get_loans_report(s, e, st)
            t_amount = t_paid = t_bal = 0.0
            for L in data:
                tree.insert('', 'end', values=(
                    L['employee_display'], f"${float(L['amount']):.2f}",
                    L['date_issued'], L['due_date'], self._translate_status(L['status']),
                    f"${float(L['total_paid']):.2f}", f"${float(L['balance']):.2f}"
                ), tags=('paid',) if L['status']=='paid' else ('overdue',) if L['status']=='overdue' else ())
                t_amount += float(L['amount'])
                t_paid += float(L['total_paid'])
                t_bal += float(L['balance'])
            tree.tag_configure('overdue', background='#ffcccc'); tree.tag_configure('paid', background='#ccffcc')
            totals_lbl.config(text=f"Totales: Monto=${t_amount:.2f}, Pagado=${t_paid:.2f}, Saldo=${t_bal:.2f}")

        ttk.Button(main, text="Generar Reporte", command=generate).grid(row=5, column=0, columnspan=2, pady=10)

        main.columnconfigure(1, weight=1); main.rowconfigure(3, weight=1)
        generate()

    # -----------------------------
    # EDICIÓN / ELIMINACIÓN
    # -----------------------------
    def edit_loan(self):
        sel = self.loans_tree.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Seleccione un préstamo para editar")
            return
        loan_id = self.loans_tree.item(sel[0])['values'][0]
        loan = self.controller.get_loan_by_id(loan_id)
        if not loan:
            messagebox.showerror("Error", "No se pudo obtener el préstamo")
            return

        win = tk.Toplevel(self.parent); win.title("Editar Préstamo"); win.geometry("480x340"); win.transient(self.parent); win.grab_set()
        main = ttk.Frame(win, padding=10); main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="Empleado:").grid(row=0, column=0, sticky=tk.W, pady=4)
        emp_cb = ttk.Combobox(main, state="readonly", width=30)
        emps = self.controller.list_employees()
        emp_cb['values'] = [f"{e['id']} - {e['first_name']} {e['last_name']}" for e in emps]
        current_emp = f"{loan.get('employee_id') or ''} - {loan.get('first_name','') or ''} {loan.get('last_name','') or ''}".strip()
        # fallback
        if loan.get('employee_id'):
            emp_cb.set(f"{loan['employee_id']} - {loan.get('first_name','')} {loan.get('last_name','')}")
        elif emp_cb['values']:
            emp_cb.set(emp_cb['values'][0])

        ttk.Label(main, text="Monto:").grid(row=1, column=0, sticky=tk.W, pady=4)
        amount_e = ttk.Entry(main); amount_e.insert(0, str(loan['amount'])); amount_e.grid(row=1, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main, text="Fecha préstamo:").grid(row=2, column=0, sticky=tk.W, pady=4)
        d1 = DateEntry(main, date_pattern='yyyy-mm-dd'); d1.set_date(datetime.strptime(loan['date_issued'], '%Y-%m-%d'))
        d1.grid(row=2, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main, text="Vence:").grid(row=3, column=0, sticky=tk.W, pady=4)
        d2 = DateEntry(main, date_pattern='yyyy-mm-dd'); d2.set_date(datetime.strptime(loan['due_date'], '%Y-%m-%d'))
        d2.grid(row=3, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main, text="Interés (%):").grid(row=4, column=0, sticky=tk.W, pady=4)
        intr_e = ttk.Entry(main); intr_e.insert(0, str(loan['interest_rate'])); intr_e.grid(row=4, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main, text="Notas:").grid(row=5, column=0, sticky=tk.W, pady=4)
        notes_e = ttk.Entry(main); notes_e.insert(0, loan.get('notes') or ''); notes_e.grid(row=5, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        def save():
            try:
                emp_id = None
                val = emp_cb.get()
                if val and " - " in val:
                    emp_id = int(val.split(" - ", 1)[0])
                amount = float(amount_e.get())
                di = d1.get_date().strftime('%Y-%m-%d')
                dd = d2.get_date().strftime('%Y-%m-%d')
                intr = float(intr_e.get() or "0")
                notes = notes_e.get()
                self.controller.update_loan(loan_id, emp_id, amount, di, dd, intr, notes)
                messagebox.showinfo("Préstamo", "Actualizado correctamente")
                win.destroy()
                self.load_loans()
                self.update_alerts()
            except ValueError:
                messagebox.showerror("Error", "Valores inválidos")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        btns = ttk.Frame(main); btns.grid(row=6, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Guardar", command=save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancelar", command=win.destroy).pack(side=tk.LEFT, padx=6)
        main.columnconfigure(1, weight=1)

    def delete_loan(self):
        sel = self.loans_tree.selection()
        if not sel:
            messagebox.showwarning("Advertencia", "Seleccione un préstamo para eliminar")
            return
        loan_id = self.loans_tree.item(sel[0])['values'][0]
        emp = self.loans_tree.item(sel[0])['values'][1]
        if messagebox.askyesno("Confirmar", f"¿Eliminar el préstamo de '{emp}'? Se eliminarán también sus pagos."):
            try:
                self.controller.delete_loan(loan_id)
                messagebox.showinfo("Préstamo", "Eliminado correctamente")
                self.load_loans()
                self.update_alerts()
            except Exception as e:
                messagebox.showerror("Error", str(e))
