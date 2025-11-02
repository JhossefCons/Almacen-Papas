"""
Ventana de login para la aplicación
"""
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

class LoginWindow:
    def __init__(self, auth_manager):
        self.auth_manager = auth_manager
        self.result = False
        
        self.root = tk.Tk()
        self.root.title("Distribuidora de papa - Inicio de Sesión")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # --- CAMBIO 1: Cargar el icono PEQUEÑO para la barra de título ---
        try:
            icon_image = Image.open("assets/icons/iconoPapa.png")
            w, h = icon_image.size
            max_size = 64
            scale = min(max_size / w, max_size / h)
            new_w, new_h = int(w * scale), int(h * scale)
            icon_image = icon_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.icon_photo = ImageTk.PhotoImage(icon_image)
            self.root.iconphoto(False, self.icon_photo)
        except Exception as e:
            print(f"No se pudo cargar el icono de la ventana (iconoPapa.png): {e}")
        
        self.center_window()
        self.setup_ui()
        self.root.mainloop()
        
    def center_window(self):
        """Centrar la ventana en la pantalla"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
    def setup_ui(self):
        
        # Marco principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Título con icono
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=2, pady=20)
        
        # --- CAMBIO 2: Cargar el LOGO NUEVO para mostrar DENTRO de la ventana ---
        try:
            logo_image = Image.open("assets/icons/logo distribuidora de papa santa lucia.png")
            w, h = logo_image.size
            max_size = 250
            scale = min(max_size / w, max_size / h)
            new_w, new_h = int(w * scale), int(h * scale)
            logo_image = logo_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            # Guardar en una variable de instancia DIFERENTE
            self.logo_photo = ImageTk.PhotoImage(logo_image) 
        except Exception as e:
            print(f"No se pudo cargar el logo (logo distribuidora...): {e}")
            self.logo_photo = None # Fallback por si la imagen no carga

        # Usar la nueva variable self.logo_photo
        icon_label = ttk.Label(title_frame, image=self.logo_photo)
        icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Campos de formulario
        ttk.Label(main_frame, text="Usuario:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(main_frame, width=25)
        self.username_entry.grid(row=1, column=1, pady=5, padx=10)
        
        ttk.Label(main_frame, text="Contraseña:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(main_frame, width=25, show="*")
        self.password_entry.grid(row=2, column=1, pady=5, padx=10)
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        login_btn = ttk.Button(button_frame, text="Iniciar Sesión", command=self.attempt_login)
        login_btn.pack(side=tk.LEFT, padx=10)
        
        cancel_btn = ttk.Button(button_frame, text="Cancelar", command=self.cancel_login)
        cancel_btn.pack(side=tk.LEFT, padx=10)
        
        # Configurar el enfoque y eventos
        self.username_entry.focus()
        self.root.bind('<Return>', lambda event: self.attempt_login())
        
        # Configurar grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
    def attempt_login(self):
        """Intentar iniciar sesión con las credenciales proporcionadas"""
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Por favor ingrese usuario y contraseña")
            return
            
        user = self.auth_manager.verify_login(username, password)
        if user:
            self.auth_manager.current_user = user['id']
            self.auth_manager.user_role = user['role']
            self.result = True
            self.root.destroy()
        else:
            messagebox.showerror("Error", "Credenciales inválidas")
            self.password_entry.delete(0, tk.END)
            self.username_entry.focus()
            
    def cancel_login(self):
        """Cancelar el inicio de sesión"""
        self.result = False
        self.root.destroy()