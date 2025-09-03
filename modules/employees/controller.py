# modules/employees/controller.py
"""
Controlador de Empleados
CRUD básico de empleados (nombre, apellido, salario, estado).
"""

class EmployeesController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth = auth_manager
        self._ensure_schema()

    def _ensure_schema(self):
        self.db.execute_query("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                salary REAL NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def list_employees(self, include_inactive=True):
        q = "SELECT * FROM employees"
        if not include_inactive:
            q += " WHERE is_active=1"
        q += " ORDER BY last_name, first_name"
        rows = self.db.execute_query(q)
        return [dict(r) for r in rows] if rows else []

    def add_employee(self, first_name, last_name, salary):
        if not self.auth.has_permission("admin"):
            raise Exception("Solo los administradores pueden crear empleados")
        if not first_name or not last_name:
            raise Exception("Nombre y apellido son obligatorios")
        s = float(salary)
        if s < 0:
            raise Exception("El salario no puede ser negativo")
        emp_id = self.db.execute_query(
            "INSERT INTO employees (first_name, last_name, salary) VALUES (?, ?, ?)",
            (first_name.strip(), last_name.strip(), s)
        )
        return emp_id


    def update_employee(self, emp_id, first_name, last_name, salary, is_active=True):
        if not self.auth.has_permission("admin"):
            raise Exception("Solo administrador puede editar empleados")
        if not first_name or not last_name:
            raise Exception("Nombre y apellido son obligatorios")
        s = float(salary)
        if s < 0:
            raise Exception("El salario no puede ser negativo")
        self.db.execute_query(
            "UPDATE employees SET first_name=?, last_name=?, salary=?, is_active=? WHERE id=?",
            (first_name.strip(), last_name.strip(), s, 1 if is_active else 0, emp_id)
        )
        return True

    def toggle_active(self, emp_id, active: bool):
        if not self.auth.has_permission("admin"):
            raise Exception("Solo administrador puede cambiar el estado")
        self.db.execute_query(
            "UPDATE employees SET is_active=? WHERE id=?",
            (1 if active else 0, emp_id)
        )
        return True

    def get_employee(self, emp_id):
        r = self.db.execute_query("SELECT * FROM employees WHERE id=?", (emp_id,))
        return dict(r[0]) if r else None
