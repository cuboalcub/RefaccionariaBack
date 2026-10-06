"""Tests extra ventas: cubre ramas restantes de services, ticket, reporte, views, controllers, repos y models."""

from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

import pytest
from django.contrib.auth.models import AnonymousUser

from inventario.services.detalle_inventario_service import DetalleInventarioService
from inventario.services.precio_sucursal_service import PrecioSucursalService
from repository.exceptions import NotFoundError
from usuario.models import Perfil
from ventas.models import Reporte, detalleVenta, venta
from ventas.repositories.detalleventa_repository import DetalleVentaRepository
from ventas.repositories.metodopago_repository import MetodoPagoRepository
from ventas.repositories.ventas_repository import VentaRepository
from ventas.services.detalleventa_service import DetalleVentaService
from ventas.services.metodopago_service import MetodoPagoService
from ventas.services.reporte_ventas_service import ReporteVentasService
from ventas.services.ventaTicket_service import VentaTicketService
from ventas.services.ventas_services import VentaService
from tests.factories import (
    InventarioFactory,
    MetodoPagoFactory,
    ProductoFactory,
    SucursalFactory,
    UserFactory,
)


# ---------------------------------------------------------------- helpers
def _legacy_venta(user, inv, mp):
    return VentaService().create(
        {"id_usuario": user.id, "id_inventario": inv.id, "id_metodoPago": mp.id}
    )


def _entrada(prod, inv, qty=10):
    DetalleInventarioService().create(
        {
            "id_producto": prod.id,
            "id_inventario": inv.id,
            "cantidad": qty,
            "tipo_movimiento": "ENTRADA",
            "razon": "Compra",
        }
    )


def _venta_con_stock(qty_venta=2, precio="100.00"):
    suc = SucursalFactory()
    inv = InventarioFactory(id_sucursal=suc)
    prod = ProductoFactory(precio_venta=Decimal(precio))
    _entrada(prod, inv)
    user = UserFactory()
    Perfil.objects.create(usuario=user, id_sucursal=suc)
    mp = MetodoPagoFactory()
    v = _legacy_venta(user, inv, mp)
    det = DetalleVentaService().create(
        {"id_producto": prod.id, "id_venta": v["id"], "cantidad": qty_venta}, user=user
    )
    return suc, inv, prod, user, mp, v, det


# ------------------------------------------------------- VentaService._to_dict
@pytest.mark.django_db
class TestVentaToDict:
    def test_sin_inventario_ni_relaciones(self):
        v = venta.objects.create(
            id_usuario=None, id_metodoPago=None, id_inventario=None, total=Decimal("0.00")
        )
        d = VentaService()._to_dict(v)
        assert d["id_inventario"] is None
        assert d["id_sucursal"] is None
        assert d["id_usuario"] is None
        assert d["id_metodoPago"] is None
        assert d["fecha"] is not None

    def test_id_sucursal_excepcion_devuelve_none(self):
        class _BadInv:
            id = 999

            @property
            def id_sucursal_id(self):
                raise Exception("boom")

        inst = SimpleNamespace(
            id=1,
            id_usuario=None,
            id_metodoPago=None,
            id_inventario=_BadInv(),
            total=Decimal("5.00"),
            fecha=None,
        )
        d = VentaService()._to_dict(inst)
        assert d["id_inventario"] == 999
        assert d["id_sucursal"] is None
        assert d["fecha"] is None


# ---------------------------------------------------------- VentaService.get_all
@pytest.mark.django_db
class TestVentaGetAll:
    def _dos_ventas(self):
        sa, sb = SucursalFactory(), SucursalFactory()
        ia, ib = InventarioFactory(id_sucursal=sa), InventarioFactory(id_sucursal=sb)
        u, mp = UserFactory(), MetodoPagoFactory()
        _legacy_venta(u, ia, mp)
        _legacy_venta(u, ib, mp)
        return sa, sb, ia, ib

    def test_paginado_ok(self):
        self._dos_ventas()
        r = VentaService().get_all(page=1, page_size=1)
        assert r["total"] == 2
        assert r["page"] == 1 and r["page_size"] == 1
        assert r["total_pages"] == 2
        assert len(r["results"]) == 1
        r2 = VentaService().get_all(page=2, page_size=1)
        assert len(r2["results"]) == 1
        assert r["results"][0]["id"] != r2["results"][0]["id"]

    def test_page_invalido(self):
        with pytest.raises(ValueError, match="enteros"):
            VentaService().get_all(page="abc")
        with pytest.raises(ValueError, match="enteros"):
            VentaService().get_all(page=1, page_size="x")

    def test_page_menor_1(self):
        with pytest.raises(ValueError, match=">= 1"):
            VentaService().get_all(page=0)
        with pytest.raises(ValueError, match=">= 1"):
            VentaService().get_all(page=1, page_size=0)

    def test_sucursal_invalida(self):
        with pytest.raises(ValueError, match="sucursal_id debe ser entero"):
            VentaService().get_all(sucursal_id="abc")

    def test_sucursal_no_encontrada(self):
        with pytest.raises(ValueError, match="no encontrada"):
            VentaService().get_all(sucursal_id=999999)

    def test_id_inventario_invalido(self):
        with pytest.raises(ValueError, match="id_inventario debe ser entero"):
            VentaService().get_all(id_inventario="zzz")

    def test_filtros(self):
        sa, sb, ia, ib = self._dos_ventas()
        solo_a = VentaService().get_all(sucursal_id=sa.id)
        assert len(solo_a) == 1 and solo_a[0]["id_sucursal"] == sa.id
        por_inv = VentaService().get_all(id_inventario=ib.id)
        assert len(por_inv) == 1 and por_inv[0]["id_inventario"] == ib.id
        pag = VentaService().get_all(page=1, page_size=10, sucursal_id=sb.id)
        assert pag["total"] == 1 and pag["sucursal_id"] == sb.id
        ambos = VentaService().get_all(
            page=1, page_size=10, sucursal_id=sa.id, id_inventario=ia.id
        )
        assert ambos["total"] == 1


