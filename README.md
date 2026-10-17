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
- `POST /api/ventas/` **ignora** `total`, `id_usuario` e `id_inventario` enviados por el cliente. `id_usuario` y sucursal se toman automáticamente del JWT/perfil (`Authorization: Bearer <access_token>` → `Perfil.sucursal → Inventario`). Solo recibe `id_metodo_pago` (más `detalles` opcional para creación atómica). El total se calcula automáticamente sumando los `subtotal` de sus detalles. Staff/superuser puede enviar `sucursal_id` como override explícito. Las respuestas exponen `id_sucursal` (ya no `id_inventario`) y `GET /api/ventas/` filtra por `sucursal_id` (staff) en vez de `id_inventario`.
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
```
RefaccionariaBack
├─ .opencode
│  ├─ opencode.json
│  ├─ package-lock.json
│  ├─ package.json
│  ├─ plugins
│  │  └─ graphify.js
│  └─ skills
│     └─ graphify
│        ├─ .graphify_version
│        ├─ SKILL.md
│        └─ references
│           ├─ add-watch.md
│           ├─ exports.md
│           ├─ extraction-spec.md
│           ├─ github-and-merge.md
│           ├─ hooks.md
│           ├─ query.md
│           ├─ transcribe.md
│           └─ update.md
├─ AGENTS.md
├─ README.md
├─ RTR
│  ├─ __init__.py
│  ├─ asgi.py
│  ├─ settings.py
│  ├─ settings_test.py
│  ├─ urls.py
│  └─ wsgi.py
├─ clientes
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ controllers
│  │  ├─ __init__.py
│  │  └─ cliente_controller.py
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  └─ __init__.py
│  ├─ models.py
│  ├─ repositories
│  │  ├─ __init__.py
│  │  └─ cliente_repository.py
│  ├─ services
│  │  ├─ __init__.py
│  │  └─ cliente_service.py
│  ├─ tests
│  │  ├─ __init__.py
│  │  └─ test_cliente_api.py
│  └─ urls.py
├─ docs
│  ├─ INDICE.md
│  ├─ REPORT_catalogos.md
│  ├─ REPORT_inventario.md
│  ├─ REPORT_usuarios.md
│  ├─ REPORT_ventas.md
│  └─ RUNBOOK_migracion.md
├─ estructura.txt
├─ interfaces
│  ├─ __init__.py
│  ├─ controller.py
│  ├─ repository.py
│  └─ service.py
├─ inventario
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ controllers
│  │  ├─ detalle_inventario_controller.py
│  │  ├─ inventario_controller.py
│  │  ├─ movimiento_inventario_controller.py
│  │  └─ precio_sucursal_controller.py
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_detalleinventario_id_detalle_venta.py
│  │  ├─ 0003_detalleinventario_costo_and_more.py
│  │  ├─ 0004_remove_detalleinventario_costo_and_more.py
│  │  ├─ 0005_precio_sucursal.py
│  │  ├─ 0006_seed_precio_sucursal.py
│  │  ├─ 0007_alter_detalleinventario_id_detalle_venta.py
│  │  └─ __init__.py
│  ├─ models.py
│  ├─ repositories
│  │  ├─ detalle_inventario_repository.py
│  │  ├─ inventario_repository.py
│  │  ├─ movimiento_inventario_repository.py
│  │  └─ precio_sucursal_repository.py
│  ├─ services
│  │  ├─ detalle_inventario_service.py
│  │  ├─ inventario_service.py
│  │  ├─ movimiento_inventario_service.py
│  │  └─ precio_sucursal_service.py
│  ├─ tests
│  │  ├─ __init__.py
│  │  └─ test_legacy.py
│  └─ urls.py
├─ manage.py
├─ notifications
│  ├─ __init__.py
│  ├─ apps.py
│  ├─ controllers
│  │  └─ notification_controller.py
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_notification_persistente.py
│  │  └─ __init__.py
│  ├─ models.py
│  ├─ repositories
│  │  └─ notification_repository.py
│  ├─ services
│  │  ├─ notification_service.py
│  │  ├─ stock_alerts.py
│  │  └─ thresholds.py
│  ├─ tests
│  │  ├─ __init__.py
│  │  ├─ conftest.py
│  │  ├─ test_inventory_hooks.py
│  │  ├─ test_migration_backup.py
│  │  ├─ test_notification_api.py
│  │  ├─ test_stock_alerts.py
│  │  └─ test_thresholds.py
│  └─ urls.py
├─ producto
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ controllers
│  │  ├─ producto_controller.py
│  │  ├─ proveedor_controller.py
│  │  └─ tipo_controller.py
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_delete_notification.py
│  │  ├─ 0002_initial.py
│  │  ├─ 0004_remove_producto_existencia.py
│  │  ├─ 0005_merge_20261011_1415.py
│  │  └─ __init__.py
│  ├─ models.py
│  ├─ repositories
│  │  ├─ producto_repository.py
│  │  ├─ proveedor_repository.py
│  │  └─ tipo_repository.py
│  ├─ services
│  │  ├─ producto_service.py
│  │  ├─ proveedor_service.py
│  │  └─ tipo_service.py
│  ├─ tests
│  │  └─ __init__.py
│  └─ urls.py
├─ pytest.ini
├─ repository
│  ├─ __init__.py
│  ├─ base_controller.py
│  ├─ base_repository.py
│  ├─ base_service.py
│  ├─ exceptions.py
│  └─ permissions.py
├─ requirements.txt
├─ skills-lock.json
├─ sucursales
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ controllers
│  │  └─ sucursal_controller.py
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_sucursal_codigo_postal_sucursal_codigo_sucursal_and_more.py
│  │  ├─ 0003_sucursal_optional_fields.py
│  │  └─ __init__.py
│  ├─ models.py
│  ├─ repositories
│  │  └─ sucursal_repository.py
│  ├─ services
│  │  └─ sucursal_service.py
│  ├─ tests
│  │  ├─ __init__.py
│  │  └─ test_legacy.py
│  └─ urls.py
├─ tests
│  ├─ __init__.py
│  ├─ conftest.py
│  ├─ factories.py
│  ├─ test_base_clientes_usuario.py
│  ├─ test_cierre_100.py
│  ├─ test_fase3_endurecimiento.py
│  ├─ test_flujos_e2e.py
│  ├─ test_inventario.py
│  ├─ test_inventario_extra.py
│  ├─ test_inventario_scoping.py
│  ├─ test_producto_sucursal.py
│  ├─ test_usuarios_gestion.py
│  ├─ test_ventas.py
│  ├─ test_ventas_creacion_atomica.py
│  ├─ test_ventas_delete_regresion.py
│  ├─ test_ventas_extra.py
│  └─ test_ventas_seguridad.py
├─ usuario
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ controllers
│  │  ├─ perfil_controller.py
│  │  └─ usuario_controller.py
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_perfil_rol.py
│  │  └─ __init__.py
│  ├─ models.py
│  ├─ repositories
│  │  ├─ perfil_repository.py
│  │  └─ usuario_repository.py
│  ├─ serializers.py
│  ├─ services
│  │  ├─ perfil_service.py
│  │  └─ usuario_service.py
│  ├─ tests
│  │  ├─ __init__.py
│  │  ├─ test_perfil_service.py
│  │  ├─ test_user_controller.py
│  │  ├─ test_user_repository.py
│  │  └─ test_user_service.py
│  └─ urls.py
└─ ventas
   ├─ __init__.py
   ├─ admin.py
   ├─ apps.py
   ├─ controllers
   │  ├─ detalle_venta_controller.py
   │  ├─ metodo_pago_controller.py
   │  ├─ venta_controller.py
   │  └─ venta_ticket_controller.py
   ├─ migrations
   │  ├─ 0001_initial.py
   │  ├─ 0002_venta_id_inventario.py
   │  ├─ 0003_rename_id_metodopago_venta_id_metodo_pago.py
   │  └─ __init__.py
   ├─ models.py
   ├─ repositories
   │  ├─ detalle_venta_repository.py
   │  ├─ metodo_pago_repository.py
   │  └─ venta_repository.py
   ├─ services
   │  ├─ detalle_venta_service.py
   │  ├─ metodo_pago_service.py
   │  ├─ reporte_venta_service.py
   │  ├─ venta_service.py
   │  └─ venta_ticket_service.py
   ├─ templates
   │  └─ ventas
   ├─ tests
   │  ├─ __init__.py
   │  └─ test_legacy.py
   ├─ urls.py
   └─ views
      ├─ __init__.py
      └─ reporte_venta_view.py

```
```
RefaccionariaBack
├─ .opencode
│  ├─ opencode.json
│  ├─ package-lock.json
│  ├─ package.json
│  ├─ plugins
│  │  └─ graphify.js
│  └─ skills
│     └─ graphify
│        ├─ .graphify_version
│        ├─ SKILL.md
│        └─ references
│           ├─ add-watch.md
│           ├─ exports.md
│           ├─ extraction-spec.md
│           ├─ github-and-merge.md
│           ├─ hooks.md
│           ├─ query.md
│           ├─ transcribe.md
│           └─ update.md
├─ AGENTS.md
├─ README.md
├─ RTR
│  ├─ __init__.py
│  ├─ asgi.py
│  ├─ settings.py
│  ├─ settings_test.py
│  ├─ urls.py
│  └─ wsgi.py
├─ clientes
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ controllers
│  │  ├─ __init__.py
│  │  └─ cliente_controller.py
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  └─ __init__.py
│  ├─ models.py
│  ├─ repositories
│  │  ├─ __init__.py
│  │  └─ cliente_repository.py
│  ├─ services
│  │  ├─ __init__.py
│  │  └─ cliente_service.py
│  ├─ tests
│  │  ├─ __init__.py
│  │  └─ test_cliente_api.py
│  └─ urls.py
├─ docs
│  ├─ INDICE.md
│  ├─ REPORT_catalogos.md
│  ├─ REPORT_inventario.md
│  ├─ REPORT_usuarios.md
│  ├─ REPORT_ventas.md
│  └─ RUNBOOK_migracion.md
├─ estructura.txt
├─ interfaces
│  ├─ __init__.py
│  ├─ controller.py
│  ├─ repository.py
│  └─ service.py
├─ inventario
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ controllers
│  │  ├─ detalle_inventario_controller.py
│  │  ├─ inventario_controller.py
│  │  ├─ movimiento_inventario_controller.py
│  │  └─ precio_sucursal_controller.py
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_detalleinventario_id_detalle_venta.py
│  │  ├─ 0003_detalleinventario_costo_and_more.py
│  │  ├─ 0004_remove_detalleinventario_costo_and_more.py
│  │  ├─ 0005_precio_sucursal.py
│  │  ├─ 0006_seed_precio_sucursal.py
│  │  ├─ 0007_alter_detalleinventario_id_detalle_venta.py
│  │  └─ __init__.py
│  ├─ models.py
│  ├─ repositories
│  │  ├─ detalle_inventario_repository.py
│  │  ├─ inventario_repository.py
│  │  ├─ movimiento_inventario_repository.py
│  │  └─ precio_sucursal_repository.py
│  ├─ services
│  │  ├─ detalle_inventario_service.py
│  │  ├─ inventario_service.py
│  │  ├─ movimiento_inventario_service.py
│  │  └─ precio_sucursal_service.py
│  ├─ tests
│  │  ├─ __init__.py
│  │  └─ test_legacy.py
│  └─ urls.py
├─ manage.py
├─ notifications
│  ├─ __init__.py
│  ├─ apps.py
│  ├─ controllers
│  │  └─ notification_controller.py
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_notification_persistente.py
│  │  └─ __init__.py
│  ├─ models.py
│  ├─ repositories
│  │  └─ notification_repository.py
│  ├─ services
│  │  ├─ notification_service.py
│  │  ├─ stock_alerts.py
│  │  └─ thresholds.py
│  ├─ tests
│  │  ├─ __init__.py
│  │  ├─ conftest.py
│  │  ├─ test_inventory_hooks.py
│  │  ├─ test_migration_backup.py
│  │  ├─ test_notification_api.py
│  │  ├─ test_stock_alerts.py
│  │  └─ test_thresholds.py
│  └─ urls.py
├─ producto
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ controllers
│  │  ├─ producto_controller.py
│  │  ├─ proveedor_controller.py
│  │  └─ tipo_controller.py
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_delete_notification.py
│  │  ├─ 0002_initial.py
│  │  ├─ 0004_remove_producto_existencia.py
│  │  ├─ 0005_merge_20261011_1415.py
│  │  └─ __init__.py
│  ├─ models.py
│  ├─ repositories
│  │  ├─ producto_repository.py
│  │  ├─ proveedor_repository.py
│  │  └─ tipo_repository.py
│  ├─ services
│  │  ├─ producto_service.py
│  │  ├─ proveedor_service.py
│  │  └─ tipo_service.py
│  ├─ tests
│  │  └─ __init__.py
│  └─ urls.py
├─ pytest.ini
├─ repository
│  ├─ __init__.py
│  ├─ base_controller.py
│  ├─ base_repository.py
│  ├─ base_service.py
│  ├─ exceptions.py
│  └─ permissions.py
├─ requirements.txt
├─ skills-lock.json
├─ sucursales
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ controllers
│  │  └─ sucursal_controller.py
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_sucursal_codigo_postal_sucursal_codigo_sucursal_and_more.py
│  │  ├─ 0003_sucursal_optional_fields.py
│  │  └─ __init__.py
│  ├─ models.py
│  ├─ repositories
│  │  └─ sucursal_repository.py
│  ├─ services
│  │  └─ sucursal_service.py
│  ├─ tests
│  │  ├─ __init__.py
│  │  └─ test_legacy.py
│  └─ urls.py
├─ tests
│  ├─ __init__.py
│  ├─ conftest.py
│  ├─ factories.py
│  ├─ test_base_clientes_usuario.py
│  ├─ test_cierre_100.py
│  ├─ test_fase3_endurecimiento.py
│  ├─ test_flujos_e2e.py
│  ├─ test_inventario.py
│  ├─ test_inventario_extra.py
│  ├─ test_inventario_scoping.py
│  ├─ test_producto_sucursal.py
│  ├─ test_usuarios_gestion.py
│  ├─ test_ventas.py
│  ├─ test_ventas_creacion_atomica.py
│  ├─ test_ventas_delete_regresion.py
│  ├─ test_ventas_extra.py
│  └─ test_ventas_seguridad.py
├─ usuario
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ controllers
│  │  ├─ perfil_controller.py
│  │  └─ usuario_controller.py
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_perfil_rol.py
│  │  └─ __init__.py
│  ├─ models.py
│  ├─ repositories
│  │  ├─ perfil_repository.py
│  │  └─ usuario_repository.py
│  ├─ serializers.py
│  ├─ services
│  │  ├─ perfil_service.py
│  │  └─ usuario_service.py
│  ├─ tests
│  │  ├─ __init__.py
│  │  ├─ test_perfil_service.py
│  │  ├─ test_user_controller.py
│  │  ├─ test_user_repository.py
│  │  └─ test_user_service.py
│  └─ urls.py
└─ ventas
   ├─ __init__.py
   ├─ admin.py
   ├─ apps.py
   ├─ controllers
   │  ├─ detalle_venta_controller.py
   │  ├─ metodo_pago_controller.py
   │  ├─ venta_controller.py
   │  └─ venta_ticket_controller.py
   ├─ migrations
   │  ├─ 0001_initial.py
   │  ├─ 0002_venta_id_inventario.py
   │  ├─ 0003_rename_id_metodopago_venta_id_metodo_pago.py
   │  └─ __init__.py
   ├─ models.py
   ├─ repositories
   │  ├─ detalle_venta_repository.py
   │  ├─ metodo_pago_repository.py
   │  └─ venta_repository.py
   ├─ services
   │  ├─ detalle_venta_service.py
   │  ├─ metodo_pago_service.py
   │  ├─ reporte_venta_service.py
   │  ├─ venta_service.py
   │  └─ venta_ticket_service.py
   ├─ templates
   │  └─ ventas
   ├─ tests
   │  ├─ __init__.py
   │  └─ test_legacy.py
   ├─ urls.py
   └─ views
      ├─ __init__.py
      └─ reporte_venta_view.py

```