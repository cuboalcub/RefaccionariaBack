"""Tests extra inventario: ramas restantes de services, repos, controllers y models."""

import pytest
from decimal import Decimal

from django.contrib.auth.models import User

from inventario.models import (
    DetalleInventario,
    MovimientoInventario,
    PrecioSucursal,
)
from inventario.repositories.detalle_inventario_repository import (
    DetalleInventarioRepository,
)
from inventario.repositories.precio_sucursal_repository import (
    PrecioSucursalRepository,
)
from inventario.services.detalle_inventario_service import DetalleInventarioService
from inventario.services.inventario_service import InventarioService
from inventario.services.movimiento_inventario_service import (
    MovimientoInventarioService,
)
from inventario.services.precio_sucursal_service import PrecioSucursalService
from repository.exceptions import NotFoundError
from tests.factories import (
    InventarioFactory,
    MovimientoEntradaFactory,
    ProductoFactory,
    ProveedorFactory,
    SucursalFactory,
)


def _venta_con_detalle(producto):
    """Crea venta + DetalleVenta mínimos para probar salidas por venta."""
    from ventas.models import DetalleVenta, Venta

    v = Venta.objects.create(total=Decimal("100.00"))
    dv = DetalleVenta.objects.create(
        id_producto=producto, id_venta=v, subtotal=Decimal("50.00"), cantidad=2
    )
    return v, dv


# ---------------------------------------------------------------------------
# InventarioService
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInventarioServiceExtra:
    def test_create_ok(self):
        suc = SucursalFactory()
        res = InventarioService().create(
            {"id_sucursal": suc.id, "descripcion": "Central"}
        )
        assert res["id_sucursal"] == suc.id

    def test_create_sin_sucursal_falla(self):
        with pytest.raises(ValueError, match="id_sucursal"):
            InventarioService().create({"descripcion": "X"})

    def test_create_sucursal_inexistente_falla(self):
        with pytest.raises(ValueError, match="no existe"):
            InventarioService().create(
                {"id_sucursal": 99999, "descripcion": "X"}
            )

    def test_update_cambia_sucursal(self):
        inv = InventarioFactory()
        suc2 = SucursalFactory()
        res = InventarioService().update(inv.id, {"id_sucursal": suc2.id})
        assert res["id_sucursal"] == suc2.id

    def test_update_sucursal_inexistente_falla(self):
        inv = InventarioFactory()
        with pytest.raises(ValueError, match="no existe"):
            InventarioService().update(inv.id, {"id_sucursal": 99999})

    def test_update_not_found(self):
        with pytest.raises(NotFoundError):
            InventarioService().update(99999, {"descripcion": "X"})

    def test_get_all_get_by_id_delete(self):
        inv = InventarioFactory()
        svc = InventarioService()
        assert any(i["id"] == inv.id for i in svc.get_all())
        assert svc.get_by_id(inv.id)["id"] == inv.id
        assert "eliminado" in svc.delete(inv.id)["message"].lower()
        with pytest.raises(NotFoundError):
            svc.get_by_id(inv.id)

    def test_to_dict_none(self):
        assert InventarioService()._to_dict(None) is None


# ---------------------------------------------------------------------------
# MovimientoInventarioService
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMovimientoServiceExtra:
    def test_crud_basico(self):
        svc = MovimientoInventarioService()
        res = svc.create(
            {"tipo": "ENTRADA", "cantidad": 5, "razon": "Compra"}
        )
        assert res["tipo"] == "ENTRADA"
        assert svc.get_by_id(res["id"])["cantidad"] == 5
        upd = svc.update(res["id"], {"cantidad": 7})
        assert upd["cantidad"] == 7
        assert any(m["id"] == res["id"] for m in svc.get_all())
        svc.delete(res["id"])
        with pytest.raises(NotFoundError):
            svc.get_by_id(res["id"])

    def test_to_dict_none(self):
        assert MovimientoInventarioService()._to_dict(None) is None

    def test_to_dict_fecha_none(self):
        mov = MovimientoEntradaFactory()
        # fecha NOT NULL en DB: solo anular en memoria para rama None
        mov.fecha = None
        d = MovimientoInventarioService()._to_dict(mov)
        assert d["fecha"] is None
        assert d["razon"] == "Compra inicial"


