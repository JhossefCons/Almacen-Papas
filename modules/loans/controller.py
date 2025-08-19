"""
Controlador para el módulo de préstamos a empleados
"""
from datetime import datetime, timedelta
from database.models import Loan, LoanPayment

class LoansController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth_manager = auth_manager
    
    def add_loan(self, employee_name, amount, date_issued, due_date, interest_rate, notes):
        """Agregar un nuevo préstamo"""
        if not self.auth_manager.current_user:
            raise Exception("Usuario no autenticado")
        
        query = """
            INSERT INTO loans (employee_name, amount, date_issued, due_date, interest_rate, notes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        loan_id = self.db.execute_query(
            query, (employee_name, amount, date_issued, due_date, interest_rate, notes, self.auth_manager.current_user)
        )
        
        return loan_id
    
    def update_loan(self, loan_id, employee_name, amount, date_issued, due_date, interest_rate, notes):
        """Actualizar un préstamo existente"""
        # Verificar permisos (solo admin puede editar)
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden editar préstamos")
        
        query = """
            UPDATE loans 
            SET employee_name=?, amount=?, date_issued=?, due_date=?, interest_rate=?, notes=?
            WHERE id=?
        """
        
        self.db.execute_query(
            query, (employee_name, amount, date_issued, due_date, interest_rate, notes, loan_id)
        )
        
        return True
    
    def delete_loan(self, loan_id):
        """Eliminar un préstamo"""
        # Verificar permisos (solo admin puede eliminar)
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden eliminar préstamos")
        
        # Primero eliminar los pagos asociados
        self.db.execute_query("DELETE FROM loan_payments WHERE loan_id=?", (loan_id,))
        
        # Luego eliminar el préstamo
        query = "DELETE FROM loans WHERE id=?"
        self.db.execute_query(query, (loan_id,))
        
        return True
    
    def get_loans(self, status_filter=None, employee_filter=None):
        """Obtener préstamos con filtros opcionales"""
        query = """
            SELECT l.*, u.username 
            FROM loans l 
            LEFT JOIN users u ON l.user_id = u.id
            WHERE 1=1
        """
        params = []
        
        if status_filter:
            query += " AND l.status = ?"
            params.append(status_filter)
        
        if employee_filter:
            query += " AND l.employee_name LIKE ?"
            params.append(f"%{employee_filter}%")
        
        query += " ORDER BY l.date_issued DESC, l.created_at DESC"
        
        results = self.db.execute_query(query, params)
        return [dict(row) for row in results] if results else []
    
    def get_loan_by_id(self, loan_id):
        """Obtener un préstamo específico por ID"""
        query = "SELECT * FROM loans WHERE id = ?"
        result = self.db.execute_query(query, (loan_id,))
        return dict(result[0]) if result else None
    
    def add_payment(self, loan_id, payment_date, amount, notes):
        """Agregar un pago a un préstamo"""
        if not self.auth_manager.current_user:
            raise Exception("Usuario no autenticado")
        
        query = """
            INSERT INTO loan_payments (loan_id, payment_date, amount, notes, user_id)
            VALUES (?, ?, ?, ?, ?)
        """
        
        payment_id = self.db.execute_query(
            query, (loan_id, payment_date, amount, notes, self.auth_manager.current_user)
        )
        
        # Actualizar el estado del préstamo si está completamente pagado
        self._update_loan_status(loan_id)
        
        return payment_id
    
    def update_payment(self, payment_id, payment_date, amount, notes):
        """Actualizar un pago existente"""
        # Verificar permisos (solo admin puede editar)
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden editar pagos")
        
        query = """
            UPDATE loan_payments 
            SET payment_date=?, amount=?, notes=?
            WHERE id=?
        """
        
        self.db.execute_query(query, (payment_date, amount, notes, payment_id))
        
        # Actualizar el estado del préstamo
        payment = self.get_payment_by_id(payment_id)
        if payment:
            self._update_loan_status(payment['loan_id'])
        
        return True
    
    def delete_payment(self, payment_id):
        """Eliminar un pago"""
        # Verificar permisos (solo admin puede eliminar)
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden eliminar pagos")
        
        # Obtener el loan_id antes de eliminar para actualizar el estado después
        payment = self.get_payment_by_id(payment_id)
        
        query = "DELETE FROM loan_payments WHERE id=?"
        self.db.execute_query(query, (payment_id,))
        
        # Actualizar el estado del préstamo
        if payment:
            self._update_loan_status(payment['loan_id'])
        
        return True
    
    def get_payment_by_id(self, payment_id):
        """Obtener un pago específico por ID"""
        query = "SELECT * FROM loan_payments WHERE id = ?"
        result = self.db.execute_query(query, (payment_id,))
        return dict(result[0]) if result else None
    
    def get_loan_payments(self, loan_id):
        """Obtener todos los pagos de un préstamo"""
        query = """
            SELECT lp.*, u.username 
            FROM loan_payments lp 
            LEFT JOIN users u ON lp.user_id = u.id
            WHERE lp.loan_id = ?
            ORDER BY lp.payment_date DESC, lp.created_at DESC
        """
        
        results = self.db.execute_query(query, (loan_id,))
        return [dict(row) for row in results] if results else []
    
    def get_loan_summary(self, loan_id):
        """Obtener resumen de un préstamo (total pagado, saldo pendiente)"""
        loan = self.get_loan_by_id(loan_id)
        if not loan:
            return None
        
        payments = self.get_loan_payments(loan_id)
        total_paid = sum(float(payment['amount']) for payment in payments)
        
        # Calcular interés si aplica
        principal = float(loan['amount'])
        if float(loan['interest_rate']) > 0:
            total_due = principal * (1 + float(loan['interest_rate']) / 100)
        else:
            total_due = principal
        
        balance = total_due - total_paid
        
        # Determinar si está vencido
        due_date = datetime.strptime(loan['due_date'], '%Y-%m-%d').date()
        is_overdue = balance > 0 and due_date < datetime.now().date()
        
        return {
            'loan': loan,
            'total_paid': total_paid,
            'total_due': total_due,
            'balance': balance,
            'is_overdue': is_overdue,
            'payments': payments
        }
    
    def _update_loan_status(self, loan_id):
        """Actualizar el estado de un préstamo basado en los pagos"""
        summary = self.get_loan_summary(loan_id)
        if not summary:
            return
        
        new_status = 'active'
        if summary['balance'] <= 0:
            new_status = 'paid'
        elif summary['is_overdue']:
            new_status = 'overdue'
        
        query = "UPDATE loans SET status = ? WHERE id = ?"
        self.db.execute_query(query, (new_status, loan_id))
    
    def get_overdue_loans(self):
        """Obtener préstamos vencidos"""
        query = "SELECT * FROM loans WHERE status = 'overdue' ORDER BY due_date"
        results = self.db.execute_query(query)
        return [dict(row) for row in results] if results else []
    
    def get_loans_report(self, start_date=None, end_date=None, status_filter=None):
        """Generar reporte de préstamos"""
        query = """
            SELECT 
                l.*,
                (SELECT COALESCE(SUM(amount), 0) FROM loan_payments WHERE loan_id = l.id) as total_paid,
                (l.amount * (1 + l.interest_rate / 100)) - 
                (SELECT COALESCE(SUM(amount), 0) FROM loan_payments WHERE loan_id = l.id) as balance
            FROM loans l
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND l.date_issued >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND l.date_issued <= ?"
            params.append(end_date)
        
        if status_filter:
            query += " AND l.status = ?"
            params.append(status_filter)
        
        query += " ORDER BY l.date_issued DESC"
        
        results = self.db.execute_query(query, params)
        return [dict(row) for row in results] if results else []