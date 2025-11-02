# modules/cash_register/cash_register_views.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import csv

from modules.cash_register.cash_register_controller import CashRegisterController

# Mapeos de valores internos <-> etiquetas en español
TYPE_TO_ES = {"income": "Ingreso", "expense": "Egreso"}
TYPE_FROM_ES = {v: k for k, v in TYPE_TO_ES.items()}
PAYMENT_TO_ES = {"cash": "Efectivo", "transfer": "Transferencia"}
PAYMENT_FROM_ES = {v: k for k, v in PAYMENT_TO_ES.items()}


class CashRegisterView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth_manager = auth_manager
        self.controller = CashRegisterController(database, auth_manager)

        self.setup_ui()
        self.load_transactions()

    def setup_ui(self):
        """Configurar la interfaz de usuario del módulo de caja"""
        try:
            self.parent.winfo_toplevel().title("Caja - Módulo de Movimientos")
        except Exception:
            pass

        style = ttk.Style()
        style.configure("Income.TLabel", foreground="green",font=("TkDefaultFont", 10, "bold"))
        style.configure("Expense.TLabel", foreground="red",font=("TkDefaultFont", 10, "bold"))
        style.configure("Balance.TLabel", font=("TkDefaultFont", 10, "bold"))

        main_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(main_paned, padding=10)
        main_paned.add(left_frame, weight=1)

        right_frame = ttk.Frame(main_paned, padding=10)
        main_paned.add(right_frame, weight=2)

        # --- Formulario: Nueva transacción ---
        form_frame = ttk.LabelFrame(left_frame, text="Nueva transacción", padding=10)
        form_frame.pack(fill=tk.X, pady=(0, 10))
        # (El contenido del formulario no cambia, se mantiene igual que tu versión)
        ttk.Label(form_frame, text="Fecha:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.date_entry = DateEntry(form_frame, date_pattern='yyyy-mm-dd')
        self.date_entry.set_date(datetime.now())
        self.date_entry.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        ttk.Label(form_frame, text="Tipo:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.type_var = tk.StringVar(value="Ingreso")
        type_combo = ttk.Combobox(form_frame, textvariable=self.type_var, state="readonly", width=18)
        type_combo['values'] = tuple(TYPE_TO_ES.values())
        type_combo.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        ttk.Label(form_frame, text="Descripción:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.desc_entry = ttk.Entry(form_frame)
        self.desc_entry.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        ttk.Label(form_frame, text="Monto:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.amount_entry = ttk.Entry(form_frame)
        self.amount_entry.grid(row=3, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        ttk.Label(form_frame, text="Método de pago:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.payment_var = tk.StringVar(value="Efectivo")
        payment_combo = ttk.Combobox(form_frame, textvariable=self.payment_var, state="readonly", width=18)
        payment_combo['values'] = tuple(PAYMENT_TO_ES.values())
        payment_combo.grid(row=4, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        ttk.Label(form_frame, text="Categoría:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.category_entry = ttk.Entry(form_frame)
        self.category_entry.grid(row=5, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Agregar", command=self.add_transaction).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Limpiar", command=self.clear_form).pack(side=tk.LEFT, padx=5)
        form_frame.columnconfigure(1, weight=1)

        # --- Filtros ---
        filter_frame = ttk.LabelFrame(left_frame, text="Filtros", padding=10)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        # (El contenido de los filtros no cambia, se mantiene igual que tu versión)
        ttk.Label(filter_frame, text="Desde:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.start_date = DateEntry(filter_frame, date_pattern='yyyy-mm-dd')
        self.start_date.set_date(datetime.now() - timedelta(days=30))
        self.start_date.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        ttk.Label(filter_frame, text="Hasta:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.end_date = DateEntry(filter_frame, date_pattern='yyyy-mm-dd')
        self.end_date.set_date(datetime.now())
        self.end_date.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        ttk.Label(filter_frame, text="Tipo:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.filter_type = ttk.Combobox(filter_frame, state="readonly", width=18)
        self.filter_type['values'] = ('',) + tuple(TYPE_TO_ES.values())
        self.filter_type.set('')
        self.filter_type.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        ttk.Label(filter_frame, text="Método:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.filter_payment = ttk.Combobox(filter_frame, state="readonly", width=18)
        self.filter_payment['values'] = ('',) + tuple(PAYMENT_TO_ES.values())
        self.filter_payment.set('')
        self.filter_payment.grid(row=3, column=1, sticky=tk.EW, pady=2, padx=(5, 0))
        ttk.Button(filter_frame, text="Aplicar filtros", command=self.apply_filters) \
            .grid(row=4, column=0, columnspan=2, pady=10)
        filter_frame.columnconfigure(1, weight=1)

        # --- Resumen ---
        summary_frame = ttk.LabelFrame(left_frame, text="Resumen", padding=10)
        summary_frame.pack(fill=tk.X)
        # (El contenido del resumen no cambia, se mantiene igual que tu versión)
        self.income_var = tk.StringVar(value="Ingresos: $0.00")
        self.expense_var = tk.StringVar(value="Egresos: $0.00")
        self.balance_var = tk.StringVar(value="Balance: $0.00")
        ttk.Label(summary_frame, textvariable=self.income_var, style="Income.TLabel").pack(anchor=tk.W)
        ttk.Label(summary_frame, textvariable=self.expense_var, style="Expense.TLabel").pack(anchor=tk.W)
        ttk.Label(summary_frame, textvariable=self.balance_var, style="Balance.TLabel").pack(anchor=tk.W)

        # --- Notebook: Movimientos / Gráficos ---
        tab_control = ttk.Notebook(right_frame)
        tab_control.pack(fill=tk.BOTH, expand=True)
        table_frame = ttk.Frame(tab_control)
        tab_control.add(table_frame, text="Movimientos")
        chart_frame = ttk.Frame(tab_control)
        tab_control.add(chart_frame, text="Gráficos")

        # --- Treeview ---
        columns = ('id', 'date', 'type', 'description', 'amount', 'payment', 'category', 'user')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        # (Configuración de encabezados y columnas se mantiene igual)
        headers = ['ID', 'Fecha', 'Tipo', 'Descripción', 'Monto', 'Método', 'Categoría', 'Usuario']
        for col, text in zip(columns, headers): self.tree.heading(col, text=text)
        self.tree.column('id', width=40, anchor=tk.CENTER)
        self.tree.column('date', width=90, anchor=tk.CENTER)
        self.tree.column('type', width=90, anchor=tk.CENTER)
        self.tree.column('description', width=220, anchor=tk.W)
        self.tree.column('amount', width=100, anchor=tk.E)
        self.tree.column('payment', width=110, anchor=tk.CENTER)
        self.tree.column('category', width=140, anchor=tk.W)
        self.tree.column('user', width=120, anchor=tk.W)
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.tag_configure('income', foreground='green')
        self.tree.tag_configure('expense', foreground='red')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Button(chart_frame, text="Generar gráfico mensual", command=self.show_monthly_chart).pack(pady=10)

        # *** CAMBIO: Bind doble clic llama a open_edit_dialog ***
        self.tree.bind('<Double-1>', self.on_item_double_click)

        # --- Botones de acción ---
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=(6, 0))
        # *** CAMBIO: Botón Editar llama a open_edit_dialog ***
        if self.auth_manager.has_permission('admin'):
            ttk.Button(action_frame, text="Editar", command=self.open_edit_dialog).pack(side=tk.LEFT, padx=5)
            ttk.Button(action_frame, text="Eliminar", command=self.delete_transaction).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Actualizar", command=self.load_transactions).pack(side=tk.RIGHT, padx=5)
        ttk.Button(action_frame, text="Reporte", command=self.show_report).pack(side=tk.RIGHT, padx=5)

    # --- Lógica (Métodos _insert_row, refresh_all, load_transactions, etc. se mantienen igual) ---
    def _insert_row(self, trans):
        amount = float(trans['amount'])
        tipo_es = TYPE_TO_ES.get(trans['type'], trans['type'])
        pago_es = PAYMENT_TO_ES.get(trans['payment_method'], trans['payment_method'])
        tag = 'income' if trans['type'] == 'income' else 'expense'
        self.tree.insert('', 'end', values=(
            trans['id'], trans['date'], tipo_es, trans['description'],
            f"${amount:.2f}", pago_es, trans.get('category') or '', trans.get('username') or ''
        ), tags=(tag,))

    def refresh_all(self):
        self.load_transactions()

    def load_transactions(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        transactions = self.controller.get_transactions()
        total_income = 0.0; total_expense = 0.0
        for trans in transactions:
            amount = float(trans['amount'])
            if trans['type'] == 'income': total_income += amount
            else: total_expense += amount
            self._insert_row(trans)
        self._update_summary(total_income, total_expense)

    def _update_summary(self, total_income: float, total_expense: float):
        balance = total_income - total_expense
        self.income_var.set(f"Ingresos: ${total_income:.2f}")
        self.expense_var.set(f"Egresos: ${total_expense:.2f}")
        self.balance_var.set(f"Balance: ${balance:.2f}")

    def apply_filters(self):
        start_date = self.start_date.get_date().strftime('%Y-%m-%d')
        end_date = self.end_date.get_date().strftime('%Y-%m-%d')
        type_filter_es = (self.filter_type.get() or '').strip()
        type_filter = TYPE_FROM_ES.get(type_filter_es) if type_filter_es else None
        payment_filter_es = (self.filter_payment.get() or '').strip()
        payment_filter = PAYMENT_FROM_ES.get(payment_filter_es) if payment_filter_es else None
        for item in self.tree.get_children(): self.tree.delete(item)
        transactions = self.controller.get_transactions(start_date, end_date, type_filter, payment_filter)
        total_income = 0.0; total_expense = 0.0
        for trans in transactions:
            amount = float(trans['amount'])
            if trans['type'] == 'income': total_income += amount
            else: total_expense += amount
            self._insert_row(trans)
        self._update_summary(total_income, total_expense)

    def add_transaction(self):
        try:
            date = self.date_entry.get_date().strftime('%Y-%m-%d')
            type_val_internal = TYPE_FROM_ES.get(self.type_var.get(), 'income')
            description = self.desc_entry.get().strip()
            amount_text = self.amount_entry.get().strip()
            payment_method_internal = PAYMENT_FROM_ES.get(self.payment_var.get(), 'cash')
            category = (self.category_entry.get() or '').strip()
            if not description: raise ValueError("La descripción es obligatoria")
            try: amount = float(amount_text)
            except ValueError: raise ValueError("El monto debe ser un número válido")
            if amount <= 0: raise ValueError("El monto debe ser mayor a cero")
            self.controller.add_transaction(date, type_val_internal, description, amount, payment_method_internal, category)
            messagebox.showinfo("Éxito", "Transacción agregada correctamente")
            self.clear_form(); self.load_transactions()
        except ValueError as ve: messagebox.showerror("Error de Validación", str(ve))
        except Exception as e: messagebox.showerror("Error", f"No se pudo agregar la transacción: {str(e)}")

    def clear_form(self):
        self.date_entry.set_date(datetime.now())
        self.type_var.set('Ingreso')
        self.desc_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)
        self.payment_var.set('Efectivo')
        self.category_entry.delete(0, tk.END)

    def on_item_double_click(self, event):
        """Manejar doble clic en un item del treeview"""
        if self.auth_manager.has_permission('admin'):
            self.open_edit_dialog()

    # *** NUEVO: Método para abrir el diálogo de edición ***
    def open_edit_dialog(self):
        """Abre la ventana para editar la transacción seleccionada."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione una transacción para editar")
            return

        item = self.tree.item(selection[0])
        trans_id = item['values'][0]

        try:
            # Obtener datos completos de la transacción desde el controlador
            transaction_data = self.controller.get_transaction_by_id(trans_id)
            if not transaction_data:
                messagebox.showerror("Error", f"No se encontró la transacción con ID {trans_id}")
                return

            # Crear y mostrar el diálogo de edición
            EditTransactionDialog(self.parent, self.controller, transaction_data, self.load_transactions)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el editor: {str(e)}")

    def delete_transaction(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione una transacción para eliminar")
            return
        item = self.tree.item(selection[0])
        trans_id = item['values'][0]; desc = item['values'][3]
        if messagebox.askyesno("Confirmar", f"¿Está seguro de eliminar la transacción '{desc}'?"):
            try:
                self.controller.delete_transaction(trans_id)
                messagebox.showinfo("Éxito", "Transacción eliminada correctamente")
                self.load_transactions()
            except Exception as e: messagebox.showerror("Error", f"No se pudo eliminar la transacción: {str(e)}")

    # (Métodos show_report y show_monthly_chart se mantienen igual)
    def show_report(self):
        report_win = tk.Toplevel(self.parent)
        report_win.title("Reporte de caja")
        report_win.geometry("800x520")
        top = ttk.Frame(report_win, padding=10); top.pack(fill=tk.X)
        ttk.Label(top, text="Desde:").grid(row=0, column=0, sticky=tk.W)
        d1 = DateEntry(top, date_pattern='yyyy-mm-dd'); d1.set_date(self.start_date.get_date()); d1.grid(row=0, column=1, padx=5)
        ttk.Label(top, text="Hasta:").grid(row=0, column=2, sticky=tk.W)
        d2 = DateEntry(top, date_pattern='yyyy-mm-dd'); d2.set_date(self.end_date.get_date()); d2.grid(row=0, column=3, padx=5)
        ttk.Label(top, text="Agrupar por:").grid(row=0, column=4, sticky=tk.W)
        group_var = tk.StringVar(value="Día"); group_combo = ttk.Combobox(top, textvariable=group_var, state="readonly", width=12); group_combo['values'] = ("Día", "Semana", "Mes"); group_combo.grid(row=0, column=5, padx=5)
        btns = ttk.Frame(top); btns.grid(row=0, column=6, padx=10)
        ttk.Button(btns, text="Generar", command=lambda: generate()).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Exportar CSV", command=lambda: export_csv()).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Exportar PDF", command=lambda: export_pdf()).pack(side=tk.LEFT, padx=2)
        table_frame = ttk.Frame(report_win, padding=10); table_frame.pack(fill=tk.BOTH, expand=True)
        cols = ("fecha", "ingresos", "egresos", "balance"); rep_tree = ttk.Treeview(table_frame, columns=cols, show='headings')
        for c, t in zip(cols, ["Fecha", "Ingresos", "Egresos", "Balance"]): rep_tree.heading(c, text=t)
        rep_tree.column("fecha", width=120, anchor=tk.CENTER); rep_tree.column("ingresos", width=120, anchor=tk.E); rep_tree.column("egresos", width=120, anchor=tk.E); rep_tree.column("balance", width=120, anchor=tk.E)
        rep_tree.tag_configure('pos', foreground='#0b6b0b', background='#e9fbe9'); rep_tree.tag_configure('neg', foreground='#8b0000', background='#fdeaea')
        rep_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=rep_tree.yview); rep_tree.configure(yscrollcommand=rep_scroll.set); rep_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); rep_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        footer = ttk.Frame(report_win, padding=10); footer.pack(fill=tk.X); sum_ing = tk.StringVar(value="Ingresos: $0.00"); sum_egr = tk.StringVar(value="Egresos: $0.00"); sum_bal = tk.StringVar(value="Balance: $0.00")
        ttk.Label(footer, textvariable=sum_ing, style="Income.TLabel").pack(side=tk.LEFT, padx=10); ttk.Label(footer, textvariable=sum_egr, style="Expense.TLabel").pack(side=tk.LEFT, padx=10); ttk.Label(footer, textvariable=sum_bal, style="Balance.TLabel").pack(side=tk.LEFT, padx=10)
        def generate():
            for i in rep_tree.get_children(): rep_tree.delete(i)
            start = d1.get_date().strftime('%Y-%m-%d'); end = d2.get_date().strftime('%Y-%m-%d'); gb_map = {"Día": "day", "Semana": "week", "Mes": "month"}; group_by = gb_map.get(group_var.get(), "day")
            try: data = self.controller.get_cash_flow_report(start, end, group_by)
            except Exception as e: messagebox.showerror("Error", f"No se pudo generar el reporte: {e}"); return
            tot_inc = 0.0; tot_exp = 0.0
            for row in data: f_inc = float(row['income']); f_exp = float(row['expense']); bal = float(row['balance']); tot_inc += f_inc; tot_exp += f_exp; tag = 'pos' if bal >= 0 else 'neg'; rep_tree.insert('', 'end', values=(row['date'], f"${f_inc:,.2f}", f"${f_exp:,.2f}", f"${bal:,.2f}"), tags=(tag,))
            sum_ing.set(f"Ingresos: ${tot_inc:,.2f}"); sum_egr.set(f"Egresos: ${tot_exp:,.2f}"); sum_bal.set(f"Balance: ${(tot_inc - tot_exp):,.2f}")
        def export_csv():
            if not rep_tree.get_children(): messagebox.showinfo("Información", "Primero genere el reporte para exportar."); return
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", ".csv")], title="Guardar reporte como");
            if not path: return
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f: writer = csv.writer(f); writer.writerow(["Fecha", "Ingresos", "Egresos", "Balance"]);
                for iid in rep_tree.get_children(): writer.writerow(rep_tree.item(iid)['values'])
                messagebox.showinfo("Éxito", "Reporte exportado correctamente")
            except Exception as e: messagebox.showerror("Error", f"No se pudo exportar el reporte: {e}")
        def export_pdf():
            if not rep_tree.get_children(): messagebox.showinfo("Información", "Primero genere el reporte para exportar."); return
            start_fmt = d1.get_date().strftime('%Y%m%d'); end_fmt = d2.get_date().strftime('%Y%m%d'); default_name = f"reporte_caja_{start_fmt}_{end_fmt}.pdf"
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", ".pdf")], title="Guardar reporte como", initialfile=default_name)
            if not path: return
            try:
                doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
                story = []; styles = getSampleStyleSheet(); title = Paragraph("<b>Reporte de Caja</b>", styles['Title']); periodo = Paragraph(f"Período: {d1.get_date().strftime('%Y-%m-%d')} a {d2.get_date().strftime('%Y-%m-%d')} | Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal'])
                story += [title, Spacer(1, 4*mm), periodo, Spacer(1, 6*mm)]; headers = ["Fecha", "Ingresos", "Egresos", "Balance"]; data = [headers]; tot_inc = 0.0; tot_exp = 0.0;
                def to_float(txt): return float(str(txt).replace('$', '').replace(',', ''))
                for iid in rep_tree.get_children(): fecha, inc_txt, eg_txt, bal_txt = rep_tree.item(iid)['values']; tot_inc += to_float(inc_txt); tot_exp += to_float(eg_txt); data.append([fecha, inc_txt, eg_txt, bal_txt])
                data.append(["Totales", f"${tot_inc:,.2f}", f"${tot_exp:,.2f}", f"${(tot_inc - tot_exp):,.2f}"]); table = Table(data, repeatRows=1)
                ts = TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('TEXTCOLOR', (0,0), (-1,0), colors.black), ('ALIGN', (1,1), (-1,-1), 'RIGHT'), ('ALIGN', (0,0), (-1,0), 'CENTER'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 10), ('GRID', (0,0), (-1,-1), 0.25, colors.grey), ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.whitespoke, colors.transparent]), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold')])
                if len(data) > 1: ts.add('TEXTCOLOR', (1, 1), (1, -1), colors.HexColor('#0b6b0b')); ts.add('TEXTCOLOR', (2, 1), (2, -1), colors.HexColor('#8b0000')); ts.add('TEXTCOLOR', (3, 1), (3, -1), colors.black)
                ts.add('BACKGROUND', (0, len(data)-1), (-1, len(data)-1), colors.lightgrey); table.setStyle(ts); story.append(table); story.append(Spacer(1, 6*mm)); story.append(Paragraph(sum_ing.get(), styles['Normal'])); story.append(Paragraph(sum_egr.get(), styles['Normal'])); story.append(Paragraph(sum_bal.get(), styles['Normal']))
                doc.build(story); messagebox.showinfo("Éxito", "PDF exportado correctamente")
            except Exception as e: messagebox.showerror("Error", f"No se pudo exportar el PDF: {e}")
        generate()

    def show_monthly_chart(self):
        try:
            monthly_data = self.controller.get_monthly_summary()
            if not monthly_data: messagebox.showinfo("Información", "No hay datos disponibles para generar el gráfico"); return
            chart_window = tk.Toplevel(self.parent); chart_window.title("Gráfico mensual"); chart_window.geometry("800x600")
            chart_frame = ttk.Frame(chart_window); chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            try: import matplotlib.pyplot as plt; from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            except ImportError: messagebox.showerror("Error", "Para ver los gráficos necesita instalar matplotlib:\n\npip install matplotlib"); chart_window.destroy(); return
            months = [item['month'] for item in monthly_data]; incomes = [float(item['income']) for item in monthly_data]; expenses = [float(item['expense']) for item in monthly_data]; balances = [inc - exp for inc, exp in zip(incomes, expenses)]
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
            x = range(len(months)); width = 0.4; ax1.bar([i - width/2 for i in x], incomes, width, label='Ingresos'); ax1.bar([i + width/2 for i in x], expenses, width, label='Egresos'); ax1.set_xlabel('Mes'); ax1.set_ylabel('Monto ($)'); ax1.set_title('Ingresos vs Egresos por mes'); ax1.set_xticks(list(x)); ax1.set_xticklabels(months, rotation=45, ha='right'); ax1.legend(); ax1.grid(True, alpha=0.3)
            ax2.plot(months, balances, marker='o', linewidth=2); ax2.set_xlabel('Mes'); ax2.set_ylabel('Balance ($)'); ax2.set_title('Balance mensual'); ax2.grid(True, alpha=0.3); ax2.tick_params(axis='x', rotation=45); plt.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=chart_frame); canvas.draw(); canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True); ttk.Button(chart_frame, text="Cerrar", command=chart_window.destroy).pack(pady=10)
        except Exception as e: messagebox.showerror("Error", f"Error al generar el gráfico: {str(e)}")


# *** NUEVA CLASE: Diálogo para Editar Transacción ***
class EditTransactionDialog:
    def __init__(self, parent, controller, transaction_data, refresh_callback):
        self.controller = controller
        self.data = transaction_data
        self.refresh_callback = refresh_callback

        self.top = tk.Toplevel(parent)
        self.top.title(f"Editar Transacción ID: {self.data['id']}")
        self.top.geometry("400x320")
        self.top.transient(parent)
        self.top.grab_set()

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        main_frame = ttk.Frame(self.top, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Fecha:").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.date_entry = DateEntry(main_frame, date_pattern='yyyy-mm-dd', width=15)
        self.date_entry.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main_frame, text="Tipo:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.type_var = tk.StringVar()
        type_combo = ttk.Combobox(main_frame, textvariable=self.type_var, state="readonly", width=18)
        type_combo['values'] = tuple(TYPE_TO_ES.values())
        type_combo.grid(row=1, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main_frame, text="Descripción:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.desc_entry = ttk.Entry(main_frame)
        self.desc_entry.grid(row=2, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main_frame, text="Monto:").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.amount_entry = ttk.Entry(main_frame)
        self.amount_entry.grid(row=3, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main_frame, text="Método de pago:").grid(row=4, column=0, sticky=tk.W, pady=4)
        self.payment_var = tk.StringVar()
        payment_combo = ttk.Combobox(main_frame, textvariable=self.payment_var, state="readonly", width=18)
        payment_combo['values'] = tuple(PAYMENT_TO_ES.values())
        payment_combo.grid(row=4, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        ttk.Label(main_frame, text="Categoría:").grid(row=5, column=0, sticky=tk.W, pady=4)
        self.category_entry = ttk.Entry(main_frame)
        self.category_entry.grid(row=5, column=1, sticky=tk.EW, pady=4, padx=(5, 0))

        footer = ttk.Frame(main_frame)
        footer.grid(row=6, column=0, columnspan=2, pady=(15,0))

        self.save_btn = ttk.Button(footer, text="Guardar Cambios", command=self._save_changes)
        self.save_btn.pack(side=tk.RIGHT, padx=5)
        self.cancel_btn = ttk.Button(footer, text="Cancelar", command=self.top.destroy)
        self.cancel_btn.pack(side=tk.RIGHT)

        main_frame.columnconfigure(1, weight=1)

    def _load_data(self):
        """Carga los datos de la transacción en los campos del diálogo."""
        try:
            date_obj = datetime.strptime(self.data['date'], '%Y-%m-%d')
            self.date_entry.set_date(date_obj)
        except ValueError:
            self.date_entry.set_date(datetime.now()) # Fallback

        self.type_var.set(TYPE_TO_ES.get(self.data['type'], 'Ingreso'))
        self.desc_entry.insert(0, self.data['description'])
        self.amount_entry.insert(0, str(self.data['amount']))
        self.payment_var.set(PAYMENT_TO_ES.get(self.data['payment_method'], 'Efectivo'))
        self.category_entry.insert(0, self.data.get('category') or '')

    def _save_changes(self):
        """Intenta guardar los cambios realizados en la transacción."""
        try:
            date = self.date_entry.get_date().strftime('%Y-%m-%d')
            type_val_internal = TYPE_FROM_ES.get(self.type_var.get(), 'income')
            description = self.desc_entry.get().strip()
            amount_text = self.amount_entry.get().strip()
            payment_method_internal = PAYMENT_FROM_ES.get(self.payment_var.get(), 'cash')
            category = (self.category_entry.get() or '').strip()

            # Validaciones (igual que al agregar)
            if not description: raise ValueError("La descripción es obligatoria")
            try: amount = float(amount_text)
            except ValueError: raise ValueError("El monto debe ser un número válido")
            if amount <= 0: raise ValueError("El monto debe ser mayor a cero")

            # Llamar al controlador para actualizar
            self.controller.update_transaction(
                self.data['id'], date, type_val_internal, description, amount, payment_method_internal, category
            )

            messagebox.showinfo("Éxito", "Transacción actualizada correctamente.", parent=self.top)
            self.refresh_callback() # Llama a load_transactions de la vista principal
            self.top.destroy()

        except ValueError as ve:
            messagebox.showerror("Error de Validación", str(ve), parent=self.top)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo actualizar la transacción: {str(e)}", parent=self.top)