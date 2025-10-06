"""
Módulo de Anticipos a Terceros (Ventas a Crédito)
- Crea ventas a crédito con reducción de inventario genérico
- Registra pagos en caja
- Lista ventas y pagos
"""

from datetime import datetime
from typing import Optional, List, Dict, Tuple
from modules.cash_register.controller import CashRegisterController


class AdvancesToThirdPartiesController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth = auth_manager
        self.cash = CashRegisterController(database, auth_manager)

    # ------------------------------
    # Inventario (usa potato_inventory para productos genéricos)
    # ------------------------------
    def add_inventory_record(
        self, date: str, product_name: str, quality: str, operation: str,
        quantity: int, unit_price: float, supplier_customer: str, notes: str = "",
    ) -> int:
        """
        Agrega registro de inventario (entrada/salida) usando potato_inventory
        """
        if not self.auth.current_user:
            raise Exception("Usuario no autenticado")

        if operation not in ("entry", "exit"):
            raise ValueError("operation debe ser 'entry' o 'exit'")
        if quantity <= 0 or unit_price < 0:
            raise ValueError("Cantidad y precio deben ser positivos")

        if operation == "exit":
            current_stock = self.get_stock(product_name, quality)
            if current_stock < quantity:
                raise ValueError(f"Stock insuficiente de {product_name} {quality}. Disponible: {current_stock}, solicitado: {quantity}")

        total_value = round(quantity * float(unit_price), 2)

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
            date, product_name, quality, operation, int(quantity), float(unit_price),
            total_value, (supplier_customer or "").strip(), (notes or "").strip(), user_id_val, now,
        )

        new_id = self.db.execute_query(insert_sql, params)
        return int(new_id)

    def get_stock(self, product_name: Optional[str] = None, quality: Optional[str] = None) -> int:
        where, params = "", []
        if product_name:
            where += " AND LOWER(potato_type) = ?"
            params.append(product_name.lower())
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

    # ------------------------------
    # Ventas a Crédito
    # ------------------------------
    def create_credit_sale(
        self,
        date: str,
        customer_name: str,
        product_name: str,
        quality: str,
        quantity: int,
        unit_price: float,
        notes: str = "",
    ) -> int:
        if not self.auth.current_user:
            raise Exception("Usuario no autenticado")

        if quantity <= 0:
            raise ValueError("La cantidad debe ser positiva")
        if unit_price < 0:
            raise ValueError("El precio unitario no puede ser negativo")

        stock = self.get_stock(product_name, quality)
        if stock < quantity:
            raise ValueError(
                f"Stock insuficiente de {product_name} {quality}. Disponible: {stock}, solicitado: {quantity}"
            )

        # Registrar salida de inventario
        self.add_inventory_record(
            date=date,
            product_name=product_name,
            quality=quality,
            operation="exit",
            quantity=quantity,
            unit_price=unit_price,
            supplier_customer=customer_name,
            notes=notes,
        )

        # Calcular total
        total_amount = round(quantity * unit_price, 2)

        # Insertar venta a crédito
        user_id_val = (self.auth.current_user["id"]
                    if isinstance(self.auth.current_user, dict) and "id" in self.auth.current_user
                    else self.auth.current_user)

        insert_sql = """
            INSERT INTO credit_sales
                (date, customer_name, product_name, quantity, unit_price, quality, total_amount, status, notes, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        params = (
            date, customer_name, product_name, int(quantity), float(unit_price), quality,
            total_amount, (notes or "").strip(), user_id_val, now,
        )

        sale_id = self.db.execute_query(insert_sql, params)
        return int(sale_id)

    def list_credit_sales(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        customer_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict]:
        q = [
            "SELECT cs.*, u.username",
            "FROM credit_sales cs",
            "LEFT JOIN users u ON u.id = cs.user_id",
            "WHERE 1=1"
        ]
        params: list = []

        if start_date:
            q.append("AND cs.date >= ?")
            params.append(start_date)
        if end_date:
            q.append("AND cs.date <= ?")
            params.append(end_date)
        if customer_name:
            q.append("AND LOWER(cs.customer_name) LIKE LOWER(?)")
            params.append(f"%{customer_name}%")
        if status:
            q.append("AND cs.status = ?")
            params.append(status)

        q.append("ORDER BY cs.date DESC, cs.created_at DESC")
        rows = self.db.execute_query(" ".join(q), tuple(params) if params else None)
        return [dict(r) for r in rows] if rows else []

    def get_credit_sale_totals(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        customer_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, float]:
        q = [
            "SELECT COALESCE(SUM(total_amount),0) AS total",
            "FROM credit_sales WHERE 1=1"
        ]
        params: list = []
        if start_date:
            q.append("AND date >= ?"); params.append(start_date)
        if end_date:
            q.append("AND date <= ?"); params.append(end_date)
        if customer_name:
            q.append("AND LOWER(customer_name) LIKE LOWER(?)"); params.append(f"%{customer_name}%")
        if status:
            q.append("AND status = ?"); params.append(status)
        rows = self.db.execute_query(" ".join(q), tuple(params) if params else None)
        r = dict(rows[0]) if rows else {"total":0.0}
        return {"amount": float(r.get("total") or 0.0)}

    # ------------------------------
    # Pagos de Ventas a Crédito
    # ------------------------------
    def add_payment(
        self,
        credit_sale_id: int,
        payment_date: str,
        amount: float,
        payment_method: str,
        notes: str = "",
    ) -> int:
        if not self.auth.current_user:
            raise Exception("Usuario no autenticado")

        if amount <= 0:
            raise ValueError("El monto del pago debe ser positivo")

        # Verificar que la venta existe
        sale = self.db.execute_query("SELECT * FROM credit_sales WHERE id = ?", (credit_sale_id,))
        if not sale:
            raise ValueError("Venta a crédito no encontrada")

        # Insertar pago
        user_id_val = (self.auth.current_user["id"]
                    if isinstance(self.auth.current_user, dict) and "id" in self.auth.current_user
                    else self.auth.current_user)

        insert_sql = """
            INSERT INTO credit_sale_payments
                (credit_sale_id, payment_date, amount, payment_method, notes, user_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        params = (
            int(credit_sale_id), payment_date, float(amount), payment_method,
            (notes or "").strip(), user_id_val, now,
        )

        payment_id = self.db.execute_query(insert_sql, params)

        # Registrar en caja como ingreso
        desc = f"Pago venta crédito ID {credit_sale_id}"
        self.cash.add_transaction(payment_date, "income", desc, amount, payment_method, "credito")

        # Verificar si la venta está pagada completamente
        total_paid = self.get_total_paid(credit_sale_id)
        sale_amount = float(sale[0]["total_amount"])
        if total_paid >= sale_amount:
            self.db.execute_query("UPDATE credit_sales SET status = 'paid' WHERE id = ?", (credit_sale_id,))

        return int(payment_id)

    def get_payments(self, credit_sale_id: Optional[int] = None) -> List[Dict]:
        q = [
            "SELECT csp.*, cs.customer_name, u.username",
            "FROM credit_sale_payments csp",
            "LEFT JOIN credit_sales cs ON cs.id = csp.credit_sale_id",
            "LEFT JOIN users u ON u.id = csp.user_id",
            "WHERE 1=1"
        ]
        params = []
        if credit_sale_id:
            q.append("AND csp.credit_sale_id = ?")
            params.append(credit_sale_id)

        q.append("ORDER BY csp.payment_date DESC, csp.created_at DESC")
        rows = self.db.execute_query(" ".join(q), tuple(params) if params else None)
        return [dict(r) for r in rows] if rows else []

    def get_total_paid(self, credit_sale_id: int) -> float:
        rows = self.db.execute_query(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM credit_sale_payments WHERE credit_sale_id = ?",
            (credit_sale_id,)
        )
        return float(rows[0]["total"]) if rows else 0.0

    def get_credit_sale_with_payments(self, credit_sale_id: int) -> Dict:
        sale = self.db.execute_query("SELECT * FROM credit_sales WHERE id = ?", (credit_sale_id,))
        if not sale:
            return None
        sale_dict = dict(sale[0])
        payments = self.get_payments(credit_sale_id)
        sale_dict["payments"] = payments
        sale_dict["total_paid"] = sum(p["amount"] for p in payments)
        sale_dict["remaining"] = sale_dict["total_amount"] - sale_dict["total_paid"]
        return sale_dict
