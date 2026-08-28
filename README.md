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
- `POST /api/detalles-inventario/` recibe:
  ```json
  {
    "id_producto": 1,
    "id_inventario": 1,
    "id_movimiento": 1,
    "id_proveedor": 1,
    "cantidad": 5
  }
  ```
- `id_movimiento` es un `MovimientoInventario` de tipo `ENTRADA` (suma al stock) o `SALIDA` (resta; valida stock suficiente).
- `GET /api/inventarios/mi-sucursal/` devuelve el inventario de la sucursal del usuario autenticado, agrupado por producto con su stock actual.

### Ventas
- `POST /api/ventas/` **ignora** el `total` enviado por el cliente. Recibe `id_usuario`, `id_metodoPago` y `id_inventario` (el inventario del que se descontará stock). El total se calcula automáticamente sumando los `subtotal` de sus detalles (`POST /api/detalle/`).
- `POST /api/detalle/` recibe `id_producto`, `id_venta`, `cantidad`; valida el stock contra el inventario de la venta y registra automáticamente una salida en `DetalleInventario` (`MovimientoInventario` SALIDA). Al borrar/ajustar el detalle, la salida se revierte.
- El `subtotal` de cada detalle se calcula **en el servidor** como `precio_venta * cantidad` del producto (se ignora cualquier `subtotal` enviado por el cliente).

### Autenticación
- La mayoría de los endpoints requieren el header `Authorization: Bearer <access_token>` (JWT).
- Públicos: `POST /api/login` y `POST /api/users` (registro).
- `DELETE /api/users/<id>` solo para usuarios staff.