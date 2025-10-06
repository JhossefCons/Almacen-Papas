"""
Vista de Ventas (Tkinter + ttk)
- Registrar venta (impacta inventario, costales y Caja)
- Historial con filtros (fecha, tipo, calidad)
- Totales y Exportar PDF
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime, timedelta

from modules.sales.controller import SalesController
from modules.inventory.controller import VALID_COMBOS

PAY_TO_CODE = {"Efectivo": "cash", "Transferencia": "transfer"}
CODE_TO_PAY = {"cash": "Efectivo", "transfer": "Transferencia"}


class SalesView:
    def __init__(self, parent, database, auth_manager, cash_controller):
        self.parent = parent
        self.db = database
        self.auth = auth_manager
        self.controller = SalesController(database, auth_manager, cash_controller)

        self._build_ui()
        self._auto_fill_price()
        self._refresh_stock_labels()
        self._load_sales()  # al abrir, ver últimos 30 días

    # ---------------------------
    # UI
    # ---------------------------
    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=8)
        container.pack(fill=tk.BOTH, expand=True)

        # Panel izquierdo: Nueva venta
        left = ttk.LabelFrame(container, text="Nueva venta", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        # Panel derecho: Historial y filtros
        right = ttk.Frame(container)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ---- Formulario de venta ----
        row = 0
        ttk.Label(left, text="Fecha:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.date_entry = DateEntry(left, date_pattern="yyyy-mm-dd")
        self.date_entry.set_date(datetime.now())
        self.date_entry.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        row += 1

        ttk.Label(left, text="Producto:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.type_cb = ttk.Combobox(left, state="readonly")
        self._load_product_options()
        self.type_cb.grid(row=row, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        self.type_cb.bind("<<ComboboxSelected>>", self._on_combo_change)
        row += 1

        ttk.Label(left, text="Calidad:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.quality_cb = ttk.Combobox(left, state="readonly")
        self._reload_quality_options("parda")
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

        for c in (0, 1):
            left.grid_columnconfigure(c, weight=1)

        # Por defecto el precio es autollenado (campo bloqueado)
        self._apply_price_state(disable_when_auto=True)

        # ---- Filtros y acciones (derecha) ----
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

        ttk.Label(filters, text="Tipo:").grid(row=0, column=4, sticky=tk.W, pady=2)
        self.f_type = ttk.Combobox(filters, state="readonly", values=("", *VALID_COMBOS.keys()), width=12)
        self.f_type.set("")
        self.f_type.grid(row=0, column=5, sticky=tk.W, padx=(4, 12))

        ttk.Label(filters, text="Calidad:").grid(row=0, column=6, sticky=tk.W, pady=2)
        self.f_quality = ttk.Combobox(filters, state="readonly", values=("",), width=14)
        self.f_quality.set("")
        self.f_quality.grid(row=0, column=7, sticky=tk.W, padx=(4, 12))

        def on_filter_type_change(_=None):
            t = (self.f_type.get() or "").strip().lower()
            if t and t in VALID_COMBOS:
                self.f_quality.config(values=("", *VALID_COMBOS[t]))
            else:
                self.f_quality.config(values=("",))
            self.f_quality.set("")

        self.f_type.bind("<<ComboboxSelected>>", on_filter_type_change)

        ttk.Button(filters, text="Aplicar", command=self._load_sales).grid(row=0, column=8, padx=(8, 4))
        ttk.Button(filters, text="Exportar PDF", command=self._export_pdf).grid(row=0, column=9, padx=(4, 0))

        for i in range(10):
            filters.grid_columnconfigure(i, weight=1)


        # ---- Tabla historial con scroll ----
        sales_frame = ttk.LabelFrame(right, text="Historial de ventas", padding=(6, 6, 6, 6))
        sales_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        sales_frame.grid_rowconfigure(0, weight=1)
        sales_frame.grid_columnconfigure(0, weight=1)

        columns = ('date', 'type', 'quality', 'qty', 'unit', 'total', 'customer', 'pay', 'user', 'notes')
        self.sales_tree = ttk.Treeview(
            sales_frame, columns=columns, show='headings', height=18, style="Sales.Treeview"
        )

        ysb = ttk.Scrollbar(sales_frame, orient=tk.VERTICAL, command=self.sales_tree.yview)
        xsb = ttk.Scrollbar(sales_frame, orient=tk.HORIZONTAL, command=self.sales_tree.xview)
        self.sales_tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        self.sales_tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        headers = {
            'date': 'Fecha', 'type': 'Producto', 'quality': 'Calidad', 'qty': 'Bultos',
            'unit': 'Precio U.', 'total': 'Total', 'customer': 'Cliente', 'pay': 'Pago',
            'user': 'Usuario', 'notes': 'Notas'
        }
        widths = {
            'date': 110, 'type': 60, 'quality': 80, 'qty': 60,
            'unit': 110, 'total': 120, 'customer': 120, 'pay': 80, 'user': 120, 'notes': 320
        }
        anchors = {
            'date': tk.CENTER, 'type': tk.W, 'quality': tk.W, 'qty': tk.CENTER,
            'unit': tk.E, 'total': tk.E, 'customer': tk.W, 'pay': tk.CENTER, 'user': tk.W, 'notes': tk.W
        }

        for c in columns:
            self.sales_tree.heading(c, text=headers[c])
            self.sales_tree.column(c, width=widths[c], anchor=anchors[c], stretch=False)

        self.sales_tree.tag_configure('odd', background="#fafafa")     # zebra

        # ---- Totales ----
        totals_box = ttk.Frame(right)
        totals_box.pack(fill=tk.X, pady=(6, 0))
        self.totals_lbl = ttk.Label(totals_box, text="Totales: —", font=('Segoe UI', 9, 'bold'))
        self.totals_lbl.pack(anchor=tk.E)

    # ---------------------------
    # Helpers (form)
    # ---------------------------
    def _load_product_options(self):
        try:
            rows = self.db.execute_query("SELECT DISTINCT potato_type FROM potato_inventory ORDER BY potato_type")
            products = [r['potato_type'] for r in rows] if rows else []
            self.type_cb["values"] = tuple(products)
            if products:
                self.type_cb.set(products[0])
        except Exception as e:
            self.type_cb["values"] = ()
            print(f"Error loading products: {e}")

    def _reload_quality_options(self, potato_type: str):
        values = VALID_COMBOS.get(potato_type.lower(), [])
        self.quality_cb["values"] = tuple(values)
        self.quality_cb.set(values[0] if values else "")

    def _on_combo_change(self, _evt=None):
        self._auto_fill_price()
        self._refresh_stock_labels()

    def _apply_price_state(self, disable_when_auto: bool):
        if disable_when_auto and not self.manual_price.get():
            self.unit_price_entry.config(state="disabled")
        else:
            self.unit_price_entry.config(state="normal")

    def _auto_fill_price(self):
        if self.manual_price.get():
            return
        t = self.type_cb.get().strip().lower()
        q = self.quality_cb.get().strip().lower()
        price = self.controller.get_last_sale_price(t, q)

        self.unit_price_entry.config(state="normal")
        self.unit_price_entry.delete(0, tk.END)
        if price is not None:
            self.unit_price_entry.insert(0, str(price))
        else:
            self.unit_price_entry.insert(0, "")
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
            t = self.type_cb.get().strip().lower()
            q = self.quality_cb.get().strip().lower()
            stock = self.controller.get_stock(t, q)
            sacks = self.controller.get_sacks()
            self._set_stock_text(f"Stock seleccionado: {stock} bultos")
            self._set_sacks_text(f"Costales disponibles: {sacks}")
        except Exception as e:
            self._set_stock_text(f"Stock seleccionado: ? ({e})")

    def _set_stock_text(self, text):
        if not hasattr(self, "stock_label"):
            self.stock_label = ttk.Label(self.parent)
        self.stock_label.config(text=text)

    def _set_sacks_text(self, text):
        if not hasattr(self, "sacks_label"):
            self.sacks_label = ttk.Label(self.parent)
        self.sacks_label.config(text=text)

    def _reset_form(self):
        self.qty_entry.delete(0, tk.END)
        self.customer_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)
        self.payment_cb.set("Efectivo")
        self.add_to_cash.set(True)
        self.manual_price.set(False)
        self._auto_fill_price()
        self._apply_price_state(disable_when_auto=True)

    # ---------------------------
    # Acciones formulario
    # ---------------------------
    def _create_sale(self):
        try:
            date = self.date_entry.get_date().strftime("%Y-%m-%d")
            t = self.type_cb.get().strip().lower()
            q = self.quality_cb.get().strip().lower()

            qty_str = self.qty_entry.get().strip()
            if not qty_str:
                raise ValueError("Ingrese la cantidad.")
            qty = int(qty_str)

            price_str = self.unit_price_entry.get().strip()
            if price_str == "":
                raise ValueError("Ingrese el precio unitario (o desmarque 'Editar precio' para autollenar).")
            price = float(price_str)

            pay = PAY_TO_CODE[self.payment_cb.get()]
            customer = self.customer_entry.get().strip()
            notes = self.notes_entry.get().strip()
            register_cash = self.add_to_cash.get()

            self.controller.create_sale(
                date=date,
                potato_type=t,
                quality=q,
                quantity=qty,
                sale_unit_price=price,
                payment_method=pay,
                customer=customer,
                notes=notes,
                register_cash=register_cash,
            )

            messagebox.showinfo("Venta", "Venta registrada correctamente.")
            self._refresh_stock_labels()
            self._reset_form()
            self._load_sales()  # refrescar historial
            try:
                self.parent.event_generate("<<SaleCreated>>", when="tail")
            except Exception:
                pass
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------------------------
    # Historial / Reporte
    # ---------------------------
    def _get_filters(self):
        start = self.start_de.get_date().strftime('%Y-%m-%d')
        end = self.end_de.get_date().strftime('%Y-%m-%d')
        t = (self.f_type.get() or "").strip().lower() or None
        q = (self.f_quality.get() or "").strip().lower() or None
        return start, end, t, q

    def _load_sales(self):
        # limpiar
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
                        r['potato_type'],
                        r['quality'],
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

    def _export_pdf(self):
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            messagebox.showerror(
                "Falta dependencia",
                "Para generar PDF necesitas instalar reportlab:\n\npip install reportlab"
            )
            return

        start, end, t, q = self._get_filters()
        try:
            data, totals = self.controller.get_sales_report(start, end, t, q)
        except Exception as e:
            messagebox.showerror("Reporte de Ventas", f"Error obteniendo datos: {e}")
            return

        if not data:
            messagebox.showwarning("Reporte de Ventas", "No hay ventas en el período seleccionado.")
            return

        default_name = f"reporte_ventas_{start.replace('-','')}_{end.replace('-','')}.pdf"
        path = filedialog.asksaveasfilename(
            title="Guardar reporte como",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF", "*.pdf")]
        )
        if not path:
            return

        try:
            doc = SimpleDocTemplate(
                path, pagesize=landscape(A4),
                leftMargin=18, rightMargin=18, topMargin=18, bottomMargin=22
            )
            styles = getSampleStyleSheet()
            title = Paragraph("<b>Reporte de Ventas</b>", styles['Title'])

            meta = Paragraph(
                f"Período: <b>{start}</b> a <b>{end}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                styles['Normal']
            )

            table_data = [["Fecha", "Tipo", "Calidad", "Bultos",
                           "Precio U.", "Total", "Cliente", "Pago", "Usuario", "Notas"]]
            for r in data:
                pay = r.get('payment_method')
                pay_disp = CODE_TO_PAY.get(pay, '—') if pay else '—'
                table_data.append([
                    r['date'],
                    r['potato_type'],
                    r['quality'],
                    str(int(r['quantity'])),
                    f"${float(r['unit_price']):,.2f}",
                    f"${float(r['total_value']):,.2f}",
                    r.get('supplier_customer') or '',
                    pay_disp,
                    r.get('username') or '',
                    r.get('notes') or ''
                ])

            table_data.append([
                "Totales", "", "", str(int(totals['quantity'])),
                "", f"${float(totals['amount']):,.2f}", "", "", "", ""
            ])

            tbl = Table(table_data, repeatRows=1)
            tbl.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                ('ALIGN', (3, 1), (3, -2), 'CENTER'),  # Bultos
                ('ALIGN', (4, 1), (5, -2), 'RIGHT'),   # Precios
                ('ALIGN', (7, 1), (8, -2), 'CENTER'),  # Pago / Usuario
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cccccc')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#fbfbfb')]),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e9')),
            ]))

            story = [title, Spacer(0, 8), meta, Spacer(0, 10), tbl]

            def _footer(canvas, doc):
                canvas.saveState()
                canvas.setFont("Helvetica", 9)
                canvas.drawRightString(doc.pagesize[0] - 18, 12, f"Página {doc.page}")
                canvas.restoreState()

            doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
            messagebox.showinfo("Reporte de Ventas", f"PDF generado correctamente:\n{path}")
        except Exception as e:
            messagebox.showerror("Reporte de Ventas", f"No se pudo generar el PDF:\n{e}")

    # públicos (para refresco general desde MainWindow)
    def refresh_all(self):
        self._load_product_options()
        self._auto_fill_price()
        self._refresh_stock_labels()
        self._load_sales()
