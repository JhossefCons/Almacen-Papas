# modules/inventory/inventory_controller.py
"""
Controlador de Inventario de Productos (Generalizado)
- Registra entradas/salidas para cualquier producto
- Calcula stock actual dinámicamente
- Gestiona stock de costales (empaque)
- Valorización del inventario (costo, valor potencial, margen)
"""
from datetime import datetime
from typing import List, Dict, Any, Optional

class InventoryController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth = auth_manager

    # MODIFICADO: Ahora consulta la tabla 'products'
    def get_all_products(self) -> Dict[str, List[str]]:
        """
        Devuelve un diccionario de todos los productos y sus calidades
        desde la tabla de productos definidos.
        """
        rows = self.db.execute_query("SELECT name, qualities FROM products ORDER BY name")
        products = {}
        if rows:
            for row in rows:
                products[row["name"]] = row["qualities"].split(',')
        return products

    # ------------------------------
    # Utilidades / permisos
    # ------------------------------
    def validate_type_quality(self, product_name: str, quality: str):
        t = (product_name or "").strip().lower()
        q = (quality or "").strip().lower()
        if not t or not q:
            raise ValueError("El nombre del producto y la calidad son obligatorios.")
        return t, q

    def _require_admin(self):
        if not getattr(self.auth, "has_permission", None) or not self.auth.has_permission("admin"):
            raise PermissionError("Solo el usuario administrador puede realizar esta acción")

    # ------------------------------
    # Consultas dinámicas de productos
    # ------------------------------
    def get_all_products(self) -> Dict[str, List[str]]:
        """
        Devuelve un diccionario de todos los productos y sus calidades únicas desde la BD.
        Ej: {'Parda': ['Primera', 'Segunda'], 'Amarilla': ['Unica']}
        """
        rows = self.db.execute_query(
            "SELECT DISTINCT LOWER(product_name) as name, LOWER(quality) as quality FROM inventory_movements ORDER BY name, quality"
        )
        products = {}
        if not rows:
            return {}
        for row in rows:
            name_key = row['name'].capitalize()
            quality_val = row['quality'].capitalize()
            if name_key not in products:
                products[name_key] = []
            if quality_val not in products[name_key]:
                products[name_key].append(quality_val)
        return products

    # ------------------------------
    # Precio de referencia por combinación (venta)
    # ------------------------------
    def _ensure_price_table(self):
        self.db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS inventory_prices (
                product_name TEXT NOT NULL,
                quality     TEXT NOT NULL,
                unit_price  REAL NOT NULL,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (product_name, quality)
            )
            """
        )

    def get_reference_price(self, product_name: str, quality: str) -> Optional[float]:
        self._ensure_price_table()
        t, q = self.validate_type_quality(product_name, quality)
        row = self.db.execute_query(
            "SELECT unit_price FROM inventory_prices WHERE product_name=? AND quality=?", (t, q)
        )
        if row:
            try:
                return float(row[0]["unit_price"])
            except Exception:
                return None
        return self.get_last_purchase_price(t, q)

    def set_reference_price(self, product_name: str, quality: str, unit_price: float):
        self._require_admin()
        self._ensure_price_table()
        t, q = self.validate_type_quality(product_name, quality)
        price = float(unit_price)
        if price < 0:
            raise ValueError("El precio debe ser mayor o igual a 0.")
        self.db.execute_query(
            """
            INSERT INTO inventory_prices (product_name, quality, unit_price, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(product_name, quality)
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
    def get_last_purchase_price(self, product_name: str, quality: str) -> Optional[float]:
        t, q = self.validate_type_quality(product_name, quality)
        rows = self.db.execute_query(
            """
            SELECT unit_price
                FROM inventory_movements
                WHERE LOWER(product_name)=? AND LOWER(quality)=? AND operation='entry'
                ORDER BY date DESC, id DESC
                LIMIT 1
            """,
            (t, q),
        )
        return float(rows[0]["unit_price"]) if rows else None

    def add_inventory_record(
        self, date: str, product_name: str, quality: str, operation: str,
        quantity: int, unit_price: float, supplier_customer: str, notes: str = "",
    ) -> int:
        if not self.auth.current_user:
            raise Exception("Usuario no autenticado")

        product_name, quality = self.validate_type_quality(product_name, quality)
        if operation not in ("entry", "exit"):
            raise ValueError("operation debe ser 'entry' o 'exit'")
        if quantity <= 0 or unit_price < 0:
            raise ValueError("Cantidad y precio deben ser positivos")

        if operation == "exit":
            current_stock = self.get_current_stock(product_name, quality)
            if current_stock < quantity:
                raise ValueError(f"Stock insuficiente para {product_name} {quality}. Stock actual: {current_stock}")
            if self.get_sacks_count() < quantity:
                raise ValueError(f"No hay suficientes costales para la venta ({quantity} requeridos).")

        total_value = round(quantity * float(unit_price), 2)
        user_id_val = self.auth.current_user["id"]

        insert_sql = """
            INSERT INTO inventory_movements
                (date, product_name, quality, operation, quantity, unit_price, total_value,
                supplier_customer, notes, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        params = (
            date, product_name, quality, operation, int(quantity), float(unit_price),
            total_value, (supplier_customer or "").strip(), (notes or "").strip(), user_id_val, now,
        )

        new_id = self.db.execute_query(insert_sql, params)

        if operation == "exit":
            self.consume_sacks(quantity)

        return int(new_id)

    def get_current_stock(self, product_name: Optional[str] = None, quality: Optional[str] = None) -> int:
        where, params = "", []
        if product_name:
            where += " AND LOWER(product_name) = ?"
            params.append(product_name.lower())
        if quality:
            where += " AND LOWER(quality) = ?"
            params.append(quality.lower())

        query = f"""
            SELECT
                COALESCE(SUM(CASE WHEN operation='entry' THEN quantity ELSE 0 END), 0)
                - COALESCE(SUM(CASE WHEN operation='exit'  THEN quantity ELSE 0 END), 0) AS stock
            FROM inventory_movements
            WHERE 1=1 {where}
        """
        row = self.db.execute_query(query, tuple(params))
        return int(row[0]["stock"]) if row else 0

    def get_stock_matrix(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        all_products = self.get_all_products()
        for p_type, qualities in all_products.items():
            for q in qualities:
                stock = self.get_current_stock(p_type, q)
                price = self.get_reference_price(p_type, q)
                result.append({
                    "product_name": p_type,
                    "quality": q,
                    "stock": stock,
                    "price": price if price is not None else 0.0
                })
        return result

    def get_inventory_valuation(self) -> List[Dict[str, Any]]:
        rows = self.db.execute_query("""
            SELECT LOWER(product_name) AS product_name, LOWER(quality) AS quality,
                    SUM(CASE WHEN operation='entry' THEN quantity ELSE 0 END) AS qty_in,
                    SUM(CASE WHEN operation='entry' THEN quantity * unit_price ELSE 0 END) AS cost_in
            FROM inventory_movements
            GROUP BY LOWER(product_name), LOWER(quality)
        """)
        avg_cost_map = {}
        if rows:
            for r in rows:
                qty = float(r["qty_in"] or 0)
                cost_sum = float(r["cost_in"] or 0)
                avg_cost_map[(r["product_name"], r["quality"])] = (cost_sum / qty) if qty > 0 else None

        result: List[Dict[str, Any]] = []
        all_products = self.get_all_products()
        for p_type, qualities in all_products.items():
            for q in qualities:
                p_type_lower = p_type.lower()
                q_lower = q.lower()
                stock = self.get_current_stock(p_type_lower, q_lower)
                avg_cost = avg_cost_map.get((p_type_lower, q_lower))
                ref_price = self.get_reference_price(p_type_lower, q_lower)
                cost_value = (stock * avg_cost) if (avg_cost is not None) else 0.0
                potential_revenue = (stock * ref_price) if (ref_price is not None) else 0.0
                
                result.append({
                    "product_name": p_type,
                    "quality": q,
                    "stock": stock,
                    "avg_cost": avg_cost,
                    "cost_value": cost_value,
                    "ref_price": ref_price,
                    "potential_revenue": potential_revenue
                })
        return result

    def set_stock_by_admin(self, product_name: str, quality: str, target_stock: int, note: str = ""):
        self._require_admin()
        t, q = self.validate_type_quality(product_name, quality)
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