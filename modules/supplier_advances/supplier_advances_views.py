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

# --- CAMBIO: Importaciones para PDF ---
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False
# --- FIN CAMBIO ---

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
        
        self.apply_adv_btn = ttk.Button(self.lf_app, text="Aplicar a Compra", command=self._apply_purchase)
        self.apply_adv_btn.grid(row=7, column=0, columnspan=2, pady=10)
        
        self.lf_app.columnconfigure(1, weight=1)
        self._toggle_application_form(False)

    def _build_right_panel_history(self, parent):
        """Construye el historial (filtros y árbol) en el panel derecho."""
        filters = ttk.LabelFrame(parent, text="Historial de Anticipos", padding=8)
        filters.pack(fill=tk.X)

        ttk.Label(filters, text="Desde:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.start_de = DateEntry(filters, date_pattern='yyyy-mm-dd', width=12)
        self.start_de.set_date(datetime.now() - timedelta(days=30))
        self.start_de.grid(row=0, column=1, sticky=tk.W, padx=(4, 12))
        self.start_de.bind("<<DateEntrySelected>>", lambda e: self._load_advances_list())

        ttk.Label(filters, text="Hasta:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.end_de = DateEntry(filters, date_pattern='yyyy-mm-dd', width=12)
        self.end_de.set_date(datetime.now())
        self.end_de.grid(row=0, column=3, sticky=tk.W, padx=(4, 12))
        self.end_de.bind("<<DateEntrySelected>>", lambda e: self._load_advances_list())

        ttk.Label(filters, text="Estado:").grid(row=0, column=4, sticky=tk.W, pady=2)
        self.status_cb = ttk.Combobox(filters, state="readonly", width=14, 
                                      values=["Todos", "Pendientes", "Aplicados"])
        self.status_cb.set("Pendientes")
        self.status_cb.grid(row=0, column=5, sticky=tk.W, padx=(4, 12))
        self.status_cb.bind("<<ComboboxSelected>>", lambda e: self._load_advances_list())
        
        self.apply_filter_btn = ttk.Button(filters, text="Buscar", command=self._load_advances_list)
        self.apply_filter_btn.grid(row=0, column=6, padx=(8, 4))
        
        self.delete_adv_btn = ttk.Button(filters, text="Eliminar Anticipo", command=self._delete_advance)
        self.delete_adv_btn.grid(row=0, column=7, padx=4)

        self.report_adv_btn = ttk.Button(filters, text="Reporte PDF", command=self._export_pdf)
        self.report_adv_btn.grid(row=0, column=8, padx=4)

        # --- Tabla Principal ---
        tree_frame = ttk.Frame(parent, padding=(0, 10, 0, 0))
        tree_frame.pack(fill=tk.BOTH, expand=True)

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

        headers = {
            'id': 'ID', 'date': 'Fecha', 'supplier': 'Proveedor', 'total': 'Monto',
            'status': 'Estado', 'applied_at': 'Fecha Aplic.', 'notes': 'Nota Anticipo'
        }
        widths = {'id': 40, 'date': 90, 'supplier': 200, 'total': 100, 'status': 80, 'applied_at': 90, 'notes': 250}
        
        for c in columns:
            anchor = tk.W 
            if c == 'total': anchor = tk.E
            elif c in ('id', 'date', 'status', 'applied_at'): anchor = tk.CENTER
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
            self.status_map_es = {"unpaid": "Pendiente", "applied": "Aplicado"} # Para el PDF
            self.current_status_filter_es = self.status_cb.get()
            
            status = status_map.get(self.current_status_filter_es, "all")
            
            advances = self.controller.get_all_advances(start, end, status)
            
            for i, adv in enumerate(advances):
                status_text = self.status_map_es.get(adv['status'], adv['status'])
                tag = "applied_status" if adv['status'] == 'applied' else "unpaid_status"
                tags = (tag, "oddrow") if i % 2 else (tag,)

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
            supplier = self.supplier_entry.get().strip()
            if not supplier:
                messagebox.showerror("Dato Vacío", "El nombre del 'Proveedor' no puede estar vacío.")
                return

            date = self.adv_date_entry.get_date().strftime('%Y-%m-%d')

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

            self.controller.create_advance(supplier, date, amount, notes, method)
            
            messagebox.showinfo("Éxito", "Anticipo registrado. Se ha creado un egreso en caja.")
            self._clear_advance_form()
            self._load_advances_list()
            
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
            notes = ""

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
        adv_id = self.selected_advance_id
        if not adv_id:
            messagebox.showwarning("Sin selección", "Por favor, seleccione un anticipo de la lista.")
            return

        adv = self.selected_advance_data
        if not adv:
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
                self.controller.delete_advance(adv_id)
                messagebox.showinfo("Éxito", "Anticipo eliminado.")
                self.refresh_all()
            except Exception as e:
                messagebox.showerror("Error al eliminar", str(e))

    # --- CAMBIO: Método _export_pdf implementado ---
    def _export_pdf(self):
        """Exporta el historial filtrado de anticipos a un PDF."""
        
        if not REPORTLAB_OK:
            messagebox.showerror("Error", "La librería ReportLab no está instalada.\n\nInstálala con: pip install reportlab")
            return

        try:
            # 1. Obtener datos y filtros
            start = self.start_de.get_date().strftime('%Y-%m-%d')
            end = self.end_de.get_date().strftime('%Y-%m-%d')
            status_map = {"Pendientes": "unpaid", "Aplicados": "applied", "Todos": "all"}
            status_filter_es = self.current_status_filter_es
            status_filter_en = status_map.get(status_filter_es, "all")
            
            advances = self.controller.get_all_advances(start, end, status_filter_en)

            # 2. Pedir al usuario dónde guardar
            default_name = f"reporte_anticipos_{start.replace('-','')}_{end.replace('-','')}.pdf"
            path = filedialog.asksaveasfilename(
                title="Guardar Reporte PDF",
                initialfile=default_name,
                defaultextension=".pdf",
                filetypes=[("PDF Files", "*.pdf")]
            )
            if not path:
                return # Usuario canceló

            # 3. Crear el documento PDF
            doc = SimpleDocTemplate(
                path, pagesize=landscape(A4),
                leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=20*mm
            )
            story = []
            styles = getSampleStyleSheet()

            # Título y Metadatos
            title = Paragraph("<b>Reporte de Anticipos a Proveedores</b>", styles['Title'])
            meta_text = (
                f"Período: <b>{start}</b> a <b>{end}</b> | "
                f"Estado: <b>{status_filter_es}</b> | "
                f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            meta = Paragraph(meta_text, styles['Normal'])
            story += [title, Spacer(1, 4*mm), meta, Spacer(1, 6*mm)]

            # 4. Preparar datos de la tabla
            headers = ["ID", "Fecha", "Proveedor", "Monto", "Estado", "Fecha Aplic.", "Nota Anticipo"]
            table_data = [headers]
            
            total_monto = 0.0

            if not advances:
                table_data.append(["(Sin registros para este período)", "", "", "", "", "", ""])
            else:
                for adv in advances:
                    status_text = self.status_map_es.get(adv['status'], adv['status'])
                    monto = float(adv['total_amount'])
                    total_monto += monto
                    
                    table_data.append([
                        adv['id'],
                        adv['date_issued'],
                        adv['supplier_name'],
                        f"S/ {monto:,.2f}",
                        status_text,
                        adv['applied_at'] or 'N/A',
                        adv['notes'] or ''
                    ])

            # 5. Añadir fila de totales
            table_data.append([
                "TOTALES", "", "", f"S/ {total_monto:,.2f}", "", "", ""
            ])

            # 6. Definir anchos de columna (en mm)
            colWidths = [15*mm, 25*mm, 80*mm, 35*mm, 25*mm, 30*mm, 80*mm]
            tbl = Table(table_data, colWidths=colWidths, repeatRows=1)

            # 7. Aplicar estilos a la tabla
            style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),      # Encabezado
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,0), 'CENTER'),                 # Alineación encabezado
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 10),
                
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),          # Rejilla
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.whitesmoke, colors.transparent]),
                
                ('ALIGN', (0,1), (1,-1), 'CENTER'),                 # Col ID, Fecha
                ('ALIGN', (3,1), (3,-1), 'RIGHT'),                  # Col Monto
                ('ALIGN', (4,1), (5,-1), 'CENTER'),                 # Col Estado, Fecha Aplic.
                ('ALIGN', (1,1), (2,-1), 'LEFT'),                   # Col Proveedor
                ('ALIGN', (6,1), (6,-1), 'LEFT'),                   # Col Nota
                
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),    # Fila de Totales
                ('BACKGROUND', (0,-1), (-1,-1), colors.lightblue),
                ('ALIGN', (3,-1), (3,-1), 'RIGHT'),                 # Total Monto
            ])
            tbl.setStyle(style)
            story.append(tbl)
            
            # 8. Footer (número de página)
            def footer(canvas, doc):
                canvas.saveState()
                canvas.setFont('Helvetica', 9)
                canvas.drawRightString(doc.pagesize[0] - 15*mm, 10*mm, f"Página {doc.page}")
                canvas.restoreState()

            # 9. Construir el PDF
            doc.build(story, onFirstPage=footer, onLaterPages=footer)
            messagebox.showinfo("Exportar PDF", f"PDF generado correctamente:\n{path}")

        except Exception as e:
            messagebox.showerror("Error al Exportar PDF", f"No se pudo generar el PDF:\n{e}")