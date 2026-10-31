"""Contrato nuevo de Venta: id_sucursal directo, estado completada/cancelada,
id_cliente opcional y cancelación suave con restitución de stock."""

import pytest
from decimal import Decimal

from inventario.services.movimiento_inventario_service import MovimientoInventarioService
from ventas.models import Venta
from ventas.repositories.venta_repository import VentaRepository
from ventas.services.detalle_venta_service import DetalleVentaService
from ventas.services.venta_service import VentaService
from tests.factories import (
    MetodoPagoFactory,
    ProductoFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil
from clientes.models import Cliente


def _tienda(cantidad_entrada=10, precio=Decimal("100.00")):
    suc = SucursalFactory()
    inv = suc
    prod = ProductoFactory(precio_venta=precio)
    MovimientoInventarioService().create(
        {
            "id_producto": prod.id,
            "id_sucursal": inv.id,
            "cantidad": cantidad_entrada,
            "tipo_movimiento": "ENTRADA",
            "razon": "Compra",
        }
    )
    u = UserFactory()
    Perfil.objects.create(usuario=u, id_sucursal=suc)
    mp = MetodoPagoFactory()
    return suc, inv, prod, u, mp


def _venta(user, suc, mp, detalles=None):
    data = {
        "id_usuario": user.id,
        "id_sucursal": suc.id,
        "id_metodo_pago": mp.id,
    }
    if detalles:
        data["detalles"] = detalles
    return VentaService().crear_venta_completa(data) if detalles else VentaService().create(data)


@pytest.mark.django_db
class TestVentaSucursalYCliente:
    def test_create_con_id_sucursal_directo(self):
        suc, inv, prod, u, mp = _tienda()
        res = _venta(u, suc, mp)
        assert res["id_sucursal"] == suc.id
        assert "id_inventario" not in res

    def test_id_inventario_deprecado_exige_id_sucursal(self):
        suc, inv, prod, u, mp = _tienda()
        with pytest.raises(ValueError, match="id_sucursal"):
            VentaService().create(
                {
                    "id_usuario": u.id,
                    "id_inventario": inv.id,
                    "id_metodo_pago": mp.id,
                }
            )

    def test_legacy_id_sucursal_inexistente_400(self):
        _, _, _, u, mp = _tienda()
        with pytest.raises(ValueError, match="no encontrada"):
            VentaService().create(
                {"id_usuario": u.id, "id_metodo_pago": mp.id, "id_sucursal": 999999}
            )

    def test_id_cliente_opcional(self):
        suc, _, _, u, mp = _tienda()
        res = _venta(u, suc, mp)
        assert res["id_cliente"] is None

    def test_id_cliente_valido_e_inexistente(self):
        suc, _, _, u, mp = _tienda()
        cliente = Cliente.objects.create(
            id_sucursal=suc, nombre="Ana", apellido_paterno="Ruiz", telefono="55"
        )
        res = VentaService().create(
            {
                "id_usuario": u.id,
                "id_sucursal": suc.id,
                "id_metodo_pago": mp.id,
                "id_cliente": cliente.id,
            }
        )
        assert res["id_cliente"] == cliente.id
        with pytest.raises(ValueError, match="Cliente con id 999999 no encontrado"):
            VentaService().create(
                {
                    "id_usuario": u.id,
                    "id_sucursal": suc.id,
                    "id_metodo_pago": mp.id,
                    "id_cliente": 999999,
                }
            )

    def test_id_cliente_en_crear_venta_completa(self):
        suc, _, prod, u, mp = _tienda()
        cliente = Cliente.objects.create(
            id_sucursal=suc, nombre="Beto", apellido_paterno="Lopez", telefono="55"
        )
        res = VentaService().crear_venta_completa(
            {
                "id_usuario": u.id,
                "id_sucursal": suc.id,
                "id_metodo_pago": mp.id,
                "id_cliente": cliente.id,
                "detalles": [{"producto": prod.id, "cantidad": 2}],
            }
        )
        assert res["id_cliente"] == cliente.id
        assert res["estado"] == "completada"
        assert Decimal(res["total"]) == Decimal("200.00")


@pytest.mark.django_db
class TestCancelacionSuave:
    def test_delete_cancela_revierte_stock_y_mantiene_detalle(self):
        suc, inv, prod, u, mp = _tienda()
        v = _venta(u, suc, mp, detalles=[{"producto": prod.id, "cantidad": 2}])
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 8

        res = VentaService().delete(v["id"])
        assert res["message"] == "venta cancelada exitosamente"
        assert res["estado"] == "cancelada"
        venta = Venta.objects.get(id=v["id"])
        assert venta.estado == "cancelada"
        # detalle sobrevive, el stock vuelve
        assert venta.detalleventa_set.count() == 1
        assert venta.total == Decimal("200.00")
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 10

    def test_delete_idempotente_no_duplica_reversion(self):
        suc, inv, prod, u, mp = _tienda()
        v = _venta(u, suc, mp, detalles=[{"producto": prod.id, "cantidad": 3}])
        VentaService().delete(v["id"])
        res = VentaService().delete(v["id"])
        assert res["message"] == "venta ya estaba cancelada"
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 10

    def test_put_estado_cancelada_revierte_stock(self):
        suc, inv, prod, u, mp = _tienda()
        v = _venta(u, suc, mp, detalles=[{"producto": prod.id, "cantidad": 2}])
        res = VentaService().update(v["id"], {"estado": "cancelada"})
        assert res["estado"] == "cancelada"
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 10
        # idempotente: segunda vez sin doble reversión
        res2 = VentaService().update(v["id"], {"estado": "cancelada"})
        assert res2["estado"] == "cancelada"
        assert MovimientoInventarioService().get_stock(prod.id, inv.id) == 10

    def test_put_estado_invalido_400(self):
        suc, _, _, u, mp = _tienda()
        v = _venta(u, suc, mp)
        with pytest.raises(ValueError, match="estado inválido"):
            VentaService().update(v["id"], {"estado": "pendiente"})

    def test_put_no_reactiva_cancelada(self):
        suc, _, _, u, mp = _tienda()
        v = _venta(u, suc, mp)
        VentaService().update(v["id"], {"estado": "cancelada"})
        with pytest.raises(ValueError, match="No se puede reactivar"):
            VentaService().update(v["id"], {"estado": "completada"})

    def test_put_id_cliente_actualiza(self):
        suc, _, _, u, mp = _tienda()
        v = _venta(u, suc, mp)
        cliente = Cliente.objects.create(
            id_sucursal=suc, nombre="Ana", apellido_paterno="Ruiz", telefono="55"
        )
        res = VentaService().update(v["id"], {"id_cliente": cliente.id})
        assert res["id_cliente"] == cliente.id
        with pytest.raises(ValueError, match="Cliente con id"):
            VentaService().update(v["id"], {"id_cliente": 999999})

    def test_ticket_y_detalle_en_venta_cancelada(self):
        suc, inv, prod, u, mp = _tienda()
        v = _venta(u, suc, mp, detalles=[{"producto": prod.id, "cantidad": 1}])
        VentaService().delete(v["id"])
        from ventas.services.venta_ticket_service import VentaTicketService

        t = VentaTicketService().get_ticket(v["id"])
        assert t["folio"] == v["id"]
        # los detalles no admiten cambios sobre venta cancelada
        with pytest.raises(ValueError, match="cancelada"):
            DetalleVentaService().create(
                {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 1}, user=u
            )

    def test_put_cambia_metodo_pago_en_cancelada(self):
        suc, _, _, u, mp = _tienda()
        v = _venta(u, suc, mp)
        VentaService().update(v["id"], {"estado": "cancelada"})
        mp2 = MetodoPagoFactory(tipo="TARJETA", descripcion="Tarjeta")
        VentaService().update(
            v["id"], {"estado": "cancelada", "id_metodo_pago": mp2.id}
        )
        assert Venta.objects.get(id=v["id"]).id_metodo_pago_id == mp2.id


@pytest.mark.django_db
class TestVentaCanceladaBloqueaDetalles:
    def _venta_cancelada_con_detalle(self):
        suc, inv, prod, u, mp = _tienda()
        v = _venta(u, suc, mp, detalles=[{"producto": prod.id, "cantidad": 2}])
        det = DetalleVentaService().get_by_id(
            Venta.objects.get(id=v["id"]).detalleventa_set.first().id
        )
        VentaService().delete(v["id"])
        return suc, inv, prod, u, v, det

    def test_update_detalle_lanza(self):
        _, _, prod, u, v, det = self._venta_cancelada_con_detalle()
        with pytest.raises(ValueError, match="cancelada"):
            DetalleVentaService().update(det["id"], {"cantidad": 1}, user=u)

    def test_delete_detalle_lanza(self):
        _, _, prod, u, v, det = self._venta_cancelada_con_detalle()
        with pytest.raises(ValueError, match="cancelada"):
            DetalleVentaService().delete(det["id"], user=u)


@pytest.mark.django_db
class TestRamasDefensivasNuevas:
    def test_perfil_fallback_query_explota(self):
        # Perfil.cacheado ausente; la query del fallback revienta -> warning sucursal
        from unittest import mock

        from types import SimpleNamespace

        class _Boom:
            @property
            def id_sucursal_id(self):
                raise Exception("boom")

        with mock.patch("usuario.models.Perfil") as mperfil:
            mperfil.objects.filter.return_value.first.return_value = _Boom()
            with pytest.raises(ValueError, match="no tiene una sucursal"):
                VentaService()._sucursal_del_usuario(SimpleNamespace(id=1, perfil=None))
        # la misma query exitosa cubre la rama feliz del fallback
        with mock.patch("usuario.models.Perfil") as mperfil:
            mperfil.objects.filter.return_value.first.return_value = SimpleNamespace(
                id_sucursal_id=42
            )
            assert VentaService()._sucursal_del_usuario(SimpleNamespace(id=1, perfil=None)) == 42

    def test_update_venta_inexistente_not_found(self):
        from repository.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            VentaService().update(999999, {"estado": "cancelada"})

    def test_update_detalle_repo_sin_venta(self, monkeypatch):
        from types import SimpleNamespace

        from repository.exceptions import NotFoundError

        suc, inv, prod, u, mp = _tienda()
        v = _venta(u, suc, mp, detalles=[{"producto": prod.id, "cantidad": 1}])
        det_id = Venta.objects.get(id=v["id"]).detalleventa_set.first().id
        svc = DetalleVentaService()
        monkeypatch.setattr(
            svc, "venta_repo", SimpleNamespace(get_by_id=lambda _id: None)
        )
        with pytest.raises(NotFoundError, match="Venta con id"):
            svc.update(det_id, {"cantidad": 1})


@pytest.mark.django_db
class TestReporteExcluyeCanceladas:
    def test_repo_filtra_estado(self):
        from django.utils import timezone

        suc, inv, prod, u, mp = _tienda()
        v_ok = _venta(u, suc, mp, detalles=[{"producto": prod.id, "cantidad": 1}])
        v_can = _venta(u, suc, mp, detalles=[{"producto": prod.id, "cantidad": 2}])
        VentaService().delete(v_can["id"])

        repo = VentaRepository()
        ahora = timezone.localtime()
        ini = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        fin = ini + __import__("datetime").timedelta(days=1)
        ids = [x.id for x in repo.get_ventas_por_rango(ini, fin)]
        assert v_ok["id"] in ids
        assert v_can["id"] not in ids
        total = repo.get_total_ventas_por_rango(ini, fin)
        assert total == Decimal("100.00")
