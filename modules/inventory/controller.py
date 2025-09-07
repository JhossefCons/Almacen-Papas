# modules/inventory/controller.py
"""
Controlador de Inventario de Papas
- Registra entradas/salidas
- Calcula stock actual
- Resumen mensual (para gráficos)
- Gestiona stock de costales (empaque)
- Actualiza registros (solo admin)
- Precio de referencia por combinación (tabla inventory_prices)
- Valorización del inventario (costo, valor potencial, margen)
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

VALID_COMBOS = {
    "parda": ["primera", "segunda", "tercera"],
    "colorada": ["primera", "tercera"],
    "amarilla": ["primera", "segunda", "tercera"],
}

class InventoryController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth = auth_manager

    # ------------------------------
    # Utilidades / permisos
    # ------------------------------
    def validate_type_quality(self, potato_type: str, quality: str):
        t = (potato_type or "").strip().lower()
        q = (quality or "").strip().lower()
        if t not in VALID_COMBOS or q not in VALID_COMBOS[t]:
            raise ValueError(f"Combinación inválida: tipo='{potato_type}', calidad='{quality}'.")
        return t, q

    def _require_admin(self):
        if not getattr(self.auth, "has_permission", None) or not self.auth.has_permission("admin"):
            raise PermissionError("Solo el usuario administrador puede realizar esta acción")

    # ------------------------------
    # Precio de referencia por combinación (venta)
    # ------------------------------
    def _ensure_price_table(self):
        self.db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS inventory_prices (
                potato_type TEXT NOT NULL,
                quality     TEXT NOT NULL,
                unit_price  REAL NOT NULL,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (potato_type, quality)
            )
            """
        )

    def get_reference_price(self, potato_type: str, quality: str) -> Optional[float]:
        """Precio de VENTA de referencia; si no existe, usamos el último precio de entrada como sugerencia."""
        self._ensure_price_table()
        t, q = self.validate_type_quality(potato_type, quality)
        row = self.db.execute_query(
            "SELECT unit_price FROM inventory_prices WHERE potato_type=? AND quality=?", (t, q)
        )
        if row:
            try:
                return float(row[0]["unit_price"])
            except Exception:
                return None
        # fallback: último precio de compra registrado
        return self.get_last_purchase_price(t, q)

    def set_reference_price(self, potato_type: str, quality: str, unit_price: float):
        self._require_admin()
        self._ensure_price_table()
        t, q = self.validate_type_quality(potato_type, quality)
        price = float(unit_price)
        if price < 0:
            raise ValueError("El precio debe ser mayor o igual a 0.")
        self.db.execute_query(
            """
            INSERT INTO inventory_prices (potato_type, quality, unit_price, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(potato_type, quality)
            DO UPDATE SET unit_price=excluded.unit_price, updated_at=CURRENT_TIMESTAMP
            """,
            (t, q, price),
        )

    # ------------------------------
    # Costales
    # ------------------------------
    def get_sacks_count(self) -> int:
        row = self.db.execute_query("SELECT sacks_count FROM packaging_stock WHERE id = 1")
        return int(row[0]["sacks_count"]) if row else 0

    def add_sacks(self, amount: int, price: float = None):
        if amount <= 0:
            raise ValueError("La cantidad de costales debe ser positiva")
        update_fields = ["sacks_count = sacks_count + ?"]
        params = [int(amount)]
        if price is not None:
            update_fields.append("sack_price = ?")
            params.append(float(price))
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE packaging_stock SET {', '.join(update_fields)} WHERE id = 1"
        self.db.execute_query(query, tuple(params))

    def set_sacks(self, new_count: int):
        self._require_admin()
        if new_count < 0:
            raise ValueError("El stock de costales no puede ser negativo")
        self.db.execute_query(
            "UPDATE packaging_stock SET sacks_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
            (int(new_count),),
        )

    def consume_sacks(self, amount: int):
        if amount <= 0:
            return
        current = self.get_sacks_count()
        if current < amount:
            raise ValueError(f"No hay suficientes costales. En stock: {current}, requeridos: {amount}")
        self.db.execute_query(
            "UPDATE packaging_stock SET sacks_count = sacks_count - ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
            (int(amount),),
        )

    def get_sack_price(self) -> float:
        row = self.db.execute_query("SELECT sack_price FROM packaging_stock WHERE id = 1")
        return float(row[0]["sack_price"]) if row and row[0]["sack_price"] is not None else 0.0

    # ------------------------------
    # Altas / consultas / actualización
    # ------------------------------
    def get_last_unit_price(self, potato_type: str, quality: str, operation: str) -> Optional[float]:
        """
        Devuelve el último precio (unit_price) registrado para la combinación y operación dadas.
        operation: 'entry' (compras) o 'exit' (ventas)
        """
        op = (operation or "").strip().lower()
        if op not in ("entry", "exit"):
            raise ValueError("operation debe ser 'entry' o 'exit'")
        rows = self.db.execute_query(
            """
            SELECT unit_price
              FROM potato_inventory
             WHERE LOWER(potato_type)=? AND LOWER(quality)=? AND operation=?
             ORDER BY date DESC, id DESC
             LIMIT 1
            """,
            (potato_type.lower(), quality.lower(), op),
        )
        if rows:
            try:
                return float(rows[0]["unit_price"])
            except Exception:
                return None
        return None

    def get_last_purchase_price(self, potato_type: str, quality: str) -> Optional[float]:
        """Último precio de COMPRA (de entradas) para autollenar."""
        return self.get_last_unit_price(potato_type, quality, "entry")

    def add_inventory_record(
        self, date: str, potato_type: str, quality: str, operation: str,
        quantity: int, unit_price: float, supplier_customer: str, notes: str = "",
    ) -> int:
        """
        unit_price:
        - 'entry' = PRECIO DE COMPRA (costo)
        - 'exit'  = PRECIO DE VENTA aplicado
        """
        if not self.auth.current_user:
            raise Exception("Usuario no autenticado")

        potato_type, quality = self.validate_type_quality(potato_type, quality)
        if operation not in ("entry", "exit"):
            raise ValueError("operation debe ser 'entry' o 'exit'")
        if quantity <= 0 or unit_price < 0:
            raise ValueError("Cantidad y precio deben ser positivos")

        if operation == "exit":
            current_potato = self.get_current_stock(potato_type, quality)
            if current_potato < quantity:
                raise ValueError(f"Stock insuficiente para {potato_type} {quality}. Stock actual: {current_potato}")
            if self.get_sacks_count() < quantity:
                raise ValueError(f"No hay suficientes costales para la venta ({quantity} requeridos).")

        total_value = round(quantity * float(unit_price), 2)

        # ✅ user_id correcto (coherente con el resto del código)
        user_id_val = (self.auth.current_user["id"]
                    if isinstance(self.auth.current_user, dict) and "id" in self.auth.current_user
                    else self.auth.current_user)

        insert_sql = """
            INSERT INTO potato_inventory
                (date, potato_type, quality, operation, quantity, unit_price, total_value,
                supplier_customer, notes, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        params = (
            date, potato_type, quality, operation, int(quantity), float(unit_price),
            total_value, (supplier_customer or "").strip(), (notes or "").strip(), user_id_val, now,
        )

        # ✅ Esto COMMIT ya (tu execute_query lo hace para no-SELECT) y devuelve el id insertado
        new_id = self.db.execute_query(insert_sql, params)

        # Si es salida, descontar costales (también COMMIT)
        if operation == "exit":
            self.consume_sacks(quantity)

        return int(new_id)


    def get_current_stock(self, potato_type: Optional[str] = None, quality: Optional[str] = None) -> int:
        where, params = "", []
        if potato_type:
            where += " AND LOWER(potato_type) = ?"
            params.append(potato_type.lower())
        if quality:
            where += " AND LOWER(quality) = ?"
            params.append(quality.lower())

        query = f"""
            SELECT
                COALESCE(SUM(CASE WHEN operation='entry' THEN quantity ELSE 0 END), 0)
              - COALESCE(SUM(CASE WHEN operation='exit'  THEN quantity ELSE 0 END), 0) AS stock
            FROM potato_inventory
            WHERE 1=1 {where}
        """
        row = self.db.execute_query(query, tuple(params))
        return int(row[0]["stock"]) if row else 0

    def get_stock_matrix(self) -> List[Dict[str, Any]]:
        """Todas las combinaciones con stock actual + precio de venta de referencia (incluye 0)."""
        result: List[Dict[str, Any]] = []
        for p_type, qualities in VALID_COMBOS.items():
            for q in qualities:
                stock = self.get_current_stock(p_type, q)
                price = self.get_reference_price(p_type, q)
                result.append({
                    "potato_type": p_type,
                    "quality": q,
                    "stock": stock,
                    "price": price if price is not None else 0.0
                })
        return result

    def get_entries_history(self, limit: int = 200) -> List[Dict[str, Any]]:
        """(Opcional) Historial de ENTRADAS: fecha, tipo, calidad, cantidad, precio compra, proveedor, notas."""
        rows = self.db.execute_query(
            """
            SELECT date, potato_type, quality, quantity, unit_price, supplier_customer, notes
              FROM potato_inventory
             WHERE operation='entry'
             ORDER BY date DESC, id DESC
             LIMIT ?
            """,
            (int(limit),),
        )
        return [dict(r) for r in rows] if rows else []

    def get_monthly_summary(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        if not year:
            year = datetime.now().year
        rows = self.db.execute_query("""
            SELECT
                strftime('%Y-%m', date) AS month,
                SUM(CASE WHEN operation='exit'  THEN total_value ELSE 0 END) AS total_income,
                SUM(CASE WHEN operation='entry' THEN total_value ELSE 0 END) AS total_expense
            FROM potato_inventory
            WHERE strftime('%Y', date) = ?
            GROUP BY strftime('%Y-%m', date)
            ORDER BY month
        """, (str(year),))
        return [dict(r) for r in rows] if rows else []

    # ------------------------------
    # Valorización del inventario
    # ------------------------------
    def get_inventory_valuation(self) -> List[Dict[str, Any]]:
        """
        Devuelve para cada combinación:
        stock, avg_cost (promedio ponderado entradas), cost_value, ref_price, potential_revenue, potential_margin.
        """
        # Promedio ponderado de compras por combinación
        rows = self.db.execute_query("""
            SELECT LOWER(potato_type) AS potato_type, LOWER(quality) AS quality,
                   SUM(CASE WHEN operation='entry' THEN quantity ELSE 0 END) AS qty_in,
                   SUM(CASE WHEN operation='entry' THEN quantity * unit_price ELSE 0 END) AS cost_in
            FROM potato_inventory
            GROUP BY LOWER(potato_type), LOWER(quality)
        """)
        avg_cost_map = {}
        if rows:
            for r in rows:
                qty = float(r["qty_in"] or 0)
                cost_sum = float(r["cost_in"] or 0)
                avg_cost_map[(r["potato_type"], r["quality"])] = (cost_sum / qty) if qty > 0 else None

        # Armar resultado
        result: List[Dict[str, Any]] = []
        for p_type, qualities in VALID_COMBOS.items():
            for q in qualities:
                stock = self.get_current_stock(p_type, q)
                avg_cost = avg_cost_map.get((p_type, q))
                ref_price = self.get_reference_price(p_type, q)
                cost_value = (stock * avg_cost) if (avg_cost is not None) else 0.0
                potential_revenue = (stock * ref_price) if (ref_price is not None) else 0.0
                margin = potential_revenue - cost_value
                result.append({
                    "potato_type": p_type,
                    "quality": q,
                    "stock": stock,
                    "avg_cost": avg_cost,
                    "cost_value": cost_value,
                    "ref_price": ref_price,
                    "potential_revenue": potential_revenue
                })
        return result

    # ------------------------------
    # Ajustes / edición
    # ------------------------------
    def update_inventory_record(
        self, record_id: int, new_quantity: int,
        new_unit_price: Optional[float] = None,
        new_supplier_customer: Optional[str] = None,
        new_notes: Optional[str] = None,
    ):
        self._require_admin()
        rows = self.db.execute_query("SELECT * FROM potato_inventory WHERE id = ?", (int(record_id),))
        rec = dict(rows[0]) if rows else None
        if not rec:
            raise ValueError("Registro no encontrado")

        old_qty = int(rec["quantity"])
        new_qty = int(new_quantity)
        if new_qty <= 0:
            raise ValueError("La cantidad debe ser positiva")

        potato_type, quality, operation = rec["potato_type"], rec["quality"], rec["operation"]

        if operation == "exit":
            available_potato = self.get_current_stock(potato_type, quality) + old_qty
            if available_potato < new_qty:
                raise ValueError(f"Stock insuficiente tras la edición. Disponible: {available_potato}, solicitado: {new_qty}")
            delta = new_qty - old_qty
            if delta > 0:
                self.consume_sacks(delta)
            elif delta < 0:
                self.add_sacks(-delta)

        unit_price = float(new_unit_price) if new_unit_price is not None else float(rec["unit_price"])
        total_value = round(unit_price * new_qty, 2)
        supplier_customer = (new_supplier_customer if new_supplier_customer is not None else rec["supplier_customer"]) or ""
        notes = (new_notes if new_notes is not None else rec["notes"]) or ""

        self.db.execute_query(
            """
            UPDATE potato_inventory
               SET quantity = ?, unit_price = ?, total_value = ?, supplier_customer = ?, notes = ?
             WHERE id = ?
            """,
            (new_qty, unit_price, total_value, supplier_customer, notes, int(record_id)),
        )

    def set_stock_by_admin(self, potato_type: str, quality: str, target_stock: int, note: str = ""):
        """Ajuste administrativo de stock total (no afecta costales ni Caja)."""
        self._require_admin()
        t, q = self.validate_type_quality(potato_type, quality)
        current = self.get_current_stock(t, q)
        target = int(target_stock)
        delta = target - current
        if delta == 0:
            return
        date = datetime.now().strftime("%Y-%m-%d")
        if delta > 0:
            self.add_inventory_record(date, t, q, "entry", delta, 0.0, "ajuste", f"Ajuste admin. {note or ''}".strip())
        else:
            self.add_inventory_record(date, t, q, "exit", -delta, 0.0, "ajuste", f"Ajuste admin. {note or ''}".strip())
            
    def get_reference_sale_price(self, potato_type: str, quality: str):
        """
        Devuelve el precio de VENTA de referencia para (tipo, calidad).
        Intenta en este orden:
        1) Tabla de referencias (si existe): price_reference
        2) Última ENTRADA con columna sale_unit_price (si existe en potato_inventory)
        3) Última SALIDA (exit) como último recurso
        """
        potato_type = potato_type.lower().strip()
        quality = quality.lower().strip()

        # 1) Tabla de referencias, si la usas
        try:
            rows = self.db.execute_query("""
                SELECT sale_price
                  FROM price_reference
                 WHERE potato_type=? AND quality=?
                 ORDER BY updated_at DESC
                 LIMIT 1
            """, (potato_type, quality))
            if rows:
                return float(rows[0]["sale_price"])
        except Exception:
            pass

        # 2) Última ENTRADA con columna sale_unit_price (si la tienes en potato_inventory)
        try:
            rows = self.db.execute_query("""
                SELECT sale_unit_price AS p
                  FROM potato_inventory
                 WHERE operation='entry'
                   AND potato_type=? AND quality=?
                   AND sale_unit_price IS NOT NULL
                 ORDER BY date DESC, id DESC
                 LIMIT 1
            """, (potato_type, quality))
            if rows and rows[0]["p"] is not None:
                return float(rows[0]["p"])
        except Exception:
            pass

        # 3) Última SALIDA (exit) – sólo como último recurso
        rows = self.db.execute_query("""
            SELECT unit_price
              FROM potato_inventory
             WHERE operation='exit'
               AND potato_type=? AND quality=?
             ORDER BY date DESC, id DESC
             LIMIT 1
        """, (potato_type, quality))
        return float(rows[0]["unit_price"]) if rows else None