# ------------------------------------------- VentaService._resolve_inventario
@pytest.mark.django_db
class TestResolveInventario:
    def test_staff_sin_sucursal_falla(self):
        u = UserFactory()
        with pytest.raises(ValueError, match="no tiene una sucursal"):
            VentaService()._resolve_inventario_for_user(u)

    def test_sucursal_sin_inventario_falla(self):
        suc = SucursalFactory()
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        with pytest.raises(ValueError, match="no tiene un inventario"):
            VentaService()._resolve_inventario_for_user(u)

    def test_multi_inventario_devuelve_primero(self):
        suc = SucursalFactory()
        i1, i2 = InventarioFactory(id_sucursal=suc), InventarioFactory(id_sucursal=suc)
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        inv = VentaService()._resolve_inventario_for_user(u)
        assert inv.id == min(i1.id, i2.id)

    def test_fallback_perfil_no_cacheado(self):
        # perfil existe en DB pero user.perfil no cacheado -> fallback por query
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        fresh = type(u).objects.get(id=u.id)
        assert VentaService()._resolve_inventario_for_user(fresh).id == inv.id

    def test_fallback_query_encuentra_perfil(self):
        # descriptor/perfil ausente pero query sí lo encuentra (línea 121)
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        bare = SimpleNamespace(id=u.id, perfil=None)
        assert VentaService()._resolve_inventario_for_user(bare).id == inv.id


# ---------------------------------------------------------- VentaService.create
@pytest.mark.django_db
class TestVentaCreateExtra:
    def test_sin_campos(self):
        with pytest.raises(ValueError, match="Faltan campos obligatorios"):
            VentaService().create({})

    def test_solo_usuario_sin_metodo(self):
        u = UserFactory()
        with pytest.raises(ValueError, match="id_metodoPago"):
            VentaService().create({"id_usuario": u.id})

    def test_sin_usuario_pide_auth(self):
        mp = MetodoPagoFactory()
        with pytest.raises(ValueError, match="id_usuario"):
            VentaService().create({"id_metodoPago": mp.id})

    def test_usuario_inexistente(self):
        mp = MetodoPagoFactory()
        with pytest.raises(ValueError, match="no encontrado"):
            VentaService().create({"id_usuario": 999999, "id_metodoPago": mp.id})

    def test_metodo_inexistente(self):
        u = UserFactory()
        with pytest.raises(ValueError, match="no encontrado"):
            VentaService().create({"id_usuario": u.id, "id_metodoPago": 999999,
                                   "id_inventario": 1})

    def test_inventario_inexistente_legacy(self):
        u, mp = UserFactory(), MetodoPagoFactory()
        with pytest.raises(ValueError, match="no encontrado"):
            VentaService().create(
                {"id_usuario": u.id, "id_metodoPago": mp.id, "id_inventario": 999999}
            )

    def test_legacy_sin_inventario(self):
        u, mp = UserFactory(), MetodoPagoFactory()
        with pytest.raises(ValueError, match="id_inventario"):
            VentaService().create({"id_usuario": u.id, "id_metodoPago": mp.id})

    def test_legacy_con_anonymous_user(self):
        u, inv, mp = UserFactory(), InventarioFactory(), MetodoPagoFactory()
        res = VentaService().create(
            {"id_usuario": u.id, "id_inventario": inv.id, "id_metodoPago": mp.id},
            user=AnonymousUser(),
        )
        assert res["id_usuario"] == u.id

    def test_staff_override_id_inventario(self):
        sa, sb = SucursalFactory(), SucursalFactory()
        InventarioFactory(id_sucursal=sa)
        inv_b = InventarioFactory(id_sucursal=sb)
        staff = UserFactory(is_staff=True)
        Perfil.objects.create(usuario=staff, id_sucursal=sa)
        mp = MetodoPagoFactory()
        res = VentaService().create(
            {"id_metodoPago": mp.id, "id_inventario": inv_b.id}, user=staff
        )
        assert res["id_inventario"] == inv_b.id

    def test_staff_override_inexistente(self):
        staff = UserFactory(is_staff=True)
        mp = MetodoPagoFactory()
        with pytest.raises(ValueError, match="no encontrado"):
            VentaService().create(
                {"id_metodoPago": mp.id, "id_inventario": 999999}, user=staff
            )

    def test_staff_sin_inventario_pide_explicito(self):
        staff = UserFactory(is_staff=True)
        mp = MetodoPagoFactory()
        with pytest.raises(ValueError, match="envíe id_inventario explícito"):
            VentaService().create({"id_metodoPago": mp.id}, user=staff)

    def test_normal_ignora_override_usa_su_sucursal(self):
        sa, sb = SucursalFactory(), SucursalFactory()
        inv_a = InventarioFactory(id_sucursal=sa)
        inv_b = InventarioFactory(id_sucursal=sb)
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=sa)
        mp = MetodoPagoFactory()
        res = VentaService().create(
            {"id_metodoPago": mp.id, "id_inventario": inv_b.id}, user=u
        )
        assert res["id_inventario"] == inv_a.id


