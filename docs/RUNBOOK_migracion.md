# Runbook — ventana de migración a producción (NO EJECUTADO)

Migraciones pendientes: `usuario.0002_perfil_rol` (columna + backfill staff→admin),
`inventario.0007` (PROTECT, no-op SQL). Riesgo bajo; igual se exige ventana con backup.

## Pre (staging/local)
- [ ] Suite completa en verde + cobertura 100% + `makemigrations --check` limpio.
- [ ] `sqlmigrate usuario 0002` y `sqlmigrate inventario 0007` revisados.
- [ ] Congelar PRs a `Deploy`; avisar a sucursales (los clientes viejos se rompen: registro público, `id_inventario`, POST detalle, poderes de cajero).

## Ventana
1. Snapshot de Neon + `pg_dump -t usuario_perfil -t inventario_detalleinventario`.
2. Deploy a Render (código nuevo, sin tráfico aún si es posible).
3. `python manage.py migrate usuario inventario` (o `migrate` completo).
4. Verificación solo-lectura:
   - `SELECT rol, COUNT(*) FROM usuario_perfil GROUP BY rol;` (staff → admin, resto cajero).
   - `SELECT column_name FROM information_schema.columns WHERE table_name='usuario_perfil';`
   - Login staff + encargado + cajero; venta atómica de $1 y su reversión; `POST /api/detalleventa/` → 410.
5. Humo frontend: login por rol, vender, reporte (encargado), alta de cajero.

## Rollback
- `migrate usuario 0001` + `migrate inventario 0006` (reversa del backfill incluida), o restore del snapshot.
- El código anterior es compatible hacia atrás: ignora `rol` (default BD `'cajero'`) y no usa PROTECT a nivel SQL.
- Reabrir tráfico y comunicar.
