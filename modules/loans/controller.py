# modules/loans/controller.py
"""
Controlador para el módulo de préstamos a empleados
- Empleados (utilidades mínimas por si no existe el módulo)
- Préstamos ligados a employee_id
- Pagos (marca deducción nómina cuando aplique)
- Impacto en Caja: préstamos, pagos y nómina
"""

from datetime import datetime
from modules.cash_register.controller import CashRegisterController


class LoansController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth_manager = auth_manager
        self.cash = CashRegisterController(database, auth_manager)
        self._ensure_schema()  # <- importante

    def _ensure_schema(self):
        """Garantiza columnas/tablas requeridas: employees, loans.employee_id, loan_payments.is_payroll_deduction"""
        # employees (por si no existe el módulo de empleados aún)
        self.db.execute_query("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                salary REAL NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # columna loans.employee_id
        try:
            self.db.execute_query("SELECT employee_id FROM loans LIMIT 1")
        except Exception:
            self.db.execute_query("ALTER TABLE loans ADD COLUMN employee_id INTEGER")

        # columna loan_payments.is_payroll_deduction
        try:
            self.db.execute_query("SELECT is_payroll_deduction FROM loan_payments LIMIT 1")
        except Exception:
            self.db.execute_query("ALTER TABLE loan_payments ADD COLUMN is_payroll_deduction INTEGER DEFAULT 0")

        # índices útiles
        try:
            self.db.execute_query("CREATE INDEX IF NOT EXISTS idx_lp_payroll ON loan_payments(is_payroll_deduction)")
        except Exception:
            pass

    # ------------ Utilidades Empleados (mínimas) ------------
    def add_employee(self, first_name: str, last_name: str, salary: float):
        if not self.auth_manager.has_permission("admin"):
            raise Exception("Solo los administradores pueden crear empleados")
        if not first_name or not last_name:
            raise Exception("Nombre y apellido son obligatorios")
        s = float(salary)
        if s < 0:
            raise Exception("El salario no puede ser negativo")
        return self.db.execute_query(
            "INSERT INTO employees (first_name, last_name, salary) VALUES (?, ?, ?)",
            (first_name.strip(), last_name.strip(), s)
        )

    def list_employees(self, only_active=True):
        q = "SELECT * FROM employees"
        if only_active:
            q += " WHERE is_active=1"
        q += " ORDER BY last_name, first_name"
        rows = self.db.execute_query(q)
        return [dict(r) for r in rows] if rows else []

    def get_employee(self, emp_id: int):
        r = self.db.execute_query("SELECT * FROM employees WHERE id=?", (emp_id,))
        return dict(r[0]) if r else None

    def format_employee_name(self, emp_row: dict):
        if not emp_row:
            return ""
        return f"{emp_row['first_name']} {emp_row['last_name']}"

    # -------------------- Préstamos --------------------
    def add_loan(self, employee_id: int, amount: float, date_issued: str,
                 due_date: str, interest_rate: float, notes: str,
                 register_in_cash: bool = True, payment_method: str = "cash"):
        # solo admin
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden crear préstamos")

        emp = self.get_employee(employee_id)
        if not emp:
            raise Exception("Empleado no existe")

        if float(amount) <= 0:
            raise Exception("El monto debe ser mayor a cero")
        if float(interest_rate) < 0:
            raise Exception("La tasa de interés no puede ser negativa")
        if due_date <= date_issued:
            raise Exception("La fecha de vencimiento debe ser posterior a la fecha de préstamo")

        emp_name = self.format_employee_name(emp)
        loan_id = self.db.execute_query(
            """
            INSERT INTO loans (employee_name, amount, date_issued, due_date, interest_rate, notes, user_id, employee_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (emp_name, float(amount), date_issued, due_date, float(interest_rate), (notes or ""),
             self.auth_manager.current_user, employee_id)
        )

        if register_in_cash:
            self.cash.add_transaction(date_issued, "expense",
                                      f"Préstamo a empleado: {emp_name}",
                                      float(amount), payment_method, "prestamo_empleado")
        return loan_id

    def update_loan(self, loan_id, employee_id, amount, date_issued, due_date, interest_rate, notes):
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden editar préstamos")
        emp = self.get_employee(employee_id) if employee_id else None
        emp_name = self.format_employee_name(emp) if emp else None
        self.db.execute_query(
            """
            UPDATE loans
               SET employee_id = COALESCE(?, employee_id),
                   employee_name = COALESCE(?, employee_name),
                   amount=?, date_issued=?, due_date=?, interest_rate=?, notes=?
             WHERE id=?
            """,
            (employee_id, emp_name, float(amount), date_issued, due_date, float(interest_rate), (notes or ""), loan_id)
        )
        return True

    def delete_loan(self, loan_id):
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden eliminar préstamos")
        self.db.execute_query("DELETE FROM loan_payments WHERE loan_id=?", (loan_id,))
        self.db.execute_query("DELETE FROM loans WHERE id=?", (loan_id,))
        return True

    def get_loans(self, status_filter=None, employee_filter=None, employee_id=None):
        q = """
        SELECT l.*, u.username, e.first_name, e.last_name
          FROM loans l
     LEFT JOIN users u ON l.user_id = u.id
     LEFT JOIN employees e ON l.employee_id = e.id
         WHERE 1=1
        """
        p = []
        if status_filter:
            q += " AND l.status = ?"; p.append(status_filter)
        if employee_filter:
            q += " AND (l.employee_name LIKE ? OR (e.first_name || ' ' || e.last_name) LIKE ?)"
            like = f"%{employee_filter}%"; p.extend([like, like])
        if employee_id:
            q += " AND l.employee_id = ?"; p.append(employee_id)
        q += " ORDER BY l.date_issued DESC, l.created_at DESC"

        rows = self.db.execute_query(q, p)
        out = []
        for r in rows or []:
            d = dict(r)
            d["employee_display"] = (f"{d.get('first_name','')} {d.get('last_name','')}".strip()
                                     if d.get("first_name") else (d.get("employee_name") or "—"))
            out.append(d)
        return out

    def get_loan_by_id(self, loan_id):
        r = self.db.execute_query(
            """SELECT l.*, e.first_name, e.last_name
                 FROM loans l
            LEFT JOIN employees e ON e.id = l.employee_id
                WHERE l.id=?""", (loan_id,))
        if not r:
            return None
        d = dict(r[0])
        d["employee_display"] = (f"{d.get('first_name','')} {d.get('last_name','')}".strip()
                                 if d.get("first_name") else (d.get("employee_name") or "—"))
        return d

    # -------------------- Pagos --------------------
    def add_payment(self, loan_id, payment_date, amount, notes,
                    register_in_cash: bool = True, payment_method: str = "cash",
                    is_payroll_deduction: bool = False):
        # si quieres que solo admin pueda registrar pagos, descomenta:
        # if not self.auth_manager.has_permission('admin'):
        #     raise Exception("Solo los administradores pueden registrar pagos")

        if not self.auth_manager.current_user:
            raise Exception("Usuario no autenticado")
        if float(amount) <= 0:
            raise Exception("El monto del pago debe ser mayor a cero")

        pay_id = self.db.execute_query(
            """
            INSERT INTO loan_payments (loan_id, payment_date, amount, notes, user_id, is_payroll_deduction)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (loan_id, payment_date, float(amount), (notes or ""), self.auth_manager.current_user,
             1 if is_payroll_deduction else 0)
        )

        if register_in_cash:
            loan = self.get_loan_by_id(loan_id)
            emp_name = loan.get("employee_display") if loan else "Empleado"
            self.cash.add_transaction(payment_date, "income",
                                      f"Pago préstamo {emp_name}",
                                      float(amount), payment_method, "prestamo_empleado")

        self._update_loan_status(loan_id)
        return pay_id

    def update_payment(self, payment_id, payment_date, amount, notes):
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden editar pagos")
        self.db.execute_query(
            "UPDATE loan_payments SET payment_date=?, amount=?, notes=? WHERE id=?",
            (payment_date, float(amount), (notes or ""), payment_id)
        )
        p = self.get_payment_by_id(payment_id)
        if p:
            self._update_loan_status(p['loan_id'])
        return True

    def delete_payment(self, payment_id):
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden eliminar pagos")
        p = self.get_payment_by_id(payment_id)
        self.db.execute_query("DELETE FROM loan_payments WHERE id=?", (payment_id,))
        if p:
            self._update_loan_status(p['loan_id'])
        return True

    def get_payment_by_id(self, payment_id):
        r = self.db.execute_query("SELECT * FROM loan_payments WHERE id=?", (payment_id,))
        return dict(r[0]) if r else None

    def get_loan_payments(self, loan_id):
        r = self.db.execute_query(
            """SELECT lp.*, u.username 
                 FROM loan_payments lp
            LEFT JOIN users u ON u.id = lp.user_id
                WHERE lp.loan_id=?
             ORDER BY lp.payment_date DESC, lp.created_at DESC""",
            (loan_id,))
        return [dict(x) for x in r] if r else []

    # -------------------- Resúmenes / Estados --------------------
    def get_loan_summary(self, loan_id):
        loan = self.get_loan_by_id(loan_id)
        if not loan:
            return None
        pays = self.get_loan_payments(loan_id)
        total_paid = sum(float(p['amount']) for p in pays)
        principal = float(loan['amount'])
        total_due = principal * (1 + float(loan['interest_rate'])/100) if float(loan['interest_rate']) > 0 else principal
        balance = total_due - total_paid
        due_date = datetime.strptime(loan['due_date'], '%Y-%m-%d').date()
        is_overdue = balance > 0 and due_date < datetime.now().date()
        return {'loan': loan, 'total_paid': total_paid, 'total_due': total_due,
                'balance': balance, 'is_overdue': is_overdue, 'payments': pays}

    def _update_loan_status(self, loan_id):
        s = self.get_loan_summary(loan_id)
        if not s:
            return
        new_status = 'active'
        if s['balance'] <= 0:
            new_status = 'paid'
        elif s['is_overdue']:
            new_status = 'overdue'
        self.db.execute_query("UPDATE loans SET status=? WHERE id=?", (new_status, loan_id))

    def get_overdue_loans(self):
        r = self.db.execute_query(
            """SELECT l.*, e.first_name, e.last_name
                 FROM loans l
            LEFT JOIN employees e ON e.id = l.employee_id
                WHERE l.status='overdue'
             ORDER BY l.due_date""")
        out = []
        for x in r or []:
            d = dict(x)
            d["employee_display"] = (f"{d.get('first_name','')} {d.get('last_name','')}".strip()
                                     if d.get("first_name") else (d.get("employee_name") or "—"))
            out.append(d)
        return out

    # -------------------- Nómina (pago con deducción) --------------------
    def process_payroll_payment(self, employee_id: int, date: str,
                                payment_method: str = "cash", register_in_cash: bool = True):
        # solo admin
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden procesar nómina")

        emp = self.get_employee(employee_id)
        if not emp:
            raise Exception("Empleado no existe")
        gross = float(emp["salary"])
        if gross <= 0:
            raise Exception("El salario configurado para el empleado es 0")

        # préstamos con saldo
        loans = self.get_loans(employee_id=employee_id)
        loans_with_balance = []
        for L in loans:
            s = self.get_loan_summary(L['id'])
            if s and s['balance'] > 0:
                loans_with_balance.append((L, s['balance']))
        loans_with_balance.sort(key=lambda t: t[0]['date_issued'])

        remaining = gross
        total_deducted = 0.0
        breakdown = []

        for loan, bal in loans_with_balance:
            if remaining <= 0:
                break
            pay = min(remaining, bal)
            # Registrar como deducción de nómina (no impacta caja directamente aquí)
            self.add_payment(loan_id=loan['id'], payment_date=date, amount=pay,
                             notes="Deducción de nómina", register_in_cash=False,
                             is_payroll_deduction=True)
            remaining -= pay
            total_deducted += pay
            breakdown.append({"loan_id": loan['id'], "applied": pay})

        net = gross - total_deducted

        if register_in_cash:
            emp_name = self.format_employee_name(emp)
            if total_deducted > 0:
                self.cash.add_transaction(date, "income",
                                          f"Deducción préstamo vía nómina: {emp_name}",
                                          round(total_deducted, 2), payment_method, "nomina_deduccion_prestamo")
            if net > 0:
                self.cash.add_transaction(date, "expense",
                                          f"Pago de salario: {emp_name}",
                                          round(net, 2), payment_method, "nomina_pago")

        return {"employee": self.format_employee_name(emp),
                "gross_salary": round(gross, 2),
                "total_deducted": round(total_deducted, 2),
                "net_paid": round(net, 2),
                "applied": breakdown}

    # -------------------- Reporte de préstamos --------------------
    def get_loans_report(self, start_date=None, end_date=None, status_filter=None):
        q = """
        SELECT l.*, e.first_name, e.last_name,
               (SELECT COALESCE(SUM(amount),0) FROM loan_payments WHERE loan_id=l.id) AS total_paid,
               (l.amount * (1 + l.interest_rate/100.0)) -
               (SELECT COALESCE(SUM(amount),0) FROM loan_payments WHERE loan_id=l.id) AS balance
          FROM loans l
     LEFT JOIN employees e ON e.id = l.employee_id
         WHERE 1=1
        """
        p = []
        if start_date:
            q += " AND l.date_issued>=?"; p.append(start_date)
        if end_date:
            q += " AND l.date_issued<=?"; p.append(end_date)
        if status_filter:
            q += " AND l.status=?"; p.append(status_filter)
        q += " ORDER BY l.date_issued DESC"

        rows = self.db.execute_query(q, p)
        data = []
        for r in rows or []:
            d = dict(r)
            d["employee_display"] = (f"{d.get('first_name','')} {d.get('last_name','')}".strip()
                                     if d.get("first_name") else (d.get("employee_name") or "—"))
            data.append(d)
        return data
