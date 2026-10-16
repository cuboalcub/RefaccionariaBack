"""Pruebas de la migración 0002_notification_persistente (respaldo + sustitución).

Estrategia: la DB de test arranca en latest; cada prueba retrocede
notifications a 0001 con MigrationExecutor, prepara el escenario, avanza a
0002 y verifica. Todas dejan la DB en latest y sin tabla legacy, para no
contaminar otras pruebas. Nada toca Neon/Render (settings_test: sqlite).
"""

import pytest
from django.core.management import call_command
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor

from tests.factories import ProductoFactory, SucursalFactory, UserFactory

MIG_0001 = [("notifications", "0001_initial")]
MIG_0002 = [("notifications", "0002_notification_persistente")]
LEGACY = "notifications_notification_legacy"
NUEVA = "notifications_notification"
COLUMNAS_VIEJAS = {"id", "tipo", "mensaje", "leido", "creado_en", "producto_id"}
COLUMNAS_NUEVAS = {
    "id", "destinatario_id", "tipo", "titulo", "mensaje", "leida",
    "creada_en", "resuelta_en", "ref_producto_id", "ref_sucursal_id",
    "ref_inventario_id", "stock",
}


def _migrar(objetivos):
    MigrationExecutor(connection).migrate(objetivos)


def _modelo_viejo():
    estado = MigrationExecutor(connection).loader.project_state(
        ("notifications", "0001_initial")
    )
    return estado.apps.get_model("notifications", "Notification")


def _columnas(tabla):
    with connection.cursor() as cursor:
        return {
            f.name
            for f in connection.introspection.get_table_description(cursor, tabla)
        }


def _tablas():
    with connection.cursor() as cursor:
        return set(connection.introspection.table_names(cursor))


def _limpiar_legacy():
    with connection.cursor() as cursor:
        cursor.execute(f'DROP TABLE IF EXISTS "{LEGACY}"')


def _ir_a_0001():
    _limpiar_legacy()
    _migrar(MIG_0001)


def _volver_a_latest():
    # Deja la DB en latest y sin legacy: se retira cualquier respaldo
    # previo (si no, el guard abortaría), se avanza (recrea el respaldo
    # desde las filas viejas) y se retira para aislar otras pruebas.
    _limpiar_legacy()
    _migrar(MIG_0002)
    _limpiar_legacy()


def _sembrar_viejas(n=4):
    Vieja = _modelo_viejo()
    prod = ProductoFactory()
    filas = [
        Vieja.objects.create(
            tipo="AGOTADO" if i % 2 else "BAJO_STOCK",
            mensaje=f"Vieja {i}",
            leido=bool(i % 2),
            producto_id=prod.id,
        )
        for i in range(n)
    ]
    return prod, [(f.tipo, f.mensaje, f.leido, f.producto_id) for f in filas]


def _leer_legacy():
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT tipo, mensaje, leido, producto_id FROM "{LEGACY}" ORDER BY id'
        )
        return [(t, m, bool(l), p) for t, m, l, p in cursor.fetchall()]


@pytest.mark.django_db(transaction=True)
class TestMigracionRespaldo:
    def test_forward_preserva_filas_y_crea_esquema_nuevo(self):
        _ir_a_0001()
        _, valores = _sembrar_viejas(4)
        _migrar(MIG_0002)
        try:
            assert _leer_legacy() == valores
            assert _columnas(NUEVA) == COLUMNAS_NUEVAS
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT COUNT(*) FROM "{NUEVA}"')
                assert cursor.fetchone()[0] == 0
        finally:
            _limpiar_legacy()

    def test_forward_sin_filas_no_crea_legacy(self):
        _ir_a_0001()
        _migrar(MIG_0002)
        try:
            assert LEGACY not in _tablas()
            assert _columnas(NUEVA) == COLUMNAS_NUEVAS
        finally:
            _limpiar_legacy()

    def test_reintento_tras_fallo_deja_todo_como_antes(self):
        _ir_a_0001()
        _, valores = _sembrar_viejas(2)
        # Fallo simulado: legacy preexistente -> la migración aborta.
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE TABLE "{LEGACY}" (id INTEGER PRIMARY KEY)')
        with pytest.raises(Exception, match="ya existe"):
            _migrar(MIG_0002)
        try:
            # Nada cambió: tabla vieja intacta, sin esquema nuevo.
            assert _columnas(NUEVA) == COLUMNAS_VIEJAS
            Vieja = _modelo_viejo()
            assert Vieja.objects.count() == 2
            # Reintento tras retirar el bloqueo: éxito y respaldo correcto.
            _limpiar_legacy()
            _migrar(MIG_0002)
            assert _leer_legacy() == valores
            assert _columnas(NUEVA) == COLUMNAS_NUEVAS
        finally:
            _limpiar_legacy()

    def test_legacy_previa_aborta_sin_sobrescribir(self):
        _ir_a_0001()
        _sembrar_viejas(1)
        with connection.cursor() as cursor:
            cursor.execute(
                f'CREATE TABLE "{LEGACY}" AS SELECT * FROM "{NUEVA}" WHERE FALSE'
            )
            cursor.execute(f'SELECT COUNT(*) FROM "{LEGACY}"')
            assert cursor.fetchone()[0] == 0
        try:
            with pytest.raises(Exception, match="ya existe"):
                _migrar(MIG_0002)
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT COUNT(*) FROM "{LEGACY}"')
                assert cursor.fetchone()[0] == 0
            assert _columnas(NUEVA) == COLUMNAS_VIEJAS
        finally:
            _volver_a_latest()

    def test_reversa_restaura_y_conserva_respaldo(self):
        _ir_a_0001()
        _, valores = _sembrar_viejas(3)
        _migrar(MIG_0002)
        assert _leer_legacy() == valores
        _migrar(MIG_0001)
        try:
            # Filas devueltas a la tabla vieja recreada...
            Vieja = _modelo_viejo()
            restauradas = [
                (f.tipo, f.mensaje, f.leido, f.producto_id)
                for f in Vieja.objects.order_by("id")
            ]
            assert restauradas == valores
            # ...y respaldo conservado (no se elimina automáticamente).
            assert _leer_legacy() == valores
        finally:
            _volver_a_latest()

    def test_instalacion_limpia_sin_legacy_y_con_constraint(self):
        # La DB de test ya es instalación limpia en latest.
        assert LEGACY not in _tablas()
        assert _columnas(NUEVA) == COLUMNAS_NUEVAS
        from notifications.models import Notification

        user = UserFactory()
        prod = ProductoFactory()
        suc = SucursalFactory()
        Notification.objects.create(
            destinatario=user, tipo="warning", titulo="T", mensaje="M",
            ref_producto=prod, ref_sucursal=suc,
        )
        with pytest.raises(IntegrityError):
            Notification.objects.create(
                destinatario=user, tipo="warning", titulo="T2", mensaje="M2",
                ref_producto=prod, ref_sucursal=suc,
            )


class TestSinCambiosPendientes:
    @pytest.mark.django_db
    def test_makemigrations_check(self):
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)
