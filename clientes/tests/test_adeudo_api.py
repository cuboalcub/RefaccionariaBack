"""Pruebas de Adeudo y AbonoAdeudo: modelo, servicios, reglas de saldo y API.

Cubre la creación desde una venta a crédito, el scoping por sucursal
(derivada del cliente), permisos por rol y el flujo de abonos.
"""

from decimal import Decimal

import pytest
from django.db.models import ProtectedError
from rest_framework.test import APIClient

from clientes.models import Adeudo
from clientes.services.adeudo_service import AdeudoService
from clientes.services.abono_adeudo_service import AbonoAdeudoService
from tests.factories import (
    AbonoAdeudoFactory,
    AdeudoFactory,
    ClienteFactory,
    MetodoPagoFactory,
    SucursalFactory,
    UserFactory,
)
from usuario.models import Perfil
from ventas.models import Venta


def _auth(rol="cajero", sucursal=None, staff=False):
    user = UserFactory(is_staff=staff)
    Perfil.objects.create(usuario=user, rol=rol, id_sucursal=sucursal)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _venta(cliente, total="150.00"):
    return Venta.objects.create(
        id_cliente=cliente,
        id_metodo_pago=MetodoPagoFactory(),
        id_sucursal=cliente.id_sucursal,
        total=Decimal(total),
        iva=Decimal("0"),
    )


def _adeudo(cliente, **kw):
    base = {"monto_total": Decimal("100.00"), "saldo": Decimal("100.00")}
    base.update(kw)
    return Adeudo.objects.create(id_cliente=cliente, **base)


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestModelo:
    def test_defaults_y_str(self):
        cliente = ClienteFactory()
        adeudo = AdeudoFactory(id_cliente=cliente)
        assert adeudo.estado == "pendiente"
        assert adeudo.saldo == Decimal("100.00")
        assert str(adeudo).startswith("Adeudo ")
        assert str(AbonoAdeudoFactory(id_adeudo=adeudo)).startswith("Abono ")

    def test_borrar_cliente_con_adeudo_falla(self):
        adeudo = AdeudoFactory()
        with pytest.raises(ProtectedError):
            adeudo.id_cliente.delete()


# ---------------------------------------------------------------------------
# AdeudoService.create
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAdeudoCreate:
    def test_crea_desde_venta_y_deriva_monto(self):
        cliente = ClienteFactory()
        venta = _venta(cliente, "150.00")
        out = AdeudoService().create({"id_cliente": cliente.id, "id_venta": venta.id})
        assert out["monto_total"] == "150.00"
        assert out["saldo"] == "150.00"
        assert out["id_venta"] == venta.id
        assert out["estado"] == "pendiente"

    def test_ignora_saldo_estado_y_sucursal_del_payload(self):
        cliente = ClienteFactory()
        out = AdeudoService().create(
            {
                "id_cliente": cliente.id,
                "monto_total": "80.50",
                "saldo": "0.00",
                "estado": "pagado",
                "id_sucursal": 999,
            }
        )
        assert out["saldo"] == "80.50"
        assert out["estado"] == "pendiente"

    def test_cliente_inexistente(self):
        with pytest.raises(ValueError, match="cliente indicado no existe"):
            AdeudoService().create({"id_cliente": 99999, "monto_total": "10"})

    def test_venta_inexistente(self):
        cliente = ClienteFactory()
        with pytest.raises(ValueError, match="venta indicada no existe"):
            AdeudoService().create({"id_cliente": cliente.id, "id_venta": 99999})

    def test_venta_de_otro_cliente(self):
        cliente = ClienteFactory()
        otro = ClienteFactory()
        venta = _venta(otro)
        with pytest.raises(ValueError, match="no pertenece al cliente"):
            AdeudoService().create({"id_cliente": cliente.id, "id_venta": venta.id})

    def test_venta_duplicada(self):
        cliente = ClienteFactory()
        venta = _venta(cliente)
        AdeudoService().create({"id_cliente": cliente.id, "id_venta": venta.id})
        with pytest.raises(ValueError, match="ya tiene un adeudo"):
            AdeudoService().create({"id_cliente": cliente.id, "id_venta": venta.id})

    def test_sin_monto_ni_venta(self):
        cliente = ClienteFactory()
        with pytest.raises(ValueError, match="monto_total"):
            AdeudoService().create({"id_cliente": cliente.id})

    @pytest.mark.parametrize("monto", ["0", "-5", "0.00"])
    def test_monto_no_positivo(self, monto):
        cliente = ClienteFactory()
        with pytest.raises(ValueError, match="mayor a 0"):
            AdeudoService().create({"id_cliente": cliente.id, "monto_total": monto})

    def test_monto_invalido(self):
        cliente = ClienteFactory()
        with pytest.raises(ValueError, match="monto inválido"):
            AdeudoService().create({"id_cliente": cliente.id, "monto_total": "abc"})