# --------------------------------- DetalleVentaService precio / recalcular
@pytest.mark.django_db
class TestDetallePrecioRecalculo:
    def test_precio_aplicable_fallback(self):
        suc, inv, prod, user, mp, v, det = _venta_con_stock()
        vobj = venta.objects.get(id=v["id"])
        assert DetalleVentaService()._precio_aplicable(prod, vobj) == prod.precio_venta

    def test_precio_aplicable_sin_inventario_en_venta(self):
        prod = ProductoFactory(precio_venta=Decimal("77.00"))
        fake_venta = SimpleNamespace(id_inventario_id=None)
        assert DetalleVentaService()._precio_aplicable(prod, fake_venta) == Decimal("77.00")

    def test_precio_aplicable_usa_precio_sucursal(self):
        suc, inv, prod, user, mp, v, det = _venta_con_stock()
        PrecioSucursalService().create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "150.00"}
        )
        vobj = venta.objects.get(id=v["id"])
        assert DetalleVentaService()._precio_aplicable(prod, vobj) == Decimal("150.00")

    def test_recalcular_total(self):
        suc, inv, prod, user, mp, v, det = _venta_con_stock(qty_venta=2)
        total = DetalleVentaService()._recalcular_total(v["id"])
        assert total == Decimal("200.00")
        assert venta.objects.get(id=v["id"]).total == Decimal("200.00")


# ---------------------------------------------------- DetalleVentaService.update
@pytest.mark.django_db
class TestDetalleUpdate:
    def test_not_found(self):
        with pytest.raises(NotFoundError):
            DetalleVentaService().update(999999, {"cantidad": 1})

    def test_venta_sin_inventario(self):
        suc, inv, prod, user, mp, v, det = _venta_con_stock()
        venta.objects.filter(id=v["id"]).update(id_inventario=None)
        with pytest.raises(ValueError, match="no tiene inventario"):
            DetalleVentaService().update(det["id"], {"cantidad": 5})

    def test_cambio_producto_sin_stock(self):
        suc, inv, prod, user, mp, v, det = _venta_con_stock()
        prod2 = ProductoFactory(precio_venta=Decimal("50.00"))
        with pytest.raises(ValueError, match="stock 0"):
            DetalleVentaService().update(det["id"], {"id_producto": prod2.id}, user=user)

    def test_recalcula_subtotal_y_total(self):
        suc, inv, prod, user, mp, v, det = _venta_con_stock(qty_venta=2)
        res = DetalleVentaService().update(det["id"], {"cantidad": 3}, user=user)
        assert res["subtotal"] == "300.00"
        assert venta.objects.get(id=v["id"]).total == Decimal("300.00")


# ---------------------------------------------------- DetalleVentaService.delete
@pytest.mark.django_db
class TestDetalleDelete:
    def test_not_found(self):
        with pytest.raises(NotFoundError):
            DetalleVentaService().delete(999999)

    def test_restituye_total(self):
        suc, inv, prod, user, mp, v, det = _venta_con_stock(qty_venta=2)
        assert venta.objects.get(id=v["id"]).total == Decimal("200.00")
        out = DetalleVentaService().delete(det["id"])
        assert "eliminado" in out["message"]
        assert venta.objects.get(id=v["id"]).total == Decimal("0")
        with pytest.raises(NotFoundError):
            DetalleVentaService().get_by_id(det["id"])

    def test_to_dict(self):
        suc, inv, prod, user, mp, v, det = _venta_con_stock()
        d = DetalleVentaService().get_by_id(det["id"])
        assert d["id_producto"] == prod.id and d["id_venta"] == v["id"]
        assert d["cantidad"] == 2 and d["subtotal"] == "200.00"


