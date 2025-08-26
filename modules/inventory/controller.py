"""
Controlador de Inventario de Papas
- Registra entradas/salidas
- Calcula stock actual
- Resume por mes (para gráficos)
- (Opcional) registra automáticamente en Caja desde la Vista
"""

from datetime import datetime
from typing import List, Dict, Any, Optional


class InventoryController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth = auth_manager

    # ------------------------------
    # Altas de inventario
    # ------------------------------
    def add_inventory_record(
        self,
        date: str,
        potato_type: str,
        quality: str,
        operation: str,           # 'entry' | 'exit'
        quantity: int,
        unit_price: float,
        supplier_customer: str,
        notes: str = "",
    ) -> int:
        """
        Agrega una entrada o salida de inventario.
        Devuelve el id del registro insertado.
        """
        if not self.auth.current_user:
            raise Exception("Usuario no autenticado")

        if operation not in ("entry", "exit"):
            raise ValueError("operation debe ser 'entry' o 'exit'")

        if quantity <= 0 or unit_price < 0:
            raise ValueError("Cantidad y precio deben ser positivos")

        # Si es salida, verificar stock suficiente
        if operation == "exit":
            current = self.get_current_stock(potato_type, quality)
            if current < quantity:
                raise ValueError(
                    f"Stock insuficiente para {potato_type} {quality}. "
                    f"Stock actual: {current}, solicitado: {quantity}"
                )

        total_value = round(quantity * unit_price, 2)

        insert = """
            INSERT INTO potato_inventory
                (date, potato_type, quality, operation, quantity, unit_price, total_value,
                 supplier_customer, notes, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        params = (
            date,
            potato_type.strip(),
            quality.strip(),
            operation,
            int(quantity),
            float(unit_price),
            total_value,
            supplier_customer.strip(),
            (notes or "").strip(),
            self.auth.current_user["username"],
            now,
        )

        # Ejecutar y devolver id
        self.db.execute_query(insert, params)
        # Algunos wrappers no devuelven lastrowid, así que consultamos el último propio
        q_last = """
            SELECT id
            FROM potato_inventory
            WHERE created_by = ?
            ORDER BY id DESC
            LIMIT 1
        """
        row = self.db.execute_query(q_last, (self.auth.current_user["username"],))
        return int(row[0]["id"]) if row else -1

    # ------------------------------
    # Lecturas / consultas
    # ------------------------------
    def get_inventory_records(self, limit: int = 500) -> List[Dict[str, Any]]:
        query = """
            SELECT *
            FROM potato_inventory
            ORDER BY date DESC, id DESC
            LIMIT ?
        """
        rows = self.db.execute_query(query, (limit,))
        return [dict(r) for r in rows] if rows else []

    def get_current_stock(self, potato_type: Optional[str] = None, quality: Optional[str] = None) -> int:
        """
        Stock actual total o por (tipo, calidad).
        """
        where = ""
        params: List[Any] = []
        if potato_type:
            where += " AND potato_type = ?"
            params.append(potato_type)
        if quality:
            where += " AND quality = ?"
            params.append(quality)

        query = f"""
            SELECT
                COALESCE(SUM(CASE WHEN operation='entry' THEN quantity ELSE 0 END), 0)
              - COALESCE(SUM(CASE WHEN operation='exit'  THEN quantity ELSE 0 END), 0) AS stock
            FROM potato_inventory
            WHERE 1=1 {where}
        """
        row = self.db.execute_query(query, tuple(params))
        return int(row[0]["stock"]) if row else 0

    def get_stock_for_chart(self) -> List[Dict[str, Any]]:
        """
        Regresa el stock por (tipo, calidad) para graficar barras actuales.
        """
        query = """
            SELECT potato_type, quality,
                COALESCE(SUM(CASE WHEN operation='entry' THEN quantity ELSE 0 END), 0)
              - COALESCE(SUM(CASE WHEN operation='exit'  THEN quantity ELSE 0 END), 0) AS stock
            FROM potato_inventory
            GROUP BY potato_type, quality
            HAVING stock <> 0
            ORDER BY potato_type, quality
        """
        rows = self.db.execute_query(query)
        return [dict(r) for r in rows] if rows else []

    def get_monthly_summary(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Resumen mensual del año indicado:
        - total_income: total vendido (salidas)
        - total_expense: total comprado (entradas)
        """
        if not year:
            year = datetime.now().year

        query = """
            SELECT
                strftime('%Y-%m', date) AS month,
                SUM(CASE WHEN operation='exit'  THEN total_value ELSE 0 END) AS total_income,
                SUM(CASE WHEN operation='entry' THEN total_value ELSE 0 END) AS total_expense
            FROM potato_inventory
            WHERE strftime('%Y', date) = ?
            GROUP BY strftime('%Y-%m', date)
            ORDER BY month
        """
        rows = self.db.execute_query(query, (str(year),))
        return [dict(r) for r in rows] if rows else []
