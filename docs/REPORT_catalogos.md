# Módulo catálogos — reporte de validación

Alcance: productos, tipos, proveedores, clientes, sucursales (globales, sin scoping por sucursal por decisión Fase 1).

## Archivos inspeccionados
`producto/controllers/{producto,tipo,proveedor}_controller.py`, `clientes/controllers/cliente_controller.py`,
`sucursales/controllers/sucursal_controller.py`, `repository/base_controller.py` (permisos declarativos).

## Reglas de negocio verificadas
- Lectura abierta a autenticados; alta para cajero+; modificación/baja para encargado+; sucursales (alta/baja/modificación) solo admin.
- Comportamiento previo preservado (filtros, paginación, validaciones); solo se agregó el gate de rol (403 sin permiso).

## Pruebas
- Existentes adaptadas: `test_producto_sucursal.py`, `test_base_clientes_usuario.py::TestClienteAPI`,
  `clientes/tests/test_cliente_api.py` (promoción a encargado/admin donde prueban escritura).
- Aprobadas todas, fallidas 0, omitidas 0.

## Riesgos y pendientes
- Catálogos globales: un cajero ve productos/clientes de todas las sucursales (decisión consciente; reevaluar si hay datos sensibles por sucursal).
- Precios siguen siendo el mecanismo de diferenciación por sucursal, ya acotado (ver REPORT_inventario).