# ------------------------------------------- DetalleVenta cross-sucursal/stock
@pytest.mark.django_db
class TestDetalleCrossSucursal:
    def test_staff_bypass_cross_sucursal(self):
        sa, sb = SucursalFactory(), SucursalFactory()
        inv_a = InventarioFactory(id_sucursal=sa)
        prod = ProductoFactory(precio_venta=Decimal("100.00"))
        _entrada(prod, inv_a)
        owner = UserFactory()
        mp = MetodoPagoFactory()
        v = _legacy_venta(owner, inv_a, mp)
        staff_b = UserFactory(is_staff=True)
        Perfil.objects.create(usuario=staff_b, id_sucursal=sb)
        res = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 1}, user=staff_b
        )
        assert res["subtotal"] == "100.00"

    def test_producto_stock_0_mensaje(self):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory()  # sin movimientos -> stock 0
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        mp = MetodoPagoFactory()
        v = _legacy_venta(u, inv, mp)
        with pytest.raises(ValueError, match="stock 0"):
            DetalleVentaService().create(
                {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 1}, user=u
            )

    def test_create_venta_inexistente(self):
        prod = ProductoFactory()
        with pytest.raises(NotFoundError):
            DetalleVentaService().create(
                {"id_producto": prod.id, "id_venta": 999999, "cantidad": 1}
            )

    def test_create_venta_sin_inventario(self):
        prod = ProductoFactory()
        u, mp = UserFactory(), MetodoPagoFactory()
        v = venta.objects.create(
            id_usuario=u, id_metodoPago=mp, id_inventario=None, total=Decimal("0.00")
        )
        with pytest.raises(ValueError, match="no tiene inventario"):
            DetalleVentaService().create(
                {"id_producto": prod.id, "id_venta": v.id, "cantidad": 1}
            )

    def test_create_faltan_campos(self):
        with pytest.raises(ValueError, match="Faltan campos"):
            DetalleVentaService().create({"cantidad": 1})


# ---------------------------------------------------------- MetodoPagoService
@pytest.mark.django_db
class TestMetodoPagoService:
    def test_crud(self):
        svc = MetodoPagoService()
        created = svc.create({"tipo": "TARJETA", "descripcion": "Credito"})
        assert created["tipo"] == "TARJETA"
        got = svc.get_by_id(created["id"])
        assert got["descripcion"] == "Credito"
        upd = svc.update(created["id"], {"descripcion": "Debito"})
        assert upd["descripcion"] == "Debito"
        assert len(svc.get_all()) == 1
        out = svc.delete(created["id"])
        assert "eliminado" in out["message"]
        with pytest.raises(NotFoundError):
            svc.get_by_id(created["id"])

    def test_to_dict(self):
        mp = MetodoPagoFactory(tipo="EFECTIVO", descripcion="cash")
        d = MetodoPagoService()._to_dict(mp)
        assert d == {"id": mp.id, "tipo": "EFECTIVO", "descripcion": "cash"}


# ---------------------------------------------------------- VentaTicketService
@pytest.mark.django_db
class TestVentaTicket:
    def test_ok(self):
        suc, inv, prod, user, mp, v, det = _venta_con_stock(qty_venta=2)
        t = VentaTicketService().get_ticket(v["id"])
        assert t["folio"] == v["id"]
        assert t["fecha"] is not None
        assert t["vendedor"] == user.username
        assert t["metodo_pago"] == mp.tipo
        assert t["sucursal"] == str(inv.id_sucursal)
        assert t["total"] == "200.00"
        assert len(t["productos"]) == 1
        p = t["productos"][0]
        assert p["nombre"] == prod.nombre and p["cantidad"] == 2
        assert p["precio_unitario"] == "100.00" and p["subtotal"] == "200.00"

    def test_not_found(self):
        with pytest.raises(NotFoundError):
            VentaTicketService().get_ticket(999999)

    def test_detalle_cantidad_0(self):
        u, inv, mp = UserFactory(), InventarioFactory(), MetodoPagoFactory()
        v = _legacy_venta(u, inv, mp)
        prod = ProductoFactory()
        detalleVenta.objects.create(
            id_producto=prod, id_venta=venta.objects.get(id=v["id"]),
            subtotal=Decimal("0.00"), cantidad=0,
        )
        t = VentaTicketService().get_ticket(v["id"])
        assert t["productos"][0]["precio_unitario"] == "0"

    def test_venta_sin_relaciones(self):
        v = venta.objects.create(
            id_usuario=None, id_metodoPago=None, id_inventario=None,
            total=Decimal("10.00"),
        )
        t = VentaTicketService().get_ticket(v.id)
        assert t["vendedor"] is None and t["metodo_pago"] is None
        assert t["sucursal"] is None and t["productos"] == []

    def test_fecha_none_y_sin_sucursal(self):
        fake_det = SimpleNamespace(
            subtotal=Decimal("10.00"), cantidad=1,
            id_producto=SimpleNamespace(nombre="X"),
        )
        fake_qs = mock.MagicMock()
        fake_qs.all.return_value = [fake_det]
        fake_venta = SimpleNamespace(
            id=7, fecha=None, id_usuario=None, id_metodoPago=None,
            id_inventario=SimpleNamespace(id_sucursal=None),
            detalleventa_set=fake_qs, total=Decimal("10.00"),
        )
        chain = mock.MagicMock()
        chain.select_related.return_value.prefetch_related.return_value \
            .filter.return_value.first.return_value = fake_venta
        with mock.patch("ventas.services.ventaTicket_service.venta") as mv:
            mv.objects = chain.select_related.return_value.prefetch_related \
                .return_value.filter.return_value  # noqa
            # reconstruir cadena completa sobre el mock de manager
            mv.objects = mock.MagicMock()
            mv.objects.select_related.return_value.prefetch_related.return_value \
                .filter.return_value.first.return_value = fake_venta
            t = VentaTicketService().get_ticket(7)
        assert t["fecha"] is None and t["sucursal"] is None
        assert t["productos"][0]["precio_unitario"] == "10.00"


