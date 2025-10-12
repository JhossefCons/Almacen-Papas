# modules/employees/views.py
"""
Vista de Administración de Empleados
- Lista, crear, editar (salario/estado), activar/desactivar.
- Solo admin puede modificar.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from modules.employees.employees_controller import EmployeesController


class EmployeesView:
    def __init__(self, parent, database, auth_manager):
        self.parent = parent
        self.db = database
        self.auth = auth_manager
        self.controller = EmployeesController(database, auth_manager)

        self._build_ui()
        self.load_employees()
        # Escuchar el evento personalizado para refrescarse automáticamente
        self.parent.winfo_toplevel().bind("<<EmployeeChanged>>", lambda e: self.load_employees())

    def _build_ui(self):
        container = ttk.Frame(self.parent, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        # Barra de acciones
        actions = ttk.Frame(container)
        actions.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(actions, text="Nuevo", command=self._new_employee_dialog,
                state=("normal" if self.auth.has_permission("admin") else "disabled")
            ).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Editar", command=self._edit_employee_dialog,
                   state=("normal" if self.auth.has_permission("admin") else "disabled")).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Activar", command=lambda: self._toggle(True),
                   state=("normal" if self.auth.has_permission("admin") else "disabled")).pack(side=tk.LEFT, padx=4)
        ttk.Button(actions, text="Desactivar", command=lambda: self._toggle(False),
                   state=("normal" if self.auth.has_permission("admin") else "disabled")).pack(side=tk.LEFT, padx=4)

        ttk.Button(actions, text="Actualizar", command=self.load_employees).pack(side=tk.RIGHT, padx=4)

        # Tabla
        columns = ("id", "first_name", "last_name", "salary", "is_active", "created_at")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", height=18)
        headers = {
            "id":"ID", "first_name":"Nombre", "last_name":"Apellido", "salary":"Salario",
            "is_active":"Estado", "created_at":"Creado"
        }
        widths = {"id":50, "first_name":140, "last_name":160, "salary":100, "is_active":80, "created_at":140}
        for c in columns:
            self.tree.heading(c, text=headers[c])
            anchor = tk.CENTER if c in ("id","salary","is_active") else tk.W
            self.tree.column(c, width=widths[c], anchor=anchor)

        ysb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure("inactive", foreground="gray")
        self.tree.bind("<Double-1>", lambda e: self._edit_employee_dialog())

    # públicos
    def refresh_all(self):
        self.load_employees()

    def load_employees(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = self.controller.list_employees(include_inactive=True)
        for r in rows:
            tags = ("inactive",) if not r["is_active"] else ()
            self.tree.insert("", tk.END, values=(
                r["id"], r["first_name"], r["last_name"], f"{float(r['salary']):.2f}",
                "Activo" if r["is_active"] else "Inactivo", (r["created_at"] or "")[:19]
            ), tags=tags)

    def _sel_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(self.tree.item(sel[0], "values")[0])

    def _new_employee_dialog(self):
        win = tk.Toplevel(self.parent); win.title("Nuevo empleado"); win.geometry("360x220"); win.transient(self.parent); win.grab_set()
        frm = ttk.Frame(win, padding=10); frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Nombre:").grid(row=0, column=0, sticky=tk.W, pady=4)
        e_first = ttk.Entry(frm); e_first.grid(row=0, column=1, sticky=tk.EW, pady=4)

        ttk.Label(frm, text="Apellido:").grid(row=1, column=0, sticky=tk.W, pady=4)
        e_last = ttk.Entry(frm); e_last.grid(row=1, column=1, sticky=tk.EW, pady=4)

        ttk.Label(frm, text="Salario:").grid(row=2, column=0, sticky=tk.W, pady=4)
        e_sal = ttk.Entry(frm); e_sal.grid(row=2, column=1, sticky=tk.EW, pady=4)

        def save():
            try:
                self.controller.add_employee(e_first.get().strip(), e_last.get().strip(), float((e_sal.get() or "0").strip()))
                messagebox.showinfo("Empleados", "Empleado creado.")
                # Notificar a otros módulos que un empleado ha cambiado
                self.parent.winfo_toplevel().event_generate("<<EmployeeChanged>>")
                win.destroy(); self.load_employees()
            except ValueError:
                messagebox.showerror("Error", "Salario inválido")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        btns = ttk.Frame(frm); btns.grid(row=3, column=0, columnspan=2, pady=8)
        ttk.Button(btns, text="Guardar", command=save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancelar", command=win.destroy).pack(side=tk.LEFT, padx=6)
        frm.columnconfigure(1, weight=1)

    def _edit_employee_dialog(self):
        emp_id = self._sel_id()
        if not emp_id:
            messagebox.showwarning("Empleados", "Seleccione un empleado")
            return
        if not self.auth.has_permission("admin"):
            messagebox.showerror("Permiso denegado", "Solo administrador puede editar")
            return
        emp = self.controller.get_employee(emp_id)
        if not emp:
            messagebox.showerror("Error", "Empleado no encontrado")
            return

        win = tk.Toplevel(self.parent); win.title("Editar empleado"); win.geometry("380x240"); win.transient(self.parent); win.grab_set()
        frm = ttk.Frame(win, padding=10); frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Nombre:").grid(row=0, column=0, sticky=tk.W, pady=4)
        e_first = ttk.Entry(frm); e_first.insert(0, emp["first_name"]); e_first.grid(row=0, column=1, sticky=tk.EW, pady=4)

        ttk.Label(frm, text="Apellido:").grid(row=1, column=0, sticky=tk.W, pady=4)
        e_last = ttk.Entry(frm); e_last.insert(0, emp["last_name"]); e_last.grid(row=1, column=1, sticky=tk.EW, pady=4)

        ttk.Label(frm, text="Salario:").grid(row=2, column=0, sticky=tk.W, pady=4)
        e_sal = ttk.Entry(frm); e_sal.insert(0, f"{float(emp['salary']):.2f}"); e_sal.grid(row=2, column=1, sticky=tk.EW, pady=4)

        is_act = tk.BooleanVar(value=bool(emp["is_active"]))
        ttk.Checkbutton(frm, text="Activo", variable=is_act).grid(row=3, column=1, sticky=tk.W, pady=4)

        def save():
            try:
                self.controller.update_employee(emp_id, e_first.get().strip(), e_last.get().strip(),
                                                float((e_sal.get() or "0").strip()), is_act.get())
                # Notificar a otros módulos que un empleado ha cambiado
                self.parent.winfo_toplevel().event_generate("<<EmployeeChanged>>")
                messagebox.showinfo("Empleados", "Empleado actualizado.")
                win.destroy(); self.load_employees()
            except ValueError:
                messagebox.showerror("Error", "Salario inválido")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        btns = ttk.Frame(frm); btns.grid(row=4, column=0, columnspan=2, pady=8)
        ttk.Button(btns, text="Guardar", command=save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancelar", command=win.destroy).pack(side=tk.LEFT, padx=6)
        frm.columnconfigure(1, weight=1)

    def _toggle(self, active: bool):
        emp_id = self._sel_id()
        if not emp_id:
            messagebox.showwarning("Empleados", "Seleccione un empleado")
            return
        try:
            self.controller.toggle_active(emp_id, active)
            # Notificar a otros módulos que un empleado ha cambiado
            self.parent.winfo_toplevel().event_generate("<<EmployeeChanged>>")
            self.load_employees()
        except Exception as e:
            messagebox.showerror("Error", str(e))
