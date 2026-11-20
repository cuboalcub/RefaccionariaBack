# Módulo usuarios — reporte de validación

## Archivos inspeccionados
`usuario/models.py` (Perfil.rol), `services/{usuario_service,perfil_service}.py`,
`controllers/{usuario,perfil}_controller.py`, `migrations/0002_perfil_rol.py`,
`repository/permissions.py` (matriz), `repository/base_controller.py` (permisos declarativos).

## Reglas de negocio verificadas
- Login emite `id_sucursal` y `rol`; registro cerrado (encargado crea cajeros propios, staff libre, anónimo 401).
- Staff sin `id_sucursal` hereda la de su perfil; si no tiene, el alta responde 400. Siempre se crea `Perfil` para que el usuario pueda operar.
- Encargado modifica datos/password/activo de su sucursal; no borra, no cambia roles/sucursales, no toca otras sucursales (403).
- Staff puede reasignar `id_sucursal`/`rol` con `PUT /api/users/<id>`; `PUT /api/perfil/` sigue ignorando el rol (sin auto-escalación).
- Definición única de admin: `is_staff` (superuser la implica).
- Backfill: staff existentes → admin, resto cajero (migración con reversa, sin aplicar en prod).

## Pruebas (14 nuevas + existentes de usuario/perfil)
- Nuevas: `tests/test_usuarios_gestion.py` (14: alta, modificación, lista filtrada, denegaciones, registro).
- Existentes adaptadas: `usuario/tests/test_user_controller.py` (staff en contrato), `test_cierre_100.py`.
- Aprobadas todas, fallidas 0, omitidas 0.

## Bugs encontrados y correcciones
- Registro público aceptaba `rol` (se ignoraba pero llegaba al ORM): ahora se descarta + test.
- `GET /api/users` y detalle sin scoping: filtrados/403 por sucursal.
- Alta de staff sin `id_sucursal` dejaba al usuario sin `Perfil` y no podía operar: ahora hereda la sucursal del creador (o 400) y el `Perfil` siempre se crea.
- Inconsistencia admin (`is_superuser` vs `IsAdminUser→is_staff`): documentada; negocio usa `is_staff`.
- `is_active=False` permitía login por password: ahora `/api/login` responde 401 (refresh JWT ya lo rechazaba).
- Correos duplicados en alta/edición: se validan case-insensitive (400); vacío sigue permitido.
- Escalada de privilegios en alta: se descartan `is_staff`/`is_superuser`/`is_active` del payload.

## Riesgos y pendientes
- Reasignación de `rol`/sucursal por staff vía API: auditar quién la ejecuta (sin log de cambios todavía).
- Arranque: primer staff vía `createsuperuser`; sin él nadie da de alta.
- Unicidad de correo solo a nivel aplicación (sin índice en BD): dos altas concurrentes podrían duplicar.