# ------------------------------------------------------- ReporteVentasService
@pytest.mark.django_db
class TestReporteRangos:
    svc = ReporteVentasService()

    def test_day(self):
        from datetime import timedelta

        ini, fin = self.svc._calcular_rango("day")
        assert fin - ini == timedelta(days=1)
        assert (ini.hour, ini.minute) == (0, 0)

    def test_week(self):
        from datetime import timedelta

        ini, fin = self.svc._calcular_rango("week")
        assert ini.weekday() == 0 and fin - ini == timedelta(days=7)

    def test_quincena_1(self):
        ini, fin = self.svc._calcular_rango("quincena", year=2026, month=5, quincena=1)
        assert (ini.day, fin.day) == (1, 16) and ini.month == 5

    def test_quincena_2(self):
        ini, fin = self.svc._calcular_rango("quincena", year=2026, month=5, quincena=2)
        assert ini.day == 16 and (fin.month, fin.day) == (6, 1)

    def test_quincena_2_diciembre(self):
        ini, fin = self.svc._calcular_rango("quincena", year=2026, month=12, quincena=2)
        assert ini.day == 16 and (fin.year, fin.month, fin.day) == (2027, 1, 1)

    def test_quincena_sin_params(self):
        with pytest.raises(ValueError, match="year, month y quincena"):
            self.svc._calcular_rango("quincena")

    def test_quincena_invalida(self):
        with pytest.raises(ValueError, match="1 o 2"):
            self.svc._calcular_rango("quincena", year=2026, month=5, quincena=3)

    def test_month_con_params(self):
        ini, fin = self.svc._calcular_rango("month", year=2026, month=2)
        assert (ini.month, ini.day) == (2, 1) and (fin.month, fin.day) == (3, 1)

    def test_month_diciembre(self):
        ini, fin = self.svc._calcular_rango("month", year=2026, month=12)
        assert (fin.year, fin.month) == (2027, 1)

    def test_month_sin_params(self):
        ini, fin = self.svc._calcular_rango("month")
        assert ini.day == 1 and fin >= ini

    def test_year(self):
        ini, fin = self.svc._calcular_rango("year", year=2026)
        assert (ini.year, ini.month, ini.day) == (2026, 1, 1)
        assert (fin.year, fin.month) == (2027, 1)

    def test_year_sin_year(self):
        with pytest.raises(ValueError, match="year"):
            self.svc._calcular_rango("year")

    def test_tipo_invalido(self):
        with pytest.raises(ValueError, match="inválido"):
            self.svc._calcular_rango("semestre")


@pytest.mark.django_db
class TestReporteGenerar:
    def test_con_vendedor_con_nombre_y_detalles(self):
        suc, inv, prod, user, mp, v, det = _venta_con_stock(qty_venta=2)
        user.first_name, user.last_name = "Juan", "Perez"
        user.save()
        rep = ReporteVentasService().generar_reporte("day")
        assert rep["tipo"] == "day"
        ids = [x["id"] for x in rep["ventas"]]
        assert v["id"] in ids
        row = next(x for x in rep["ventas"] if x["id"] == v["id"])
        assert row["vendedor"] == "Juan Perez"
        assert row["metodo_pago"] == mp.tipo
        assert row["total"] == Decimal("200.00")
        assert row["detalles"][0]["producto"] == prod.nombre
        assert row["detalles"][0]["cantidad"] == 2
        assert rep["total_general"] >= Decimal("200.00")

    def test_vendedor_sin_nombre_usa_username(self):
        suc, inv, prod, user, mp, v, det = _venta_con_stock()
        rep = ReporteVentasService().generar_reporte("day")
        row = next(x for x in rep["ventas"] if x["id"] == v["id"])
        assert row["vendedor"] == user.username

    def test_sin_metodo_y_detalles_vacios(self):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        u = UserFactory()
        v = venta.objects.create(
            id_usuario=u, id_metodoPago=None, id_inventario=inv, total=Decimal("0.00")
        )
        rep = ReporteVentasService().generar_reporte("day")
        row = next(x for x in rep["ventas"] if x["id"] == v.id)
        assert row["metodo_pago"] is None and row["detalles"] == []


