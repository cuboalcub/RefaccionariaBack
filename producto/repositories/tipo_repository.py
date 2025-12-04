from producto.models import Tipo
from django.core.exceptions import ObjectDoesNotExist

class TipoRepository:
    @staticmethod
    def get_all():
        """
        Devuelve todos los tipos como queryset.
        """
        return Tipo.objects.all()

    @staticmethod
    def create(tipo_data):
        """
        Crea un tipo nuevo en la base de datos.
        tipo_data debería ser un diccionario.
        """
        tipo = Tipo.objects.create(**tipo_data)
        return tipo

    @staticmethod
    def update(tipo_id, tipo_data):
        """
        Actualiza un tipo existente. Devuelve None si no existe.
        """
        try:
            tipo = Tipo.objects.get(id=tipo_id)
            for key, value in tipo_data.items():
                setattr(tipo, key, value)
            tipo.save()
            return tipo
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def delete(tipo_id):
        """
        Elimina un tipo por ID. Devuelve True si lo eliminó, False si no existe.
        """
        try:
            tipo = Tipo.objects.get(id=tipo_id)
            tipo.delete()
            return True
        except ObjectDoesNotExist:
            return False
        
    @staticmethod
    def get_by_nombre(nombre):
        """
        Devuelve un tipo por nombre o None si no existe.
        """
        try:
            
            return Tipo.objects.get(nombre=nombre)
        
        except ObjectDoesNotExist:
            return None

    @staticmethod   
    def get_by_id(tipo_id)
        try:
            return Tipo.objects.get(id = tipo_id)
        except ObjectDoesNotExist:
            return None