# Ayuda – Ventas

Esta sección describe el flujo de **Ventas** (pestaña “Ventas”) y cómo impacta en **Inventario** y **Caja**.

## ¿Qué hace esta pestaña?
- Registra **salidas** de papa (ventas por bultos).
- **Descuenta** existencias del inventario según **tipo** y **calidad**.
- **Consume costales** (1 costal por cada bulto vendido).
- (Opcional) Registra el **ingreso en Caja** según el método de pago.

---

## Flujo para registrar una venta
1. **Fecha**: seleccione la fecha de la operación.
2. **Tipo y Calidad**: elija la combinación válida (parda/amarilla/colorada + primera/segunda/tercera).
3. **Cantidad (bultos)**: ingrese la cantidad a vender.
4. **Precio unitario**:
   - Por defecto se **autollenará** con el último precio usado en ventas de esa combinación (si no hay, intenta el último de entrada).
   - Si necesita un precio distinto, marque **“Editar precio manualmente”** y escriba el nuevo valor.
5. **Método de pago**: Efectivo o Transferencia.
6. **Cliente** (opcional) y **Notas** (opcional).
7. (Opcional) **Registrar en Caja**: marque la casilla para generar el ingreso.
8. Presione **“Registrar venta”**.

> Si el stock de papa o los costales no alcanzan, el sistema mostrará un error y no registrará la venta.

---

## Reglas de negocio
- **Stock**: no puede vender más bultos de los disponibles para esa combinación de tipo/calidad.
- **Costales**: debe haber al menos tantos costales como bultos a vender. Se descuentan automáticamente.
- **Caja**:
  - Si activa “Registrar en Caja”: se crea un **ingreso** por `cantidad × precio unitario`.
  - Puede ver/filtrar dichos movimientos en el **Módulo de Caja**.

---

## Preguntas frecuentes

**¿Puedo editar una venta después de creada?**  
Sí, si eres **administrador**. Desde Inventario se puede editar el registro (cantidad/precio/notas). El sistema ajustará costales e importes conforme a la nueva cantidad.

**¿De dónde sale el precio por defecto?**  
Se toma el **último precio de venta** para esa combinación (tipo + calidad). Si no existe, intenta el último **precio de entrada**.

**Vendí con el precio equivocado**  
Edita el registro como administrador o registra una venta de ajuste.

---

## Consejos
- Mantén actualizado el **stock de costales** desde Inventario (Costales → Agregar/Ajustar).
- Usa **“Registrar en Caja”** para que la contabilidad quede completa sin pasos manuales.
- Si vendes varias calidades, registra cada una como **venta separada**.