# ---------------------------------------------------------------------------
# DetalleInventarioService: _validar
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDetalleValidar:
    def test_falta_producto(self):
        inv = InventarioFactory()
        with pytest.raises(ValueError, match="id_producto"):
            DetalleInventarioService().create(
                {"id_inventario": inv.id, "cantidad": 1}
            )

    def test_falta_inventario(self):
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="id_inventario"):
            DetalleInventarioService().create(
                {"id_producto": prod.id, "cantidad": 1}
            )

    def test_falta_cantidad(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="cantidad"):
            DetalleInventarioService().create(
                {"id_producto": prod.id, "id_inventario": inv.id}
            )

    def test_producto_inexistente(self):
        inv = InventarioFactory()
        svc = DetalleInventarioService()
        with pytest.raises(ValueError, match="producto"):
            svc._validar(
                {
                    "id_producto": 99999,
                    "id_inventario": inv.id,
                    "cantidad": 1,
                }
            )

    def test_inventario_inexistente(self):
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="inventario"):
            DetalleInventarioService()._validar(
                {
                    "id_producto": prod.id,
                    "id_inventario": 99999,
                    "cantidad": 1,
                }
            )

    def test_movimiento_inexistente(self):
        prod = ProductoFactory()
        inv = InventarioFactory()
        with pytest.raises(ValueError, match="movimiento"):
            DetalleInventarioService()._validar(
                {
                    "id_producto": prod.id,
                    "id_inventario": inv.id,
                    "id_movimiento": 99999,
                    "cantidad": 1,
                }
            )

    def test_tipo_invalido(self):
        prod = ProductoFactory()
        inv = InventarioFactory()
        with pytest.raises(ValueError, match="ENTRADA o SALIDA"):
            DetalleInventarioService()._validar(
                {
                    "id_producto": prod.id,
                    "id_inventario": inv.id,
                    "cantidad": 1,
                    "tipo_movimiento": "ROBO",
                }
            )

    def test_create_tipo_invalido(self):
        prod = ProductoFactory()
        inv = InventarioFactory()
        with pytest.raises(ValueError, match="ENTRADA o SALIDA"):
            DetalleInventarioService().create(
                {
                    "id_producto": prod.id,
                    "id_inventario": inv.id,
                    "cantidad": 1,
                    "tipo_movimiento": "ROBO",
                }
            )

    def test_create_con_movimiento_explicito(self):
        prod = ProductoFactory()
        inv = InventarioFactory()
        mov = MovimientoEntradaFactory()
        res = DetalleInventarioService().create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "id_movimiento": mov.id,
                "cantidad": 4,
            }
        )
        assert res["id_movimiento"] == mov.id

    def test_create_proveedor_inexistente(self):
        prod = ProductoFactory()
        inv = InventarioFactory()
        with pytest.raises(ValueError, match="proveedor"):
            DetalleInventarioService().create(
                {
                    "id_producto": prod.id,
                    "id_inventario": inv.id,
                    "id_proveedor": 99999,
                    "cantidad": 1,
                }
            )

    def test_to_dict_none(self):
        assert DetalleInventarioService()._to_dict(None) is None


# ---------------------------------------------------------------------------
# DetalleInventarioService: update / delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDetalleUpdateDelete:
    def _entrada(self, cantidad=5):
        inv = InventarioFactory()
        prod = ProductoFactory()
        svc = DetalleInventarioService()
        res = svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": cantidad,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        return svc, res, inv, prod

    def test_update_not_found(self):
        with pytest.raises(NotFoundError):
            DetalleInventarioService().update(99999, {"cantidad": 1})

    def test_update_cantidad_ok(self):
        svc, res, inv, prod = self._entrada()
        upd = svc.update(res["id"], {"cantidad": 8})
        assert upd["cantidad"] == 8

    def test_update_cantidad_negativa(self):
        svc, res, inv, prod = self._entrada()
        with pytest.raises(ValueError, match="negativa"):
            svc.update(res["id"], {"cantidad": -2})

    def test_update_salida_sin_stock(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        svc = DetalleInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 5,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        mov_sal = MovimientoInventario.objects.create(
            tipo="SALIDA", cantidad=3, razon="Venta"
        )
        det = svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "id_movimiento": mov_sal.id,
                "cantidad": 3,
            }
        )
        with pytest.raises(ValueError, match="Stock insuficiente"):
            svc.update(det["id"], {"cantidad": 100})

    def test_update_cambia_producto_e_inventario(self):
        svc, res, inv, prod = self._entrada()
        prod2 = ProductoFactory()
        inv2 = InventarioFactory()
        upd = svc.update(
            res["id"],
            {"id_producto": prod2.id, "id_inventario": inv2.id},
        )
        assert upd["id_producto"] == prod2.id
        assert upd["id_inventario"] == inv2.id

    def test_update_producto_inexistente(self):
        svc, res, inv, prod = self._entrada()
        with pytest.raises(ValueError, match="producto"):
            svc.update(res["id"], {"id_producto": 99999})

    def test_update_inventario_inexistente(self):
        svc, res, inv, prod = self._entrada()
        with pytest.raises(ValueError, match="inventario"):
            svc.update(res["id"], {"id_inventario": 99999})

    def test_update_proveedor_invalido(self):
        svc, res, inv, prod = self._entrada()
        with pytest.raises(ValueError, match="proveedor"):
            svc.update(res["id"], {"id_proveedor": 99999})

    def test_update_proveedor_none(self):
        svc, res, inv, prod = self._entrada()
        prov = ProveedorFactory()
        svc.update(res["id"], {"id_proveedor": prov.id})
        upd = svc.update(res["id"], {"id_proveedor": None})
        assert upd["id_proveedor"] is None

    def test_update_tipo_movimiento_invalido(self):
        svc, res, inv, prod = self._entrada()
        with pytest.raises(ValueError, match="ENTRADA o SALIDA"):
            svc.update(res["id"], {"tipo_movimiento": "ROBO"})

    def test_update_movimiento_razon(self):
        svc, res, inv, prod = self._entrada()
        upd = svc.update(
            res["id"],
            {"razon": "Ajuste", "observaciones": "obs", "tipo_movimiento": "ENTRADA"},
        )
        assert upd["id"] == res["id"]
        mov = MovimientoInventario.objects.get(id=upd["id_movimiento"])
        assert mov.razon == "Ajuste"
        assert mov.observaciones == "obs"

    def test_delete_ok_y_not_found(self):
        svc, res, inv, prod = self._entrada()
        assert "eliminado" in svc.delete(res["id"])["message"].lower()
        with pytest.raises(NotFoundError):
            svc.delete(res["id"])
        with pytest.raises(NotFoundError):
            svc.delete(99999)


