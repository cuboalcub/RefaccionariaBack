"""SKU automático: categoría-marca-id, alias `sku` de API y filtro por sku."""

import pytest
from rest_framework.test import APIClient

from producto.models import Producto
from producto.services.producto_service import ProductoService
from tests.factories import (
    ProductoFactory,
    ProveedorFactory,
    TipoFactory,
    UserFactory,
)


def _auth(rol="cajero"):
    from usuario.models import Perfil

    user = UserFactory()
    Perfil.objects.create(usuario=user, rol=rol)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _payload(tipo, proveedor, **kw):
    data = {
        "id_tipo": tipo.id,
        "id_proveedor": proveedor.id,
        "nombre": "Filtro de aceite",
        "codigo_barras": f"CB-{tipo.id}-{proveedor.id}",
        "precio_venta": "100.00",
        "marca": "Bosch",
        "costo": "50.00",
    }
    data.update(kw)
    return data


@pytest.mark.django_db
class TestSkuAutomatico:
    def test_genera_categoria_marca_id(self):
        tipo = TipoFactory(nombre="Filtro")
        prov = ProveedorFactory()
        obj = ProductoService().create(_payload(tipo, prov))

        assert obj["sku"] == f"FIL-BOS-{obj['id']:04d}"
        assert obj["clave"] == obj["sku"]
        assert Producto.objects.get(pk=obj["id"]).clave == obj["sku"]

    def test_normaliza_acentos_y_simbolos(self):
        tipo = TipoFactory(nombre="Filtración")
        prov = ProveedorFactory()
        obj = ProductoService().create(_payload(tipo, prov, marca="Bösch & Cía"))

        assert obj["sku"].startswith("FIL-BOS-")

    def test_respeta_clave_explicita(self):
        tipo = TipoFactory()
        prov = ProveedorFactory()
        obj = ProductoService().create(_payload(tipo, prov, clave="MANUAL-1"))

        assert obj["sku"] == "MANUAL-1"

    def test_update_no_regenera(self):
        tipo = TipoFactory(nombre="Filtro")
        prov = ProveedorFactory()
        obj = ProductoService().create(_payload(tipo, prov))
        sku = obj["sku"]

        actualizado = ProductoService().update(obj["id"], {"marca": "OtraMarca"})

        assert actualizado["sku"] == sku

    def test_api_expone_sku_y_filtra(self):
        tipo = TipoFactory(nombre="Filtro")
        prov = ProveedorFactory()
        client = _auth()
        r = client.post("/api/productos/", _payload(tipo, prov), format="json")
        assert r.status_code == 201
        sku = r.json()["sku"]
        assert r.json()["clave"] == sku

        filtrado = client.get("/api/productos/", {"sku": sku})

        assert filtrado.status_code == 200
        assert len(filtrado.json()) == 1
        assert filtrado.json()[0]["sku"] == sku

    def test_api_acepta_sku_en_create(self):
        tipo = TipoFactory()
        prov = ProveedorFactory()
        client = _auth()
        r = client.post(
            "/api/productos/", _payload(tipo, prov, sku="SKU-MANUAL"), format="json"
        )

        assert r.status_code == 201
        assert r.json()["sku"] == "SKU-MANUAL"

    def test_producto_sin_clave_explicita_en_factory(self):
        """Los productos creados por ORM mantienen su clave tal cual."""
        p = ProductoFactory(clave="FAB-1")

        assert ProductoService()._to_dict(p)["sku"] == "FAB-1"