# ---------------------------------------------------------- ReporteVentasView
@pytest.mark.django_db
class TestReporteView:
    def _auth(self, api_client, user):
        api_client.force_authenticate(user=user)
        return api_client

    def test_sin_tipo_400(self, api_client, user):
        assert self._auth(api_client, user).get("/api/reporte/").status_code == 400

    def test_tipo_invalido_400(self, api_client, user):
        c = self._auth(api_client, user)
        assert c.get("/api/reporte/", {"tipo": "x"}).status_code == 400

    def test_ok_pdf(self, api_client, user):
        _venta_con_stock()
        c = self._auth(api_client, user)
        with mock.patch(
            "ventas.views.reporte_ventas_view.render_to_string", return_value="<html/>"
        ), mock.patch("ventas.views.reporte_ventas_view.HTML") as mhtml:
            mhtml.return_value.write_pdf.return_value = b"%PDF-fake"
            resp = c.get("/api/reporte/", {"tipo": "day"})
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/pdf"
        assert Reporte.objects.filter(tipo="day").exists()

    def test_ok_quincena_params(self, api_client, user):
        c = self._auth(api_client, user)
        with mock.patch(
            "ventas.views.reporte_ventas_view.render_to_string", return_value="<html/>"
        ), mock.patch("ventas.views.reporte_ventas_view.HTML") as mhtml:
            mhtml.return_value.write_pdf.return_value = b"%PDF-fake"
            resp = c.get(
                "/api/reporte/",
                {"tipo": "quincena", "year": "2026", "month": "5", "quincena": "1"},
            )
        assert resp.status_code == 200


# --------------------------------------------------------------- controllers
@pytest.mark.django_db
class TestVentasController:
    def test_get_propia_sucursal(self, auth_client, user, inventario):
        mp = MetodoPagoFactory()
        otra = InventarioFactory()
        VentaService().create(
            {"id_usuario": user.id, "id_inventario": otra.id, "id_metodoPago": mp.id}
        )
        VentaService().create(
            {"id_usuario": user.id, "id_inventario": inventario.id,
             "id_metodoPago": mp.id}
        )
        resp = auth_client.get("/api/ventas/")
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_get_page_invalido_400(self, auth_client):
        assert auth_client.get("/api/ventas/", {"page": "abc"}).status_code == 400

    def test_get_paginado_staff(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        u, inv, mp = UserFactory(), InventarioFactory(), MetodoPagoFactory()
        _legacy_venta(u, inv, mp)
        resp = api_client.get("/api/ventas/", {"page": "1", "page_size": "5"})
        assert resp.status_code == 200
        assert resp.data["total"] >= 1

    def test_get_sucursal_invalida_staff_400(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        resp = api_client.get("/api/ventas/", {"sucursal_id": "abc"})
        assert resp.status_code == 400

    def test_get_inventario_invalido_staff_400(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        resp = api_client.get("/api/ventas/", {"id_inventario": "abc"})
        assert resp.status_code == 400

    def test_get_usuario_sin_sucursal_400(self, api_client, user):
        api_client.force_authenticate(user=user)
        assert api_client.get("/api/ventas/").status_code == 400

    def test_post_ok_y_error(self, auth_client):
        mp = MetodoPagoFactory()
        ok = auth_client.post("/api/ventas/", {"id_metodoPago": mp.id}, format="json")
        assert ok.status_code == 201
        bad = auth_client.post("/api/ventas/", {}, format="json")
        assert bad.status_code == 400

    def test_post_staff_override(self, api_client, staff_user):
        inv = InventarioFactory()
        api_client.force_authenticate(user=staff_user)
        mp = MetodoPagoFactory()
        resp = api_client.post(
            "/api/ventas/", {"id_metodoPago": mp.id, "id_inventario": inv.id},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["id_inventario"] == inv.id

    def test_detail_get_put_delete(self, auth_client, user, inventario):
        mp = MetodoPagoFactory()
        v = _legacy_venta(user, inventario, mp)
        assert auth_client.get(f"/api/ventas/{v['id']}/").status_code == 200
        assert auth_client.get("/api/ventas/999999/").status_code == 404
        put = auth_client.put(
            f"/api/ventas/{v['id']}/", {"total": "99.00"}, format="json"
        )
        assert put.status_code == 200
        assert auth_client.delete(f"/api/ventas/{v['id']}/").status_code == 200
        assert auth_client.delete("/api/ventas/999999/").status_code == 404


@pytest.mark.django_db
class TestDetalleController:
    def _ctx(self, api_client):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory(precio_venta=Decimal("100.00"))
        _entrada(prod, inv)
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        api_client.force_authenticate(user=u)
        mp = MetodoPagoFactory()
        v = _legacy_venta(u, inv, mp)
        return prod, v, u

    def test_post_ok_404_400(self, api_client):
        prod, v, u = self._ctx(api_client)
        ok = api_client.post(
            "/api/detalleventa/",
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 1},
            format="json",
        )
        assert ok.status_code == 201
        nf = api_client.post(
            "/api/detalleventa/",
            {"id_producto": prod.id, "id_venta": 999999, "cantidad": 1},
            format="json",
        )
        assert nf.status_code == 404
        bad = api_client.post("/api/detalleventa/", {"cantidad": 1}, format="json")
        assert bad.status_code == 400

    def test_put_ok_404_400(self, api_client):
        prod, v, u = self._ctx(api_client)
        det = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 1}, user=u
        )
        ok = api_client.put(
            f"/api/detalleventa/{det['id']}/", {"cantidad": 2}, format="json"
        )
        assert ok.status_code == 200
        assert ok.data["subtotal"] == "200.00"
        assert api_client.put("/api/detalleventa/999999/", {"cantidad": 2},
                              format="json").status_code == 404
        # cantidad mayor al stock -> ValueError -> 400
        bad = api_client.put(
            f"/api/detalleventa/{det['id']}/", {"cantidad": 9999}, format="json"
        )
        assert bad.status_code == 400

    def test_update_producto_inexistente_gap(self, api_client):
        # Producto inexistente -> NotFoundError (404 en API)
        prod, v, u = self._ctx(api_client)
        det = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 1}, user=u
        )
        from repository.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            DetalleVentaService().update(det["id"], {"id_producto": 999999})
        assert api_client.put(
            f"/api/detalleventa/{det['id']}/",
            {"id_producto": 999999},
            format="json",
        ).status_code == 404

    def test_detail_get_delete(self, api_client):
        prod, v, u = self._ctx(api_client)
        det = DetalleVentaService().create(
            {"id_producto": prod.id, "id_venta": v["id"], "cantidad": 1}, user=u
        )
        assert api_client.get(f"/api/detalleventa/{det['id']}/").status_code == 200
        assert api_client.delete(f"/api/detalleventa/{det['id']}/").status_code == 200