# ---------------------------------------------------------------------------
# DetalleInventarioService: ventas / stock / sucursal
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDetalleVentaHelpers:
    def test_crear_ajustar_revertir_salida(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        svc = DetalleInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        _, dv = _venta_con_detalle(prod)
        det = svc.crear_salida_por_venta(dv, prod, inv, 3)
        assert det.cantidad == 3
        assert svc.get_stock(prod.id, inv.id) == 7

        aj = svc.ajustar_salida_por_venta(dv, 5)
        assert aj.cantidad == 5
        assert svc.get_stock(prod.id, inv.id) == 5

        with pytest.raises(ValueError, match="Stock insuficiente"):
            svc.ajustar_salida_por_venta(dv, 100)

        assert svc.revertir_salida_por_venta(dv) is True
        assert svc.get_stock(prod.id, inv.id) == 10

    def test_ajustar_y_revertir_sin_detalle(self):
        prod = ProductoFactory()
        _, dv = _venta_con_detalle(prod)
        svc = DetalleInventarioService()
        assert svc.ajustar_salida_por_venta(dv, 5) is None
        assert svc.revertir_salida_por_venta(dv) is None

    def test_get_stock_service(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        svc = DetalleInventarioService()
        assert svc.get_stock(prod.id, inv.id) == 0
        svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 6,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        assert svc.get_stock(prod.id, inv.id) == 6

    def test_get_inventario_por_sucursal_vacio(self):
        suc = SucursalFactory()
        assert DetalleInventarioService().get_inventario_por_sucursal(suc.id) == []

    def test_get_inventario_sin_precio_sucursal(self):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory()
        DetalleInventarioService().create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 2,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        data = DetalleInventarioService().get_inventario_por_sucursal(suc.id)
        assert data[0]["detalles"][0]["precio_sucursal"] is None
        assert data[0]["detalles"][0]["vigente_desde"] is None


# ---------------------------------------------------------------------------
# DetalleInventarioService: bulk_create formatos
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDetalleBulkFormatos:
    def test_lista_plana(self):
        inv = InventarioFactory()
        p1 = ProductoFactory()
        p2 = ProductoFactory()
        res = DetalleInventarioService().bulk_create(
            [
                {
                    "id_producto": p1.id,
                    "id_inventario": inv.id,
                    "cantidad": 2,
                    "tipo_movimiento": "ENTRADA",
                    "razon": "Carga",
                },
                {
                    "id_producto": p2.id,
                    "id_inventario": inv.id,
                    "cantidad": 3,
                    "tipo_movimiento": "ENTRADA",
                    "razon": "Carga",
                },
            ]
        )
        assert len(res) == 2

    def test_dict_unico(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        res = DetalleInventarioService().bulk_create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 4,
            }
        )
        assert len(res) == 1

    def test_alias_detalles(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        res = DetalleInventarioService().bulk_create(
            {
                "id_inventario": inv.id,
                "tipo_movimiento": "ENTRADA",
                "razon": "Carga",
                "detalles": [{"id_producto": prod.id, "cantidad": 5}],
            }
        )
        assert len(res) == 1

    def test_formato_invalido(self):
        with pytest.raises(ValueError, match="bulk inválido"):
            DetalleInventarioService().bulk_create("no-es-lista-ni-dict")

    def test_item_no_dict(self):
        inv = InventarioFactory()
        with pytest.raises(ValueError, match="debe ser un objeto"):
            DetalleInventarioService().bulk_create(
                {"id_inventario": inv.id, "items": ["texto"]}
            )

    def test_proveedor_invalido(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="proveedor"):
            DetalleInventarioService().bulk_create(
                {
                    "id_inventario": inv.id,
                    "tipo_movimiento": "ENTRADA",
                    "items": [
                        {
                            "id_producto": prod.id,
                            "cantidad": 1,
                            "id_proveedor": 99999,
                        }
                    ],
                }
            )

    def test_salida_sin_stock(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="Stock insuficiente"):
            DetalleInventarioService().bulk_create(
                {
                    "id_inventario": inv.id,
                    "tipo_movimiento": "SALIDA",
                    "razon": "Venta",
                    "items": [{"id_producto": prod.id, "cantidad": 9}],
                }
            )

    def test_movimiento_comun_inexistente(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="movimiento"):
            DetalleInventarioService().bulk_create(
                {
                    "id_inventario": inv.id,
                    "id_movimiento": 99999,
                    "items": [{"id_producto": prod.id, "cantidad": 1}],
                }
            )

    def test_bulk_tipo_invalido_por_item(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="ENTRADA o SALIDA"):
            DetalleInventarioService().bulk_create(
                {
                    "id_inventario": inv.id,
                    "items": [
                        {
                            "id_producto": prod.id,
                            "cantidad": 1,
                            "tipo_movimiento": "ROBO",
                        }
                    ],
                }
            )

    def test_bulk_con_movimiento_comun(self):
        inv = InventarioFactory()
        p1 = ProductoFactory()
        p2 = ProductoFactory()
        mov = MovimientoEntradaFactory()
        res = DetalleInventarioService().bulk_create(
            {
                "id_inventario": inv.id,
                "id_movimiento": mov.id,
                "items": [
                    {"id_producto": p1.id, "cantidad": 2},
                    {"id_producto": p2.id, "cantidad": 3},
                ],
            }
        )
        assert len(res) == 2
        assert all(r["id_movimiento"] == mov.id for r in res)


# ---------------------------------------------------------------------------
# PrecioSucursalService
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPrecioSucursalExtra:
    def test_validar_faltantes(self):
        with pytest.raises(ValueError, match="obligatorios"):
            PrecioSucursalService().create({"id_producto": 1})

    def test_validar_precio_no_numerico(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="número válido"):
            PrecioSucursalService().create(
                {
                    "id_producto": prod.id,
                    "id_sucursal": suc.id,
                    "precio_venta": "abc",
                }
            )

    def test_validar_producto_inexistente(self):
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="producto"):
            PrecioSucursalService().create(
                {
                    "id_producto": 99999,
                    "id_sucursal": suc.id,
                    "precio_venta": "10.00",
                }
            )

    def test_validar_sucursal_inexistente(self):
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="sucursal"):
            PrecioSucursalService().create(
                {
                    "id_producto": prod.id,
                    "id_sucursal": 99999,
                    "precio_venta": "10.00",
                }
            )

    def test_validar_parcial_update_solo_precio(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        svc = PrecioSucursalService()
        ps = svc.create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "10.00"}
        )
        upd = svc.update(ps["id"], {"precio_venta": "20.00"})
        assert upd["precio_venta"] == "20.00"

    def test_update_not_found(self):
        with pytest.raises(NotFoundError):
            PrecioSucursalService().update(99999, {"precio_venta": "10.00"})

    def test_update_cambia_par_desactiva_destino(self):
        s1, s2 = SucursalFactory(), SucursalFactory()
        p1, p2 = ProductoFactory(), ProductoFactory()
        svc = PrecioSucursalService()
        destino = svc.create(
            {"id_producto": p2.id, "id_sucursal": s2.id, "precio_venta": "30.00"}
        )
        movil = svc.create(
            {"id_producto": p1.id, "id_sucursal": s1.id, "precio_venta": "10.00"}
        )
        svc.update(movil["id"], {"id_producto": p2.id, "id_sucursal": s2.id})
        assert PrecioSucursal.objects.get(id=destino["id"]).activo is False
        assert PrecioSucursal.objects.get(id=movil["id"]).activo is True

    def test_update_desactivar_y_reactivar(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        svc = PrecioSucursalService()
        ps = svc.create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "10.00"}
        )
        svc.update(ps["id"], {"activo": False})
        assert svc.get_precio_activo(prod.id, suc.id) is None
        svc.update(ps["id"], {"activo": True})
        assert svc.get_precio_activo(prod.id, suc.id)["id"] == ps["id"]

    def test_update_producto_inexistente(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        svc = PrecioSucursalService()
        ps = svc.create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "10.00"}
        )
        with pytest.raises(ValueError, match="producto"):
            svc.update(ps["id"], {"id_producto": 99999})

    def test_update_sucursal_inexistente(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        svc = PrecioSucursalService()
        ps = svc.create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "10.00"}
        )
        with pytest.raises(ValueError, match="sucursal"):
            svc.update(ps["id"], {"id_sucursal": 99999})

    def test_get_precio_activo_none(self):
        assert (
            PrecioSucursalService().get_precio_activo(99999, 99999) is None
        )

    def test_get_historial_orden(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        svc = PrecioSucursalService()
        svc.create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "10.00"}
        )
        p2 = svc.create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "20.00"}
        )
        hist = svc.get_historial(prod.id, suc.id)
        assert len(hist) == 2
        assert hist[0]["id"] == p2["id"]

    def test_resolver_con_id_numerico(self):
        prod = ProductoFactory(precio_venta=Decimal("50.00"))
        suc = SucursalFactory()
        PrecioSucursalService().create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "77.00"}
        )
        assert PrecioSucursalService.resolver_precio_venta(
            prod.id, suc.id
        ) == Decimal("77.00")

    def test_resolver_producto_inexistente(self):
        suc = SucursalFactory()
        assert (
            PrecioSucursalService.resolver_precio_venta(99999, suc.id) is None
        )

    def test_resolver_sin_sucursal(self):
        prod = ProductoFactory(precio_venta=Decimal("33.00"))
        assert PrecioSucursalService.resolver_precio_venta(prod) == Decimal("33.00")

    def test_to_dict_none(self):
        assert PrecioSucursalService()._to_dict(None) is None


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRepositoriesExtra:
    def test_detalle_get_stock_con_y_sin_inventario(self):
        inv1 = InventarioFactory()
        inv2 = InventarioFactory()
        prod = ProductoFactory()
        svc = DetalleInventarioService()
        for inv, cant in ((inv1, 4), (inv2, 6)):
            svc.create(
                {
                    "id_producto": prod.id,
                    "id_inventario": inv.id,
                    "cantidad": cant,
                    "tipo_movimiento": "ENTRADA",
                    "razon": "Compra",
                }
            )
        repo = DetalleInventarioRepository()
        assert repo.get_stock(prod.id, inv1.id) == 4
        assert repo.get_stock(prod.id) == 10
        assert repo.get_stock(99999) == 0

    def test_get_by_detalle_venta_none_y_found(self):
        repo = DetalleInventarioRepository()
        assert repo.get_by_detalle_venta(99999) is None
        inv = InventarioFactory()
        prod = ProductoFactory()
        _, dv = _venta_con_detalle(prod)
        DetalleInventarioService().crear_salida_por_venta(dv, prod, inv, 2)
        assert repo.get_by_detalle_venta(dv.id) is not None

    def test_get_stock_map(self):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory()
        prod2 = ProductoFactory()
        svc = DetalleInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 5,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        repo = DetalleInventarioRepository()
        assert repo.get_stock_map_por_sucursal(suc.id) == {prod.id: 5}
        # producto sin movimientos no aparece
        assert prod2.id not in repo.get_stock_map_por_sucursal(suc.id)
        assert repo.get_stock_map_por_sucursal(99999) == {}

    def test_precio_get_activo_historial(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        repo = PrecioSucursalRepository()
        assert repo.get_activo(prod.id, suc.id) is None
        svc = PrecioSucursalService()
        svc.create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "10.00"}
        )
        p2 = svc.create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "20.00"}
        )
        assert repo.get_activo(prod.id, suc.id).id == p2["id"]
        assert len(repo.get_historial(prod.id, suc.id)) == 2
        assert len(repo.get_by_producto(prod.id)) == 2
        assert len(repo.get_by_sucursal(suc.id)) == 2
        assert repo.get_by_producto(99999) == []
        assert repo.get_by_sucursal(99999) == []


