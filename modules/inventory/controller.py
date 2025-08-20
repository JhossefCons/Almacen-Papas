"""
Controlador para el módulo de inventario de papa
"""
from datetime import datetime, timedelta
from database.models import PotatoInventory

class InventoryController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth_manager = auth_manager
        
        # Definir tipos y calidades de papa permitidas
        self.potato_types = ['parda', 'amarilla', 'colorada']
        self.qualities = ['primera', 'segunda', 'tercera']
        
        # Validar combinaciones permitidas
        self.allowed_combinations = {
            'parda': ['primera', 'segunda', 'tercera'],
            'amarilla': ['primera', 'tercera'],
            'colorada': ['primera', 'segunda', 'tercera']
        }
    
    def validate_potato_combination(self, potato_type, quality):
        """Validar si la combinación tipo-calidad es permitida"""
        if potato_type not in self.allowed_combinations:
            return False
        return quality in self.allowed_combinations[potato_type]
    
    def add_inventory_record(self, date, potato_type, quality, operation, quantity, unit_price, supplier_customer, notes):
        """Agregar un nuevo registro de inventario"""
        if not self.auth_manager.current_user:
            raise Exception("Usuario no autenticado")
        
        # Validar combinación tipo-calidad
        if not self.validate_potato_combination(potato_type, quality):
            raise Exception(f"Combinación no permitida: {potato_type} - {quality}")
        
        # Calcular valor total
        total_value = quantity * unit_price
        
        query = """
            INSERT INTO potato_inventory 
            (date, potato_type, quality, operation, quantity, unit_price, total_value, supplier_customer, notes, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        record_id = self.db.execute_query(
            query, (date, potato_type, quality, operation, quantity, unit_price, total_value, 
                   supplier_customer, notes, self.auth_manager.current_user)
        )
        
        return record_id
    
    def update_inventory_record(self, record_id, date, potato_type, quality, operation, quantity, unit_price, supplier_customer, notes):
        """Actualizar un registro de inventario existente"""
        # Verificar permisos (solo admin puede editar)
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden editar registros de inventario")
        
        # Validar combinación tipo-calidad
        if not self.validate_potato_combination(potato_type, quality):
            raise Exception(f"Combinación no permitida: {potato_type} - {quality}")
        
        # Calcular valor total
        total_value = quantity * unit_price
        
        query = """
            UPDATE potato_inventory 
            SET date=?, potato_type=?, quality=?, operation=?, quantity=?, unit_price=?, 
                total_value=?, supplier_customer=?, notes=?
            WHERE id=?
        """
        
        self.db.execute_query(
            query, (date, potato_type, quality, operation, quantity, unit_price, 
                   total_value, supplier_customer, notes, record_id)
        )
        
        return True
    
    def delete_inventory_record(self, record_id):
        """Eliminar un registro de inventario"""
        # Verificar permisos (solo admin puede eliminar)
        if not self.auth_manager.has_permission('admin'):
            raise Exception("Solo los administradores pueden eliminar registros de inventario")
        
        query = "DELETE FROM potato_inventory WHERE id=?"
        self.db.execute_query(query, (record_id,))
        return True
    
    def get_inventory_records(self, start_date=None, end_date=None, potato_type_filter=None, 
                            quality_filter=None, operation_filter=None):
        """Obtener registros de inventario con filtros opcionales"""
        query = """
            SELECT pi.*, u.username 
            FROM potato_inventory pi 
            LEFT JOIN users u ON pi.user_id = u.id
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND pi.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND pi.date <= ?"
            params.append(end_date)
        
        if potato_type_filter:
            query += " AND pi.potato_type = ?"
            params.append(potato_type_filter)
        
        if quality_filter:
            query += " AND pi.quality = ?"
            params.append(quality_filter)
        
        if operation_filter:
            query += " AND pi.operation = ?"
            params.append(operation_filter)
        
        query += " ORDER BY pi.date DESC, pi.created_at DESC"
        
        results = self.db.execute_query(query, params)
        return [dict(row) for row in results] if results else []
    
    def get_current_stock(self, potato_type=None, quality=None):
        """Obtener el stock actual con filtros opcionales"""
        query = """
            SELECT 
                potato_type,
                quality,
                SUM(CASE WHEN operation = 'entry' THEN quantity ELSE -quantity END) as current_stock,
                AVG(CASE WHEN operation = 'entry' THEN unit_price ELSE NULL END) as avg_cost
            FROM potato_inventory
            WHERE 1=1
        """
        params = []
        
        if potato_type:
            query += " AND potato_type = ?"
            params.append(potato_type)
        
        if quality:
            query += " AND quality = ?"
            params.append(quality)
        
        query += " GROUP BY potato_type, quality HAVING current_stock > 0"
        
        results = self.db.execute_query(query, params)
        return [dict(row) for row in results] if results else []
    
    def get_stock_alerts(self, threshold=20):
        """Obtener alertas de stock bajo"""
        current_stock = self.get_current_stock()
        alerts = []
        
        for item in current_stock:
            if item['current_stock'] <= threshold:
                alerts.append({
                    'potato_type': item['potato_type'],
                    'quality': item['quality'],
                    'current_stock': item['current_stock'],
                    'threshold': threshold
                })
        
        return alerts
    
    def get_inventory_movement(self, start_date, end_date, group_by='day'):
        """Obtener movimiento de inventario para un período"""
        if group_by == 'day':
            group_clause = "GROUP BY date, potato_type, quality ORDER BY date"
        elif group_by == 'week':
            group_clause = "GROUP BY strftime('%Y-%W', date), potato_type, quality ORDER BY date"
        elif group_by == 'month':
            group_clause = "GROUP BY strftime('%Y-%m', date), potato_type, quality ORDER BY date"
        else:
            group_clause = "GROUP BY date, potato_type, quality ORDER BY date"
        
        query = f"""
            SELECT 
                date,
                potato_type,
                quality,
                SUM(CASE WHEN operation = 'entry' THEN quantity ELSE 0 END) as entries,
                SUM(CASE WHEN operation = 'exit' THEN quantity ELSE 0 END) as exits,
                SUM(CASE WHEN operation = 'entry' THEN total_value ELSE -total_value END) as net_value
            FROM potato_inventory 
            WHERE date BETWEEN ? AND ?
            {group_clause}
        """
        
        results = self.db.execute_query(query, (start_date, end_date))
        return [dict(row) for row in results] if results else []
    
    def get_inventory_report(self, start_date=None, end_date=None):
        """Generar reporte completo de inventario"""
        query = """
            SELECT 
                potato_type,
                quality,
                SUM(CASE WHEN operation = 'entry' THEN quantity ELSE 0 END) as total_entries,
                SUM(CASE WHEN operation = 'exit' THEN quantity ELSE 0 END) as total_exits,
                SUM(CASE WHEN operation = 'entry' THEN quantity ELSE -quantity END) as current_stock,
                SUM(CASE WHEN operation = 'entry' THEN total_value ELSE 0 END) as total_entry_value,
                SUM(CASE WHEN operation = 'exit' THEN total_value ELSE 0 END) as total_exit_value,
                AVG(CASE WHEN operation = 'entry' THEN unit_price ELSE NULL END) as avg_cost_price
            FROM potato_inventory
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " GROUP BY potato_type, quality ORDER BY potato_type, quality"
        
        results = self.db.execute_query(query, params)
        return [dict(row) for row in results] if results else []
    
    def get_cost_analysis(self, potato_type=None, quality=None):
        """Análisis de costos por tipo y calidad"""
        query = """
            SELECT 
                potato_type,
                quality,
                AVG(unit_price) as avg_price,
                MIN(unit_price) as min_price,
                MAX(unit_price) as max_price,
                COUNT(*) as transactions
            FROM potato_inventory
            WHERE operation = 'entry'
        """
        params = []
        
        if potato_type:
            query += " AND potato_type = ?"
            params.append(potato_type)
        
        if quality:
            query += " AND quality = ?"
            params.append(quality)
        
        query += " GROUP BY potato_type, quality ORDER BY potato_type, quality"
        
        results = self.db.execute_query(query, params)
        return [dict(row) for row in results] if results else []
    
    def get_stock_for_chart(self):
        """Obtener stock para gráficos"""
        return self.get_current_stock()  # Ya tenemos este método