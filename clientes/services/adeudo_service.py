from decimal import Decimal, InvalidOperation

from django.db import transaction

from repository.base_service import BaseService
from repository.exceptions import NotFoundError
from clientes.models import Adeudo, Cliente
from clientes.repositories.adeudo_repository import AdeudoRepository
from ventas.models import Venta


def _a_decimal(valor):
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("monto inválido")


class AdeudoService(BaseService):
    def __init__(self):
        super().__init__(model=Adeudo, repository=AdeudoRepository())

    def get_all(self, sucursal_id=None, cliente_id=None, estado=None):
        filtros = {}
        if sucursal_id is not None:
            filtros["id_cliente__id_sucursal_id"] = sucursal_id
        if cliente_id is not None:
            filtros["id_cliente_id"] = cliente_id
        if estado is not None:
            filtros["estado"] = estado
        if not filtros:
            return super().get_all()
        return self.get_by_filters(filtros)

    def _resolver_cliente(self, data):
        cliente_id = data.get("id_cliente")
        cliente = Cliente.objects.filter(id=cliente_id).first() if cliente_id else None
        if not cliente:
            raise ValueError("El cliente indicado no existe")
        return cliente

    def _resolver_venta(self, data, cliente):
        venta_id = data.get("id_venta")
        if venta_id in (None, ""):
            return None
        venta = Venta.objects.filter(id=venta_id).first()
        if not venta:
            raise ValueError("La venta indicada no existe")
        if venta.id_cliente_id is not None and venta.id_cliente_id != cliente.id:
            raise ValueError("La venta no pertenece al cliente indicado")
        if Adeudo.objects.filter(id_venta_id=venta.id).exists():
            raise ValueError("La venta ya tiene un adeudo registrado")
        return venta

    def create(self, data):
        data = dict(data)
        data.pop("id_sucursal", None)
        data.pop("saldo", None)
        data.pop("estado", None)

        cliente = self._resolver_cliente(data)
        venta = self._resolver_venta(data, cliente)

        monto = data.get("monto_total")
        if monto in (None, ""):
            monto = venta.total if venta else None
        if monto is None:
            raise ValueError("Faltan campos obligatorios: monto_total")
        monto = _a_decimal(monto)
        if monto <= 0:
            raise ValueError("monto_total debe ser mayor a 0")

        data["id_cliente"] = cliente
        data["id_venta"] = venta
        data["monto_total"] = monto
        data["saldo"] = monto
        data["estado"] = "pendiente"
        return super().create(data)

    def update(self, entity_id, data):
        adeudo = self.repository.get_by_id(entity_id)
        if not adeudo:
            raise NotFoundError(f"adeudo con id {entity_id} no encontrado")

        data = dict(data)
        for campo in ("id_cliente", "id_venta", "saldo", "estado", "id_sucursal"):
            data.pop(campo, None)

        if data.get("monto_total") not in (None, ""):
            monto = _a_decimal(data["monto_total"])
            if monto <= 0:
                raise ValueError("monto_total debe ser mayor a 0")
            if adeudo.abonos.exists():
                raise ValueError("No se puede cambiar monto_total con abonos registrados")
            data["monto_total"] = monto
            data["saldo"] = monto
        else:
            data.pop("monto_total", None)

        return super().update(entity_id, data)

    def delete(self, entity_id, user=None):
        with transaction.atomic():
            adeudo = Adeudo.objects.select_for_update().filter(id=entity_id).first()
            if not adeudo:
                raise NotFoundError(f"adeudo con id {entity_id} no encontrado")
            if adeudo.estado == "cancelado":
                return {
                    "message": "adeudo ya estaba cancelado",
                    "id": adeudo.id,
                    "estado": adeudo.estado,
                }
            adeudo.estado = "cancelado"
            adeudo.save(update_fields=["estado", "updated_at"])
            return {
                "message": "adeudo cancelado exitosamente",
                "id": adeudo.id,
                "estado": adeudo.estado,
            }
