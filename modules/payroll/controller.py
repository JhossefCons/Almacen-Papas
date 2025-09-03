# modules/payroll/controller.py
"""
Controlador de Nómina (reporte mensual)
- Calcula por empleado: salario bruto, deducción de préstamos (loan_payments marcados),
  neto calculado (bruto - deducción), neto pagado en Caja y diferencias.
"""

class PayrollController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth = auth_manager
        self._ensure_indexes()

    def _ensure_indexes(self):
        try:
            self.db.execute_query("CREATE INDEX IF NOT EXISTS idx_lp_is_payroll ON loan_payments(is_payroll_deduction)")
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

        # Traer todos los empleados (activos e inactivos para reportes históricos)
        emps = self.db.execute_query("SELECT * FROM employees ORDER BY last_name, first_name") or []
        out = []
        totals = {"gross":0.0, "deduct":0.0, "net_calc":0.0, "net_cash":0.0, "diff":0.0}

        for r in emps:
            emp = dict(r)
            emp_id = emp["id"]
            name = f"{emp['first_name']} {emp['last_name']}".strip()
            gross = float(emp.get("salary") or 0)

            # Deducción por préstamos (pagos marcados como nómina en ese mes)
            q_ded = """
                SELECT COALESCE(SUM(lp.amount),0) AS s, COUNT(DISTINCT lp.loan_id) AS n
                  FROM loan_payments lp
                  JOIN loans l ON l.id = lp.loan_id
                 WHERE lp.is_payroll_deduction = 1
                   AND l.employee_id = ?
                   AND strftime('%Y-%m', lp.payment_date) = ?
            """
            row_ded = self.db.execute_query(q_ded, (emp_id, ym))
            deducted = float(row_ded[0]["s"]) if row_ded else 0.0
            loans_count = int(row_ded[0]["n"]) if row_ded else 0

            # Neto calculado
            net_calc = max(gross - deducted, 0.0)

            # Neto pagado (gasto) en Caja ese mes
            q_cash_net = """
                SELECT COALESCE(SUM(amount),0) s
                  FROM cash_register
                 WHERE type='expense'
                   AND category='nomina_pago'
                   AND strftime('%Y-%m', date)=?
                   AND description LIKE ?
            """
            desc_like = f"Pago de salario: {name}%"
            r_net = self.db.execute_query(q_cash_net, (ym, desc_like)) or [{'s':0}]
            net_cash = float(r_net[0]['s'] or 0)

            # Ingreso por deducción (validación)
            q_cash_ded = """
                SELECT COALESCE(SUM(amount),0) s
                  FROM cash_register
                 WHERE type='income'
                   AND category='nomina_deduccion_prestamo'
                   AND strftime('%Y-%m', date)=?
                   AND description LIKE ?
            """
            desc_like2 = f"Deducción préstamo vía nómina: {name}%"
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
