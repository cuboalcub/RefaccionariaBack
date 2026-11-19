# Módulo inventario — reporte de validación

## Archivos inspeccionados
`inventario/models.py`, `services/{inventario,detalle_inventario,movimiento_inventario,precio_sucursal}_*.py`,
`controllers/{inventario,detalle_inventario,movimiento_inventario,precio_sucursal}_*.py`,
`repository/base_service.py` (fix `get_by_filters`), `repository/permissions.py`.

## Reglas de negocio verificadas
- Stock calculado `SUM(signo×cantidad)`; ENTRADA suma, SALIDA valida y resta.
- Salidas por venta crean `Movimiento SALIDA + DetalleInventario`; ajuste/reversión sincronizan cantidades.
- Bulk valida línea por línea (incl. sucursal) dentro de una transacción.
- Precio por sucursal único activo (`UniqueConstraint`), historial ordenado.
- Scoping: inventarios/detalles/bulk/precios acotados a sucursal JWT (staff override/ bypass); movimientos globales con gates por rol (sin FK a sucursal: limitación documentada).
- Matriz: ver (todos), escribir inventario/precios (encargado+), admin inventarios (admin+).

## Pruebas (129 + compartidas: 10+80+39)
- Existentes: `tests/test_inventario.py`, `test_inventario_extra.py`, `inventario/tests/test_legacy.py`.
- Nuevas: `tests/test_inventario_scoping.py` (39: matriz 403/400/200, staff, formatos).
- Aprobadas 129, fallidas 0, omitidas 0.

## Bugs encontrados y correcciones
- Endpoints de inventario/precios sin scoping (cualquier autenticado operaba cualquier sucursal): cerrados con 403 + tests.
- `BaseService.get_by_filters` roto (llamaba método inexistente; el código lo marcaba como GAP): fallback a `filter()`.
- `GET /api/reporte/` sin auth: activado `IsAuthenticated`.
- `id_detalle_venta SET_NULL` → `PROTECT` (migración 0007, no-op SQL).

## Riesgos y pendientes
- Movimientos sin sucursal: auditar por join con detalles si se requiere trazabilidad.
- Bulk con `SALIDA` compartida: lógica de movimiento común compleja pero cubierta; vigilar doble conteo en evoluciones.