# ---------------------------------------------------------------------------
# AdeudoService.update / delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAdeudoUpdateDelete:
    def test_update_concepto_y_monto_sin_abonos(self):
        adeudo = AdeudoFactory()
        out = AdeudoService().update(
            adeudo.id, {"concepto": "Fiado", "monto_total": "250.00"}
        )
        assert out["concepto"] == "Fiado"
        assert out["monto_total"] == "250.00"
        assert out["saldo"] == "250.00"

    def test_update_ignora_campos_inmutables(self):
        adeudo = AdeudoFactory()
        otro = ClienteFactory()
        out = AdeudoService().update(
            adeudo.id,
            {
                "id_cliente": otro.id,
                "id_venta": 123,
                "saldo": "0",
                "estado": "pagado",
                "monto_total": "",
            },
        )
        assert out["id_cliente"] == adeudo.id_cliente_id
        assert out["estado"] == "pendiente"
        assert out["saldo"] == "100.00"

    def test_update_monto_con_abonos_falla(self):
        adeudo = AdeudoFactory()
        AbonoAdeudoFactory(id_adeudo=adeudo, monto=Decimal("10.00"))
        with pytest.raises(ValueError, match="con abonos registrados"):
            AdeudoService().update(adeudo.id, {"monto_total": "200.00"})

    def test_update_monto_invalido_y_no_positivo(self):
        adeudo = AdeudoFactory()
        with pytest.raises(ValueError, match="monto inválido"):
            AdeudoService().update(adeudo.id, {"monto_total": "abc"})
        with pytest.raises(ValueError, match="mayor a 0"):
            AdeudoService().update(adeudo.id, {"monto_total": "0"})

    def test_update_inexistente(self):
        from repository.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            AdeudoService().update(99999, {"concepto": "x"})

    def test_delete_cancela_e_idempotente(self):
        adeudo = AdeudoFactory()
        out = AdeudoService().delete(adeudo.id)
        assert out["estado"] == "cancelado"
        adeudo.refresh_from_db()
        assert adeudo.estado == "cancelado"
        assert AdeudoService().delete(adeudo.id)["message"].endswith("cancelado")

    def test_delete_inexistente(self):
        from repository.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            AdeudoService().delete(99999)


