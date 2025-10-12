# modules/sales/sales_controller.py
"""
Módulo de Ventas
- Crea ventas (salidas de inventario) para cualquier producto
- Valida stock de producto y costales
- Descuenta costales
- Registra ingreso en Caja (opcional)
- Lista/Reporta ventas
"""

from datetime import datetime
from typing import Optional, List, Dict, Tuple
from modules.inventory.inventory_controller import InventoryController


class SalesController:
    def __init__(self, database, auth_manager, cash_controller):
        self.db = database
        self.auth = auth_manager
        self.cash = cash_controller
        self.inv = InventoryController(database, auth_manager)

    # -------------------------
    # Consultas de apoyo
    # -------------------------
    def get_last_sale_price(self, product_name: str, quality: str):
        return self.inv.get_reference_price(product_name, quality)

    def get_stock(self, product_name: str, quality: str) -> int:
        return self.inv.get_current_stock(product_name, quality)

    def get_sacks(self) -> int:
        return self.inv.get_sacks_count()

    # -------------------------
    # Venta
    # -------------------------
    def create_sale(
        self,
        date: str,
        product_name: str,
        quality: str,
        quantity: int,
        sale_unit_price: float,
        payment_method: str,
        customer: str,
        notes: str = "",
        register_cash: bool = True,
    ) -> int:
        if not self.auth.current_user:
            raise Exception("Usuario no autenticado")

        product_name, quality = self.inv.validate_type_quality(product_name, quality)
        if quantity <= 0:
            raise ValueError("La cantidad debe ser positiva")
        if sale_unit_price < 0:
            raise ValueError("El precio unitario no puede ser negativo")

        stock = self.get_stock(product_name, quality)
        if stock < quantity:
            raise ValueError(
                f"Stock insuficiente de {product_name.capitalize()} {quality.capitalize()}. Disponible: {stock}, solicitado: {quantity}"
            )

        sacks = self.get_sacks()
        if sacks < quantity:
            raise ValueError(
                f"No hay suficientes costales. En stock: {sacks}, requeridos: {quantity}"
            )

        sale_id = self.inv.add_inventory_record(
            date=date,
            product_name=product_name,
            quality=quality,
            operation="exit",
            quantity=quantity,
            unit_price=sale_unit_price,
            supplier_customer=customer,
            notes=notes,
        )

        if register_cash:
            total = round(quantity * sale_unit_price, 2)
            desc = f"Venta {product_name.capitalize()} {quality.capitalize()} ({quantity} bultos)"
            self.cash.add_transaction(date, "income", desc, total, payment_method, "venta")

        return sale_id

    # -------------------------
    # Historial / Reportes
    # -------------------------
    def list_sales(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        product_name: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> List[Dict]:
        q = [
            "SELECT im.*, u.username,",
            "  (SELECT cr.payment_method FROM cash_register cr",
            "     WHERE cr.type='income' AND cr.category='venta'",
            "       AND cr.date = im.date",
            "       AND cr.amount = im.total_value",
            "       AND cr.description = 'Venta ' || im.product_name || ' ' || im.quality || ' (' || im.quantity || ' bultos)'",
            "     LIMIT 1) AS payment_method",
            "FROM inventory_movements im",
            "LEFT JOIN users u ON u.id = im.user_id",
            "WHERE im.operation='exit'",
            "  AND COALESCE(im.supplier_customer,'') <> 'ajuste'"
        ]
        params: list = []

        if start_date:
            q.append("AND im.date >= ?")
            params.append(start_date)
        if end_date:
            q.append("AND im.date <= ?")
            params.append(end_date)
        if product_name:
            q.append("AND LOWER(im.product_name) = LOWER(?)")
            params.append(product_name)
        if quality:
            q.append("AND LOWER(im.quality) = LOWER(?)")
            params.append(quality)

        q.append("ORDER BY im.date DESC, im.created_at DESC")
        rows = self.db.execute_query(" ".join(q), tuple(params) if params else None)
        return [dict(r) for r in rows] if rows else []

    def get_sales_totals(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        product_name: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> Dict[str, float]:
        q = [
            "SELECT COALESCE(SUM(quantity),0) AS qty, COALESCE(SUM(total_value),0) AS total",
            "FROM inventory_movements WHERE operation='exit'",
            "  AND COALESCE(supplier_customer,'') <> 'ajuste'"
        ]
        params: list = []
        if start_date:
            q.append("AND date >= ?"); params.append(start_date)
        if end_date:
            q.append("AND date <= ?"); params.append(end_date)
        if product_name:
            q.append("AND LOWER(product_name) = LOWER(?)"); params.append(product_name)
        if quality:
            q.append("AND LOWER(quality) = LOWER(?)"); params.append(quality)
        rows = self.db.execute_query(" ".join(q), tuple(params) if params else None)
        r = dict(rows[0]) if rows else {"qty":0, "total":0.0}
        return {"quantity": float(r.get("qty") or 0), "amount": float(r.get("total") or 0.0)}

    def get_sales_report(
        self,
        start_date: str,
        end_date: str,
        product_name: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> Tuple[List[Dict], Dict[str, float]]:
        data = self.list_sales(start_date, end_date, product_name, quality)
        totals = self.get_sales_totals(start_date, end_date, product_name, quality)
        return data, totals