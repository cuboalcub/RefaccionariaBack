from decimal import Decimal

from django.db import transaction

from repository.base_service import BaseService
from clientes.models import AbonoAdeudo, Adeudo
from clientes.repositories.abono_adeudo_repository import AbonoAdeudoRepository
from clientes.services.adeudo_service import _a_decimal


class AbonoAdeudoService(BaseService):
    def __init__(self):
        super().__init__(model=AbonoAdeudo, repository=AbonoAdeudoRepository())

    def get_all(self, adeudo_id):
        return self.get_by_filters({"id_adeudo_id": adeudo_id})

    @transaction.atomic
    def create(self, data, user=None):
        data = dict(data)
        data.pop("id_sucursal", None)

        adeudo_id = data.get("id_adeudo")
        adeudo = (
            Adeudo.objects.select_for_update().filter(id=adeudo_id).first()
            if adeudo_id
            else None
        )
        if not adeudo:
            raise ValueError("El adeudo indicado no existe")
        if adeudo.estado != "pendiente":
            raise ValueError("Solo se pueden abonar adeudos pendientes")

        monto = _a_decimal(data.get("monto"))
        if monto <= 0:
            raise ValueError("monto debe ser mayor a 0")
        if monto > adeudo.saldo:
            raise ValueError("El abono no puede exceder el saldo pendiente")

        data["id_adeudo"] = adeudo
        data["monto"] = monto
        data["id_usuario"] = user if getattr(user, "is_authenticated", False) else None
        abono = super().create(data)

        adeudo.saldo = adeudo.saldo - monto
        if adeudo.saldo <= 0:
            adeudo.saldo = Decimal("0")
            adeudo.estado = "pagado"
        adeudo.save(update_fields=["saldo", "estado", "updated_at"])
        return abono
