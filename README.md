# Refaccionaria backend  


## Pasos para iniciar
### crear venv
```bash
python3 -m venv .venv
```
### Activar en Linux
```bash
source .venv/bin/activate
```
### Activar en Windows PowerShell
```bash
source .venv/bin/activate
```
### Descargar bibliotecas
```bash
pip install -r requirements.txt
```
### Configurar variables de entorno
```bash
cp .env.example .env
# edita .env y define SECRET_KEY y DEBUG=True para desarrollo
```

## Pasos para ejecutar
### pasos para migrar
```bash
python manage.py makemigrations

python manage.py migrate
```
### Corre Django
```bash
python manage.py runserver
```

├── APP/                  # App de usuarios
│   ├── controllers/        # Controladores (views o APIs)
│   │   ├── user_controller.py
│   │
│   ├── services/           # Lógica de negocio
│   │   ├── user_service.py
│   │
│   ├── repositories/       # Acceso a datos (ORM queries)
│   │   ├── user_repository.py
│   │
│   ├── models.py           # Entidades de datos
│   ├── urls.py
│   └── tests.py

## Contrato de API (importante para el frontend)

### Productos
- `POST /api/productos/` **no** recibe `existencia` ni `id_movimientos`. El producto solo guarda datos (precio, costo, clave, etc.). El stock vive en `DetalleInventario`.

### Inventario (libro de movimientos)
- El stock de un producto se calcula como `Σ ENTRADAS − Σ SALIDAS` de los `DetalleInventario` por inventario.
- `POST /api/detalles-inventario/` recibe **dos formas**:
  1. **Con movimiento existente** (requiere crear antes `POST /api/movimientos-inventario/`):
  ```json
  {
    "id_producto": 1,
    "id_inventario": 1,
    "id_movimiento": 1,
    "id_proveedor": 1,
    "cantidad": 5
  }
  ```
  2. **Sin movimiento (auto-creación)** — `id_movimiento` es opcional; si no se envía, el backend crea automáticamente el `MovimientoInventario`:
  ```json
  {
    "id_producto": 1,
    "id_inventario": 1,
    "cantidad": 7
  }
  ```
  O con tipo/razón explícitos (por defecto `tipo_movimiento=ENTRADA`, `razon=Ajuste manual`):
  ```json
  {
    "id_producto": 1,
    "id_inventario": 1,
    "cantidad": 3,
    "tipo_movimiento": "SALIDA",
    "razon": "Ajuste por merma",
    "observaciones": "Productos dañados"
  }
  ```
- `id_movimiento` es un `MovimientoInventario` de tipo `ENTRADA` (suma al stock) o `SALIDA` (resta; valida stock suficiente). Si no se envía, se auto-crea según `tipo_movimiento`.
- `GET /api/inventarios/mi-sucursal/` devuelve el inventario de la sucursal del usuario autenticado, agrupado por producto con su stock actual.

### Ventas
- `POST /api/ventas/` **ignora** `total`, `id_usuario` e `id_inventario` enviados por el cliente. `id_usuario` y sucursal se toman automáticamente del JWT/perfil (`Authorization: Bearer <access_token>` → `Perfil.sucursal → Inventario`). Solo recibe `id_metodoPago` (más `detalles` opcional para creación atómica). El total se calcula automáticamente sumando los `subtotal` de sus detalles. Staff/superuser puede enviar `sucursal_id` como override explícito. Las respuestas exponen `id_sucursal` (ya no `id_inventario`) y `GET /api/ventas/` filtra por `sucursal_id` (staff) en vez de `id_inventario`.
- `POST /api/detalleventa/` (crear) está **deprecado** → `410 Gone`: crear siempre con `POST /api/ventas/` + `detalles` (atómico). `GET/PUT/DELETE` por unidad siguen vigentes; al ajustar/borrar el detalle, la salida se revierte (con locks de venta + stock).
- `DetalleInventario.id_detalle_venta` es `PROTECT`: el borrado directo por ORM/shell de detalles con salida vinculada falla en vez de dejar huérfanos; borrar siempre vía servicios.
- El `subtotal` de cada detalle se calcula **en el servidor** como `precio_venta * cantidad` del producto (se ignora cualquier `subtotal` enviado por el cliente).

### Autenticación
- La mayoría de los endpoints requieren el header `Authorization: Bearer <access_token>` (JWT).
- Público: `POST /api/login`. El registro es cerrado: `POST /api/users` exige encargado (crea cajeros de su sucursal) o staff.
- `DELETE /api/users/<id>` solo para usuarios staff.

### Roles y sucursales
- `Perfil.rol`: `cajero` (default) / `encargado` / `admin`. `is_staff` implica todo (`is_superuser` la implica). Sin perfil el rol es `cajero`.
- Matriz: cajero vende y lee; encargado además anula ventas, escribe inventario/bulk y precios, ve reporte y gestiona usuarios de su sucursal (crear cajeros, modificar datos/password/activo; no borra ni cambia roles); admin además gestiona inventarios y sucursales. El login expone `rol`; el registro y `PUT /api/perfil/` lo ignoran (sin auto-escalación; el rol se asigna por shell/admin).
- Todo está acotado por sucursal (JWT/perfil, staff con override): otra sucursal → 403, sin sucursal → 400. Sin permiso de rol → 403. Movimientos y lectura de catálogos siguen globales.