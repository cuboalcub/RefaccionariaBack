"""Tests extra inventario: ramas restantes de services, repos, controllers y models."""

import pytest
from decimal import Decimal

from django.contrib.auth.models import User

from inventario.models import Stock, MovimientoInventario, PrecioSucursal
from inventario.repositories.stock_repository import StockRepository
from inventario.repositories.precio_sucursal_repository import (
    PrecioSucursalRepository,
)
from inventario.services.movimiento_inventario_service import (
    MovimientoInventarioService,
)
from inventario.services.precio_sucursal_service import PrecioSucursalService
from repository.exceptions import NotFoundError
from tests.factories import (
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
# MovimientoInventarioService
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMovimientoServiceExtra:
    def test_crud_basico(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        res = svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "tipo": "ENTRADA",
                "cantidad": 5,
                "razon": "Compra",
            }
        )
        assert res["tipo"] == "ENTRADA"
        assert res["id_sucursal"] == suc.id
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
        from tests.factories import MovimientoEntradaFactory

        mov = MovimientoEntradaFactory()
        # fecha NOT NULL en DB: solo anular en memoria para rama None
        mov.fecha = None
        d = MovimientoInventarioService()._to_dict(mov)
        assert d["fecha"] is None
        assert d["razon"] == "Compra inicial"

    def test_get_stock_map_por_sucursal(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 7,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        assert svc.get_stock_map_por_sucursal(suc.id) == {prod.id: 7}


# ---------------------------------------------------------------------------
# MovimientoInventarioService: _validar
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMovimientoValidar:
    def test_falta_producto(self):
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="id_producto"):
            MovimientoInventarioService().create({"id_sucursal": suc.id, "cantidad": 1})

    def test_falta_sucursal(self):
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="id_sucursal"):
            MovimientoInventarioService().create({"id_producto": prod.id, "cantidad": 1})

    def test_falta_cantidad(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="cantidad"):
            MovimientoInventarioService().create(
                {"id_producto": prod.id, "id_sucursal": suc.id}
            )

    def test_producto_inexistente(self):
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="producto"):
            MovimientoInventarioService()._validar(
                {"id_producto": 99999, "id_sucursal": suc.id, "cantidad": 1}
            )

    def test_sucursal_inexistente(self):
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="sucursal"):
            MovimientoInventarioService()._validar(
                {"id_producto": prod.id, "id_sucursal": 99999, "cantidad": 1}
            )

    def test_id_movimiento_externo_deprecado(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="deprecado"):
            MovimientoInventarioService().create(
                {
                    "id_producto": prod.id,
                    "id_sucursal": suc.id,
                    "id_movimiento": 1,
                    "cantidad": 1,
                }
            )

    def test_movimiento_inexistente_bulk(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="deprecado"):
            MovimientoInventarioService().bulk_create(
                {
                    "id_sucursal": suc.id,
                    "id_movimiento": 99999,
                    "items": [{"id_producto": prod.id, "cantidad": 1}],
                }
            )

    def test_tipo_invalido(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="ENTRADA o SALIDA"):
            MovimientoInventarioService()._validar(
                {
                    "id_producto": prod.id,
                    "id_sucursal": suc.id,
                    "cantidad": 1,
                    "tipo_movimiento": "ROBO",
                }
            )

    def test_create_tipo_invalido(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="ENTRADA o SALIDA"):
            MovimientoInventarioService().create(
                {
                    "id_producto": prod.id,
                    "id_sucursal": suc.id,
                    "cantidad": 1,
                    "tipo_movimiento": "ROBO",
                }
            )

    def test_create_proveedor_inexistente(self):
        prod = ProductoFactory()
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="proveedor"):
            MovimientoInventarioService().create(
                {
                    "id_producto": prod.id,
                    "id_sucursal": suc.id,
                    "id_proveedor": 99999,
                    "cantidad": 1,
                }
            )

    def test_to_dict_none(self):
        assert MovimientoInventarioService()._to_dict(None) is None


