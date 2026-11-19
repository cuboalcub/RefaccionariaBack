# Reportes de validación por módulo — Backend Refaccionaria

Metodología aplicada: N1 unitarias → N2 integración → N3 API → N4 regresión.
Gate: suite completa en verde + cobertura 100% (`pytest.ini`).

- `REPORT_ventas.md` — ventas, detalles, ticket, reporte, creación atómica.
- `REPORT_inventario.md` — inventarios, movimientos, detalles, bulk, precios.
- `REPORT_usuarios.md` — auth, perfiles, roles, gestión por encargado.
- `REPORT_catalogos.md` — productos, tipos, proveedores, clientes, sucursales.

Estado global (cierre Fase 4): **543 passed, 0 failed, cobertura 100%**.
Incluye `tests/test_flujos_e2e.py` (venta→ticket→reporte→reversión, gestión en cadena).
