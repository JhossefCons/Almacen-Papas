# modules/supplier_advances/supplier_advances_controller.py
"""
Controlador para Anticipos a Proveedores
- Crea un anticipo y registra el egreso en Caja.
- Aplica el anticipo contra una compra y registra el pago restante (si lo hay).
- Revierte un anticipo (con un ingreso en Caja) si se elimina.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime
from modules.cash_register.cash_register_controller import CashRegisterController

class SupplierAdvancesController:
    def __init__(self, database, auth_manager, cash_controller):
        self.db = database
        self.auth: AuthManager = auth_manager # Asumiendo que tienes AuthManager
        self.cash: CashRegisterController = cash_controller

    def _get_user_id(self):
        if not self.auth.current_user:
            raise PermissionError("Usuario no autenticado.")
        # Ajusta esto según cómo almacenes el ID del usuario
        return self.auth.current_user if isinstance(self.auth.current_user, int) else self.auth.current_user.get('id')


    def create_advance(self, supplier_name: str, date: str, amount: float, notes: str, payment_method: str) -> int:
        """
        Crea un nuevo anticipo y REGISTRA EL EGRESO en Caja.
        """
        if amount <= 0:
            raise ValueError("El monto del anticipo debe ser positivo.")
        if not supplier_name:
            raise ValueError("Debe especificar un nombre de proveedor.")
        
        user_id = self._get_user_id()
        conn = self.db.connect()
        cursor = conn.cursor()
        try:
            # 1. Registrar el GASTO en Caja
            cash_id = self.cash.add_transaction(
                date=date,
                type="expense",
                description=f"Anticipo a proveedor: {supplier_name}",
                amount=amount,
                payment_method=payment_method,
                category="anticipo_proveedor"
            )
            
            # 2. Insertar el anticipo
            cursor.execute(
                """
                INSERT INTO supplier_advances 
                    (supplier_name, date_issued, total_amount, status, notes, user_id, created_at)
                VALUES (?, ?, ?, 'unpaid', ?, ?, CURRENT_TIMESTAMP)
                """,
                (supplier_name.strip(), date, amount, notes, user_id)
            )
            advance_id = cursor.lastrowid
            
            conn.commit()
            return advance_id
        except Exception as e:
            conn.rollback()
            raise e

    def apply_advance(self, advance_id: int, app_date: str, purchase_total: float, 
                        pay_remaining: bool, payment_method: str, notes: str):
        """
        Aplica un anticipo contra una compra.
        Opcionalmente, registra el pago restante en Caja.
        """
        user_id = self._get_user_id()
        adv = self.get_advance(advance_id)
        
        if not adv or adv['status'] != 'unpaid':
            raise ValueError("Anticipo no encontrado o ya ha sido aplicado.")
        
        applied_amount = float(adv['total_amount'])
        
        if purchase_total < applied_amount:
            raise ValueError(f"El total de la compra (S/ {purchase_total:.2f}) no puede ser menor al anticipo (S/ {applied_amount:.2f}). No se soportan saldos a favor.")
            
        remaining_payment = round(purchase_total - applied_amount, 2)
        
        conn = self.db.connect()
        cursor = conn.cursor()
        try:
            cash_id = None
            # 1. Registrar el PAGO RESTANTE en Caja (si se marca y si hay restante)
            if pay_remaining and remaining_payment > 0:
                cash_id = self.cash.add_transaction(
                    date=app_date,
                    type="expense",
                    description=f"Pago restante compra a: {adv['supplier_name']}",
                    amount=remaining_payment,
                    payment_method=payment_method,
                    category="compra_inventario" # O la categoría que uses
                )
            
            # 2. Insertar el registro de la aplicación
            cursor.execute(
                """
                INSERT INTO supplier_advance_apps
                    (advance_id, application_date, purchase_total, applied_amount, remaining_payment, 
                     notes, user_id, cash_register_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (advance_id, app_date, purchase_total, applied_amount, remaining_payment, 
                 notes, user_id, cash_id)
            )
            
            # 3. Marcar el anticipo como 'applied'
            cursor.execute(
                "UPDATE supplier_advances SET status = 'applied', applied_at = ? WHERE id = ?",
                (app_date, advance_id)
            )
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def delete_advance(self, advance_id: int):
        """
        Elimina un anticipo NO APLICADO.
        Crea un INGRESO en Caja para reversar el gasto original.
        """
        if not self.auth.has_permission('admin'):
             raise PermissionError("Solo un administrador puede eliminar anticipos.")
             
        adv = self.get_advance(advance_id)
        if not adv:
            raise ValueError("Anticipo no encontrado.")
        if adv['status'] == 'applied':
            raise PermissionError("No se puede eliminar un anticipo que ya fue aplicado a una compra.")
        
        conn = self.db.connect()
        cursor = conn.cursor()
        try:
            # 1. Registrar la REVERSIÓN (Ingreso) en Caja
            self.cash.add_transaction(
                date=datetime.now().strftime('%Y-%m-%d'),
                type="income",
                description=f"Reversión anticipo ID {advance_id}: {adv['supplier_name']}",
                amount=adv['total_amount'],
                payment_method="cash", # O el método que corresponda
                category="reversion_anticipo"
            )
            
            # 2. Eliminar el anticipo
            cursor.execute("DELETE FROM supplier_advances WHERE id = ?", (advance_id,))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def get_advance(self, advance_id: int) -> Optional[Dict]:
        rows = self.db.execute_query("SELECT * FROM supplier_advances WHERE id = ?", (advance_id,))
        return dict(rows[0]) if rows else None

    def get_all_advances(self, start_date: str, end_date: str, status: str) -> List[Dict]:
        """Obtiene todos los anticipos con filtros."""
        query = ["SELECT * FROM supplier_advances WHERE date_issued BETWEEN ? AND ?"]
        params = [start_date, end_date]
        
        if status == 'unpaid':
            query.append("AND status = 'unpaid'")
        elif status == 'applied':
            query.append("AND status = 'applied'")
            
        query.append("ORDER BY date_issued DESC, id DESC")
        
        rows = self.db.execute_query(" ".join(query), tuple(params))
        return [dict(r) for r in rows] if rows else []