from producto.models import Movimiento
from django.core.exceptions import ObjectDoesNotExist




class MovimientoRepository:
    @staticmethod
    def get_all():
        """
        Devuelve todos los movimientos como queryset.
        """
        return Movimiento.objects.all()

    @staticmethod
    def create(movimiento_data):
        """
        Crea un movimiento nuevo en la base de datos.
        movimiento_data debería ser un diccionario.
        """
        movimiento = Movimiento.objects.create(**movimiento_data)
        return movimiento

    @staticmethod
    def update(movimiento_id, movimiento_data):
        """
        Actualiza un movimiento existente. Devuelve None si no existe.
        """
        try:
            movimiento = Movimiento.objects.get(id=movimiento_id)
            for key, value in movimiento_data.items():
                setattr(movimiento, key, value)
            movimiento.save()
            return movimiento
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def delete(movimiento_id):
        """
        Elimina un movimiento por ID. Devuelve True si lo eliminó, False si no existe.
        """
        try:
            movimiento = Movimiento.objects.get(id=movimiento_id)
            movimiento.delete()
            return True
        except ObjectDoesNotExist:
            return False    