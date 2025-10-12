# modules/products/products_views.py

import tkinter as tk
from tkinter import ttk, messagebox

from modules.products.products_controller import ProductsController

class ProductsView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth = auth_manager
        self.controller = ProductsController(database, auth_manager)
        self.is_admin = self.auth.has_permission("admin")
        
        self._build_ui()
        self.load_products()

    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=10)
        container.pack(fill=tk.BOTH, expand=True)
        
        left = ttk.LabelFrame(container, text="Gestión de Productos", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), anchor="n")

        right = ttk.LabelFrame(container, text="Lista de Productos", padding=10)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Panel Izquierdo: Formulario ---
        row = 0
        ttk.Label(left, text="Nombre Producto:").grid(row=row, column=0, sticky="w", pady=2)
        self.name_entry = ttk.Entry(left, width=30)
        self.name_entry.grid(row=row, column=1, sticky="ew", pady=2)
        row += 1
        
        ttk.Label(left, text="Calidades (separadas por coma):").grid(row=row, column=0, sticky="w", pady=2)
        self.qualities_entry = ttk.Entry(left)
        self.qualities_entry.grid(row=row, column=1, sticky="ew", pady=2)
        row += 1

        button_frame = ttk.Frame(left)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10, sticky="w")
        
        self.add_btn = ttk.Button(button_frame, text="Agregar Nuevo", command=self.add_product)
        self.add_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.update_btn = ttk.Button(button_frame, text="Guardar Cambios", command=self.update_product)
        self.update_btn.pack(side=tk.LEFT)
        self.clear_btn = ttk.Button(button_frame, text="Limpiar", command=self.clear_form)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        left.grid_columnconfigure(1, weight=1)

        # --- Panel Derecho: Tabla y Botones ---
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        cols = ('id', 'name', 'qualities')
        self.tree = ttk.Treeview(right, columns=cols, show="headings")
        
        scrollbar = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.heading('id', text='ID')
        self.tree.heading('name', text='Nombre Producto')
        self.tree.heading('qualities', text='Calidades Permitidas')
        
        self.tree.column('id', width=50, anchor=tk.CENTER, stretch=False)
        self.tree.column('name', width=200)
        self.tree.column('qualities', width=400)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)
        
        self.delete_btn = ttk.Button(right, text="Eliminar Seleccionado", command=self.delete_product)
        self.delete_btn.grid(row=1, column=0, columnspan=2, pady=(5,0), sticky="e")
        
        if not self.is_admin:
            for widget in (self.name_entry, self.qualities_entry, self.add_btn, self.update_btn, self.delete_btn):
                widget.config(state="disabled")

    def load_products(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        products = self.controller.get_all_products()
        for p in products:
            self.tree.insert('', 'end', values=(p['id'], p['name'], p['qualities_str']))
        
        self.clear_form()

    def add_product(self):
        name = self.name_entry.get()
        qualities = self.qualities_entry.get().split(',')
        try:
            self.controller.create_product(name, qualities)
            messagebox.showinfo("Éxito", "Producto agregado correctamente.")
            self.load_products()
            self.parent.event_generate("<<ProductsChanged>>")
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error", str(e))

    def update_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Sin selección", "Por favor, seleccione un producto para actualizar.")
            return
            
        product_id = self.tree.item(selected[0])['values'][0]
        name = self.name_entry.get()
        qualities = self.qualities_entry.get().split(',')
        
        try:
            self.controller.update_product(product_id, name, qualities)
            messagebox.showinfo("Éxito", "Producto actualizado correctamente.")
            self.load_products()
            self.parent.event_generate("<<ProductsChanged>>")
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error", str(e))
            
    def delete_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Sin selección", "Por favor, seleccione un producto para eliminar.")
            return

        product_id = self.tree.item(selected[0])['values'][0]
        name = self.tree.item(selected[0])['values'][1]

        if messagebox.askyesno("Confirmar", f"¿Está seguro de que desea eliminar el producto '{name}'?"):
            try:
                self.controller.delete_product(product_id)
                messagebox.showinfo("Éxito", "Producto eliminado.")
                self.load_products()
                self.parent.event_generate("<<ProductsChanged>>")
            except (ValueError, PermissionError) as e:
                messagebox.showerror("Error", str(e))
                
    def on_item_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
            
        item = self.tree.item(selected[0])['values']
        self.clear_form(keep_selection=True)
        self.name_entry.insert(0, item[1])
        self.qualities_entry.insert(0, item[2])
        
    def clear_form(self, keep_selection=False):
        self.name_entry.delete(0, 'end')
        self.qualities_entry.delete(0, 'end')
        if not keep_selection:
            if self.tree.selection():
                self.tree.selection_remove(self.tree.selection())

    def refresh_all(self):
        self.load_products()