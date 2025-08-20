"""
Controlador para el módulo de caja
"""
from datetime import datetime, timedelta
from database.models import CashTransaction

class CashRegisterController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth_manager = auth_manager
    
    def add_transaction(self, date, type, description, amount, payment_method, category):
        """Agregar una nueva transacción de caja"""
        if not self.auth_manager.current_user:
            raise Exception("Usuario no autenticado")
        
        query = """
            INSERT INTO cash_register (date, type, description, amount, payment_method, category, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        transaction_id = self.db.execute_query(
            query, (date, type, description, amount, payment_method, category, self.auth_manager.current_user)
        )
        
        return transaction_id
    
    def update_transaction(self, transaction_id, date, type, description, amount, payment_method, category):
        """Actualizar una transacción existente"""
        # Verificar permisos (solo admin puede editar)
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden editar transacciones")
        
        query = """
            UPDATE cash_register 
            SET date=?, type=?, description=?, amount=?, payment_method=?, category=?
            WHERE id=?
        """
        
        self.db.execute_query(
            query, (date, type, description, amount, payment_method, category, transaction_id)
        )
        
        return True
    
    def delete_transaction(self, transaction_id):
        """Eliminar una transacción"""
        # Verificar permisos (solo admin puede eliminar)
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden eliminar transacciones")
        
        query = "DELETE FROM cash_register WHERE id=?"
        self.db.execute_query(query, (transaction_id,))
        return True
    
    def get_transactions(self, start_date=None, end_date=None, type_filter=None, payment_method_filter=None):
        """Obtener transacciones con filtros opcionales"""
        query = """
            SELECT cr.*, u.username 
            FROM cash_register cr 
            LEFT JOIN users u ON cr.user_id = u.id
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND cr.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND cr.date <= ?"
            params.append(end_date)
        
        if type_filter:
            query += " AND cr.type = ?"
            params.append(type_filter)
        
        if payment_method_filter:
            query += " AND cr.payment_method = ?"
            params.append(payment_method_filter)
        
        query += " ORDER BY cr.date DESC, cr.created_at DESC"
        
        results = self.db.execute_query(query, params)
        return [dict(row) for row in results] if results else []
    
    def get_daily_balance(self, date):
        """Obtener el balance diario para una fecha específica"""
        query_income = """
            SELECT COALESCE(SUM(amount), 0) as total_income 
            FROM cash_register 
            WHERE date = ? AND type = 'income'
        """
        query_expense = """
            SELECT COALESCE(SUM(amount), 0) as total_expense 
            FROM cash_register 
            WHERE date = ? AND type = 'expense'
        """
        
        income_result = self.db.execute_query(query_income, (date,))
        expense_result = self.db.execute_query(query_expense, (date,))
        
        total_income = income_result[0][0] if income_result else 0
        total_expense = expense_result[0][0] if expense_result else 0
        
        return {
            'date': date,
            'income': total_income,
            'expense': total_expense,
            'balance': total_income - total_expense
        }
    
    def get_period_balance(self, start_date, end_date):
        """Obtener el balance para un período específico"""
        query_income = """
            SELECT COALESCE(SUM(amount), 0) as total_income 
            FROM cash_register 
            WHERE date BETWEEN ? AND ? AND type = 'income'
        """
        query_expense = """
            SELECT COALESCE(SUM(amount), 0) as total_expense 
            FROM cash_register 
            WHERE date BETWEEN ? AND ? AND type = 'expense'
        """
        
        income_result = self.db.execute_query(query_income, (start_date, end_date))
        expense_result = self.db.execute_query(query_expense, (start_date, end_date))
        
        total_income = income_result[0][0] if income_result else 0
        total_expense = expense_result[0][0] if expense_result else 0
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'income': total_income,
            'expense': total_expense,
            'balance': total_income - total_expense
        }
    
    def get_cash_flow_report(self, start_date, end_date, group_by='day'):
        """Generar reporte de flujo de caja"""
        if group_by == 'day':
            group_clause = "GROUP BY date ORDER BY date"
        elif group_by == 'week':
            group_clause = "GROUP BY strftime('%Y-%W', date) ORDER BY date"
        elif group_by == 'month':
            group_clause = "GROUP BY strftime('%Y-%m', date) ORDER BY date"
        else:
            group_clause = "GROUP BY date ORDER BY date"
        
        query = f"""
            SELECT 
                date,
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense,
                SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END) as balance
            FROM cash_register 
            WHERE date BETWEEN ? AND ?
            {group_clause}
        """
        
        results = self.db.execute_query(query, (start_date, end_date))
        return [dict(row) for row in results] if results else []
    
    def get_monthly_summary(self, year=None):
    """Obtener resumen mensual para gráficos"""
    if not year:
        year = datetime.now().year
    
    query = """
        SELECT 
            strftime('%Y-%m', date) as month,
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense,
            SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END) as balance
        FROM cash_register 
        WHERE strftime('%Y', date) = ?
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month
    """
    
    results = self.db.execute_query(query, (str(year),))
    return [dict(row) for row in results] if results else []