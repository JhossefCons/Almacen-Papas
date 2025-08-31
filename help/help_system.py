"""
help/help_system.py
Sistema de ayuda simple basado en archivos Markdown.
- Carga tópicos desde la carpeta ./help como <topic>.md
- Si no existe, muestra un fallback embebido
- Incluye buscador rápido dentro de la ventana de ayuda
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

DEFAULT_TOPICS = {
    "manual": "# Manual de Usuario\n\nSeleccione un tema de ayuda desde el menú o la barra de herramientas.",
    "caja": "# Ayuda - Caja\n\nRegistre ingresos y egresos, filtre por fecha y exporte si su vista lo permite.",
    "prestamos": "# Ayuda - Préstamos\n\nCree préstamos a empleados, registre pagos y consulte saldos.",
    "inventario": "# Ayuda - Inventario\n\nGestione entradas de papa, edite existencias (solo admin) y controle costales.",
    "ventas": "# Ayuda - Ventas\n\nRegistre ventas que descuentan inventario y costales y generan ingreso en Caja.",
}

class HelpSystem:
    def __init__(self, root, help_dir="help"):
        self.root = root
        self.help_dir = help_dir
        os.makedirs(self.help_dir, exist_ok=True)

    def _read_topic(self, topic: str) -> str:
        """Lee el archivo help/<topic>.md si existe, si no usa contenido por defecto."""
        if not topic:
            topic = "manual"
        path = os.path.join(self.help_dir, f"{topic}.md")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                messagebox.showerror("Ayuda", f"No se pudo leer el archivo de ayuda:\n{e}")
        return DEFAULT_TOPICS.get(topic, DEFAULT_TOPICS["manual"])

    def show_help(self, topic: str = None):
        """Muestra la ventana de ayuda con el contenido del tópico."""
        content = self._read_topic(topic)

        win = tk.Toplevel(self.root)
        win.title(f"Ayuda - {topic or 'manual'}")
        win.geometry("780x600")
        win.transient(self.root)

        # Barra superior con búsqueda
        top = ttk.Frame(win, padding=(8, 6))
        top.pack(fill=tk.X)

        ttk.Label(top, text="Buscar:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(top, textvariable=search_var, width=28)
        search_entry.pack(side=tk.LEFT, padx=(6, 6))

        def do_search():
            query = search_var.get().strip()
            if not query:
                return
            # Buscar siguiente coincidencia desde el cursor actual
            start = text.index(tk.INSERT)
            pos = text.search(query, start, tk.END, nocase=True)
            if not pos:
                # Buscar desde el inicio
                pos = text.search(query, "1.0", tk.END, nocase=True)
                if not pos:
                    messagebox.showinfo("Búsqueda", "No se encontraron coincidencias.")
                    return
            end_pos = f"{pos}+{len(query)}c"
            text.tag_remove("sel", "1.0", tk.END)
            text.tag_add("sel", pos, end_pos)
            text.mark_set(tk.INSERT, end_pos)
            text.see(pos)

        ttk.Button(top, text="Buscar", command=do_search).pack(side=tk.LEFT)
        ttk.Separator(win, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # Área de contenido
        body = ttk.Frame(win, padding=(8, 8))
        body.pack(fill=tk.BOTH, expand=True)

        text = ScrolledText(body, wrap=tk.WORD, font=("Segoe UI", 10))
        text.pack(fill=tk.BOTH, expand=True)

        # Muy simple: mostramos markdown como texto plano.
        # (Si en el futuro quieres resaltado de títulos, podemos añadirlo).
        text.insert("1.0", content)
        text.config(state="disabled")

        # Atajos
        def _on_ctrl_f(event):
            search_entry.focus()
            search_entry.select_range(0, tk.END)
            return "break"

        win.bind("<Control-f>", _on_ctrl_f)
        search_entry.focus()


class QuickHelp:
    """
    Placeholder/Helper para ayudas contextuales.
    Puedes ampliar esto para mostrar tooltips o ayuda inline por widget.
    """
    def __init__(self, root, help_system: HelpSystem):
        self.root = root
        self.help_system = help_system

    def show_topic(self, topic: str):
        self.help_system.show_help(topic)