# ---------------------------------------------------------------------------
# AbonoAdeudoService
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAbonoService:
    def test_abono_parcial_disminuye_saldo(self):
        adeudo = AdeudoFactory()
        out = AbonoAdeudoService().create({"id_adeudo": adeudo.id, "monto": "30.00"})
        assert out["monto"] == "30.00"
        assert out["id_usuario"] is None
        adeudo.refresh_from_db()
        assert adeudo.saldo == Decimal("70.00")
        assert adeudo.estado == "pendiente"

    def test_abono_total_marca_pagado(self):
        adeudo = AdeudoFactory()
        AbonoAdeudoService().create({"id_adeudo": adeudo.id, "monto": "100.00"})
        adeudo.refresh_from_db()
        assert adeudo.saldo == Decimal("0")
        assert adeudo.estado == "pagado"

    def test_abono_con_usuario(self):
        adeudo = AdeudoFactory()
        user = UserFactory()
        out = AbonoAdeudoService().create(
            {"id_adeudo": adeudo.id, "monto": "10"}, user=user
        )
        assert out["id_usuario"] == user.id

    def test_adeudo_inexistente(self):
        with pytest.raises(ValueError, match="adeudo indicado no existe"):
            AbonoAdeudoService().create({"id_adeudo": 99999, "monto": "10"})

    def test_no_abona_adeudo_no_pendiente(self):
        for estado in ("pagado", "cancelado"):
            adeudo = AdeudoFactory(estado=estado)
            with pytest.raises(ValueError, match="pendientes"):
                AbonoAdeudoService().create(
                    {"id_adeudo": adeudo.id, "monto": "10"}
                )

    def test_monto_invalido(self):
        adeudo = AdeudoFactory()
        with pytest.raises(ValueError, match="monto inválido"):
            AbonoAdeudoService().create({"id_adeudo": adeudo.id, "monto": "x"})

    def test_monto_no_positivo(self):
        adeudo = AdeudoFactory()
        with pytest.raises(ValueError, match="mayor a 0"):
            AbonoAdeudoService().create({"id_adeudo": adeudo.id, "monto": "0"})

    def test_monto_sobrepasa_saldo(self):
        adeudo = AdeudoFactory()
        with pytest.raises(ValueError, match="exceder el saldo"):
            AbonoAdeudoService().create({"id_adeudo": adeudo.id, "monto": "100.01"})

    def test_get_all_por_adeudo(self):
        adeudo = AdeudoFactory()
        otro = AdeudoFactory()
        AbonoAdeudoFactory(id_adeudo=adeudo)
        AbonoAdeudoFactory(id_adeudo=otro)
        assert len(AbonoAdeudoService().get_all(adeudo.id)) == 1


# ---------------------------------------------------------------------------
# API: adeudos
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAdeudoAPI:
    def test_listado_staff_filtra_por_sucursal_y_cliente_y_estado(self):
        suc_a, suc_b = SucursalFactory(), SucursalFactory()
        c_a = ClienteFactory(id_sucursal=suc_a)
        c_b = ClienteFactory(id_sucursal=suc_b)
        a = _adeudo(c_a)
        _adeudo(c_b, estado="pagado")
        client = _auth(staff=True)

        assert len(client.get("/api/adeudos/").data) == 2
        assert len(client.get(f"/api/adeudos/?sucursal_id={suc_a.id}").data) == 1
        assert len(client.get(f"/api/adeudos/?cliente_id={c_a.id}").data) == 1
        assert len(client.get("/api/adeudos/?estado=pagado").data) == 1
        assert a.id == client.get(f"/api/adeudos/?cliente_id={c_a.id}").data[0]["id"]

    def test_listado_staff_parametros_invalidos(self):
        client = _auth(staff=True)
        assert client.get("/api/adeudos/?sucursal_id=x").status_code == 400
        assert client.get("/api/adeudos/?cliente_id=x").status_code == 400

    def test_listado_cajero_forza_su_sucursal(self):
        suc_a, suc_b = SucursalFactory(), SucursalFactory()
        _adeudo(ClienteFactory(id_sucursal=suc_a))
        _adeudo(ClienteFactory(id_sucursal=suc_b))
        data = _auth("cajero", suc_a).get("/api/adeudos/").data
        assert len(data) == 1

    def test_listado_sin_sucursal_400(self):
        assert _auth("cajero", None).get("/api/adeudos/").status_code == 400

    def test_post_cajero_crea_en_su_sucursal(self):
        suc = SucursalFactory()
        cliente = ClienteFactory(id_sucursal=suc)
        r = _auth("cajero", suc).post(
            "/api/adeudos/", {"id_cliente": cliente.id, "monto_total": "50.00"}, format="json"
        )
        assert r.status_code == 201
        assert r.data["saldo"] == "50.00"

    def test_post_cajero_otra_sucursal_403(self):
        suc_a, suc_b = SucursalFactory(), SucursalFactory()
        cliente_b = ClienteFactory(id_sucursal=suc_b)
        r = _auth("cajero", suc_a).post(
            "/api/adeudos/", {"id_cliente": cliente_b.id, "monto_total": "50"}, format="json"
        )
        assert r.status_code == 403

    def test_post_sin_cliente_400(self):
        r = _auth("cajero", SucursalFactory()).post(
            "/api/adeudos/", {"monto_total": "50"}, format="json"
        )
        assert r.status_code == 400

    def test_post_cliente_inexistente_404(self):
        r = _auth("cajero", SucursalFactory()).post(
            "/api/adeudos/", {"id_cliente": 99999, "monto_total": "50"}, format="json"
        )
        assert r.status_code == 404

    def test_post_staff_para_cualquier_cliente(self):
        cliente = ClienteFactory()
        r = _auth(staff=True).post(
            "/api/adeudos/", {"id_cliente": cliente.id, "monto_total": "50"}, format="json"
        )
        assert r.status_code == 201

    def test_detalle_get_put_delete_y_permisos(self):
        suc = SucursalFactory()
        adeudo = AdeudoFactory(id_cliente=ClienteFactory(id_sucursal=suc))

        cajero = _auth("cajero", suc)
        assert cajero.get(f"/api/adeudos/{adeudo.id}/").status_code == 200
        assert cajero.put(f"/api/adeudos/{adeudo.id}/", {"concepto": "x"}, format="json").status_code == 403
        assert cajero.delete(f"/api/adeudos/{adeudo.id}/").status_code == 403

        encargado = _auth("encargado", suc)
        r = encargado.put(f"/api/adeudos/{adeudo.id}/", {"concepto": "x"}, format="json")
        assert r.status_code == 200
        r = encargado.delete(f"/api/adeudos/{adeudo.id}/")
        assert r.status_code == 200
        assert r.data["estado"] == "cancelado"

    def test_detalle_otra_sucursal_403(self):
        suc_a, suc_b = SucursalFactory(), SucursalFactory()
        adeudo = AdeudoFactory(id_cliente=ClienteFactory(id_sucursal=suc_b))
        r = _auth("cajero", suc_a).get(f"/api/adeudos/{adeudo.id}/")
        assert r.status_code == 403

    def test_detalle_inexistente_404(self):
        client = _auth(staff=True)
        assert client.get("/api/adeudos/99999/").status_code == 404
        assert client.put("/api/adeudos/99999/", {"concepto": "x"}, format="json").status_code == 404
        assert client.delete("/api/adeudos/99999/").status_code == 404