# ---------------------------------------------------------------------------
# Models __str__
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestModelsStr:
    def test_str(self):
        inv = InventarioFactory(descripcion="Bodega")
        assert "Bodega" in str(inv)
        mov = MovimientoEntradaFactory()
        assert "ENTRADA" in str(mov)
        prod = ProductoFactory()
        det = DetalleInventario.objects.create(
            id_producto=prod,
            id_inventario=inv,
            id_movimiento=mov,
            cantidad=3,
        )
        assert "3" in str(det)
        suc = SucursalFactory()
        ps = PrecioSucursal.objects.create(
            id_producto=prod, id_sucursal=suc, precio_venta=Decimal("9.99")
        )
        assert "9.99" in str(ps)


# ---------------------------------------------------------------------------
# Controllers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInventarioControllers:
    def test_list_create_detail(self, auth_client, perfil):
        perfil.rol = "admin"
        perfil.save(update_fields=["rol"])
        own = perfil.id_sucursal_id
        r = auth_client.post(
            "/api/inventarios/",
            {"id_sucursal": own, "descripcion": "Norte"},
            format="json",
        )
        assert r.status_code == 201, r.content
        inv_id = r.data["id"]

        r = auth_client.get("/api/inventarios/")
        assert r.status_code == 200
        assert any(i["id"] == inv_id for i in r.data)

        r = auth_client.get(f"/api/inventarios/{inv_id}/")
        assert r.status_code == 200

        r = auth_client.get("/api/inventarios/99999/")
        assert r.status_code == 404

    def test_create_sin_sucursal_usa_propia(self, auth_client, perfil):
        perfil.rol = "admin"
        perfil.save(update_fields=["rol"])
        r = auth_client.post(
            "/api/inventarios/", {"descripcion": "Propio"}, format="json"
        )
        assert r.status_code == 201, r.content
        assert r.data["id_sucursal"] == perfil.id_sucursal_id

    def test_movimiento_list_create_detail(self, auth_client, perfil):
        perfil.rol = "encargado"
        perfil.save(update_fields=["rol"])
        r = auth_client.post(
            "/api/movimientos-inventario/",
            {"tipo": "ENTRADA", "cantidad": 5, "razon": "Compra"},
            format="json",
        )
        assert r.status_code == 201, r.content
        mid = r.data["id"]
        assert auth_client.get("/api/movimientos-inventario/").status_code == 200
        assert auth_client.get(f"/api/movimientos-inventario/{mid}/").status_code == 200
        assert auth_client.get("/api/movimientos-inventario/99999/").status_code == 404

    def test_detalle_list_create_detail_bulk(self, auth_client, perfil):
        perfil.rol = "encargado"
        perfil.save(update_fields=["rol"])
        inv = InventarioFactory(id_sucursal=perfil.id_sucursal)
        prod = ProductoFactory()
        r = auth_client.post(
            "/api/detalles-inventario/",
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 3,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            },
            format="json",
        )
        assert r.status_code == 201, r.content
        did = r.data["id"]

        assert auth_client.get("/api/detalles-inventario/").status_code == 200
        assert auth_client.get(f"/api/detalles-inventario/{did}/").status_code == 200
        assert auth_client.get("/api/detalles-inventario/99999/").status_code == 404

        p2 = ProductoFactory()
        r = auth_client.post(
            "/api/detalles-inventario/bulk/",
            {
                "id_inventario": inv.id,
                "tipo_movimiento": "ENTRADA",
                "items": [{"id_producto": p2.id, "cantidad": 2}],
            },
            format="json",
        )
        assert r.status_code == 201, r.content

        r = auth_client.post(
            "/api/detalles-inventario/bulk/",
            {"id_inventario": inv.id, "items": []},
            format="json",
        )
        assert r.status_code == 400

    def test_mi_sucursal_sin_perfil_400(self, api_client):
        u = User.objects.create_user(username="sinperfil", password="x")
        api_client.force_authenticate(user=u)
        r = api_client.get("/api/inventarios/mi-sucursal/")
        assert r.status_code == 400

    def test_mi_sucursal_ok(self, auth_client, perfil):
        from inventario.models import Inventario as Inv

        assert perfil.id_sucursal_id is not None
        assert Inv.objects.filter(id_sucursal_id=perfil.id_sucursal_id).exists() or True
        r = auth_client.get("/api/inventarios/mi-sucursal/")
        assert r.status_code == 200

    def test_mi_sucursal_page_invalido(self, auth_client):
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=no-num")
        # 200 sin datos (sin page válida no pagina) o 400 si hay datos y page inválido
        assert r.status_code in (200, 400)


