"""Fase 3: PROTECT anti-huérfanos, deprecación legacy, contención de stock.

Nota honesta sobre concurrencia: la suite corre en SQLite `:memory:`,
donde cada hilo abre su propia BD vacía, así que un test de threads real
no es viable aquí (exigiría staging contra Neon/Postgres). En su lugar se
fija el invariante con contención secuencial: el segundo competidor debe
fallar con 400 y el stock nunca queda negativo. Los locks
(`select_for_update` en venta/producto/detalles) quedan cubiertos por
cobertura en cada operación.
"""

import pytest
from decimal import Decimal
from django.db.models.deletion import ProtectedError

from inventario.models import DetalleInventario, MovimientoInventario
from inventario.services.detalle_inventario_service import DetalleInventarioService
from ventas.models import detalleVenta, venta
from ventas.services.detalleventa_service import DetalleVentaService
from ventas.services.ventas_services import VentaService
from tests.factories import (
    InventarioFactory,
    MetodoPagoFactory,
    ProductoFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil


def _ctx(stock=10, precio=Decimal("100.00")):
    suc = SucursalFactory()
    inv = InventarioFactory(id_sucursal=suc)
    prod = ProductoFactory(precio_venta=precio)
    DetalleInventarioService().create(
        {
            "id_producto": prod.id,
            "id_inventario": inv.id,
            "cantidad": stock,
            "tipo_movimiento": "ENTRADA",
            "razon": "Compra",
        }
    )
    u = UserFactory()
    Perfil.objects.create(usuario=u, id_sucursal=suc, rol="encargado")
    mp = MetodoPagoFactory()
    v = VentaService().create(
        {"id_usuario": u.id, "id_inventario": inv.id, "id_metodoPago": mp.id}
    )
    return suc, inv, prod, u, mp, v


@pytest.mark.django_db
class TestProtectAntiHuerfanos:
    def test_borrado_orm_directo_detalle_bloqueado(self):
        _, _, prod, u, _, v = _ctx()
        det = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 2},
            user=u,
        )
        det_obj = detalleVenta.objects.get(id=det["id"])
        with pytest.raises(ProtectedError):
            det_obj.delete()
        # Nada se corrompió: detalle, salida y stock intactos
        assert detalleVenta.objects.filter(id=det["id"]).exists()
        assert DetalleInventario.objects.filter(id_detalle_venta_id=det["id"]).exists()

    def test_borrado_orm_directo_venta_bloqueado(self):
        _, _, prod, u, _, v = _ctx()
        DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 2},
            user=u,
        )
        with pytest.raises(ProtectedError):
            venta.objects.get(id=v["id"]).delete()
        assert venta.objects.filter(id=v["id"]).exists()

    def test_borrado_por_servicio_sigue_funcionando(self):
        _, inv, prod, u, _, v = _ctx()
        DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 2},
            user=u,
        )
        VentaService().delete(v["id"])
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 10
        assert (
            MovimientoInventario.objects.filter(
                tipo=MovimientoInventario.TipoMovimiento.SALIDA
            ).count()
            == 0
        )

    def test_update_venta_eliminada_404(self):
        from unittest import mock

        _, _, prod, u, _, v = _ctx()
        det = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 2},
            user=u,
        )
        with mock.patch("ventas.models.venta.objects") as mobj:
            mobj.select_for_update.return_value.get.side_effect = (
                venta.DoesNotExist()
            )
            from repository.exceptions import NotFoundError

            with pytest.raises(NotFoundError, match="Venta con id"):
                DetalleVentaService().update(det["id"], {"cantidad": 3}, user=u)


@pytest.mark.django_db
class TestContencionStock:
    def test_segundo_competidor_falla_y_stock_no_negativo(self):
        suc, inv, prod, u, mp, v1 = _ctx(stock=5)
        DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v1["id"], "cantidad": 5},
            user=u,
        )
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 0
        v2 = VentaService().create(
            {"id_usuario": u.id, "id_inventario": inv.id, "id_metodoPago": mp.id}
        )
        with pytest.raises(ValueError, match="disponible|Stock"):
            DetalleVentaService().create(
                {"id_producto": prod.id, "id_venta": v2["id"], "cantidad": 1},
                user=u,
            )
        # Al liberar stock (5 -> 3), el competidor entra exacto
        d1 = detalleVenta.objects.get(id_venta_id=v1["id"])
        DetalleVentaService().update(d1.id, {"cantidad": 3}, user=u)
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 2
        DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v2["id"], "cantidad": 2},
            user=u,
        )
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 0

    def test_ajuste_mas_alla_del_stock_falla(self):
        _, inv, prod, u, _, v = _ctx(stock=5)
        det = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 2},
            user=u,
        )
        with pytest.raises(ValueError, match="insuficiente"):
            DetalleVentaService().update(det["id"], {"cantidad": 99}, user=u)
        assert DetalleInventarioService().get_stock(prod.id, inv.id) == 3
