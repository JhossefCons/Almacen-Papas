"""
Módulo para la gestión de la base de datos SQLite
"""
import sqlite3
import os
import threading
from datetime import datetime

class Database:
    def __init__(self, db_name="papasoft.db"):
        self.db_name = db_name
        self.connection = None
        self._lock = threading.Lock()  # <-- para acceso concurrente seguro
        self.init_db()
        
    def connect(self):
        """Establecer conexión con la base de datos"""
        if self.connection is None:
            # permitir uso desde hilos distintos
            self.connection = sqlite3.connect(self.db_name, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
        return self.connection
    
    def close(self):
        """Cerrar la conexión con la base de datos"""
        if self.connection:
            self.connection.close()
            self.connection = None
            
    def init_db(self):
        """Inicializar la base de datos con las tablas necesarias"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Tabla de usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de caja
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cash_register (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_method TEXT NOT NULL,
                category TEXT,
                user_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Tabla de préstamos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_name TEXT NOT NULL,
                amount REAL NOT NULL,
                date_issued TEXT NOT NULL,
                due_date TEXT NOT NULL,
                interest_rate REAL DEFAULT 0,
                status TEXT DEFAULT 'active',
                notes TEXT,
                user_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Tabla de pagos de préstamos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loan_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id INTEGER,
                payment_date TEXT NOT NULL,
                amount REAL NOT NULL,
                notes TEXT,
                user_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (loan_id) REFERENCES loans (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Tabla de inventario de papa
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS potato_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                potato_type TEXT NOT NULL,
                quality TEXT NOT NULL,
                operation TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_value REAL NOT NULL,
                supplier_customer TEXT,
                notes TEXT,
                user_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Stock de costales (empaque) - tabla única con id=1
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS packaging_stock (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                sacks_count INTEGER NOT NULL DEFAULT 0,
                sack_price REAL DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Agregar columna sack_price si no existe
        try:
            cursor.execute("ALTER TABLE packaging_stock ADD COLUMN sack_price REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # columna ya existe

        cursor.execute("SELECT COUNT(*) AS c FROM packaging_stock WHERE id = 1")
        row = cursor.fetchone()
        if not row or row["c"] == 0:
            cursor.execute(
                "INSERT INTO packaging_stock (id, sacks_count, sack_price, updated_at) VALUES (1, 0, 0, CURRENT_TIMESTAMP)"
            )



        # Tabla de ventas a crédito
        cursor.execute('''CREATE TABLE IF NOT EXISTS credit_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            quality TEXT NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'active',
            notes TEXT,
            user_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')

        # Tabla de pagos de ventas a crédito
        cursor.execute('''CREATE TABLE IF NOT EXISTS credit_sale_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credit_sale_id INTEGER,
            payment_date TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            notes TEXT,
            user_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (credit_sale_id) REFERENCES credit_sales (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')

        conn.commit()
        
    def execute_query(self, query, params=None):
        """Ejecutar una consulta y retornar resultados (thread-safe)"""
        with self._lock:
            conn = self.connect()
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                    
                if query.strip().upper().startswith('SELECT'):
                    return cursor.fetchall()
                else:
                    conn.commit()
                    return cursor.lastrowid
            except sqlite3.Error as e:
                conn.rollback()
                raise e
            
    def get_cursor(self):
        """Obtener un cursor para operaciones más complejas"""
        return self.connect().cursor()
