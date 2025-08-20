"""
Sistema de ayuda y documentación para PapaSoft
"""
import tkinter as tk
from tkinter import ttk
import webbrowser
import os

class HelpSystem:
    def __init__(self, parent):
        self.parent = parent
    
    def show_help(self, topic=None):
        """Mostrar ayuda general o específica por tema"""
        help_window = tk.Toplevel(self.parent)
        help_window.title("Ayuda de PapaSoft")
        help_window.geometry("800x600")
        help_window.transient(self.parent)
        
        # Notebook para diferentes secciones de ayuda
        notebook = ttk.Notebook(help_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Pestaña de contenido general
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text="General")
        
        # Pestaña específica según el tema
        if topic:
            topic_frame = ttk.Frame(notebook, padding=10)
            notebook.add(topic_frame, text=topic.capitalize())
            self._show_topic_help(topic_frame, topic)
        
        # Pestaña de manual de usuario
        manual_frame = ttk.Frame(notebook, padding=10)
        notebook.add(manual_frame, text="Manual de Usuario")
        self._show_manual(manual_frame)
        
        # Pestaña de soporte
        support_frame = ttk.Frame(notebook, padding=10)
        notebook.add(support_frame, text="Soporte")
        self._show_support(support_frame)
        
        # Seleccionar la pestaña apropiada
        if topic:
            notebook.select(1)  # Seleccionar pestaña de tema
        else:
            notebook.select(0)  # Seleccionar pestaña general
    
    def _show_general_help(self, parent):
        """Mostrar ayuda general"""
        content = """
        <h1>Bienvenido a PapaSoft</h1>
        <p>PapaSoft es un sistema integral de gestión para negocios de papa que incluye:</p>
        <ul>
        <li><b>Módulo de Caja:</b> Control de ingresos, egresos y balances</li>
        <li><b>Módulo de Préstamos:</b> Gestión de préstamos a empleados</li>
        <li><b>Módulo de Inventario:</b> Control de stock de papa por tipo y calidad</li>
        </ul>
        
        <h2>Accesos Rápidos</h2>
        <p>• Use las pestañas para navegar entre módulos</p>
        <p>• Los administradores tienen acceso a funciones adicionales</p>
        <p>• Use el menú Archivo para cerrar sesión o salir</p>
        """
        
        self._show_html_content(parent, content)
    
    def _show_topic_help(self, parent, topic):
        """Mostrar ayuda específica por tema"""
        help_content = {
            'caja': """
            <h1>Módulo de Caja</h1>
            <h2>Registrar Transacciones</h2>
            <p>• Ingrese la fecha, tipo (ingreso/egreso), descripción, monto y método de pago</p>
            <p>• Use categorías para organizar sus transacciones</p>
            
            <h2>Filtros y Reportes</h2>
            <p>• Filtre por fecha, tipo o método de pago</p>
            <p>• Genere reportes de flujo de caja</p>
            <p>• Realice cierres de caja diarios</p>
            """,
            
            'prestamos': """
            <h1>Módulo de Préstamos</h1>
            <h2>Gestión de Préstamos</h2>
            <p>• Registre préstamos con empleado, monto, fechas y tasa de interés</p>
            <p>• Lleve control de pagos realizados</p>
            
            <h2>Alertas y Recordatorios</h2>
            <p>• El sistema alerta sobre préstamos vencidos</p>
            <p>• Vea el historial completo de pagos</p>
            """,
            
            'inventario': """
            <h1>Módulo de Inventario</h1>
            <h2>Tipos y Calidades</h2>
            <p>• Papa Parda: Primera, Segunda, Tercera</p>
            <p>• Papa Amarilla: Primera, Tercera</p>
            <p>• Papa Colorada: Primera, Segunda, Tercera</p>
            
            <h2>Control de Stock</h2>
            <p>• Registre entradas y salidas de inventario</p>
            <p>• El sistema alerta cuando el stock está bajo</p>
            <p>• Genere reportes de movimientos y costos</p>
            """
        }
        
        content = help_content.get(topic, "<p>Ayuda no disponible para este tema.</p>")
        self._show_html_content(parent, content)
    
    def _show_manual(self, parent):
        """Mostrar manual de usuario"""
        content = """
        <h1>Manual de Usuario PapaSoft</h1>
        
        <h2>1. Instalación y Configuración</h2>
        <p>• Ejecute el instalador y siga las instrucciones</p>
        <p>• La primera vez se crea un usuario admin con contraseña "admin123"</p>
        
        <h2>2. Gestión de Usuarios</h2>
        <p>• Solo administradores pueden crear y gestionar usuarios</p>
        <p>• Asigne roles según los permisos necesarios</p>
        
        <h2>3. Módulos Principales</h2>
        <h3>3.1. Módulo de Caja</h3>
        <p>• Registre todas las transacciones monetarias</p>
        <p>• Realice cierres diarios para mantener control</p>
        
        <h3>3.2. Módulo de Préstamos</h3>
        <p>• Lleve control de préstamos a empleados</p>
        <p>• Programe fechas de vencimiento y tasas de interés</p>
        
        <h3>3.3. Módulo de Inventario</h3>
        <p>• Controle el stock de papa por tipo y calidad</p>
        <p>• Registre entradas (compras) y salidas (ventas)</p>
        
        <h2>4. Reportes y Gráficos</h2>
        <p>• Genere reportes personalizados por fecha</p>
        <p>• Visualice datos con gráficos interactivos</p>
        
        <h2>5. Backup y Seguridad</h2>
        <p>• Realice backups regularmente desde el menú Administración</p>
        <p>• Mantenga sus credenciales seguras</p>
        """
        
        self._show_html_content(parent, content)
    
    def _show_support(self, parent):
        """Mostrar información de soporte"""
        content = """
        <h1>Soporte Técnico</h1>
        
        <h2>Contacto</h2>
        <p><b>Email:</b> soporte@papasoft.com</p>
        <p><b>Teléfono:</b> +1-800-PAPASOFT</p>
        <p><b>Horario:</b> Lunes a Viernes, 8:00 AM - 6:00 PM</p>
        
        <h2>Recursos Adicionales</h2>
        <p>• <a href="https://www.papasoft.com/faq">Preguntas Frecuentes</a></p>
        <p>• <a href="https://www.papasoft.com/tutoriales">Tutoriales en Video</a></p>
        <p>• <a href="https://www.papasoft.com/foro">Foro de la Comunidad</a></p>
        
        <h2>Reportar Problemas</h2>
        <p>Si encuentra un error o tiene una sugerencia:</p>
        <p>1. Describa el problema detalladamente</p>
        <p>2. Incluye capturas de pantalla si es posible</p>
        <p>3. Especifique la versión de PapaSoft que usa</p>
        """
        
        text_widget = tk.Text(parent, wrap=tk.WORD, font=('Arial', 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Configurar tags para formato básico
        text_widget.tag_configure('h1', font=('Arial', 16, 'bold'), foreground='darkblue')
        text_widget.tag_configure('h2', font=('Arial', 14, 'bold'), foreground='darkblue')
        text_widget.tag_configure('bold', font=('Arial', 10, 'bold'))
        
        # Insertar contenido con formato básico
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('<h1>'):
                text = line.replace('<h1>', '').replace('</h1>', '')
                text_widget.insert(tk.END, text + '\n\n', 'h1')
            elif line.startswith('<h2>'):
                text = line.replace('<h2>', '').replace('</h2>', '')
                text_widget.insert(tk.END, text + '\n', 'h2')
            elif line.startswith('<p><b>'):
                text = line.replace('<p><b>', '').replace('</b></p>', '')
                text_widget.insert(tk.END, text + '\n', 'bold')
            elif line.startswith('<p>'):
                text = line.replace('<p>', '').replace('</p>', '')
                text_widget.insert(tk.END, text + '\n\n')
            elif line.startswith('• <a href="'):
                # Manejar enlaces
                parts = line.split('">')
                if len(parts) >= 2:
                    url = parts[0].replace('• <a href="', '')
                    link_text = parts[1].replace('</a>', '')
                    
                    text_widget.insert(tk.END, '• ', 'bold')
                    text_widget.insert(tk.END, link_text + '\n')
                    # Podríamos hacer los enlaces clickeables con más trabajo
            else:
                text_widget.insert(tk.END, line + '\n')
        
        text_widget.config(state=tk.DISABLED)
    
    def _show_html_content(self, parent, html_content):
        """Mostrar contenido HTML básico (simplificado)"""
        text_widget = tk.Text(parent, wrap=tk.WORD, font=('Arial', 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Configurar tags para formato básico
        text_widget.tag_configure('h1', font=('Arial', 16, 'bold'), foreground='darkblue')
        text_widget.tag_configure('h2', font=('Arial', 14, 'bold'), foreground='darkblue')
        text_widget.tag_configure('bold', font=('Arial', 10, 'bold'))
        
        # Procesar contenido HTML básico
        lines = html_content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('<h1>'):
                text = line.replace('<h1>', '').replace('</h1>', '')
                text_widget.insert(tk.END, text + '\n\n', 'h1')
            elif line.startswith('<h2>'):
                text = line.replace('<h2>', '').replace('</h2>', '')
                text_widget.insert(tk.END, text + '\n', 'h2')
            elif line.startswith('<p>'):
                text = line.replace('<p>', '').replace('</p>', '')
                text_widget.insert(tk.END, text + '\n\n')
            elif line.startswith('<li>'):
                text = line.replace('<li>', '• ').replace('</li>', '')
                text_widget.insert(tk.END, text + '\n')
            elif line.startswith('<b>'):
                text = line.replace('<b>', '').replace('</b>', '')
                text_widget.insert(tk.END, text, 'bold')
            else:
                text_widget.insert(tk.END, line + '\n')
        
        text_widget.config(state=tk.DISABLED)

class QuickHelp:
    """Sistema de ayuda rápida contextual"""
    @staticmethod
    def show_quick_help(parent, widget, message):
        """Mostrar ayuda contextual para un widget"""
        # Crear tooltip
        tooltip = tk.Toplevel(parent)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{parent.winfo_pointerx()+10}+{parent.winfo_pointery()+10}")
        
        label = ttk.Label(tooltip, text=message, background="lightyellow", 
                         relief="solid", borderwidth=1, padding=5)
        label.pack()
        
        # Programar desaparición
        tooltip.after(5000, tooltip.destroy)