# ---------------------------------------------------------------------------
# API: abonos
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAbonoAPI:
    def test_listar_y_crear_abono(self):
        suc = SucursalFactory()
        adeudo = AdeudoFactory(id_cliente=ClienteFactory(id_sucursal=suc))
        client = _auth("cajero", suc)

        assert client.get(f"/api/adeudos/{adeudo.id}/abonos/").data == []
        r = client.post(
            f"/api/adeudos/{adeudo.id}/abonos/", {"monto": "40.00"}, format="json"
        )
        assert r.status_code == 201
        assert len(client.get(f"/api/adeudos/{adeudo.id}/abonos/").data) == 1
        adeudo.refresh_from_db()
        assert adeudo.saldo == Decimal("60.00")

    def test_adeudo_inexistente_404(self):
        client = _auth("cajero", SucursalFactory())
        assert client.get("/api/adeudos/99999/abonos/").status_code == 404
        r = client.post("/api/adeudos/99999/abonos/", {"monto": "10"}, format="json")
        assert r.status_code == 404

    def test_otra_sucursal_403(self):
        suc_a, suc_b = SucursalFactory(), SucursalFactory()
        adeudo = AdeudoFactory(id_cliente=ClienteFactory(id_sucursal=suc_b))
        client = _auth("cajero", suc_a)
        assert client.get(f"/api/adeudos/{adeudo.id}/abonos/").status_code == 403
        r = client.post(
            f"/api/adeudos/{adeudo.id}/abonos/", {"monto": "10"}, format="json"
        )
        assert r.status_code == 403

    def test_sobrepago_400(self):
        suc = SucursalFactory()
        adeudo = AdeudoFactory(id_cliente=ClienteFactory(id_sucursal=suc))
        r = _auth("cajero", suc).post(
            f"/api/adeudos/{adeudo.id}/abonos/", {"monto": "100.01"}, format="json"
        )
        assert r.status_code == 400