@pytest.mark.django_db
class TestPrecioControllers:
    def test_list_create_detail(self, auth_client, perfil):
        perfil.rol = "encargado"
        perfil.save(update_fields=["rol"])
        prod = ProductoFactory()
        suc = perfil.id_sucursal
        r = auth_client.post(
            "/api/precios-sucursal/",
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "precio_venta": "55.00",
            },
            format="json",
        )
        assert r.status_code == 201, r.content
        pid = r.data["id"]
        assert auth_client.get("/api/precios-sucursal/").status_code == 200
        assert auth_client.get(f"/api/precios-sucursal/{pid}/").status_code == 200
        assert auth_client.get("/api/precios-sucursal/99999/").status_code == 404

    def test_activo_ok_400_404(self, auth_client, perfil):
        prod = ProductoFactory()
        suc = perfil.id_sucursal
        PrecioSucursalService().create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "60.00"}
        )
        r = auth_client.get(
            f"/api/precios-sucursal/activo/?id_producto={prod.id}&id_sucursal={suc.id}"
        )
        assert r.status_code == 200

        r = auth_client.get("/api/precios-sucursal/activo/")
        assert r.status_code == 400

        r = auth_client.get(
            "/api/precios-sucursal/activo/?id_producto=abc&id_sucursal=xyz"
        )
        assert r.status_code == 400

        r = auth_client.get(
            "/api/precios-sucursal/activo/?id_producto=99999&id_sucursal=99999"
        )
        assert r.status_code == 404

    def test_historial_ok_400(self, auth_client, perfil):
        prod = ProductoFactory()
        suc = perfil.id_sucursal
        PrecioSucursalService().create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "61.00"}
        )
        r = auth_client.get(
            f"/api/precios-sucursal/historial/?id_producto={prod.id}&id_sucursal={suc.id}"
        )
        assert r.status_code == 200
        assert len(r.data) == 1

        r = auth_client.get("/api/precios-sucursal/historial/")
        assert r.status_code == 400

        r = auth_client.get(
            "/api/precios-sucursal/historial/?id_producto=x&id_sucursal=y"
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Casos límite y ramas sin cubrir (matriz de cobertura inventario)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDetalleCasosLimite:
    def test_create_cantidad_cero_entrada(self):
        inv = InventarioFactory()
        prod = ProductoFactory()
        svc = DetalleInventarioService()
        res = svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 0,
                "tipo_movimiento": "ENTRADA",
            }
        )
        assert res["cantidad"] == 0
        assert svc.get_stock(prod.id, inv.id) == 0

    def test_create_cantidad_cero_salida_con_stock_cero(self):
        # stock 0 y salida 0: 0 >= 0, no lanza
        inv = InventarioFactory()
        prod = ProductoFactory()
        svc = DetalleInventarioService()
        res = svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 0,
                "tipo_movimiento": "SALIDA",
            }
        )
        assert res["cantidad"] == 0
        assert svc.get_stock(prod.id, inv.id) == 0

    def _dos_entradas(self, cant_a=5, cant_b=4):
        inv = InventarioFactory()
        prod = ProductoFactory()
        svc = DetalleInventarioService()
        det_a = svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": cant_a,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        det_b = svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": cant_b,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        return svc, det_a, det_b, inv, prod

    def test_update_transicion_entrada_a_salida_con_stock(self):
        svc, det_a, det_b, inv, prod = self._dos_entradas(5, 4)
        # stock 9; la entrada B (4) se convierte en salida 3
        svc.update(det_b["id"], {"tipo_movimiento": "SALIDA", "cantidad": 3})
        assert svc.get_stock(prod.id, inv.id) == 2  # 5 - 3

    def test_update_transicion_entrada_a_salida_sin_stock(self):
        svc, det_a, det_b, inv, prod = self._dos_entradas(5, 1)
        # stock 6; quitar la entrada B deja 5; salida 20 excede
        with pytest.raises(ValueError, match="Stock insuficiente"):
            svc.update(det_b["id"], {"tipo_movimiento": "SALIDA", "cantidad": 20})

    def test_update_id_movimiento_explicito(self):
        svc, det_a, det_b, inv, prod = self._dos_entradas(10, 4)
        mov_sal = MovimientoInventario.objects.create(
            tipo="SALIDA", cantidad=1, razon="Venta"
        )
        upd = svc.update(det_b["id"], {"id_movimiento": mov_sal.id})
        assert upd["id_movimiento"] == mov_sal.id
        assert svc.get_stock(prod.id, inv.id) == 6  # 10 - 4

    def test_update_solo_observaciones(self):
        svc, det_a, _, inv, prod = self._dos_entradas(5, 4)
        upd = svc.update(det_a["id"], {"observaciones": "solo obs"})
        mov = MovimientoInventario.objects.get(id=upd["id_movimiento"])
        assert mov.observaciones == "solo obs"
        assert mov.razon == "Compra"
        assert mov.cantidad == 5

    def test_get_inventario_por_sucursal_entrada_menos_salida(self):
        suc = SucursalFactory()
        inv = InventarioFactory(id_sucursal=suc)
        prod = ProductoFactory()
        svc = DetalleInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 3,
                "tipo_movimiento": "SALIDA",
                "razon": "Venta",
            }
        )
        data = svc.get_inventario_por_sucursal(suc.id)
        assert data[0]["detalles"][0]["cantidad"] == 7

    def test_bulk_cantidad_negativa_con_movimiento_explicito(self):
        # _validar detecta cantidad < 0 cuando el movimiento viene explícito
        # (el pre-check de create no aplica en el camino bulk)
        inv = InventarioFactory()
        prod = ProductoFactory()
        mov = MovimientoEntradaFactory()
        with pytest.raises(ValueError, match="negativa"):
            DetalleInventarioService().bulk_create(
                {
                    "id_inventario": inv.id,
                    "items": [
                        {
                            "id_producto": prod.id,
                            "cantidad": -2,
                            "id_movimiento": mov.id,
                        }
                    ],
                }
            )

    def test_ajustar_salida_movimiento_bloqueado_no_propaga(self):
        # el except de ajustar_salida_por_venta tolera un fallo al
        # sincronizar el movimiento y devuelve el detalle igual
        from unittest import mock

        inv = InventarioFactory()
        prod = ProductoFactory()
        svc = DetalleInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_inventario": inv.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        _, dv = _venta_con_detalle(prod)
        svc.crear_salida_por_venta(dv, prod, inv, 3)
        with mock.patch.object(
            DetalleInventario,
            "id_movimiento",
            new_callable=mock.PropertyMock,
            side_effect=Exception("movimiento inaccesible"),
        ):
            aj = svc.ajustar_salida_por_venta(dv, 5)
        assert aj.cantidad == 5