@pytest.mark.django_db
class TestMetodoPagoController:
    def _client(self, api_client, user):
        api_client.force_authenticate(user=user)
        return api_client

    def test_crud_api(self, api_client, user):
        c = self._client(api_client, user)
        created = c.post(
            "/api/metodopago/", {"tipo": "EFECTIVO", "descripcion": "cash"},
            format="json",
        )
        assert created.status_code == 201
        pk = created.data["id"]
        assert c.get("/api/metodopago/").status_code == 200
        assert c.get(f"/api/metodopago/{pk}/").status_code == 200
        assert c.get("/api/metodopago/999999/").status_code == 404
        upd = c.put(f"/api/metodopago/{pk}/", {"descripcion": "cash2"}, format="json")
        assert upd.status_code == 200
        assert c.delete(f"/api/metodopago/{pk}/").status_code == 200

    def test_post_invalido_400(self, api_client, user):
        c = self._client(api_client, user)
        # descripcion requerida por el modelo (NOT NULL) -> 400
        assert c.post("/api/metodopago/", {"tipo": "X"}, format="json").status_code == 400


@pytest.mark.django_db
class TestTicketController:
    def test_get_ok_404(self, api_client, user):
        suc, inv, prod, owner, mp, v, det = _venta_con_stock()
        api_client.force_authenticate(user=user)
        ok = api_client.get(f"/api/ventas/{v['id']}/ticket/")
        assert ok.status_code == 200
        assert ok.data["folio"] == v["id"]
        assert api_client.get("/api/ventas/999999/ticket/").status_code == 404


# --------------------------------------------------------------- repositories
@pytest.mark.django_db
class TestVentasRepositories:
    def test_rango_y_total(self):
        from django.utils import timezone

        suc, inv, prod, user, mp, v, det = _venta_con_stock(qty_venta=2)
        repo = VentaRepository()
        ahora = timezone.localtime()
        ini = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        fin = ini + __import__("datetime").timedelta(days=1)
        qs = repo.get_ventas_por_rango(ini, fin)
        assert v["id"] in [x.id for x in qs]
        assert repo.get_total_ventas_por_rango(ini, fin) >= Decimal("200.00")
        assert repo.get_by_id(v["id"]).id == v["id"]
        assert repo.get_by_id(999999) is None

    def test_detalle_repo(self):
        suc, inv, prod, user, mp, v, det = _venta_con_stock(qty_venta=2)
        repo = DetalleVentaRepository()
        assert repo.sum_subtotales(v["id"]) == Decimal("200.00")
        assert repo.sum_subtotales(999999) == 0
        assert repo.get_by_venta(v["id"]).count() == 1

    def test_metodopago_repo(self):
        repo = MetodoPagoRepository()
        obj = repo.create({"tipo": "T", "descripcion": "d"})
        assert repo.get_by_id(obj.id).tipo == "T"
        assert len(repo.get_all()) == 1
        assert repo.get_by_id(999999) is None


# ------------------------------------------------------------------- models
@pytest.mark.django_db
class TestVentasModels:
    def test_reporte_str(self):
        from django.utils import timezone

        ahora = timezone.now()
        r = Reporte(tipo="day", fecha_inicio=ahora, fecha_fin=ahora)
        assert str(r) == f"Reporte day - {ahora} a {ahora}"