# ---------------------------------------------------------------------------
# MovimientoInventarioService: update / delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMovimientoUpdateDelete:
    def _entrada(self, cantidad=5):
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        res = svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": cantidad,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        return svc, res, suc, prod

    def test_update_not_found(self):
        with pytest.raises(NotFoundError):
            MovimientoInventarioService().update(99999, {"cantidad": 1})

    def test_update_cantidad_ok(self):
        svc, res, suc, prod = self._entrada()
        upd = svc.update(res["id"], {"cantidad": 8})
        assert upd["cantidad"] == 8
        assert svc.get_stock(prod.id, suc.id) == 8

    def test_update_cantidad_negativa(self):
        svc, res, suc, prod = self._entrada()
        with pytest.raises(ValueError, match="negativa"):
            svc.update(res["id"], {"cantidad": -2})

    def test_update_salida_sin_stock(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 5,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        res = svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 3,
                "tipo_movimiento": "SALIDA",
                "razon": "Venta",
            }
        )
        with pytest.raises(ValueError, match="Stock insuficiente"):
            svc.update(res["id"], {"cantidad": 100})
        svc.update(res["id"], {"cantidad": 5})
        assert svc.get_stock(prod.id, suc.id) == 0

    def test_update_cambia_producto_e_sucursal(self):
        svc, res, suc, prod = self._entrada()
        prod2 = ProductoFactory()
        suc2 = SucursalFactory()
        upd = svc.update(res["id"], {"id_producto": prod2.id, "id_sucursal": suc2.id})
        assert upd["id_producto"] == prod2.id
        assert upd["id_sucursal"] == suc2.id
        assert svc.get_stock(prod.id, suc.id) == 0
        assert svc.get_stock(prod2.id, suc2.id) == 5

    def test_update_producto_inexistente(self):
        svc, res, suc, prod = self._entrada()
        with pytest.raises(ValueError, match="producto"):
            svc.update(res["id"], {"id_producto": 99999})

    def test_update_sucursal_inexistente(self):
        svc, res, suc, prod = self._entrada()
        with pytest.raises(ValueError, match="sucursal"):
            svc.update(res["id"], {"id_sucursal": 99999})

    def test_update_proveedor_invalido(self):
        svc, res, suc, prod = self._entrada()
        with pytest.raises(ValueError, match="proveedor"):
            svc.update(res["id"], {"id_proveedor": 99999})

    def test_update_proveedor_none(self):
        svc, res, suc, prod = self._entrada()
        prov = ProveedorFactory()
        svc.update(res["id"], {"id_proveedor": prov.id})
        upd = svc.update(res["id"], {"id_proveedor": None})
        assert upd["id_proveedor"] is None

    def test_update_tipo_movimiento_invalido(self):
        svc, res, suc, prod = self._entrada()
        with pytest.raises(ValueError, match="ENTRADA o SALIDA"):
            svc.update(res["id"], {"tipo_movimiento": "ROBO"})

    def test_update_razon_y_observaciones(self):
        svc, res, suc, prod = self._entrada()
        upd = svc.update(res["id"], {"razon": "Ajuste", "observaciones": "obs"})
        assert upd["razon"] == "Ajuste"
        assert upd["observaciones"] == "obs"

    def test_delete_ok_y_not_found(self):
        svc, res, suc, prod = self._entrada()
        assert "eliminado" in svc.delete(res["id"])["message"].lower()
        with pytest.raises(NotFoundError):
            svc.delete(99999)

    def test_delete_salida_devuelve_stock(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 9,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        sal = svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 4,
                "tipo_movimiento": "SALIDA",
                "razon": "Venta",
            }
        )
        assert svc.get_stock(prod.id, suc.id) == 5
        svc.delete(sal["id"])
        assert svc.get_stock(prod.id, suc.id) == 9


