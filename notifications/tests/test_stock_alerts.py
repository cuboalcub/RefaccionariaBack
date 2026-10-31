"""Alertas LOW_STOCK/OUT_OF_STOCK: umbrales, ciclo, dedup, destinatarios."""

import threading

import pytest

from inventario.services.movimiento_inventario_service import MovimientoInventarioService
from notifications.models import Notification
from notifications.services import stock_alerts
from notifications.services.stock_alerts import evaluar_stock, programar_evaluacion
from tests.factories import (
    ProductoFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil

UMBRAL = 10


def _entrada(prod, inv, qty, razon="Compra"):
    return MovimientoInventarioService().create(
        {
            "id_producto": prod.id,
            "id_sucursal": inv.id,
            "cantidad": qty,
            "tipo_movimiento": "ENTRADA",
            "razon": razon,
        }
    )


def _ctx_con_usuarios(settings):
    settings.NOTIFICATIONS_LOW_STOCK_THRESHOLD = UMBRAL
    suc = SucursalFactory(nombre_sucursal="Matriz")
    inv = suc
    prod = ProductoFactory()
    u1 = UserFactory()
    u2 = UserFactory()
    Perfil.objects.create(usuario=u1, id_sucursal=suc)
    Perfil.objects.create(usuario=u2, id_sucursal=suc)
    return suc, inv, prod, u1, u2


def _activas(prod, suc, tipo=None):
    qs = Notification.objects.filter(
        ref_producto_id=prod.id, ref_sucursal_id=suc.id, resuelta_en__isnull=True
    )
    if tipo is not None:
        qs = qs.filter(tipo=tipo)
    return qs


@pytest.mark.django_db
class TestUmbrales:
    def test_out_con_stock_cero(self, settings):
        suc, inv, prod, u1, u2 = _ctx_con_usuarios(settings)
        res = evaluar_stock(prod.id, inv.id)
        assert res["stock"] == 0
        assert res["tipo"] == Notification.Tipo.OUT_OF_STOCK
        assert _activas(prod, suc).count() == 2
        n = _activas(prod, suc).first()
        assert n.tipo == "error"
        assert n.leida is False
        assert n.creada_en is not None
        assert n.stock == 0

    @pytest.mark.parametrize("qty", [1, 9])
    def test_low_entre_1_y_umbral(self, settings, qty):
        suc, inv, prod, u1, u2 = _ctx_con_usuarios(settings)
        _entrada(prod, inv, qty)
        res = evaluar_stock(prod.id, inv.id)
        assert res["stock"] == qty
        assert res["tipo"] == Notification.Tipo.LOW_STOCK
        assert _activas(prod, suc, "warning").count() == 2

    def test_sano_en_el_umbral(self, settings):
        suc, inv, prod, u1, u2 = _ctx_con_usuarios(settings)
        _entrada(prod, inv, UMBRAL)
        res = evaluar_stock(prod.id, inv.id)
        assert res["stock"] == UMBRAL
        assert res["tipo"] is None
        assert res["creadas"] == 0
        assert _activas(prod, suc).count() == 0


@pytest.mark.django_db
class TestCiclo:
    def test_transicion_low_a_out_resuelve_anterior(self, settings):
        suc, inv, prod, u1, u2 = _ctx_con_usuarios(settings)
        _entrada(prod, inv, 5)
        evaluar_stock(prod.id, inv.id)
        assert _activas(prod, suc, "warning").count() == 2
        # Venta simulada: SALIDA de 5 deja stock 0.
        MovimientoInventarioService().create(
            {
                "id_producto": prod.id,
                "id_sucursal": inv.id,
                "cantidad": 5,
                "tipo_movimiento": "SALIDA",
                "razon": "Venta",
            }
        )
        res = evaluar_stock(prod.id, inv.id)
        assert res["tipo"] == Notification.Tipo.OUT_OF_STOCK
        assert _activas(prod, suc, "warning").count() == 0
        assert _activas(prod, suc, "error").count() == 2
        resueltas = Notification.objects.filter(
            ref_producto_id=prod.id,
            ref_sucursal_id=suc.id,
            tipo="warning",
            resuelta_en__isnull=False,
        )
        assert resueltas.count() == 2

    def test_recuperacion_resuelve_sin_borrar(self, settings):
        suc, inv, prod, u1, u2 = _ctx_con_usuarios(settings)
        evaluar_stock(prod.id, inv.id)
        assert _activas(prod, suc).count() == 2
        _entrada(prod, inv, 20)
        res = evaluar_stock(prod.id, inv.id)
        assert res["tipo"] is None
        assert res["resueltas"] == 2
        assert _activas(prod, suc).count() == 0
        # Historial conservado.
        assert (
            Notification.objects.filter(
                ref_producto_id=prod.id, ref_sucursal_id=suc.id
            ).count()
            == 2
        )

    def test_reincidencia_crea_nueva(self, settings):
        suc, inv, prod, u1, u2 = _ctx_con_usuarios(settings)
        evaluar_stock(prod.id, inv.id)
        _entrada(prod, inv, 20)
        evaluar_stock(prod.id, inv.id)
        _entrada(prod, inv, 1)
        MovimientoInventarioService().create(
            {
                "id_producto": prod.id,
                "id_sucursal": inv.id,
                "cantidad": 21,
                "tipo_movimiento": "SALIDA",
                "razon": "Venta",
            }
        )
        evaluar_stock(prod.id, inv.id)
        total = Notification.objects.filter(
            ref_producto_id=prod.id, ref_sucursal_id=suc.id
        ).count()
        assert total == 4
        assert _activas(prod, suc, "error").count() == 2

    def test_dedup_segunda_evaluacion_no_duplica(self, settings):
        suc, inv, prod, u1, u2 = _ctx_con_usuarios(settings)
        evaluar_stock(prod.id, inv.id)
        res = evaluar_stock(prod.id, inv.id)
        assert res["creadas"] == 0
        assert _activas(prod, suc).count() == 2

    def test_inventario_inexistente_devuelve_none(self, settings):
        settings.NOTIFICATIONS_LOW_STOCK_THRESHOLD = UMBRAL
        assert evaluar_stock(1, 999999) is None


@pytest.mark.django_db
class TestDestinatarios:
    def test_solo_usuarios_de_la_sucursal(self, settings):
        suc, inv, prod, u1, u2 = _ctx_con_usuarios(settings)
        otra = SucursalFactory()
        otro_user = UserFactory()
        Perfil.objects.create(usuario=otro_user, id_sucursal=otra)
        sin_sucursal = UserFactory()
        evaluar_stock(prod.id, inv.id)
        assert Notification.objects.filter(destinatario_id=u1.id).count() == 1
        assert Notification.objects.filter(destinatario_id=u2.id).count() == 1
        assert Notification.objects.filter(destinatario_id=otro_user.id).count() == 0
        assert Notification.objects.filter(destinatario_id=sin_sucursal.id).count() == 0

    def test_sin_usuarios_no_crea(self, settings):
        settings.NOTIFICATIONS_LOW_STOCK_THRESHOLD = UMBRAL
        suc = SucursalFactory()
        inv = suc
        prod = ProductoFactory()
        res = evaluar_stock(prod.id, inv.id)
        assert res["creadas"] == 0
        assert Notification.objects.count() == 0

    def test_nombre_sucursal_usa_ubicacion_si_no_hay_nombre(self, settings):
        settings.NOTIFICATIONS_LOW_STOCK_THRESHOLD = UMBRAL
        suc = SucursalFactory(nombre_sucursal="", ubicacion="Norte 123")
        inv = suc
        prod = ProductoFactory()
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        evaluar_stock(prod.id, inv.id)
        n = Notification.objects.get(destinatario_id=u.id)
        assert "Norte 123" in n.mensaje

    def test_sucursal_sin_nombre_usa_ubicacion_en_mensaje(self, settings):
        settings.NOTIFICATIONS_LOW_STOCK_THRESHOLD = UMBRAL
        suc = SucursalFactory(nombre_sucursal="Sur")
        inv = suc
        prod = ProductoFactory(nombre="Bujía X")
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        evaluar_stock(prod.id, inv.id)
        n = Notification.objects.get(destinatario_id=u.id)
        assert "Bujía X" in n.mensaje
        assert "Sur" in n.mensaje


@pytest.mark.django_db(transaction=True)
class TestProgramar:
    def test_ejecuta_despues_del_commit(self, settings):
        suc, inv, prod, u1, u2 = _ctx_con_usuarios(settings)
        programar_evaluacion(prod.id, inv.id)
        assert _activas(prod, suc, "error").count() == 2

    def test_fallo_no_propaga_y_queda_en_log(self, settings, monkeypatch, caplog):
        suc, inv, prod, u1, u2 = _ctx_con_usuarios(settings)

        def _boom(pid, iid):
            raise RuntimeError("falla inventario")

        monkeypatch.setattr(stock_alerts, "evaluar_stock", _boom)
        with caplog.at_level("ERROR"):
            programar_evaluacion(prod.id, inv.id)
        assert _activas(prod, suc).count() == 0
        assert any("no se pudo evaluar alerta" in r.message for r in caplog.records)


@pytest.mark.django_db(transaction=True)
class TestConcurrencia:
    def test_evaluaciones_simultaneas_no_duplican(self, settings):
        settings.NOTIFICATIONS_LOW_STOCK_THRESHOLD = UMBRAL
        suc = SucursalFactory()
        inv = suc
        prod = ProductoFactory()
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        errores = []

        def _run():
            for _ in range(5):
                try:
                    evaluar_stock(prod.id, inv.id)
                    return
                except Exception as e:  # noqa: BLE001 - sqlite bloquea escrituras concurrentes; se reintenta
                    errores.append(e)

        hilos = [threading.Thread(target=_run) for _ in range(4)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        assert (
            Notification.objects.filter(
                ref_producto_id=prod.id,
                ref_sucursal_id=suc.id,
                resuelta_en__isnull=True,
            ).count()
            == 1
        )
