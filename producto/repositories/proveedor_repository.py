from producto.models import Proveedor
from django.core.exceptions import ObjectDoesNotExist

class ProveedorRepository:
    @staticmethod
    def get_all():
        """
        Devuelve todos los proveedores como queryset.
        """
        return Proveedor.objects.all()

    @staticmethod
    def create(proveedor_data):
        """
        Crea un proveedor nuevo en la base de datos.
        proveedor_data debería ser un diccionario.
        """
        proveedor = Proveedor.objects.create(**proveedor_data)
        return proveedor

    @staticmethod
    def update(proveedor_id, proveedor_data):
        """
        Actualiza un proveedor existente. Devuelve None si no existe.
        """
        try:
            proveedor = Proveedor.objects.get(id=proveedor_id)
            for key, value in proveedor_data.items():
                setattr(proveedor, key, value)
            proveedor.save()
            return proveedor
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def delete(proveedor_id):
        """
        Elimina un proveedor por ID. Devuelve True si lo eliminó, False si no existe.
        """
        try:
            proveedor = Proveedor.objects.get(id=proveedor_id)
            proveedor.delete()
            return True
        except ObjectDoesNotExist:
            return False
        
    @staticmethod
    def get_by_nombre(nombre):
        """
        Devuelve un proveedor por nombre o None si no existe.
        """
        try:
            
            return Proveedor.objects.get(nombre=nombre)
        
        except ObjectDoesNotExist:
            return None