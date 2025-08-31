"""
Módulo de Ventas
- Crea ventas (salidas de inventario)
- Valida stock de papa y costales
- Descuenta costales
- Registra ingreso en Caja (opcional)
"""

from datetime import datetime
from typing import Optional
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
    def get_last_sale_price(self, potato_type: str, quality: str) -> Optional[float]:
        """Último precio usado en una salida (venta). Si no hay, intenta el de entrada."""
        price = self.inv.get_last_unit_price(potato_type, quality, "exit")
        if price is None:
            price = self.inv.get_last_unit_price(potato_type, quality, "entry")
        return price

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
        """
        Inserta:
          - 1 registro en potato_inventory como 'exit'
          - Descuenta costales (cantidad)
          - (Opcional) 1 registro en cash_register como 'income'
        """
        if not self.auth.current_user:
            raise Exception("Usuario no autenticado")

        # 1) Validaciones y existencias
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

        # 2) Registrar salida en inventario (usa controlador de inventario)
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
        # Nota: add_inventory_record ya descuenta costales al ser 'exit'

        # 3) Registrar en caja (si corresponde)
        if register_cash:
            total = round(quantity * sale_unit_price, 2)
            desc = f"Venta {potato_type} {quality} ({quantity} bultos)"
            self.cash.add_transaction(date, "income", desc, total, payment_method, "venta")

        return sale_id
