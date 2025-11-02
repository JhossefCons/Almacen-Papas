# utils/scrollframe.py
import tkinter as tk
from tkinter import ttk

class ScrollFrame(ttk.Frame):
    """
    Contenedor con Canvas + Scrollbars que expone un frame `body`
    donde puedes empaquetar (pack/grid/place) el contenido de cada módulo.
    Soporta scroll vertical y horizontal + rueda del mouse (Win/Mac/Linux).
    """
    def __init__(self, parent, fit_width=True, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.fit_width = bool(fit_width)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)

        self.canvas.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.body = ttk.Frame(self.canvas)
        self._win_id = self.canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_body_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if self.fit_width:
            self.canvas.itemconfigure(self._win_id, width=self.canvas.winfo_width())

    def _on_canvas_configure(self, event):
        if self.fit_width:
            self.canvas.itemconfigure(self._win_id, width=event.width)
            
    def _on_enter(self, event):
        """Vincular eventos de rueda de mouse cuando el mouse entra al frame."""
        self._bind_mousewheel(self)

    def _on_leave(self, event):
        """Desvincular eventos de rueda de mouse cuando el mouse sale del frame."""
        self._unbind_mousewheel(self)

    def _unbind_mousewheel(self, widget):
        """Desvincula todos los eventos de la rueda del mouse."""
        widget.unbind("<MouseWheel>")
        widget.unbind("<Shift-MouseWheel>")
        widget.unbind("<Button-4>")
        widget.unbind("<Button-5>")
        widget.unbind("<Shift-Button-4>")
        widget.unbind("<Shift-Button-5>")

    # --- soporte rueda del mouse (Win/Mac/Linux) ---
    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel_windows_mac, add="+")
        widget.bind("<Shift-MouseWheel>", self._on_shift_mousewheel_windows_mac, add="+")
        widget.bind("<Button-4>", self._on_mousewheel_linux_up, add="+")
        widget.bind("<Button-5>", self._on_mousewheel_linux_down, add="+")
        widget.bind("<Shift-Button-4>", self._on_shift_mousewheel_linux_up, add="+")
        widget.bind("<Shift-Button-5>", self._on_shift_mousewheel_linux_down, add="+")

    def _on_mousewheel_windows_mac(self, event):
        # Vertical
        delta = int(-1*(event.delta/120))
        self.canvas.yview_scroll(delta, "units")

    def _on_shift_mousewheel_windows_mac(self, event):
        # Horizontal con Shift
        delta = int(-1*(event.delta/120))
        self.canvas.xview_scroll(delta, "units")

    def _on_mousewheel_linux_up(self, event):
        self.canvas.yview_scroll(-1, "units")

    def _on_mousewheel_linux_down(self, event):
        self.canvas.yview_scroll(1, "units")

    def _on_shift_mousewheel_linux_up(self, event):
        self.canvas.xview_scroll(-1, "units")

    def _on_shift_mousewheel_linux_down(self, event):
        self.canvas.xview_scroll(1, "units")

    # helpers públicos
    def scroll_to_top(self):
        self.canvas.yview_moveto(0)

    def scroll_to_left(self):
        self.canvas.xview_moveto(0)
