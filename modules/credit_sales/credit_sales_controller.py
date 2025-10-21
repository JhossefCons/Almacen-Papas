# modules/credit_sales/credit_sales_controller.py
"""
Controlador para Cuentas por Cobrar (Ventas a Crédito)
- Crea ventas que descuentan de inventario y costales.
- Permite registrar pagos parciales o totales.
- Revierte inventario si se elimina una venta a crédito.
"""

from typing import List, Dict, Tuple, Optional
from modules.inventory.inventory_controller import InventoryController
from modules.cash_register.cash_register_controller import CashRegisterController

class CreditSalesController:
    def __init__(self, database, auth_manager, cash_controller):
        self.db = database
        self.auth = auth_manager
        self.cash: CashRegisterController = cash_controller
        # Creamos nuestra propia instancia del controlador de inventario
        self.inv: InventoryController = InventoryController(database, auth_manager)

    def _get_user_id(self):
        if not self.auth.current_user:
            raise PermissionError("Usuario no autenticado.")
        return self.auth.current_user.get('id') if isinstance(self.auth.current_user, dict) else self.auth.current_user

    def create_credit_sale(self, customer_name: str, date_issued: str, due_date: Optional[str], 
                             notes: str, items: List[Dict]) -> int:
        """
        Crea una nueva venta a crédito.
        Esto descuenta el inventario y los costales INMEDIATAMENTE.
        """
        if not items:
            raise ValueError("La venta debe tener al menos un producto.")
        if not customer_name:
            raise ValueError("Debe especificar un nombre de cliente.")

        user_id = self._get_user_id()
        total_amount = sum(item['quantity'] * item['unit_price'] for item in items)
        
        conn = self.db.connect()
        cursor = conn.cursor()
        try:
            # 1. Insertar la cabecera de la venta
            cursor.execute(
                """
                INSERT INTO credit_sales 
                    (customer_name, date_issued, due_date, total_amount, status, notes, user_id, created_at)
                VALUES (?, ?, ?, ?, 'unpaid', ?, ?, CURRENT_TIMESTAMP)
                """,
                (customer_name, date_issued, due_date, total_amount, notes, user_id)
            )
            credit_sale_id = cursor.lastrowid

            # 2. Insertar items Y DESCONTAR inventario
            total_sacks_to_consume = 0
            for item in items:
                product = item['product_name']
                quality = item['quality']
                qty = int(item['quantity'])
                price = float(item['unit_price'])
                total_val = round(qty * price, 2)
                total_sacks_to_consume += qty

                # 2a. Insertar el item en la tabla de detalles
                cursor.execute(
                    """
                    INSERT INTO credit_sale_items
                        (credit_sale_id, product_name, quality, quantity, unit_price, total_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (credit_sale_id, product, quality, qty, price, total_val)
                )
                
                # 2b. Descontar del inventario (esto también consume costales implícitamente)
                # Usamos el controlador de inventario para registrar la SALIDA
                self.inv.add_inventory_record(
                    date=date_issued,
                    product_name=product,
                    quality=quality,
                    operation="exit",
                    quantity=qty,
                    unit_price=price, # Usamos el precio de venta para el registro de salida
                    supplier_customer=customer_name,
                    notes=f"Venta a crédito ID: {credit_sale_id}"
                )

            conn.commit()
            return credit_sale_id

        except Exception as e:
            conn.rollback()
            # Si algo falló (ej. no había stock), la transacción se revierte.
            raise e

    def delete_credit_sale(self, credit_sale_id: int):
        """
        Elimina una venta a crédito Y REVIERTE el inventario.
        No se debería permitir si ya tiene pagos.
        """
        summary = self.get_credit_sale_summary(credit_sale_id)
        if summary['paid'] > 0:
            raise PermissionError("No se puede eliminar una venta a crédito que ya tiene pagos registrados.")

        items = self.get_credit_sale_items(credit_sale_id)
        
        conn = self.db.connect()
        cursor = conn.cursor()
        try:
            # 1. Revertir el inventario (haciendo una ENTRADA)
            for item in items:
                self.inv.add_inventory_record(
                    date=datetime.now().strftime('%Y-%m-%d'),
                    product_name=item['product_name'],
                    quality=item['quality'],
                    operation="entry", # Operación inversa
                    quantity=item['quantity'],
                    unit_price=0, # Costo 0 porque es una reversión
                    supplier_customer=item['customer_name'], # El cliente 'devuelve'
                    notes=f"Reversión/eliminación venta a crédito ID: {credit_sale_id}"
                )
            
            # 2. Eliminar la venta (ON DELETE CASCADE se encarga de items y payments)
            cursor.execute("DELETE FROM credit_sales WHERE id = ?", (credit_sale_id,))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def update_credit_sale_details(self, credit_sale_id: int, customer_name: str, due_date: Optional[str], notes: str):
        """Actualiza solo los detalles no financieros de la venta."""
        if not customer_name:
            raise ValueError("El nombre del cliente no puede estar vacío.")
        self.db.execute_query(
            "UPDATE credit_sales SET customer_name = ?, due_date = ?, notes = ? WHERE id = ?",
            (customer_name, due_date, notes, credit_sale_id)
        )

    def add_payment(self, credit_sale_id: int, payment_date: str, amount: float, payment_method: str, notes: str):
        """Añade un pago a una venta a crédito y actualiza el estado si se paga por completo."""
        if amount <= 0:
            raise ValueError("El monto del pago debe ser positivo.")
        
        user_id = self._get_user_id()
        summary = self.get_credit_sale_summary(credit_sale_id)
        
        if (summary['balance'] - amount) < -0.01: # Permitir un pequeño margen de error
            raise ValueError(f"El pago (S/{amount:.2f}) excede el saldo pendiente (S/{summary['balance']:.2f}).")
        
        conn = self.db.connect()
        cursor = conn.cursor()
        try:
            # 1. Registrar el ingreso en Caja
            sale_info = self.db.execute_query("SELECT customer_name FROM credit_sales WHERE id = ?", (credit_sale_id,))[0]
            cash_id = self.cash.add_transaction(
                date=payment_date,
                type="income",
                description=f"Pago crédito cliente: {sale_info['customer_name']} (Venta ID: {credit_sale_id})",
                amount=amount,
                payment_method=payment_method,
                category="pago_credito_cliente"
            )
            
            # 2. Registrar el pago en la tabla de pagos
            cursor.execute(
                """
                INSERT INTO credit_sale_payments
                    (credit_sale_id, payment_date, amount, payment_method, notes, user_id, cash_register_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (credit_sale_id, payment_date, amount, payment_method, notes, user_id, cash_id)
            )
            
            # 3. Actualizar estado de la venta si se saldó
            new_balance = summary['balance'] - amount
            if new_balance < 0.01: # Si el saldo es 0 o muy cercano
                cursor.execute(
                    "UPDATE credit_sales SET status = 'paid', paid_at = ? WHERE id = ?",
                    (payment_date, credit_sale_id)
                )
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def get_credit_sale_summary(self, credit_sale_id: int) -> Dict[str, float]:
        """Devuelve el total, pagado y saldo de una venta a crédito."""
        total_row = self.db.execute_query("SELECT total_amount FROM credit_sales WHERE id = ?", (credit_sale_id,))
        paid_row = self.db.execute_query("SELECT COALESCE(SUM(amount), 0) as paid FROM credit_sale_payments WHERE credit_sale_id = ?", (credit_sale_id,))
        
        total = float(total_row[0]['total_amount']) if total_row else 0.0
        paid = float(paid_row[0]['paid']) if paid_row else 0.0
        balance = round(total - paid, 2)
        
        return {"total": total, "paid": paid, "balance": balance}

    def get_all_credit_sales(self, start_date: str, end_date: str, status: str) -> List[Dict]:
        """Obtiene todas las ventas a crédito con filtros."""
        query = ["SELECT * FROM credit_sales WHERE date_issued BETWEEN ? AND ?"]
        params = [start_date, end_date]
        
        if status == 'unpaid':
            query.append("AND status = 'unpaid'")
        elif status == 'paid':
            query.append("AND status = 'paid'")
            
        query.append("ORDER BY date_issued DESC, id DESC")
        
        rows = self.db.execute_query(" ".join(query), tuple(params))
        return [dict(r) for r in rows] if rows else []

    def get_credit_sale_items(self, credit_sale_id: int) -> List[Dict]:
        """Obtiene los productos de una venta a crédito específica."""
        # Necesitamos el nombre del cliente para la reversión
        rows = self.db.execute_query(
            """
            SELECT csi.*, cs.customer_name 
            FROM credit_sale_items csi
            JOIN credit_sales cs ON cs.id = csi.credit_sale_id
            WHERE csi.credit_sale_id = ?
            """,
            (credit_sale_id,)
        )
        return [dict(r) for r in rows] if rows else []

    def get_credit_sale_payments(self, credit_sale_id: int) -> List[Dict]:
        """Obtiene el historial de pagos de una venta a crédito."""
        rows = self.db.execute_query(
            "SELECT * FROM credit_sale_payments WHERE credit_sale_id = ? ORDER BY payment_date ASC",
            (credit_sale_id,)
        )
        return [dict(r) for r in rows] if rows else []