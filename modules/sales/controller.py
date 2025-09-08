"""
Módulo de Ventas
- Crea ventas (salidas de inventario)
- Valida stock de papa y costales
- Descuenta costales
- Registra ingreso en Caja (opcional)
- Lista/Reporta ventas
"""

from datetime import datetime
from typing import Optional, List, Dict, Tuple
from modules.loans.controller import LoansController
from modules.inventory.controller import InventoryController  # Reutilizamos validaciones y helpers


class SalesController:
    def __init__(self, database, auth_manager, cash_controller):
        self.db = database
        self.auth = auth_manager
        self.cash = cash_controller
        self.inv = InventoryController(database, auth_manager)

    # -------------------------
    # Consultas de apoyo
    # -------------------------
    def get_last_sale_price(self, potato_type: str, quality: str):
        return self.inv.get_reference_price(potato_type, quality)

    def get_stock(self, potato_type: str, quality: str) -> int:
        return self.inv.get_current_stock(potato_type, quality)

    def get_sacks(self) -> int:
        return self.inv.get_sacks_count()

    # -------------------------
    # Venta
    # -------------------------
    def create_sale(
        self,
        date: str,
        potato_type: str,
        quality: str,
        quantity: int,
        sale_unit_price: float,
        payment_method: str,          # 'cash' | 'transfer'
        customer: str,
        notes: str = "",
        register_cash: bool = True,
    ) -> int:
        if not self.auth.current_user:
            raise Exception("Usuario no autenticado")
        
        # 1) Validaciones
        potato_type, quality = self.inv.validate_type_quality(potato_type, quality)
        if quantity <= 0:
            raise ValueError("La cantidad debe ser positiva")
        if sale_unit_price < 0:
            raise ValueError("El precio unitario no puede ser negativo")

        stock = self.get_stock(potato_type, quality)
        if stock < quantity:
            raise ValueError(
                f"Stock insuficiente de {potato_type} {quality}. Disponible: {stock}, solicitado: {quantity}"
            )

        sacks = self.get_sacks()
        if sacks < quantity:
            raise ValueError(
                f"No hay suficientes costales. En stock: {sacks}, requeridos: {quantity}"
            )

        # 2) Registrar salida (esto descuenta stock y costales)
        sale_id = self.inv.add_inventory_record(
            date=date,
            potato_type=potato_type,
            quality=quality,
            operation="exit",
            quantity=quantity,
            unit_price=sale_unit_price,
            supplier_customer=customer,
            notes=notes,
        )

        # 3) Caja (opcional)
        if register_cash:
            total = round(quantity * sale_unit_price, 2)
            desc = f"Venta {potato_type} {quality} ({quantity} bultos)"
            self.cash.add_transaction(date, "income", desc, total, payment_method, "venta")

        return sale_id

    # -------------------------
    # Historial / Reportes
    # -------------------------
    def list_sales(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        potato_type: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> List[Dict]:
        """
        Devuelve ventas (po. inventario con operation='exit') con:
        - payment_method (si se registró en caja con desc y monto coincidente)
        """
        q = [
            "SELECT pi.*, u.username,",
            "  (SELECT cr.payment_method FROM cash_register cr",
            "     WHERE cr.type='income' AND cr.category='venta'",
            "       AND cr.date = pi.date",
            "       AND cr.amount = pi.total_value",
            "       AND cr.description = 'Venta ' || pi.potato_type || ' ' || pi.quality || ' (' || pi.quantity || ' bultos)'",
            "     LIMIT 1) AS payment_method",
            "FROM potato_inventory pi",
            "LEFT JOIN users u ON u.id = pi.user_id",
            "WHERE pi.operation='exit'"
            "  AND COALESCE(pi.supplier_customer,'') <> 'ajuste'"
        ]
        params: list = []

        if start_date:
            q.append("AND pi.date >= ?")
            params.append(start_date)
        if end_date:
            q.append("AND pi.date <= ?")
            params.append(end_date)
        if potato_type:
            q.append("AND LOWER(pi.potato_type) = LOWER(?)")
            params.append(potato_type)
        if quality:
            q.append("AND LOWER(pi.quality) = LOWER(?)")
            params.append(quality)

        q.append("ORDER BY pi.date DESC, pi.created_at DESC")
        rows = self.db.execute_query(" ".join(q), tuple(params) if params else None)
        return [dict(r) for r in rows] if rows else []

    def get_sales_totals(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        potato_type: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> Dict[str, float]:
        """Totales rápidos del mismo filtro que list_sales."""
        q = [
            "SELECT COALESCE(SUM(quantity),0) AS qty, COALESCE(SUM(total_value),0) AS total",
            "FROM potato_inventory WHERE operation='exit'"
            "  AND COALESCE(supplier_customer,'') <> 'ajuste'"
        ]
        params: list = []
        if start_date:
            q.append("AND date >= ?"); params.append(start_date)
        if end_date:
            q.append("AND date <= ?"); params.append(end_date)
        if potato_type:
            q.append("AND LOWER(potato_type) = LOWER(?)"); params.append(potato_type)
        if quality:
            q.append("AND LOWER(quality) = LOWER(?)"); params.append(quality)
        rows = self.db.execute_query(" ".join(q), tuple(params) if params else None)
        r = dict(rows[0]) if rows else {"qty":0, "total":0.0}
        return {"quantity": float(r.get("qty") or 0), "amount": float(r.get("total") or 0.0)}

    def get_sales_report(
        self,
        start_date: str,
        end_date: str,
        potato_type: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> Tuple[List[Dict], Dict[str, float]]:
        """Datos + totales para reporte entre fechas."""
        data = self.list_sales(start_date, end_date, potato_type, quality)
        totals = self.get_sales_totals(start_date, end_date, potato_type, quality)
        return data, totals
