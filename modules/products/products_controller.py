# modules/products/products_controller.py

from typing import List, Dict

class ProductsController:
    def __init__(self, database, auth_manager):
        self.db = database
        self.auth = auth_manager

    def _require_admin(self):
        if not self.auth.has_permission("admin"):
            raise PermissionError("Solo los administradores pueden gestionar productos.")

    def create_product(self, name: str, qualities: List[str]):
        """Crea un nuevo producto con sus calidades."""
        self._require_admin()
        
        # Validación de datos
        name = (name or "").strip().capitalize()
        if not name:
            raise ValueError("El nombre del producto no puede estar vacío.")
        
        # Filtra calidades vacías y las capitaliza
        clean_qualities = sorted([q.strip().capitalize() for q in qualities if q.strip()])
        if not clean_qualities:
            raise ValueError("Debe especificar al menos una calidad válida.")
        
        # Convierte la lista de calidades a un string separado por comas
        qualities_str = ",".join(clean_qualities)
        
        try:
            self.db.execute_query(
                "INSERT INTO products (name, qualities) VALUES (?, ?)",
                (name, qualities_str)
            )
        except self.db.connection.IntegrityError:
            raise ValueError(f"El producto '{name}' ya existe.")

    def get_all_products(self) -> List[Dict]:
        """Obtiene todos los productos y sus calidades."""
        rows = self.db.execute_query("SELECT id, name, qualities FROM products ORDER BY name ASC")
        if not rows:
            return []
        
        # Formatea los datos para la vista
        products = []
        for row in rows:
            products.append({
                "id": row["id"],
                "name": row["name"],
                "qualities_list": row["qualities"].split(','),
                "qualities_str": ", ".join(row["qualities"].split(','))
            })
        return products

    def update_product(self, product_id: int, name: str, qualities: List[str]):
        """Actualiza un producto existente."""
        self._require_admin()
        
        name = (name or "").strip().capitalize()
        if not name:
            raise ValueError("El nombre del producto no puede estar vacío.")
        
        clean_qualities = sorted([q.strip().capitalize() for q in qualities if q.strip()])
        if not clean_qualities:
            raise ValueError("Debe especificar al menos una calidad válida.")
        
        qualities_str = ",".join(clean_qualities)
        
        try:
            self.db.execute_query(
                "UPDATE products SET name = ?, qualities = ? WHERE id = ?",
                (name, qualities_str, product_id)
            )
        except self.db.connection.IntegrityError:
            raise ValueError(f"El producto '{name}' ya existe.")
            
    def delete_product(self, product_id: int):
        """Elimina un producto."""
        self._require_admin()
        
        # Opcional: Verificar si el producto está en uso en el inventario antes de borrar
        # (Esta lógica se puede añadir para mayor seguridad)
        
        self.db.execute_query("DELETE FROM products WHERE id = ?", (product_id,))