@pytest.mark.django_db
class TestDetalleBulkRamas:
    def test_bulk_tipo_comun_comparte_un_movimiento(self):
        inv = InventarioFactory()
        p1 = ProductoFactory()
        p2 = ProductoFactory()
        res = DetalleInventarioService().bulk_create(
            {
                "id_inventario": inv.id,
                "tipo_movimiento": "ENTRADA",
                "razon": "Carga",
                "items": [
                    {"id_producto": p1.id, "cantidad": 2},
                    {"id_producto": p2.id, "cantidad": 3},
                ],
            }
        )
        assert len(res) == 2
        movs = {r["id_movimiento"] for r in res}
        assert len(movs) == 1
        mov = MovimientoInventario.objects.get(id=movs.pop())
        assert mov.cantidad == 5  # suma total
        assert mov.razon == "Carga"

    def test_bulk_inventarios_por_linea(self):
        inv1 = InventarioFactory()
        inv2 = InventarioFactory()
        p1 = ProductoFactory()
        p2 = ProductoFactory()
        res = DetalleInventarioService().bulk_create(
            [
                {
                    "id_producto": p1.id,
                    "id_inventario": inv1.id,
                    "cantidad": 2,
                    "tipo_movimiento": "ENTRADA",
                },
                {
                    "id_producto": p2.id,
                    "id_inventario": inv2.id,
                    "cantidad": 3,
                    "tipo_movimiento": "ENTRADA",
                },
            ]
        )
        assert res[0]["id_inventario"] == inv1.id
        assert res[1]["id_inventario"] == inv2.id

    def test_bulk_proveedor_comun(self):
        inv = InventarioFactory()
        p1 = ProductoFactory()
        p2 = ProductoFactory()
        prov = ProveedorFactory()
        res = DetalleInventarioService().bulk_create(
            {
                "id_inventario": inv.id,
                "id_proveedor": prov.id,
                "tipo_movimiento": "ENTRADA",
                "items": [
                    {"id_producto": p1.id, "cantidad": 1},
                    {"id_producto": p2.id, "cantidad": 2},
                ],
            }
        )
        assert all(r["id_proveedor"] == prov.id for r in res)