# ---------------------------------------------------------------------------
# MovimientoInventarioService: ventas / stock / sucursal
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDetalleVentaHelpers:
    def test_crear_ajustar_revertir_salida(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        _, dv = _venta_con_detalle(prod)
        det = svc.crear_salida_por_venta(dv, prod, suc.id, 3)
        assert det["cantidad"] == 3
        assert det["id_usuario"] is None
        assert svc.get_stock(prod.id, suc.id) == 7

        aj = svc.ajustar_salida_por_venta(dv, 5)
        assert aj["cantidad"] == 5
        assert svc.get_stock(prod.id, suc.id) == 5

        with pytest.raises(ValueError, match="Stock insuficiente"):
            svc.ajustar_salida_por_venta(dv, 100)

        assert svc.revertir_salida_por_venta(dv) is True
        assert svc.get_stock(prod.id, suc.id) == 10

    def test_ajustar_salida_cambia_sucursal(self):
        suc = SucursalFactory()
        suc2 = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        _, dv = _venta_con_detalle(prod)
        svc.crear_salida_por_venta(dv, prod, suc.id, 3)
        svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc2.id,
                "cantidad": 8,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        aj = svc.ajustar_salida_por_venta(dv, 5, sucursal_id=suc2.id)
        assert aj["id_sucursal"] == suc2.id
        assert svc.get_stock(prod.id, suc.id) == 10
        assert svc.get_stock(prod.id, suc2.id) == 3

    def test_ajustar_salida_a_sucursal_sin_stock(self):
        suc = SucursalFactory()
        suc2 = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        _, dv = _venta_con_detalle(prod)
        svc.crear_salida_por_venta(dv, prod, suc.id, 3)
        with pytest.raises(ValueError, match="Stock insuficiente"):
            svc.ajustar_salida_por_venta(dv, 5, sucursal_id=suc2.id)

    def test_ajustar_y_revertir_sin_detalle(self):
        prod = ProductoFactory()
        _, dv = _venta_con_detalle(prod)
        svc = MovimientoInventarioService()
        assert svc.ajustar_salida_por_venta(dv, 5) is None
        assert svc.revertir_salida_por_venta(dv) is None

    def test_get_stock_service(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        assert svc.get_stock(prod.id, suc.id) == 0
        svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 6,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        assert svc.get_stock(prod.id, suc.id) == 6

    def test_crear_salida_por_venta_sin_stock(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        _, dv = _venta_con_detalle(prod)
        with pytest.raises(ValueError, match="Stock insuficiente"):
            MovimientoInventarioService().crear_salida_por_venta(
                dv, prod, suc.id, 1
            )

    def test_get_inventario_por_sucursal_vacio(self):
        suc = SucursalFactory()
        data = MovimientoInventarioService().get_inventario_por_sucursal(suc.id)
        assert data == {"id_sucursal": suc.id, "detalles": []}

    def test_get_inventario_sin_precio_sucursal(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        MovimientoInventarioService().create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 2,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        data = MovimientoInventarioService().get_inventario_por_sucursal(suc.id)
        assert data["detalles"][0]["precio_sucursal"] is None
        assert data["detalles"][0]["vigente_desde"] is None


# ---------------------------------------------------------------------------
# MovimientoInventarioService: bulk_create formatos
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDetalleBulkFormatos:
    def test_lista_plana(self):
        suc = SucursalFactory()
        p1 = ProductoFactory()
        p2 = ProductoFactory()
        res = MovimientoInventarioService().bulk_create(
            [
                {
                    "id_producto": p1.id,
                    "id_sucursal": suc.id,
                    "cantidad": 2,
                    "tipo_movimiento": "ENTRADA",
                    "razon": "Carga",
                },
                {
                    "id_producto": p2.id,
                    "id_sucursal": suc.id,
                    "cantidad": 3,
                    "tipo_movimiento": "ENTRADA",
                    "razon": "Carga",
                },
            ]
        )
        assert len(res) == 2

    def test_dict_unico(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        res = MovimientoInventarioService().bulk_create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 4,
            }
        )
        assert len(res) == 1

    def test_alias_detalles(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        res = MovimientoInventarioService().bulk_create(
            {
                "id_sucursal": suc.id,
                "tipo_movimiento": "ENTRADA",
                "razon": "Carga",
                "detalles": [{"id_producto": prod.id, "cantidad": 5}],
            }
        )
        assert len(res) == 1

    def test_formato_invalido(self):
        with pytest.raises(ValueError, match="bulk inválido"):
            MovimientoInventarioService().bulk_create("no-es-lista-ni-dict")

    def test_item_no_dict(self):
        suc = SucursalFactory()
        with pytest.raises(ValueError, match="debe ser un objeto"):
            MovimientoInventarioService().bulk_create(
                {"id_sucursal": suc.id, "items": ["texto"]}
            )

    def test_proveedor_invalido(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="proveedor"):
            MovimientoInventarioService().bulk_create(
                {
                    "id_sucursal": suc.id,
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
        suc = SucursalFactory()
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="Stock insuficiente"):
            MovimientoInventarioService().bulk_create(
                {
                    "id_sucursal": suc.id,
                    "tipo_movimiento": "SALIDA",
                    "razon": "Venta",
                    "items": [{"id_producto": prod.id, "cantidad": 9}],
                }
            )

    def test_bulk_tipo_invalido_por_item(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        with pytest.raises(ValueError, match="ENTRADA o SALIDA"):
            MovimientoInventarioService().bulk_create(
                {
                    "id_sucursal": suc.id,
                    "items": [
                        {
                            "id_producto": prod.id,
                            "cantidad": 1,
                            "tipo_movimiento": "ROBO",
                        }
                    ],
                }
            )


@pytest.mark.django_db
class TestDetalleBulkRamas:
    def test_bulk_un_movimiento_por_linea(self):
        suc = SucursalFactory()
        p1 = ProductoFactory()
        p2 = ProductoFactory()
        res = MovimientoInventarioService().bulk_create(
            {
                "id_sucursal": suc.id,
                "tipo_movimiento": "ENTRADA",
                "razon": "Carga",
                "items": [
                    {"id_producto": p1.id, "cantidad": 2},
                    {"id_producto": p2.id, "cantidad": 3},
                ],
            }
        )
        assert len(res) == 2
        movs = {r["id"] for r in res}
        assert len(movs) == 2
        for mov_id, expected in zip(sorted(movs), (2, 3)):
            mov = MovimientoInventario.objects.get(id=mov_id)
            assert mov.cantidad == expected
            assert mov.razon == "Carga"
            assert mov.id_sucursal_id == suc.id

    def test_bulk_sucursales_por_linea(self):
        suc1 = SucursalFactory()
        suc2 = SucursalFactory()
        p1 = ProductoFactory()
        p2 = ProductoFactory()
        res = MovimientoInventarioService().bulk_create(
            [
                {
                    "id_producto": p1.id,
                    "id_sucursal": suc1.id,
                    "cantidad": 2,
                    "tipo_movimiento": "ENTRADA",
                },
                {
                    "id_producto": p2.id,
                    "id_sucursal": suc2.id,
                    "cantidad": 3,
                    "tipo_movimiento": "ENTRADA",
                },
            ]
        )
        assert res[0]["id_sucursal"] == suc1.id
        assert res[1]["id_sucursal"] == suc2.id

    def test_bulk_proveedor_comun(self):
        suc = SucursalFactory()
        p1 = ProductoFactory()
        p2 = ProductoFactory()
        prov = ProveedorFactory()
        res = MovimientoInventarioService().bulk_create(
            {
                "id_sucursal": suc.id,
                "id_proveedor": prov.id,
                "tipo_movimiento": "ENTRADA",
                "items": [
                    {"id_producto": p1.id, "cantidad": 1},
                    {"id_producto": p2.id, "cantidad": 2},
                ],
            }
        )
        assert all(r["id_proveedor"] == prov.id for r in res)


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
    def test_stock_repo_por_sucursal(self):
        suc1 = SucursalFactory()
        suc2 = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        for suc, cant in ((suc1, 4), (suc2, 6)):
            svc.create(
                {
                    "id_producto": prod.id,
                    "id_sucursal": suc.id,
                    "cantidad": cant,
                    "tipo_movimiento": "ENTRADA",
                    "razon": "Compra",
                }
            )
        repo = StockRepository()
        assert repo.get_stock(prod.id, suc1.id) == 4
        assert repo.get_stock(prod.id, suc2.id) == 6
        assert repo.get_stock(prod.id, 99999) == 0

    def test_get_stock_map(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        prod2 = ProductoFactory()
        svc = MovimientoInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 5,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        repo = StockRepository()
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
        from tests.factories import MovimientoEntradaFactory

        suc = SucursalFactory()
        prod = ProductoFactory()
        mov = MovimientoEntradaFactory(cantidad=3, id_producto=prod, id_sucursal=suc)
        assert "ENTRADA" in str(mov)
        st = Stock.objects.create(id_producto=prod, id_sucursal=suc, cantidad=3)
        assert "3" in str(st)
        ps = PrecioSucursal.objects.create(
            id_producto=prod, id_sucursal=suc, precio_venta=Decimal("9.99")
        )
        assert "9.99" in str(ps)


# ---------------------------------------------------------------------------
# Controllers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInventarioControllers:
    def test_movimiento_list_create_detail(self, auth_client, perfil):
        perfil.rol = "encargado"
        perfil.save(update_fields=["rol"])
        prod = ProductoFactory()
        r = auth_client.post(
            "/api/movimientos-inventario/",
            {
                "id_producto": prod.id,
                "id_sucursal": perfil.id_sucursal_id,
                "tipo": "ENTRADA",
                "cantidad": 5,
                "razon": "Compra",
            },
            format="json",
        )
        assert r.status_code == 201, r.content
        assert r.data["id_usuario"] == perfil.usuario_id
        mid = r.data["id"]
        assert auth_client.get("/api/movimientos-inventario/").status_code == 200
        assert auth_client.get(f"/api/movimientos-inventario/{mid}/").status_code == 200
        assert auth_client.get("/api/movimientos-inventario/99999/").status_code == 404

    def test_movimiento_put_delete_y_errores(self, auth_client, perfil):
        perfil.rol = "encargado"
        perfil.save(update_fields=["rol"])
        prod = ProductoFactory()
        m = MovimientoInventarioService().create(
            {
                "id_producto": prod.id,
                "id_sucursal": perfil.id_sucursal_id,
                "cantidad": 5,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        r = auth_client.put(
            f"/api/movimientos-inventario/{m['id']}/",
            {"cantidad": 4},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["cantidad"] == 4
        assert (
            auth_client.put(
                "/api/movimientos-inventario/99999/", {"cantidad": 4}, format="json"
            ).status_code
            == 404
        )
        assert (
            auth_client.put(
                f"/api/movimientos-inventario/{m['id']}/",
                {"cantidad": -1},
                format="json",
            ).status_code
            == 400
        )
        assert (
            auth_client.delete(f"/api/movimientos-inventario/{m['id']}/").status_code
            == 200
        )
        assert (
            auth_client.delete("/api/movimientos-inventario/99999/").status_code == 404
        )

    def test_movimiento_post_invalido_400(self, auth_client, perfil):
        perfil.rol = "encargado"
        perfil.save(update_fields=["rol"])
        r = auth_client.post(
            "/api/movimientos-inventario/", {"id_producto": 1}, format="json"
        )
        assert r.status_code == 400

    def test_detalle_list_create_detail_bulk(self, auth_client, perfil):
        perfil.rol = "encargado"
        perfil.save(update_fields=["rol"])
        suc_id = perfil.id_sucursal_id
        prod = ProductoFactory()
        r = auth_client.post(
            "/api/detalles-inventario/",
            {
                "id_producto": prod.id,
                "id_sucursal": suc_id,
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
                "id_sucursal": suc_id,
                "tipo_movimiento": "ENTRADA",
                "items": [{"id_producto": p2.id, "cantidad": 2}],
            },
            format="json",
        )
        assert r.status_code == 201, r.content

        r = auth_client.post(
            "/api/detalles-inventario/bulk/",
            {"id_sucursal": suc_id, "items": []},
            format="json",
        )
        assert r.status_code == 400

    def test_stock_list_staff_con_filtro(self, auth_client):
        u = User.objects.create_user(username="staffer", password="x", is_staff=True)
        auth_client.force_authenticate(user=u)
        r = auth_client.get("/api/stock/")
        assert r.status_code == 200
        r = auth_client.get("/api/stock/?sucursal_id=no-num")
        assert r.status_code == 400

    def test_stock_list_no_staff_forzada_propia(self, auth_client, perfil):
        r = auth_client.get("/api/stock/")
        assert r.status_code == 200
        r = auth_client.get("/api/stock/?sucursal_id=1")
        assert r.status_code == 200

    def test_stock_list_sin_sucursal_400(self, api_client):
        u = User.objects.create_user(username="sinsucursal", password="x")
        api_client.force_authenticate(user=u)
        r = api_client.get("/api/stock/")
        assert r.status_code == 400
        assert "error" in r.data

    def test_mi_sucursal_sin_perfil_400(self, api_client):
        u = User.objects.create_user(username="sinperfil", password="x")
        api_client.force_authenticate(user=u)
        r = api_client.get("/api/inventarios/mi-sucursal/")
        assert r.status_code == 400

    def test_mi_sucursal_ok(self, auth_client, perfil):
        assert perfil.id_sucursal_id is not None
        r = auth_client.get("/api/inventarios/mi-sucursal/")
        assert r.status_code == 200
        assert r.data["id_sucursal"] == perfil.id_sucursal_id

    def test_mi_sucursal_page_invalido(self, auth_client):
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=no-num")
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
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        res = svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 0,
                "tipo_movimiento": "ENTRADA",
            }
        )
        assert res["cantidad"] == 0
        assert svc.get_stock(prod.id, suc.id) == 0

    def test_create_cantidad_cero_salida_con_stock_cero(self):
        # stock 0 y salida 0: 0 >= 0, no lanza
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        res = svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 0,
                "tipo_movimiento": "SALIDA",
            }
        )
        assert res["cantidad"] == 0
        assert svc.get_stock(prod.id, suc.id) == 0

    def _dos_entradas(self, cant_a=5, cant_b=4):
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        det_a = svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": cant_a,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        det_b = svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": cant_b,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        return svc, det_a, det_b, suc, prod

    def test_update_transicion_entrada_a_salida_con_stock(self):
        svc, det_a, det_b, suc, prod = self._dos_entradas(5, 4)
        # stock 9; la entrada B (4) se convierte en salida 3
        svc.update(det_b["id"], {"tipo_movimiento": "SALIDA", "cantidad": 3})
        assert svc.get_stock(prod.id, suc.id) == 2  # 5 - 3

    def test_update_transicion_entrada_a_salida_sin_stock(self):
        svc, det_a, det_b, suc, prod = self._dos_entradas(5, 1)
        # stock 6; quitar la entrada B deja 5; salida 20 excede
        with pytest.raises(ValueError, match="Stock insuficiente"):
            svc.update(det_b["id"], {"tipo_movimiento": "SALIDA", "cantidad": 20})

    def test_get_inventario_por_sucursal_entrada_menos_salida(self):
        suc = SucursalFactory()
        prod = ProductoFactory()
        svc = MovimientoInventarioService()
        svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 10,
                "tipo_movimiento": "ENTRADA",
                "razon": "Compra",
            }
        )
        svc.create(
            {
                "id_producto": prod.id,
                "id_sucursal": suc.id,
                "cantidad": 3,
                "tipo_movimiento": "SALIDA",
                "razon": "Venta",
            }
        )
        data = svc.get_inventario_por_sucursal(suc.id)
        assert data["detalles"][0]["cantidad"] == 7


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
class TestMiSucursalPaginacion:
    def _sembrar_detalles(self, sucursal, n=3):
        svc = MovimientoInventarioService()
        for i in range(n):
            svc.create(
                {
                    "id_producto": ProductoFactory().id,
                    "id_sucursal": sucursal.id,
                    "cantidad": i + 1,
                    "tipo_movimiento": "ENTRADA",
                    "razon": "Compra",
                }
            )
        return sucursal

    def test_page_valido_con_datos(self, auth_client, perfil):
        self._sembrar_detalles(perfil.id_sucursal, 3)
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=1&page_size=2")
        assert r.status_code == 200
        assert r.data["total"] == 3
        assert r.data["page"] == 1
        assert r.data["page_size"] == 2
        assert r.data["total_pages"] == 2
        assert len(r.data["detalles"]) == 2

    def test_page_fuera_de_rango(self, auth_client, perfil):
        self._sembrar_detalles(perfil.id_sucursal, 2)
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=5&page_size=2")
        assert r.status_code == 400
        assert "fuera de rango" in r.data["error"]

    def test_page_cero_y_page_size_cero(self, auth_client, perfil):
        self._sembrar_detalles(perfil.id_sucursal, 1)
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=0")
        assert r.status_code == 400
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=1&page_size=0")
        assert r.status_code == 400

    def test_page_no_entero_con_datos(self, auth_client, perfil):
        self._sembrar_detalles(perfil.id_sucursal, 1)
        r = auth_client.get("/api/inventarios/mi-sucursal/?page=abc")
        assert r.status_code == 400
