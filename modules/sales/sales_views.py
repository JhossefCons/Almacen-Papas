# modules/sales/sales_views.py
"""
Vista de Ventas (Tkinter + ttk)
- Registrar venta (impacta inventario, costales y Caja)
- Historial con filtros (fecha, producto, calidad)
- Totales y Exportar PDF
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime, timedelta

from modules.sales.sales_controller import SalesController

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
CODE_TO_PAY = {"cash": "Efectivo", "transfer": "Transferencia"}


class SalesView:
    def __init__(self, parent, database, auth_manager, cash_controller):
        self.parent = parent
        self.db = database
        self.auth = auth_manager
        self.controller = SalesController(database, auth_manager, cash_controller)

        self.products_data = {}

        self._build_ui()
        self.refresh_all(load_history=False)
        self._load_sales() # Cargar historial al inicio

    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=8)
        container.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(container, text="Nueva venta", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        right = ttk.Frame(container)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        row = 0
        ttk.Label(left, text="Fecha:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.date_entry = DateEntry(left, date_pattern="yyyy-mm-dd")
        self.date_entry.set_date(datetime.now())
        self.date_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Producto:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.type_cb = ttk.Combobox(left, state="readonly")
        self.type_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        self.type_cb.bind("<<ComboboxSelected>>", self._on_type_selected)
        row += 1

        # --- CAMBIO: Eliminada la lógica de "Otro..." (Requerimiento #9) ---
        # self.other_type_lbl = ttk.Label(left, text="Nombre Otro:")
        # self.other_type_entry = ttk.Entry(left)
        # self.other_quality_lbl = ttk.Label(left, text="Calidad Otro:")
        # self.other_quality_entry = ttk.Entry(left)

        ttk.Label(left, text="Calidad:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.quality_cb = ttk.Combobox(left, state="readonly")
        self.quality_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        self.quality_cb.bind("<<ComboboxSelected>>", self._on_combo_change)
        row += 1

        ttk.Label(left, text="Cantidad (bultos):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.qty_entry = ttk.Entry(left)
        self.qty_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Precio unitario (venta):").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.unit_price_entry = ttk.Entry(left)
        self.unit_price_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        self.manual_price = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            left, text="Editar precio manualmente", variable=self.manual_price,
            command=self._on_manual_price_toggle
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))
        row += 1

        ttk.Label(left, text="Método de pago:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.payment_cb = ttk.Combobox(left, state="readonly", values=tuple(PAY_TO_CODE.keys()))
        self.payment_cb.set("Efectivo")
        self.payment_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        self.add_to_cash = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="Registrar en Caja", variable=self.add_to_cash).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 6)
        )
        row += 1

        ttk.Label(left, text="Cliente:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.customer_entry = ttk.Entry(left)
        self.customer_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Notas:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.notes_entry = ttk.Entry(left)
        self.notes_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        btnf = ttk.Frame(left)
        btnf.grid(row=row, column=0, columnspan=2, pady=8, sticky=tk.W)
        ttk.Button(btnf, text="Registrar venta", command=self._create_sale).pack(side=tk.LEFT)
        row += 1

        self.stock_info_lbl = ttk.Label(left, text="Stock: - | Costales: -")
        self.stock_info_lbl.grid(row=row, column=0, columnspan=2, sticky="w", pady=(4,0))
        row += 1

        for c in (0, 1):
            left.grid_columnconfigure(c, weight=1)

        self._apply_price_state(disable_when_auto=True)

        filters = ttk.LabelFrame(right, text="Historial de ventas - Filtros", padding=8)
        filters.pack(fill=tk.X)

        ttk.Label(filters, text="Desde:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.start_de = DateEntry(filters, date_pattern='yyyy-mm-dd')
        self.start_de.set_date(datetime.now() - timedelta(days=30))
        self.start_de.grid(row=0, column=1, sticky=tk.W, padx=(4, 12))

        ttk.Label(filters, text="Hasta:").grid(row=0, column=2, sticky=tk.W, pady=2)
        self.end_de = DateEntry(filters, date_pattern='yyyy-mm-dd')
        self.end_de.set_date(datetime.now())
        self.end_de.grid(row=0, column=3, sticky=tk.W, padx=(4, 12))

        ttk.Label(filters, text="Producto:").grid(row=0, column=4, sticky=tk.W, pady=2)
        self.f_type = ttk.Combobox(filters, state="readonly", width=12)
        self.f_type.grid(row=0, column=5, sticky=tk.W, padx=(4, 12))

        ttk.Label(filters, text="Calidad:").grid(row=0, column=6, sticky=tk.W, pady=2)
        self.f_quality = ttk.Combobox(filters, state="readonly", values=("",), width=14)
        self.f_quality.set("")
        self.f_quality.grid(row=0, column=7, sticky=tk.W, padx=(4, 12))

        def on_filter_type_change(_=None):
            t = self.f_type.get()
            if t and t in self.products_data:
                self.f_quality.config(values=("", *self.products_data[t]))
            else:
                self.f_quality.config(values=("",))
            self.f_quality.set("")
        self.f_type.bind("<<ComboboxSelected>>", on_filter_type_change)

        ttk.Button(filters, text="Aplicar", command=self._load_sales).grid(row=0, column=8, padx=(8, 4))
        ttk.Button(filters, text="Exportar PDF", command=self._export_pdf).grid(row=0, column=9, padx=(4, 0), sticky=tk.E)
        
        filters.columnconfigure(9, weight=1) # Empujar PDF a la derecha

        sales_frame = ttk.LabelFrame(right, text="Historial de ventas", padding=(6, 6, 6, 6))
        sales_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        sales_frame.grid_rowconfigure(0, weight=1)
        sales_frame.grid_columnconfigure(0, weight=1)

        columns = ('date', 'product', 'quality', 'qty', 'unit', 'total', 'customer', 'pay', 'user', 'notes')
        self.sales_tree = ttk.Treeview(sales_frame, columns=columns, show='headings', height=18)

        ysb = ttk.Scrollbar(sales_frame, orient=tk.VERTICAL, command=self.sales_tree.yview)
        xsb = ttk.Scrollbar(sales_frame, orient=tk.HORIZONTAL, command=self.sales_tree.xview)
        self.sales_tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        self.sales_tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        headers = {
            'date': 'Fecha', 'product': 'Producto', 'quality': 'Calidad', 'qty': 'Bultos',
            'unit': 'Precio U.', 'total': 'Total', 'customer': 'Cliente', 'pay': 'Pago',
            'user': 'Usuario', 'notes': 'Notas'
        }
        widths = {
            'date': 110, 'product': 80, 'quality': 80, 'qty': 60,
            'unit': 110, 'total': 120, 'customer': 120, 'pay': 80, 'user': 120, 'notes': 320
        }
        anchors = {
            'date': tk.CENTER, 'product': tk.W, 'quality': tk.W, 'qty': tk.CENTER,
            'unit': tk.E, 'total': tk.E, 'customer': tk.W, 'pay': tk.CENTER, 'user': tk.W, 'notes': tk.W
        }

        for c in columns:
            self.sales_tree.heading(c, text=headers[c])
            self.sales_tree.column(c, width=widths[c], anchor=anchors[c], stretch=False)

        self.sales_tree.tag_configure('odd', background="#fafafa")

        totals_box = ttk.Frame(right)
        totals_box.pack(fill=tk.X, pady=(6, 0))
        self.totals_lbl = ttk.Label(totals_box, text="Totales: —", font=('Segoe UI', 9, 'bold'))
        self.totals_lbl.pack(anchor=tk.E)

    def _load_product_list(self):
        try:
            self.products_data = self.controller.inv.get_all_products()
            product_names = sorted(list(self.products_data.keys()))
            
            # --- CAMBIO: Ya no se añade "Otro..." ---
            self.type_cb['values'] = tuple(product_names)
            if product_names:
                self.type_cb.set(product_names[0])
            else:
                self.type_cb.set("")

            self.f_type['values'] = ("", *product_names)
            self.f_type.set("")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los productos: {e}")

    def _on_type_selected(self, _evt=None):
        selected = self.type_cb.get()

        # --- CAMBIO: Eliminada la lógica de "Otro..." ---
        qualities = self.products_data.get(selected, [])
        self.quality_cb['values'] = tuple(qualities)
        self.quality_cb.set(qualities[0] if qualities else "")
        
        self._on_combo_change()

    def _on_combo_change(self, _evt=None):
        self._auto_fill_price()
        self._refresh_stock_labels()

    def _get_form_product_data(self) -> tuple[str, str]:
        # --- CAMBIO: Eliminada la lógica de "Otro..." ---
        product = self.type_cb.get()
        quality = self.quality_cb.get()
        return product, quality

    def _apply_price_state(self, disable_when_auto: bool):
        if disable_when_auto and not self.manual_price.get():
            self.unit_price_entry.config(state="disabled")
        else:
            self.unit_price_entry.config(state="normal")

    def _auto_fill_price(self):
        if self.manual_price.get(): return
        
        product, quality = self._get_form_product_data()
        price = self.controller.get_last_sale_price(product, quality) if product and quality else None
        
        self.unit_price_entry.config(state="normal")
        self.unit_price_entry.delete(0, tk.END)
        if price is not None:
            self.unit_price_entry.insert(0, str(price))
        self._apply_price_state(disable_when_auto=True)

    def _on_manual_price_toggle(self):
        if self.manual_price.get():
            self._apply_price_state(disable_when_auto=False)
            self.unit_price_entry.focus()
            self.unit_price_entry.select_range(0, tk.END)
        else:
            self._auto_fill_price()

    def _refresh_stock_labels(self):
        try:
            product, quality = self._get_form_product_data()
            stock = self.controller.get_stock(product, quality) if product and quality else 0
            sacks = self.controller.get_sacks()
            self.stock_info_lbl.config(text=f"Stock seleccionado: {stock} bultos | Costales: {sacks}")
        except Exception:
            self.stock_info_lbl.config(text="Stock: ? | Costales: ?")

    def _reset_form(self):
        self.qty_entry.delete(0, tk.END)
        self.customer_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)
        # --- CAMBIO: Eliminada la lógica de "Otro..." ---
        # self.other_type_entry.delete(0, tk.END)
        # self.other_quality_entry.delete(0, tk.END)
        self.payment_cb.set("Efectivo")
        self.add_to_cash.set(True)
        self.manual_price.set(False)
        self._load_product_list()
        self._on_type_selected()

    def _create_sale(self):
        try:
            date = self.date_entry.get_date().strftime("%Y-m-d")
            product, quality = self._get_form_product_data()

            if not product or not quality:
                raise ValueError("Debe especificar el producto y la calidad.")

            qty_str = self.qty_entry.get().strip()
            if not qty_str: raise ValueError("Ingrese la cantidad.")
            qty = int(qty_str)

            price_str = self.unit_price_entry.get().strip()
            if not price_str: raise ValueError("Ingrese el precio unitario.")
            price = float(price_str)
            
            pay = PAY_TO_CODE[self.payment_cb.get()]
            customer = self.customer_entry.get().strip()
            notes = self.notes_entry.get().strip()
            register_cash = self.add_to_cash.get()

            self.controller.create_sale(
                date=date, product_name=product, quality=quality, quantity=qty,
                sale_unit_price=price, payment_method=pay, customer=customer,
                notes=notes, register_cash=register_cash
            )

            messagebox.showinfo("Venta", "Venta registrada correctamente.")
            self.refresh_all(load_history=True)

        except ValueError as ve:
            messagebox.showerror("Error de validación", str(ve))
        except Exception as e:
            messagebox.showerror("Error inesperado", str(e))

    def _get_filters(self):
        start = self.start_de.get_date().strftime('%Y-%m-%d')
        end = self.end_de.get_date().strftime('%Y-%m-%d')
        t = (self.f_type.get() or "").strip().lower() or None
        q = (self.f_quality.get() or "").strip().lower() or None
        return start, end, t, q

    def _load_sales(self):
        for i in self.sales_tree.get_children():
            self.sales_tree.delete(i)

        start, end, t, q = self._get_filters()
        try:
            rows, totals = self.controller.get_sales_report(start, end, t, q)

            if not rows:
                self.sales_tree.insert('', 'end', values=("— Sin ventas —", "", "", "", "", "", "", "", "", ""))
                self.totals_lbl.config(text="Totales: 0 bultos | $0.00")
                return

            for idx, r in enumerate(rows):
                pay = r.get('payment_method')
                pay_disp = CODE_TO_PAY.get(pay, '—') if pay else '—'
                self.sales_tree.insert(
                    '', 'end',
                    values=(
                        r['date'],
                        r['product_name'].capitalize(),
                        r['quality'].capitalize(),
                        int(r['quantity']),
                        f"${float(r['unit_price']):.2f}",
                        f"${float(r['total_value']):.2f}",
                        r.get('supplier_customer') or '',
                        pay_disp,
                        r.get('username') or '',
                        r.get('notes') or ''
                    ),
                    tags=('odd',) if idx % 2 else ()
                )

            self.totals_lbl.config(
                text=f"Totales: {int(totals['quantity'])} bultos | ${float(totals['amount']):.2f}"
            )
        except Exception as e:
            messagebox.showerror("Historial de ventas", str(e))

    # --- CAMBIO: Método _export_pdf implementado ---
    def _export_pdf(self):
        """Exporta el historial filtrado de Ventas a un PDF."""
        
        if not REPORTLAB_OK:
            messagebox.showerror("Error", "La librería ReportLab no está instalada.\n\nInstálala con: pip install reportlab")
            return
            
        try:
            # 1. Obtener datos y filtros
            start, end, t, q = self._get_filters()
            
            # Obtener nombres de filtros para el título
            product_filter = t.capitalize() if t else "Todos"
            quality_filter = q.capitalize() if q else "Todas"
            
            rows, totals = self.controller.get_sales_report(start, end, t, q)

            # 2. Pedir al usuario dónde guardar
            default_name = f"reporte_ventas_{start.replace('-','')}_{end.replace('-','')}.pdf"
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
                leftMargin=10*mm, rightMargin=10*mm, topMargin=15*mm, bottomMargin=20*mm
            )
            story = []
            styles = getSampleStyleSheet()

            # Título y Metadatos
            title = Paragraph("<b>Reporte de Ventas</b>", styles['Title'])
            meta_text = (
                f"Período: <b>{start}</b> a <b>{end}</b> | "
                f"Producto: <b>{product_filter}</b> | Calidad: <b>{quality_filter}</b> | "
                f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            meta = Paragraph(meta_text, styles['Normal'])
            story += [title, Spacer(1, 4*mm), meta, Spacer(1, 6*mm)]

            # 4. Preparar datos de la tabla
            headers = ["Fecha", "Producto", "Calidad", "Bultos", "Precio U.", "Total", "Cliente", "Pago", "Usuario", "Notas"]
            table_data = [headers]

            if not rows:
                table_data.append(["(Sin registros para este período)", "", "", "", "", "", "", "", "", ""])
            else:
                for r in rows:
                    pay = r.get('payment_method')
                    pay_disp = CODE_TO_PAY.get(pay, '—') if pay else '—'
                    table_data.append([
                        r['date'],
                        r['product_name'].capitalize(),
                        r['quality'].capitalize(),
                        int(r['quantity']),
                        f"${float(r['unit_price']):.2f}",
                        f"${float(r['total_value']):.2f}",
                        r.get('supplier_customer') or '',
                        pay_disp,
                        r.get('username') or '',
                        r.get('notes') or ''
                    ])

            # 5. Añadir fila de totales
            table_data.append([
                "TOTALES", "", "",
                f"{int(totals['quantity'])}", # Total Bultos
                "",
                f"${float(totals['amount']):,.2f}", # Total Monto
                "", "", "", ""
            ])

            # 6. Definir anchos de columna (en mm) - 10 columnas
            colWidths = [22*mm, 26*mm, 25*mm, 15*mm, 25*mm, 25*mm, 35*mm, 20*mm, 25*mm, 60*mm]
            tbl = Table(table_data, colWidths=colWidths, repeatRows=1)

            # 7. Aplicar estilos a la tabla
            style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),      # Encabezado
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,0), 'CENTER'),                 # Alineación encabezado
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),          # Rejilla
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.whitesmoke, colors.transparent]),
                
                ('ALIGN', (0,1), (0,-1), 'CENTER'),                 # Col Fecha
                ('ALIGN', (3,1), (3,-1), 'CENTER'),                 # Col Bultos
                ('ALIGN', (4,1), (5,-1), 'RIGHT'),                  # Cols Montos
                ('ALIGN', (7,1), (7,-1), 'CENTER'),                 # Col Pago
                ('ALIGN', (1,1), (2,-1), 'LEFT'),                   # Col Producto, Calidad
                ('ALIGN', (6,1), (6,-1), 'LEFT'),                   # Col Cliente
                ('ALIGN', (8,1), (9,-1), 'LEFT'),                   # Col Usuario, Notas
                
                ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),    # Fila de Totales
                ('BACKGROUND', (0,-1), (-1,-1), colors.lightblue),
                ('ALIGN', (3,-1), (3,-1), 'CENTER'),                # Total Bultos
                ('ALIGN', (5,-1), (5,-1), 'RIGHT'),                 # Total Monto
            ])
            tbl.setStyle(style)
            story.append(tbl)
            
            # 8. Footer (número de página)
            def footer(canvas, doc):
                canvas.saveState()
                canvas.setFont('Helvetica', 9)
                canvas.drawRightString(doc.pagesize[0] - 10*mm, 10*mm, f"Página {doc.page}")
                canvas.restoreState()

            # 9. Construir el PDF
            doc.build(story, onFirstPage=footer, onLaterPages=footer)
            messagebox.showinfo("Exportar PDF", f"PDF generado correctamente:\n{path}")

        except Exception as e:
            messagebox.showerror("Error al Exportar PDF", f"No se pudo generar el PDF:\n{e}")


    def refresh_all(self, load_history=True):
        self._load_product_list()
        self._on_type_selected()
        if load_history:
            self._load_sales()