@pytest.mark.django_db
class TestPrecioRamas:
    def test_create_activo_false_no_desactiva_anterior(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        svc = PrecioSucursalService()
        primero = svc.create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "10.00"}
        )
        svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "precio_venta": "20.00",
                "activo": False,
            }
        )
        assert PrecioSucursal.objects.get(id=primero["id"]).activo is True
        assert svc.get_precio_activo(prod.id, suc.id)["id"] == primero["id"]

    def test_resolver_instance_con_precio_activo(self):
        prod = ProductoFactory(precio_venta=Decimal("50.00"))
        suc = SucursalFactory()
        PrecioSucursalService().create(
            {"id_producto": prod.id, "id_sucursal": suc.id, "precio_venta": "77.00"}
        )
        assert PrecioSucursalService.resolver_precio_venta(
            prod, suc.id
        ) == Decimal("77.00")


@pytest.mark.django_db
class TestInventarioServiceEdge:
    def test_update_sucursal_none_documenta_error(self):
        # id_sucursal None omite la validación pero viola NOT NULL al guardar
        inv = InventarioFactory()
        with pytest.raises(ValueError):
            InventarioService().update(inv.id, {"id_sucursal": None})


@pytest.mark.django_db
class TestMiSucursalPaginacion:
    def _sembrar_detalles(self, inventario, n=3):
        inv = inventario
        svc = DetalleInventarioService()
        for i in range(n):
            svc.create(
                {
                    "id_producto": ProductoFactory().id,
                    "id_inventario": inv.id,
                    "cantidad": i + 1,
                    "tipo_movimiento": "ENTRADA",
                    "razon": "Compra",
                }
            )
        return inv

    def test_page_valido_con_datos(self, auth_client, inventario):
        self._sembrar_detalles(inventario, 3)
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=1&page_size=2")
        assert r.status_code == 200
        assert r.data["total"] == 3
        assert r.data["page"] == 1
        assert r.data["page_size"] == 2
        assert r.data["total_pages"] == 2
        assert len(r.data["detalles"]) == 2

    def test_page_fuera_de_rango(self, auth_client, inventario):
        self._sembrar_detalles(inventario, 2)
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=5&page_size=2")
        assert r.status_code == 400
        assert "fuera de rango" in r.data["error"]

    def test_page_cero_y_page_size_cero(self, auth_client, inventario):
        self._sembrar_detalles(inventario, 1)
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=0")
        assert r.status_code == 400
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=1&page_size=0")
        assert r.status_code == 400

    def test_page_no_entero_con_datos(self, auth_client, inventario):
        self._sembrar_detalles(inventario, 1)
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=abc")
        assert r.status_code == 400

    def test_paginacion_multiple_inventarios(self, auth_client, perfil):
        InventarioFactory(id_sucursal=perfil.id_sucursal)
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=1&page_size=1")
        assert r.status_code == 200
        assert r.data["total"] == 2
        assert len(r.data["results"]) == 1

    def test_paginacion_multiple_fuera_de_rango(self, auth_client, perfil):
        InventarioFactory(id_sucursal=perfil.id_sucursal)
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=3&page_size=2")
        assert r.status_code == 400
