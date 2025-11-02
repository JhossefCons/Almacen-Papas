# modules/payroll/payroll_controller.py
"""
Controlador de Nómina (Historial de Pagos)
- Procesa pagos de salario (confirmando montos) y los guarda en historial.
- Calcula deducciones de préstamos.
- Registra movimientos correspondientes en Caja.
- Consulta historial de pagos por rango de fechas.
- **Actualiza el salario base del empleado si se modifica durante el pago.**
"""
from datetime import datetime
from modules.loans.loans_controller import LoansController
from modules.cash_register.cash_register_controller import CashRegisterController
# --- CAMBIO: Importar el controlador de empleados ---
from modules.employees.employees_controller import EmployeesController
from typing import List, Dict, Tuple, Optional

class PayrollController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth = auth_manager
        self.loans_controller = LoansController(database, auth_manager)
        self.cash_controller = CashRegisterController(database, auth_manager)
        # --- CAMBIO: Instanciar el controlador de empleados ---
        self.employees_controller = EmployeesController(database, auth_manager)

    def _get_user_id(self):
        if not self.auth.current_user:
            raise PermissionError("Usuario no autenticado.")
        return self.auth.current_user if isinstance(self.auth.current_user, int) else self.auth.current_user.get('id')

    def list_employees(self, only_active=True):
        """Obtiene lista de empleados (delegado a loans_controller)."""
        return self.loans_controller.list_employees(only_active=only_active)

    def get_employee_details(self, employee_id: int) -> Optional[Dict]:
        """Obtiene detalles de un empleado, incluyendo salario base."""
        # --- CAMBIO: Usar el controlador de empleados ---
        return self.employees_controller.get_employee(employee_id)

    def calculate_deductions_for_payroll(self, employee_id: int, gross_salary: float) -> Tuple[float, List[Dict]]:
        """
        Calcula el total a deducir de préstamos activos para un salario bruto dado.
        Devuelve (total_deduccion, detalle_prestamos_afectados).
        """
        if gross_salary <= 0:
            return 0.0, []

        # Obtener préstamos activos con saldo pendiente del empleado
        loans = self.loans_controller.get_loans(employee_id=employee_id, status_filter='active')
        loans += self.loans_controller.get_loans(employee_id=employee_id, status_filter='overdue') # Incluir vencidos

        loans_with_balance = []
        for loan_dict in loans:
            summary = self.loans_controller.get_loan_summary(loan_dict['id'])
            if summary and summary['balance'] > 0.01: # Solo si hay saldo real
                loans_with_balance.append({'loan': loan_dict, 'balance': summary['balance']})

        # Ordenar por fecha de emisión para pagar los más antiguos primero
        loans_with_balance.sort(key=lambda item: item['loan']['date_issued'])

        remaining_salary_for_deduction = gross_salary
        total_deducted = 0.0
        deduction_details = [] # [{'loan_id': id, 'amount_deducted': amount}]

        for item in loans_with_balance:
            if remaining_salary_for_deduction <= 0.01:
                break # No hay más salario del cual deducir

            loan = item['loan']
            balance = item['balance']
            amount_to_deduct = min(remaining_salary_for_deduction, balance)

            deduction_details.append({
                'loan_id': loan['id'],
                'amount_deducted': round(amount_to_deduct, 2)
            })
            total_deducted += amount_to_deduct
            remaining_salary_for_deduction -= amount_to_deduct

        return round(total_deducted, 2), deduction_details

    def process_payroll_payment(self, employee_id: int, payment_date: str,
                                gross_salary_paid: float, # Salario base confirmado/ingresado
                                net_amount_paid: float, # Monto neto realmente pagado
                                loan_deductions_applied: float, # Deducción confirmada
                                deduction_details: List[Dict], # Detalle de a qué préstamos se aplicó
                                payment_method: str = "cash",
                                register_in_cash: bool = True) -> int:
        """
        Procesa y guarda un pago de nómina en el historial.
        Aplica las deducciones a los préstamos correspondientes.
        Registra los movimientos en Caja (Egreso neto + Ingreso por deducción).
        **Actualiza el salario del empleado si el 'gross_salary_paid' es diferente.**
        Devuelve el ID del registro en payroll_history.
        """
        if not self.auth.has_permission('admin'):
            raise PermissionError("Solo los administradores pueden procesar nómina")

        user_id = self._get_user_id()
        emp = self.get_employee_details(employee_id)
        if not emp:
            raise ValueError("Empleado no encontrado")

        if gross_salary_paid < 0 or net_amount_paid < 0 or loan_deductions_applied < 0:
            raise ValueError("Los montos de salario, pago neto y deducciones no pueden ser negativos.")

        calculated_net = round(gross_salary_paid - loan_deductions_applied, 2)
        if abs(calculated_net - net_amount_paid) > 0.01:
            print(f"Advertencia: El Neto Calculado ({calculated_net}) difiere del Neto Pagado ({net_amount_paid})")

        period_date = datetime.strptime(payment_date, '%Y-%m-%d')
        period_year = period_date.year
        period_month = period_date.month

        conn = self.db.connect()
        cursor = conn.cursor()
        try:
            cash_id_payment = None
            cash_id_deduction = None
            emp_name = f"{emp['first_name']} {emp['last_name']}".strip()

            # --- CAMBIO: Actualizar el salario del empleado si cambió ---
            current_salary = float(emp.get('salary', 0.0))
            if abs(current_salary - gross_salary_paid) > 0.01:
                self.employees_controller.update_employee(
                    emp_id=employee_id,
                    first_name=emp['first_name'],
                    last_name=emp['last_name'],
                    salary=gross_salary_paid, # El nuevo salario
                    is_active=emp['is_active']
                )
            # --- FIN DEL CAMBIO ---

            # 1. Registrar movimientos en Caja (si aplica)
            if register_in_cash:
                # Egreso por el neto pagado
                if net_amount_paid > 0.01:
                    cash_id_payment = self.cash_controller.add_transaction(
                        date=payment_date,
                        type="expense",
                        description=f"Pago salario {period_year}-{period_month:02d}: {emp_name}",
                        amount=net_amount_paid,
                        payment_method=payment_method,
                        category="nomina_pago"
                    )
                # Ingreso por la deducción (si hubo)
                if loan_deductions_applied > 0.01:
                     cash_id_deduction = self.cash_controller.add_transaction(
                        date=payment_date,
                        type="income",
                        description=f"Deducción nómina {period_year}-{period_month:02d}: {emp_name}",
                        amount=loan_deductions_applied,
                        payment_method=payment_method,
                        category="nomina_deduccion_prestamo"
                    )

            # 2. Registrar el pago de nómina en el historial
            cursor.execute(
                """
                INSERT INTO payroll_history (
                    employee_id, payment_date, period_year, period_month,
                    gross_salary_paid, loan_deductions, net_paid,
                    cash_register_id_payment, cash_register_id_deduction, user_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (employee_id, payment_date, period_year, period_month,
                 gross_salary_paid, loan_deductions_applied, net_amount_paid,
                 cash_id_payment, cash_id_deduction, user_id)
            )
            payroll_history_id = cursor.lastrowid

            # 3. Aplicar las deducciones a los pagos de préstamos
            if loan_deductions_applied > 0.01 and deduction_details:
                for detail in deduction_details:
                    loan_id = detail['loan_id']
                    amount_deducted = detail['amount_deducted']
                    if amount_deducted > 0.01:
                        self.loans_controller.add_payment(
                            loan_id=loan_id,
                            payment_date=payment_date,
                            amount=amount_deducted,
                            notes=f"Deducción nómina {period_year}-{period_month:02d}",
                            register_in_cash=False,
                            is_payroll_deduction=True
                        )

            conn.commit()
            return payroll_history_id

        except Exception as e:
            conn.rollback()
            raise e

    def get_payroll_history(self, start_date: str, end_date: str) -> Tuple[List[Dict], Dict[str, float]]:
        """
        Obtiene el historial de pagos de nómina dentro de un rango de fechas.
        Devuelve (lista_de_pagos, totales_del_periodo).
        """
        query = """
            SELECT
                ph.*,
                e.first_name, e.last_name,
                u.username
            FROM payroll_history ph
            JOIN employees e ON ph.employee_id = e.id
            LEFT JOIN users u ON ph.user_id = u.id
            WHERE ph.payment_date BETWEEN ? AND ?
            ORDER BY ph.payment_date DESC, e.last_name ASC, e.first_name ASC
        """
        rows = self.db.execute_query(query, (start_date, end_date))

        history_list = []
        totals = {
            "gross": 0.0,
            "deductions": 0.0,
            "net": 0.0,
            "count": 0
        }

        if rows:
            for row in rows:
                item = dict(row)
                item['employee_name'] = f"{item['first_name']} {item['last_name']}".strip()
                history_list.append(item)
                totals["gross"] += item['gross_salary_paid']
                totals["deductions"] += item['loan_deductions']
                totals["net"] += item['net_paid']
                totals["count"] += 1

        # Redondear totales
        for key in ["gross", "deductions", "net"]:
            totals[key] = round(totals[key], 2)

        return history_list, totals