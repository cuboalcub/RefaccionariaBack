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
- `POST /api/productos/` **no** recibe `id_movimientos`. El inventario se gestiona con movimientos, no con el producto.

### Movimientos (inventario)
- `POST /api/movimientos/` recibe:
  ```json
  {
    "id_producto": 1,
    "tipo": "ENTRADA",
    "cantidad": 5,
    "razon": "Compra a proveedor"
  }
  ```
- `tipo` es `ENTRADA` (suma a existencia) o `SALIDA` (resta a existencia; valida stock suficiente).
- Un movimiento pertenece a un producto (`id_producto`), y un producto puede tener muchos movimientos.

### Ventas
- `POST /api/ventas/` **ignora** el `total` enviado por el cliente. El total se calcula automáticamente sumando los `subtotal` de sus detalles (`POST /api/detalle/`).
- `POST /api/detalle/` recibe `id_producto`, `id_venta`, `cantidad` y `subtotal`; descuenta la existencia del producto y recalcula el total de la venta.

### Autenticación
- La mayoría de los endpoints requieren el header `Authorization: Bearer <access_token>` (JWT).
- Públicos: `POST /api/login` y `POST /api/users` (registro).
- `DELETE /api/users/<id>` solo para usuarios staff.