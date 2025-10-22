# modules/supplier_advances/supplier_advances_views.py
"""
Vista para Anticipos a Proveedores
- Diseño de panel dividido (similar a 'Créditos') sin ventanas emergentes.
- Panel izquierdo: Crear anticipo y Aplicar a compra.
- Panel derecho: Historial filtrable de anticipos.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime, timedelta
from modules.supplier_advances.supplier_advances_controller import SupplierAdvancesController

PAY_TO_CODE = {"Efectivo": "cash", "Transferencia": "transfer"}

class SupplierAdvancesView:
    def __init__(self, parent, database, auth_manager, cash_controller):
        self.parent = parent
        self.db = database
        self.auth = auth_manager
        self.controller = SupplierAdvancesController(database, auth_manager, cash_controller)
        
        self.selected_advance_id = None
        self.selected_advance_data = {}

        self._build_ui()
        self.refresh_all()

    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=8)
        container.pack(fill=tk.BOTH, expand=True)

        # --- Panel Izquierdo (Formularios) ---
        left_panel = ttk.Frame(container, width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        # --- Panel Derecho (Historial) ---
        right_panel = ttk.Frame(container)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Contenido Panel Izquierdo ---
        self._build_left_panel_new_advance(left_panel)
        self._build_left_panel_application(left_panel)
        
        # --- Contenido Panel Derecho ---
        self._build_right_panel_history(right_panel)

    def _build_left_panel_new_advance(self, parent):
        """Construye el formulario de 'Nuevo Anticipo'."""
        lf_new_adv = ttk.LabelFrame(parent, text="Nuevo Anticipo", padding=10)
        lf_new_adv.pack(fill=tk.X, expand=False, pady=(0, 10))

        ttk.Label(lf_new_adv, text="Proveedor:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.supplier_entry = ttk.Entry(lf_new_adv)
        self.supplier_entry.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5)

        ttk.Label(lf_new_adv, text="Fecha:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.adv_date_entry = DateEntry(lf_new_adv, date_pattern='yyyy-mm-dd', width=12)
        self.adv_date_entry.set_date(datetime.now())
        self.adv_date_entry.grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(lf_new_adv, text="Monto:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.adv_amount_entry = ttk.Entry(lf_new_adv, width=14)
        self.adv_amount_entry.grid(row=2, column=1, sticky=tk.W, padx=5)

        ttk.Label(lf_new_adv, text="Método Pago:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.adv_payment_cb = ttk.Combobox(lf_new_adv, state="readonly", values=list(PAY_TO_CODE.keys()), width=12)
        self.adv_payment_cb.set("Efectivo")
        self.adv_payment_cb.grid(row=3, column=1, sticky=tk.W, padx=5)

        ttk.Label(lf_new_adv, text="Notas:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.adv_notes_entry = ttk.Entry(lf_new_adv)
        self.adv_notes_entry.grid(row=4, column=1, columnspan=2, sticky=tk.EW, padx=5)

        self.save_adv_btn = ttk.Button(lf_new_adv, text="Guardar Anticipo", command=self._save_advance)
        self.save_adv_btn.grid(row=5, column=0, columnspan=3, pady=10)

        lf_new_adv.columnconfigure(1, weight=1)

    def _build_left_panel_application(self, parent):
        """Construye el formulario de 'Aplicar a Compra'."""
        self.lf_app = ttk.LabelFrame(parent, text="Aplicar a Compra (Seleccione un anticipo)", padding=10)
        self.lf_app.pack(fill=tk.X, expand=False)
        
        self.selected_adv_label = ttk.Label(self.lf_app, text="Anticipo: N/A", font=('Segoe UI', 9, 'bold'))
        self.selected_adv_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        ttk.Label(self.lf_app, text="Fecha Compra:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.app_date_entry = DateEntry(self.lf_app, date_pattern='yyyy-mm-dd', width=12)
        self.app_date_entry.set_date(datetime.now())
        self.app_date_entry.grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(self.lf_app, text="Total Compra:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.app_purchase_total_entry = ttk.Entry(self.lf_app, width=14)
        self.app_purchase_total_entry.grid(row=2, column=1, sticky=tk.W, padx=5)
        self.app_purchase_total_entry.bind("<KeyRelease>", self._update_application_summary)

        self.app_adv_amount_lbl = ttk.Label(self.lf_app, text="Anticipo a Aplicar: S/ 0.00")
        self.app_adv_amount_lbl.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2, padx=5)
        
        self.app_remaining_lbl = ttk.Label(self.lf_app, text="Restante a Pagar: S/ 0.00", font=('Segoe UI', 9, 'bold'))
        self.app_remaining_lbl.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=2, padx=5)

        self.app_pay_remaining_check = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.lf_app, text="Registrar pago restante en Caja", variable=self.app_pay_remaining_check).grid(
            row=5, column=0, columnspan=2, sticky=tk.W, pady=5)

        ttk.Label(self.lf_app, text="Método Pago:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self.app_payment_cb = ttk.Combobox(self.lf_app, state="readonly", values=list(PAY_TO_CODE.keys()), width=12)
        self.app_payment_cb.set("Efectivo")
        self.app_payment_cb.grid(row=6, column=1, sticky=tk.W, padx=5)

        # --- CAMBIO: Se eliminó el campo de Notas de Compra ---
        
        self.apply_adv_btn = ttk.Button(self.lf_app, text="Aplicar a Compra", command=self._apply_purchase)
        # Se movió el botón a la fila 7 (antes 8)
        self.apply_adv_btn.grid(row=7, column=0, columnspan=2, pady=10)
        
        self.lf_app.columnconfigure(1, weight=1)
        self._toggle_application_form(False) # Deshabilitado al inicio

    def _build_right_panel_history(self, parent):
        """Construye el historial (filtros y árbol) en el panel derecho."""
        filters = ttk.LabelFrame(parent, text="Historial de Anticipos", padding=8)
        filters.pack(fill=tk.X)

        ttk.Label(filters, text="Desde:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.start_de = DateEntry(filters, date_pattern='yyyy-mm-dd', width=12)
        self.start_de.set_date(datetime.now() - timedelta(days=30))
        self.start_de.grid(row=0, column=1, sticky=tk.W, padx=(4, 12))

        ttk.Label(filters, text="Hasta:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.end_de = DateEntry(filters, date_pattern='yyyy-mm-dd', width=12)
        self.end_de.set_date(datetime.now())
        self.end_de.grid(row=0, column=3, sticky=tk.W, padx=(4, 12))

        ttk.Label(filters, text="Estado:").grid(row=0, column=4, sticky=tk.W, pady=2)
        self.status_cb = ttk.Combobox(filters, state="readonly", width=14, 
                                      values=["Todos", "Pendientes", "Aplicados"])
        self.status_cb.set("Pendientes")
        self.status_cb.grid(row=0, column=5, sticky=tk.W, padx=(4, 12))
        
        self.apply_filter_btn = ttk.Button(filters, text="Buscar", command=self._load_advances_list)
        self.apply_filter_btn.grid(row=0, column=6, padx=(8, 4))
        
        self.delete_adv_btn = ttk.Button(filters, text="Eliminar Anticipo", command=self._delete_advance)
        self.delete_adv_btn.grid(row=0, column=7, padx=4)

        # --- CAMBIO: Se agregó el botón de Reporte PDF ---
        self.report_adv_btn = ttk.Button(filters, text="Reporte PDF", command=self._export_pdf)
        self.report_adv_btn.grid(row=0, column=8, padx=4)

        # --- Tabla Principal ---
        tree_frame = ttk.Frame(parent, padding=(0, 10, 0, 0))
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # --- CAMBIO: Se agregó la columna 'notes' ---
        columns = ('id', 'date', 'supplier', 'total', 'status', 'applied_at', 'notes')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=18)
        
        ysb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        xsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # --- CAMBIO: Se agregaron headers y widths para 'notes' ---
        headers = {
            'id': 'ID', 'date': 'Fecha', 'supplier': 'Proveedor', 'total': 'Monto',
            'status': 'Estado', 'applied_at': 'Fecha Aplic.', 'notes': 'Nota Anticipo'
        }
        widths = {'id': 40, 'date': 90, 'supplier': 200, 'total': 100, 'status': 80, 'applied_at': 90, 'notes': 250}
        
        for c in columns:
            # Se ajustó el anclaje para 'notes'
            anchor = tk.W 
            if c == 'total':
                anchor = tk.E
            elif c in ('id', 'date', 'status', 'applied_at'):
                anchor = tk.CENTER
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor=anchor, stretch=True)

        self.tree.tag_configure("applied_status", foreground="red", font=('Segoe UI', 9, 'bold'))
        self.tree.tag_configure("unpaid_status", foreground="#006400")
        self.tree.tag_configure("oddrow", background="#f5f5f5")
        
        self.tree.bind("<<TreeviewSelect>>", self._on_main_tree_select)
        self.tree.bind("<Double-1>", lambda e: self.app_purchase_total_entry.focus())

    # --- Métodos de Lógica de UI ---

    def refresh_all(self):
        """Método público para refrescar toda la pestaña."""
        self._clear_advance_form()
        self._clear_application_form()
        self._load_advances_list()

    def _load_advances_list(self):
        """Recarga la lista principal de anticipos."""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            start = self.start_de.get_date().strftime('%Y-%m-%d')
            end = self.end_de.get_date().strftime('%Y-%m-%d')
            status_map = {"Pendientes": "unpaid", "Aplicados": "applied", "Todos": "all"}
            status = status_map.get(self.status_cb.get(), "all")
            
            advances = self.controller.get_all_advances(start, end, status)
            
            for i, adv in enumerate(advances):
                status_text = "Aplicado" if adv['status'] == 'applied' else "Pendiente"
                tag = "applied_status" if adv['status'] == 'applied' else "unpaid_status"
                tags = (tag, "oddrow") if i % 2 else (tag,)

                # --- CAMBIO: Se agregó adv['notes'] a los valores ---
                self.tree.insert("", tk.END, iid=adv['id'], values=(
                    adv['id'],
                    adv['date_issued'],
                    adv['supplier_name'],
                    f"S/ {adv['total_amount']:.2f}",
                    status_text,
                    adv['applied_at'] or 'N/A',
                    adv['notes'] or ''
                ), tags=tags)
        except Exception as e:
            messagebox.showerror("Error al cargar anticipos", str(e))

    def _clear_advance_form(self):
        """Limpia el formulario de nuevo anticipo."""
        self.supplier_entry.delete(0, tk.END)
        self.adv_date_entry.set_date(datetime.now())
        self.adv_amount_entry.delete(0, tk.END)
        self.adv_payment_cb.set("Efectivo")
        self.adv_notes_entry.delete(0, tk.END)

    def _save_advance(self):
        """Guarda el nuevo anticipo y actualiza la Caja."""
        try:
            # --- CAMBIO: Validación de Proveedor ---
            supplier = self.supplier_entry.get().strip()
            if not supplier:
                messagebox.showerror("Dato Vacío", "El nombre del 'Proveedor' no puede estar vacío.")
                return

            date = self.adv_date_entry.get_date().strftime('%Y-%m-%d')

            # --- CAMBIO: Validación de Monto (número y > 0) ---
            try:
                amount_str = self.adv_amount_entry.get().strip()
                if not amount_str:
                    raise ValueError("El campo 'Monto' no puede estar vacío.")
                amount = float(amount_str)
                if amount <= 0:
                    raise ValueError("El 'Monto' debe ser un número positivo.")
            except ValueError as ve:
                messagebox.showerror("Dato Inválido", f"Error en 'Monto':\n{ve}", parent=self.parent)
                return
            
            method = PAY_TO_CODE[self.adv_payment_cb.get()]
            notes = self.adv_notes_entry.get().strip()

            # Esta llamada REGISTRA EL EGRESO EN CAJA
            self.controller.create_advance(supplier, date, amount, notes, method)
            
            messagebox.showinfo("Éxito", "Anticipo registrado. Se ha creado un egreso en caja.")
            self._clear_advance_form()
            self._load_advances_list() # Recargar el historial
            
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error de validación", str(e))
        except Exception as e:
            messagebox.showerror("Error inesperado", f"No se pudo crear el anticipo: {e}")

    # --- Métodos del Formulario de Aplicación ---

    def _on_main_tree_select(self, _=None):
        """Se activa al seleccionar una fila en el árbol principal."""
        selected = self.tree.selection()
        if not selected:
            self._clear_application_form()
            self._toggle_application_form(False)
            return

        self.selected_advance_id = selected[0]
        try:
            self.selected_advance_data = self.controller.get_advance(self.selected_advance_id)
            if not self.selected_advance_data:
                raise ValueError("No se pudo cargar el dato")

            supplier = self.selected_advance_data['supplier_name']
            amount = float(self.selected_advance_data['total_amount'])
            status = self.selected_advance_data['status']
            
            # Actualizar formulario de aplicación
            self.lf_app.config(text=f"Aplicar Anticipo ID: {self.selected_advance_id}")
            self.selected_adv_label.config(text=f"Proveedor: {supplier}")
            self.app_adv_amount_lbl.config(text=f"Anticipo a Aplicar: S/ {amount:.2f}")

            if status == "unpaid":
                self._toggle_application_form(True)
                self.app_purchase_total_entry.delete(0, tk.END)
                self.app_purchase_total_entry.focus()
            else:
                self._toggle_application_form(False)
                self.lf_app.config(text="Anticipo ya Aplicado")
            
            self._update_application_summary()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el anticipo: {e}")
            self._clear_application_form()
            self._toggle_application_form(False)

    def _update_application_summary(self, _=None):
        """Calcula el monto restante al escribir en 'Total Compra'."""
        try:
            purchase_total = float(self.app_purchase_total_entry.get() or 0)
        except ValueError:
            purchase_total = 0.0
            
        adv_amount = float(self.selected_advance_data.get('total_amount', 0.0))
        remaining = round(purchase_total - adv_amount, 2)
        
        self.app_remaining_lbl.config(text=f"Restante a Pagar: S/ {remaining:.2f}")
        
        if remaining < 0:
            self.app_remaining_lbl.config(foreground="red")
        else:
            self.app_remaining_lbl.config(foreground="green")

    def _toggle_application_form(self, enabled: bool):
        """Activa o desactiva todos los widgets en el frame de aplicación."""
        state = "normal" if enabled else "disabled"
        for child in self.lf_app.winfo_children():
            if isinstance(child, (ttk.Entry, ttk.Combobox, ttk.Button, DateEntry, ttk.Checkbutton)):
                child.config(state=state)

    def _clear_application_form(self):
        """Limpia el formulario de aplicación."""
        self.selected_advance_id = None
        self.selected_advance_data = {}
        self.lf_app.config(text="Aplicar a Compra (Seleccione un anticipo)")
        self.selected_adv_label.config(text="Anticipo: N/A")
        self.app_purchase_total_entry.delete(0, tk.END)
        # --- CAMBIO: Se eliminó la limpieza del campo de notas ---
        # self.app_notes_entry.delete(0, tk.END)
        self.app_payment_cb.set("Efectivo")
        self.app_adv_amount_lbl.config(text="Anticipo a Aplicar: S/ 0.00")
        self.app_remaining_lbl.config(text="Restante a Pagar: S/ 0.00", foreground="black")
        self._toggle_application_form(False)

    def _apply_purchase(self):
        """Aplica el anticipo a la compra."""
        if not self.selected_advance_id:
            messagebox.showwarning("Sin selección", "No hay un anticipo seleccionado.")
            return
        
        try:
            app_date = self.app_date_entry.get_date().strftime('%Y-%m-%d')
            
            # --- CAMBIO: Validación de Total Compra (número y > 0) ---
            try:
                purchase_total_str = self.app_purchase_total_entry.get().strip()
                if not purchase_total_str:
                    raise ValueError("El campo 'Total Compra' no puede estar vacío.")
                purchase_total = float(purchase_total_str)
                if purchase_total <= 0:
                     raise ValueError("El 'Total Compra' debe ser un número positivo.")
            except ValueError as ve:
                messagebox.showerror("Dato Inválido", f"Error en 'Total Compra':\n{ve}", parent=self.parent)
                return
            
            pay_remaining = self.app_pay_remaining_check.get()
            payment_method = PAY_TO_CODE[self.app_payment_cb.get()]
            # --- CAMBIO: Se pasan notas vacías ---
            notes = ""

            # Esta llamada REGISTRA EL PAGO RESTANTE EN CAJA (si aplica)
            self.controller.apply_advance(
                self.selected_advance_id, app_date, purchase_total,
                pay_remaining, payment_method, notes
            )
            
            messagebox.showinfo("Éxito", "Anticipo aplicado correctamente.")
            self._clear_application_form()
            self._load_advances_list()
            
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error de validación", str(e))
        except Exception as e:
            messagebox.showerror("Error inesperado", f"No se pudo aplicar el anticipo: {e}")

    def _delete_advance(self):
        """Elimina el anticipo seleccionado (y revierte la caja)."""
        # --- CAMBIO: Se usa self.selected_advance_id en lugar de leer el árbol ---
        adv_id = self.selected_advance_id
        if not adv_id:
            messagebox.showwarning("Sin selección", "Por favor, seleccione un anticipo de la lista.")
            return

        # Se usa self.selected_advance_data que ya se cargó al seleccionar
        adv = self.selected_advance_data
        if not adv:
             # Fallback por si no se seleccionó
             adv = self.controller.get_advance(adv_id)
             if not adv:
                 messagebox.showerror("Error", "No se pudo encontrar el anticipo a eliminar.")
                 return

        if adv['status'] == 'applied':
            messagebox.showerror("Acción denegada", "No se puede eliminar un anticipo que ya fue aplicado.")
            return
            
        if messagebox.askyesno("Confirmar Eliminación", 
            f"¿Está seguro de eliminar el anticipo ID {adv_id} por S/ {adv['total_amount']:.2f}?\n\n"):
            
            try:
                # Esta llamada CREA UN INGRESO EN CAJA
                self.controller.delete_advance(adv_id)
                messagebox.showinfo("Éxito", "Anticipo eliminado.")
                self.refresh_all()
            except Exception as e:
                messagebox.showerror("Error al eliminar", str(e))

    # --- CAMBIO: Se agregó el método placeholder para el PDF ---
    def _export_pdf(self):
        """Placeholder para la futura función de exportar PDF."""
        messagebox.showinfo("Función no implementada", 
                            "La generación de reportes PDF para anticipos se implementará a futuro.",
                            parent=self.parent)