# ------------------------------------------------- ramas defensivas (excepts)
@pytest.mark.django_db
class TestRamasDefensivas:
    def test_get_all_excepcion_generica(self):
        u, inv, mp = UserFactory(), InventarioFactory(), MetodoPagoFactory()
        _legacy_venta(u, inv, mp)
        with mock.patch.object(
            VentaService, "_to_dict", side_effect=RuntimeError("boom")
        ):
            with pytest.raises(ValueError, match="Error al obtener ventas"):
                VentaService().get_all()

    def test_resolve_perfil_explota_y_fallback_falla(self):
        class _Exploding:
            @property
            def id_sucursal_id(self):
                raise Exception("boom")

        user = SimpleNamespace(id=1, perfil=_Exploding())
        with mock.patch("usuario.models.Perfil") as mperfil:
            mperfil.objects.filter.side_effect = Exception("db down")
            # filter lanza -> se captura y user_sucursal_id queda None
            with pytest.raises(ValueError, match="no tiene una sucursal"):
                VentaService()._resolve_inventario_for_user(user)

    def test_precio_aplicable_inv_sin_attr(self):
        prod = ProductoFactory(precio_venta=Decimal("33.00"))
        fake_venta = SimpleNamespace(
            id_inventario_id=999999, id_inventario=SimpleNamespace()
        )
        assert DetalleVentaService()._precio_aplicable(prod, fake_venta) == Decimal(
            "33.00"
        )

    def test_validar_perfil_sin_attrs_ok(self):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory(precio_venta=Decimal("100.00"))
        _entrada(prod, inv)
        owner = UserFactory()
        mp = MetodoPagoFactory()
        v = _legacy_venta(owner, inv, mp)
        vobj = venta.objects.get(id=v["id"])
        user = SimpleNamespace(is_staff=False, is_superuser=False,
                               perfil=SimpleNamespace())
        DetalleVentaService()._validar_producto_en_inventario_sucursal(
            prod, vobj, user=user
        )  # no lanza; cubre fetch-perfil con AttributeError

    def test_validar_cross_inv_sin_attr(self):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory(precio_venta=Decimal("100.00"))
        _entrada(prod, inv)
        owner = UserFactory()
        mp = MetodoPagoFactory()
        v = _legacy_venta(owner, inv, mp)
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        fake_venta = SimpleNamespace(
            id_inventario_id=inv.id, id_inventario=SimpleNamespace()
        )
        DetalleVentaService()._validar_producto_en_inventario_sucursal(
            prod, fake_venta, user=u
        )  # resuelve sucursal por query; no lanza

    def test_validar_cross_inv_explota_captura(self):
        # hasattr() propaga excepciones no-AttributeError -> except (líneas 88-89)
        class _BadInv:
            @property
            def id_sucursal_id(self):
                raise Exception("boom")

        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory(precio_venta=Decimal("100.00"))
        _entrada(prod, inv)
        u = UserFactory()
        Perfil.objects.create(usuario=u, id_sucursal=suc)
        fake_venta = SimpleNamespace(
            id_inventario_id=inv.id, id_inventario=_BadInv()
        )
        DetalleVentaService()._validar_producto_en_inventario_sucursal(
            prod, fake_venta, user=u
        )  # sucursal None -> sin bloqueo cross; stock ok

    def test_stock0_inv_sin_attr_mensaje_con_sucursal(self):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory()  # sin stock
        fake_venta = SimpleNamespace(
            id_inventario_id=inv.id, id_inventario=SimpleNamespace()
        )
        with pytest.raises(ValueError, match=f"Sucursal {suc.id}"):
            DetalleVentaService()._validar_producto_en_inventario_sucursal(
                prod, fake_venta
            )

    def test_stock0_inv_explota_mensaje_sin_sucursal(self):
        # mismo hasattr que explota en la rama de mensaje (líneas 107-108)
        class _BadInv:
            @property
            def id_sucursal_id(self):
                raise Exception("boom")

        inv = InventarioFactory()
        prod = ProductoFactory()  # sin stock
        fake_venta = SimpleNamespace(
            id_inventario_id=inv.id, id_inventario=_BadInv()
        )
        with pytest.raises(ValueError, match=r"\(Sucursal None\) - stock 0"):
            DetalleVentaService()._validar_producto_en_inventario_sucursal(
                prod, fake_venta
            )

    def test_controller_get_valueerror_400(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        resp = api_client.get("/api/ventas/", {"page": "0"})
        assert resp.status_code == 400

    def test_controller_get_perfil_por_query(self, api_client, user):
        # descriptor sin perfil pero query DB sí lo encuentra -> línea 37
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        mp = MetodoPagoFactory()
        _legacy_venta(UserFactory(), inv, mp)
        api_client.force_authenticate(user=user)  # user sin perfil
        with mock.patch("usuario.models.Perfil") as mperfil:
            mperfil.objects.filter.return_value.first.return_value = SimpleNamespace(
                id_sucursal_id=suc.id
            )
            resp = api_client.get("/api/ventas/")
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_controller_get_perfil_query_falla_400(self, api_client, user):
        api_client.force_authenticate(user=user)  # sin perfil
        with mock.patch("usuario.models.Perfil") as mperfil:
            mperfil.objects.filter.side_effect = Exception("db down")
            resp = api_client.get("/api/ventas/")
        assert resp.status_code == 400
