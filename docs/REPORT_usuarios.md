# Módulo usuarios — reporte de validación

## Archivos inspeccionados
`usuario/models.py` (Perfil.rol), `services/{usuario_services,perfil_service}.py`,
`controllers/{usuario,perfil}_controller.py`, `migrations/0002_perfil_rol.py`,
`repository/permissions.py` (matriz), `repository/base_controller.py` (permisos declarativos).

## Reglas de negocio verificadas
- Login emite `rol`; registro cerrado (encargado crea cajeros propios, staff libre, anónimo 401).
- Encargado modifica datos/password/activo de su sucursal; no borra, no cambia roles/sucursales, no toca otras sucursales (403).
- `DELETE` solo staff; `update_user` y `PUT /api/perfil/` ignoran `is_staff/is_superuser/rol` (sin auto-escalación).
- Definición única de admin: `is_staff` (superuser la implica).
- Backfill: staff existentes → admin, resto cajero (migración con reversa, sin aplicar en prod).

## Pruebas (14 nuevas + existentes de usuario/perfil)
- Nuevas: `tests/test_usuarios_gestion.py` (14: alta, modificación, lista filtrada, denegaciones, registro).
- Existentes adaptadas: `usuario/tests/test_user_controller.py` (staff en contrato), `test_cierre_100.py`.
- Aprobadas todas, fallidas 0, omitidas 0.

## Bugs encontrados y correcciones
- Registro público aceptaba `rol` (se ignoraba pero llegaba al ORM): ahora se descarta + test.
- `GET /api/users` y detalle sin scoping: filtrados/403 por sucursal.
- Inconsistencia admin (`is_superuser` vs `IsAdminUser→is_staff`): documentada; negocio usa `is_staff`.

## Riesgos y pendientes
- Cambio de `rol` solo por shell/admin (sin endpoint): operativo, documentar responsables.
- Arranque: primer staff vía `createsuperuser`; sin él nadie da de alta.
- `is_active=False` no bloquea `login()` por password (solo JWT lo rechaza): decidir si endurecer.
