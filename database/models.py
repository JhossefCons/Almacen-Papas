"""
Modelos de datos para la aplicación PapaSoft
"""
from datetime import datetime

class User:
    def __init__(self, id, username, password, role, full_name, is_active=True, created_at=None):
        self.id = id
        self.username = username
        self.password = password
        self.role = role
        self.full_name = full_name
        self.is_active = is_active
        self.created_at = created_at or datetime.now().isoformat()
    
    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row['id'],
            username=row['username'],
            password=row['password'],
            role=row['role'],
            full_name=row['full_name'],
            is_active=bool(row['is_active']),
            created_at=row['created_at']
        )

class CashTransaction:
    def __init__(self, id, date, type, description, amount, payment_method, category, user_id, created_at=None):
        self.id = id
        self.date = date
        self.type = type  # 'income' or 'expense'
        self.description = description
        self.amount = amount
        self.payment_method = payment_method  # 'cash' or 'transfer'
        self.category = category
        self.user_id = user_id
        self.created_at = created_at or datetime.now().isoformat()
    
    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row['id'],
            date=row['date'],
            type=row['type'],
            description=row['description'],
            amount=row['amount'],
            payment_method=row['payment_method'],
            category=row['category'],
            user_id=row['user_id'],
            created_at=row['created_at']
        )

class Loan:
    def __init__(self, id, employee_name, amount, date_issued, due_date, interest_rate, status, notes, user_id, created_at=None):
        self.id = id
        self.employee_name = employee_name
        self.amount = amount
        self.date_issued = date_issued
        self.due_date = due_date
        self.interest_rate = interest_rate
        self.status = status  # 'active', 'paid', 'overdue'
        self.notes = notes
        self.user_id = user_id
        self.created_at = created_at or datetime.now().isoformat()
    
    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row['id'],
            employee_name=row['employee_name'],
            amount=row['amount'],
            date_issued=row['date_issued'],
            due_date=row['due_date'],
            interest_rate=row['interest_rate'],
            status=row['status'],
            notes=row['notes'],
            user_id=row['user_id'],
            created_at=row['created_at']
        )

class LoanPayment:
    def __init__(self, id, loan_id, payment_date, amount, notes, user_id, created_at=None):
        self.id = id
        self.loan_id = loan_id
        self.payment_date = payment_date
        self.amount = amount
        self.notes = notes
        self.user_id = user_id
        self.created_at = created_at or datetime.now().isoformat()
    
    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row['id'],
            loan_id=row['loan_id'],
            payment_date=row['payment_date'],
            amount=row['amount'],
            notes=row['notes'],
            user_id=row['user_id'],
            created_at=row['created_at']
        )

class PotatoInventory:
    def __init__(self, id, date, potato_type, quality, operation, quantity, unit_price, total_value, supplier_customer, notes, user_id, created_at=None):
        self.id = id
        self.date = date
        self.potato_type = potato_type  # 'parda', 'amarilla', 'colorada'
        self.quality = quality  # 'primera', 'segunda', 'tercera'
        self.operation = operation  # 'entry' or 'exit'
        self.quantity = quantity
        self.unit_price = unit_price
        self.total_value = total_value
        self.supplier_customer = supplier_customer
        self.notes = notes
        self.user_id = user_id
        self.created_at = created_at or datetime.now().isoformat()
    
    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row['id'],
            date=row['date'],
            potato_type=row['potato_type'],
            quality=row['quality'],
            operation=row['operation'],
            quantity=row['quantity'],
            unit_price=row['unit_price'],
            total_value=row['total_value'],
            supplier_customer=row['supplier_customer'],
            notes=row['notes'],
            user_id=row['user_id'],
            created_at=row['created_at']
        )



class CreditSale:
    def __init__(self, id, date, customer_name, product_name, quantity, unit_price, quality, total_amount, status, notes, user_id, created_at=None):
        self.id = id
        self.date = date
        self.customer_name = customer_name
        self.product_name = product_name
        self.quantity = quantity
        self.unit_price = unit_price
        self.quality = quality
        self.total_amount = total_amount
        self.status = status
        self.notes = notes
        self.user_id = user_id
        self.created_at = created_at or datetime.now().isoformat()

    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row['id'],
            date=row['date'],
            customer_name=row['customer_name'],
            product_name=row['product_name'],
            quantity=row['quantity'],
            unit_price=row['unit_price'],
            quality=row['quality'],
            total_amount=row['total_amount'],
            status=row['status'],
            notes=row['notes'],
            user_id=row['user_id'],
            created_at=row['created_at']
        )

class CreditSalePayment:
    def __init__(self, id, credit_sale_id, payment_date, amount, payment_method, notes, user_id, created_at=None):
        self.id = id
        self.credit_sale_id = credit_sale_id
        self.payment_date = payment_date
        self.amount = amount
        self.payment_method = payment_method
        self.notes = notes
        self.user_id = user_id
        self.created_at = created_at or datetime.now().isoformat()

    @classmethod
    def from_db_row(cls, row):
        return cls(
            id=row['id'],
            credit_sale_id=row['credit_sale_id'],
            payment_date=row['payment_date'],
            amount=row['amount'],
            payment_method=row['payment_method'],
            notes=row['notes'],
            user_id=row['user_id'],
            created_at=row['created_at']
        )
