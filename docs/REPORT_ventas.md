# Módulo ventas — reporte de validación

## Archivos inspeccionados
`ventas/models.py`, `services/{venta_service,detalle_venta_service,metodo_pago_service,venta_ticket_service,reporte_venta_service}.py`,
`controllers/{venta,detalle_venta,metodo_pago,venta_ticket}_*.py`, `views/reporte_venta_view.py`,
`repositories/{venta,detalle_venta,metodo_pago}_*.py`, `repository/{base_service,base_controller,permissions}.py`.

## Reglas de negocio verificadas
- Subtotal server-side (`precio×cantidad`, 2 decimales); total = suma de subtotales, recalculado en crear/actualizar/borrar detalle.
- Precio por sucursal con fallback a base; stock medido en el inventario de la venta; cross-sucursal bloqueado (staff bypass).
- Cantidad entera > 0 (un `SALIDA -N` sumaba stock: corregido).
- `PUT /api/ventas/` ignora `total/inventario/usuario` (antes manipulable).
- `DELETE venta` revierte inventario en cascada atómica (Bug A).
- Creación atómica `POST /api/ventas/ + detalles` todo-o-nada (Bug B); `POST /api/detalleventa/` deprecado → 410.
- Scoping + matriz: vender (cajero+), anular (encargado+); reporte ver (encargado+), con auth.

## Pruebas (159: 12+103+19+6+9+4+6)
- Existentes reutilizadas: `tests/test_ventas.py`, `test_ventas_extra.py`, `ventas/tests/test_legacy.py`.
- Nuevas: `test_ventas_delete_regresion.py` (6), `test_ventas_creacion_atomica.py` (9),
  `test_ventas_seguridad.py` (19), `test_fase3_endurecimiento.py` (6), `test_flujos_e2e.py` (4, compartido).
- Aprobadas 159, fallidas 0, omitidas 0. Estado real de BD en ~95% (mocks solo en ramas defensivas/PDF).

## Bugs encontrados y correcciones
- **Bug A** (delete sin restaurar): `VentaDetailController` heredaba delete genérico; movimientos `SALIDA` huérfanos con `SET_NULL`.
  Fix: override `VentaService.delete` (atomic + `revertir_salida_por_venta` + locks). Regresión verde.
- **Bug B** (venta parcial): flujo en 2 pasos sin atomicidad global.
  Fix: `crear_venta_completa` (locks deterministas, validación previa, errores por línea) + 410 en vía legacy.
- Cantidad 0/negativa, producto inexistente → 500, PUT total manipulable, reporte sin auth, detail sin scoping: todos corregidos con regresión.

## Riesgos y pendientes
- Race real solo verificable en staging Postgres (SQLite serializa escritores; test de contención fija el invariante).
- `id_detalle_venta` ahora `PROTECT`: borrados fuera de servicios lanzan `ProtectedError` (buscado).
- Clientes viejos que vendían por pasos o mandaban `id_inventario` deben migrar.
