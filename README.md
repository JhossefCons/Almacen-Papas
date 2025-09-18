# PapaSoft - Sistema de Gestión Integral

PapaSoft es una aplicación de escritorio desarrollada en Python para la gestión completa de negocios dedicados a la comercialización de papa. Proporciona herramientas integrales para controlar inventario, ventas, caja, préstamos a empleados, nómina y más, con una interfaz gráfica intuitiva basada en Tkinter.

## Características Principales

### 🏦 Módulo de Caja
- Registro detallado de entradas y salidas de dinero
- Distinción entre efectivo y transferencias bancarias
- Cuadre de caja diario, semanal y mensual
- Reportes personalizables de flujo de efectivo
- Control de arqueo de caja

### 📝 Módulo de Préstamos
- Registro completo de préstamos con fechas y términos de pago
- Historial detallado de pagos realizados
- Alertas automáticas de vencimientos próximos
- Reportes de préstamos activos y completamente saldados
- Cálculo automático de intereses y amortización

### 🥔 Módulo de Inventario
- Clasificación detallada por tipo y calidad de papa:
  - **Papa parda**: primera, segunda, tercera calidad
  - **Papa amarilla**: primera, tercera calidad
  - **Papa colorada**: primera, segunda, tercera calidad
- Control preciso de costales (empaques) y unidades
- Registro de entradas y salidas con trazabilidad
- Alertas configurables para niveles bajos de stock
- Reportes de inventario en tiempo real

### 💰 Módulo de Ventas
- Registro de ventas con detalles de productos y precios
- Control de clientes y facturación
- Integración con inventario para actualización automática de stock
- Reportes de ventas por período y producto

### 👥 Módulo de Empleados
- Gestión completa de información de empleados
- Control de asistencia y horarios
- Integración con módulo de nómina

### 💼 Módulo de Nómina
- Cálculo automático de salarios
- Registro de deducciones e ingresos adicionales
- Generación de recibos de pago
- Historial de pagos

### 🔐 Sistema de Seguridad
- Autenticación robusta de usuarios con login seguro
- Sistema de roles: administrador y empleado
- Permisos granularizados por módulo y acción
- Backup automático de base de datos con programador
- Logs de auditoría para todas las operaciones

## Arquitectura del Sistema

El proyecto está estructurado de manera modular:

- **`main.py`**: Punto de entrada principal de la aplicación
- **`ui/`**: Interfaces gráficas (ventanas de login, principal, módulos)
- **`modules/`**: Lógica de negocio dividida por funcionalidad
- **`database/`**: Gestión de base de datos SQLite con modelos y conexiones
- **`auth/`**: Sistema de autenticación y gestión de usuarios
- **`utils/`**: Utilidades comunes (notificaciones, reportes, componentes UI)
- **`assets/`**: Recursos gráficos e iconos

## Instalación

### Requisitos del Sistema
- **Python**: 3.8 o superior
- **pip**: Gestor de paquetes de Python (incluido con Python)
- **Sistema Operativo**: Windows 10+, Linux, macOS

### Instalación desde Código Fuente

1. **Clonar o descargar el proyecto**
   ```bash
   git clone <url-del-repositorio>
   cd Almacen-Papas
   ```

2. **Crear entorno virtual (recomendado)**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # En Windows
   # source venv/bin/activate  # En Linux/macOS
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar la aplicación**
   - Editar `config.ini` si es necesario para personalizar configuraciones
   - La base de datos se creará automáticamente en la primera ejecución

5. **Ejecutar la aplicación**
   ```bash
   python main.py
   ```

### Construcción de Ejecutable (Opcional)

Para crear un ejecutable independiente:

```bash
python setup.py build
```

Esto generará un ejecutable en la carpeta `build/` que puede distribuirse sin requerir Python instalado.

## Uso

1. **Primer Inicio**: La aplicación creará automáticamente un usuario administrador por defecto.
2. **Login**: Ingresar con las credenciales del administrador.
3. **Navegación**: Usar el menú principal para acceder a los diferentes módulos.
4. **Configuración**: Acceder a configuraciones desde el menú de administrador.

### Roles de Usuario
- **Administrador**: Acceso completo a todos los módulos y configuraciones
- **Empleado**: Acceso limitado según permisos asignados

## Desarrollo

### Estructura del Código
```
Almacen-Papas/
├── main.py                 # Punto de entrada
├── setup.py               # Script de construcción
├── config.ini             # Configuraciones
├── requirements.txt       # Dependencias
├── README.md              # Esta documentación
├── .gitignore             # Archivos ignorados por Git
├── assets/                # Recursos gráficos
│   └── icons/
├── auth/                  # Sistema de autenticación
├── database/              # Gestión de BD
├── modules/               # Módulos de negocio
│   ├── inventory/
│   ├── sales/
│   ├── cash_register/
│   ├── payroll/
│   ├── loans/
│   └── employees/
├── ui/                    # Interfaces gráficas
└── utils/                 # Utilidades
```

### Tecnologías Utilizadas
- **Python 3.8+**: Lenguaje principal
- **Tkinter**: Interfaz gráfica nativa
- **SQLite**: Base de datos embebida
- **Pillow**: Procesamiento de imágenes
- **tkcalendar**: Widgets de calendario
- **cx_Freeze**: Generación de ejecutables

## Contribución

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## Soporte

Para soporte técnico o reportar bugs, por favor crear un issue en el repositorio del proyecto.

## Versión

Versión actual: 1.0.0

---

**Desarrollado por**: Jhossef Nicolas Constain Nieves

