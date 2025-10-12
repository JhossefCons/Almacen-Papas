"""
Controlador de Nómina (reporte mensual)
- Calcula por empleado: salario bruto, deducción de préstamos (pagos marcados),
  neto calculado (bruto - deducción), neto pagado en Caja y diferencias.

Compatibilidad:
- Deducciones tomadas de loan_payments con bandera is_payroll_deduction=1.
- Si la bandera aún no existe/se pobló, fallback por notas que comienzan con 'Deducción por nómina'.
- Caja: usa las mismas categorías/descripciones que genera LoansController:
    * Ingreso por deducción:   type='income',  category='Pago préstamo empleado (nómina)',
                               description LIKE 'Deducción nómina - {Nombre}%'
    * Egreso por pago sueldo:  type='expense', category='Nómina',
                               description LIKE 'Pago salario - {Nombre}%'
"""
from modules.loans.loans_controller import LoansController

class PayrollController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth = auth_manager
        self.loans = LoansController(database, auth_manager)
        self._ensure_schema()

    def _ensure_schema(self):
        # Asegurar columna y el índice para marcar deducciones por nómina
        try:
            self.db.execute_query(
                "ALTER TABLE loan_payments ADD COLUMN is_payroll_deduction INTEGER NOT NULL DEFAULT 0"
            )
        except Exception:
            pass
        try:
            self.db.execute_query(
                "CREATE INDEX IF NOT EXISTS idx_lp_is_payroll ON loan_payments(is_payroll_deduction)"
            )
        except Exception:
            pass

    def _yyyymm(self, year: int, month: int) -> str:
        return f"{year:04d}-{month:02d}"

    def list_employees(self, only_active=True):
        q = "SELECT * FROM employees"
        if only_active:
            q += " WHERE is_active=1"
        q += " ORDER BY last_name, first_name"
        rows = self.db.execute_query(q)
        return [dict(r) for r in rows] if rows else []

    def get_month_report(self, year: int, month: int):
        ym = self._yyyymm(year, month)

        # Todos los empleados (activos e inactivos) para reportes históricos
        emps = self.db.execute_query("SELECT * FROM employees ORDER BY last_name, first_name") or []
        out = []
        totals = {"gross":0.0, "deduct":0.0, "net_calc":0.0, "net_cash":0.0, "diff":0.0}

        for r in emps:
            emp = dict(r)
            emp_id = emp["id"]
            name = f"{emp['first_name']} {emp['last_name']}".strip()
            gross = float(emp.get("salary") or 0)

            # --- Deducción por préstamos (por nómina) en ese mes ---
            # Preferimos bandera is_payroll_deduction=1; si no está poblada, fallback por nota
            q_ded = """
                SELECT COALESCE(SUM(lp.amount),0) AS s, COUNT(DISTINCT lp.loan_id) AS n
                  FROM loan_payments lp
                  JOIN loans l ON l.id = lp.loan_id
                 WHERE l.employee_id = ?
                   AND strftime('%Y-%m', lp.payment_date) = ?
                   AND (lp.is_payroll_deduction = 1 OR lp.notes LIKE 'Deducción por nómina%')
            """
            row_ded = self.db.execute_query(q_ded, (emp_id, ym))
            deducted = float(row_ded[0]["s"]) if row_ded else 0.0
            loans_count = int(row_ded[0]["n"]) if row_ded else 0

            # Neto calculado
            net_calc = max(gross - deducted, 0.0)

            # --- Neto pagado (egreso) en Caja ese mes ---
            # Compatibles con LoansController.process_payroll_payment:
            #   Egreso:  type='expense', category='Nómina', desc 'Pago salario - {name} ...'
            q_cash_net = """
                SELECT COALESCE(SUM(amount),0) s
                  FROM cash_register
                 WHERE type='expense'
                   AND category='Nómina'
                   AND strftime('%Y-%m', date)=?
                   AND description LIKE ?
            """
            desc_like = f"Pago salario - {name}%"
            r_net = self.db.execute_query(q_cash_net, (ym, desc_like)) or [{'s':0}]
            net_cash = float(r_net[0]['s'] or 0)

            # --- Ingreso por deducción (validación) ---
            #   Ingreso: type='income', category='Pago préstamo empleado (nómina)',
            #   desc 'Deducción nómina - {name} ...'
            q_cash_ded = """
                SELECT COALESCE(SUM(amount),0) s
                  FROM cash_register
                 WHERE type='income'
                   AND category='Pago préstamo empleado (nómina)'
                   AND strftime('%Y-%m', date)=?
                   AND description LIKE ?
            """
            desc_like2 = f"Deducción nómina - {name}%"
            r_ded_income = self.db.execute_query(q_cash_ded, (ym, desc_like2)) or [{'s':0}]
            cash_ded_income = float(r_ded_income[0]['s'] or 0)

            diff = net_cash - net_calc

            out.append({
                "employee_id": emp_id,
                "name": name or "—",
                "gross": round(gross,2),
                "deduct": round(deducted,2),
                "net_calc": round(net_calc,2),
                "net_cash": round(net_cash,2),
                "cash_ded_income": round(cash_ded_income,2),
                "loans_count": loans_count,
                "diff": round(diff,2),
            })

            totals["gross"] += gross
            totals["deduct"] += deducted
            totals["net_calc"] += net_calc
            totals["net_cash"] += net_cash
            totals["diff"] += diff

        for k in totals:
            totals[k] = round(totals[k], 2)
        return out, totals
    
    def process_salary_payment(self, employee_id: int, date: str,
                               payment_method: str = "cash",
                               register_in_cash: bool = True,
                               with_loan_deduction: bool = True):
        """Paga salario desde Nómina. Si with_loan_deduction=True,
        descuenta automáticamente saldos de préstamos del empleado."""
        if not self.auth.has_permission('admin'):
            raise Exception("Solo los administradores pueden procesar nómina")

        emp = self.loans.get_employee(employee_id)
        if not emp:
            raise Exception("Empleado no existe")
        gross = float(emp["salary"] or 0)
        if gross <= 0:
            raise Exception("El salario configurado para el empleado es 0")

        total_deducted = 0.0
        breakdown = []

        if with_loan_deduction:
            # mismos criterios que LoansController.process_payroll_payment (deducción marcada)
            loans = self.loans.get_loans(employee_id=employee_id)
            loans_with_balance = []
            for L in loans:
                s = self.loans.get_loan_summary(L['id'])
                if s and s['balance'] > 0:
                    loans_with_balance.append((L, s['balance']))
            loans_with_balance.sort(key=lambda t: t[0]['date_issued'])

            remaining = gross
            for loan, bal in loans_with_balance:
                if remaining <= 0:
                    break
                pay = min(remaining, bal)
                self.loans.add_payment(
                    loan_id=loan['id'], payment_date=date, amount=pay,
                    notes="Deducción de nómina", register_in_cash=False,
                    payment_method=payment_method, is_payroll_deduction=True
                )
                remaining -= pay
                total_deducted += pay
                breakdown.append({"loan_id": loan['id'], "applied": round(pay, 2)})

        net = max(gross - total_deducted, 0.0)

        if register_in_cash:
            emp_name = self.loans.format_employee_name(emp)
            if total_deducted > 0:
                # ingreso por deducción
                from modules.cash_register.cash_register_controller import CashRegisterController
                cash = CashRegisterController(self.db, self.auth)
                cash.add_transaction(date, "income",
                                     f"Deducción préstamo vía nómina: {emp_name}",
                                     round(total_deducted, 2), payment_method, "nomina_deduccion_prestamo")
            if net > 0:
                from modules.cash_register.cash_register_controller import CashRegisterController
                cash = CashRegisterController(self.db, self.auth)
                cash.add_transaction(date, "expense",
                                     f"Pago de salario: {emp_name}",
                                     round(net, 2), payment_method, "nomina_pago")

        return {
            "employee": self.loans.format_employee_name(emp),
            "gross_salary": round(gross, 2),
            "total_deducted": round(total_deducted, 2),
            "net_paid": round(net, 2),
            "applied": breakdown
        }

