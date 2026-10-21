"""Integración: los puntos de escritura de inventario emiten/resuelven alertas.

Usa transaction=True para que los callbacks on_commit se ejecuten de verdad.
"""

import pytest

from inventario.services.detalle_inventario_service import DetalleInventarioService
from notifications.models import Notification
from notifications.services import stock_alerts
from tests.factories import (
    InventarioFactory,
    MetodoPagoFactory,
    ProductoFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil
from ventas.services.detalle_venta_service import DetalleVentaService
from ventas.services.venta_service import VentaService


def _ctx():
    suc = SucursalFactory()
    inv = InventarioFactory(id_sucursal=suc)
    prod = ProductoFactory()
    user = UserFactory()
    Perfil.objects.create(usuario=user, id_sucursal=suc)
    return suc, inv, prod, user


def _entrada(prod, inv, qty):
    return DetalleInventarioService().create(
        {
            "id_producto": prod.id,
            "id_inventario": inv.id,
            "cantidad": qty,
            "tipo_movimiento": "ENTRADA",
            "razon": "Compra",
        }
    )


@pytest.mark.django_db(transaction=True)
class TestHooksInventario:
    def test_create_entrada_baja_emite_low(self):
        suc, inv, prod, user = _ctx()
        _entrada(prod, inv, 3)
        alertas = Notification.objects.filter(
            destinatario_id=user.id, resuelta_en__isnull=True
        )
        assert alertas.count() == 1
        assert alertas.first().tipo == "warning"

    def test_create_entrada_sana_no_emite(self):
        suc, inv, prod, user = _ctx()
        _entrada(prod, inv, 50)
        assert Notification.objects.count() == 0

    def test_update_reevalua(self):
        suc, inv, prod, user = _ctx()
        det = _entrada(prod, inv, 50)
        assert Notification.objects.count() == 0
        DetalleInventarioService().update(det["id"], {"cantidad": 2})
        assert (
            Notification.objects.filter(
                destinatario_id=user.id, tipo="warning", resuelta_en__isnull=True
            ).count()
            == 1
        )

    def test_bulk_create_reevalua(self):
        suc, inv, prod, user = _ctx()
        DetalleInventarioService().bulk_create(
            {
                "id_inventario": inv.id,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
                "items": [{"id_producto": prod.id, "cantidad": 4}],
            }
        )
        assert (
            Notification.objects.filter(
                destinatario_id=user.id, tipo="warning", resuelta_en__isnull=True
            ).count()
            == 1
        )

    def test_venta_y_cancelacion_generan_y_resuelven(self):
        suc, inv, prod, user = _ctx()
        _entrada(prod, inv, 10)
        mp = MetodoPagoFactory()
        v = VentaService().create(
            {"id_usuario": user.id, "id_inventario": inv.id, "id_metodo_pago": mp.id}
        )
        DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 10}, user=user
        )
        assert (
            Notification.objects.filter(
                destinatario_id=user.id, tipo="error", resuelta_en__isnull=True
            ).count()
            == 1
        )
        VentaService().delete(v["id"])
        assert (
            Notification.objects.filter(
                destinatario_id=user.id, resuelta_en__isnull=True
            ).count()
            == 0
        )

    def test_fallo_de_notificacion_no_revierte_inventario(self, monkeypatch):
        suc, inv, prod, user = _ctx()

        def _boom(pid, iid):
            raise RuntimeError("apagón de notificaciones")

        monkeypatch.setattr(stock_alerts, "evaluar_stock", _boom)
        det = _entrada(prod, inv, 7)
        assert det["cantidad"] == 7
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 7
        assert Notification.objects.count() == 0
