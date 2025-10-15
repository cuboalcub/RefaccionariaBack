from producto.models import Producto
from django.core.exceptions import ObjectDoesNotExist

class ProductoRepository:
    @staticmethod
    def get_all():
        """
        Devuelve todos los productos como queryset.
        """
        return Producto.objects.all()

    @staticmethod
    def create(producto_data):
        """
        Crea un producto nuevo en la base de datos.
        producto_data debería ser un diccionario.
        """
        producto = Producto.objects.create(**producto_data)
        return producto

    @staticmethod
    def update(producto_id, producto_data):
        """
        Actualiza un producto existente. Devuelve None si no existe.
        """
        try:
            producto = Producto.objects.get(id=producto_id)
            for key, value in producto_data.items():
                setattr(producto, key, value)
            producto.save()
            return producto
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def delete(producto_id):
        """
        Elimina un producto por ID. Devuelve True si lo eliminó, False si no existe.
        """
        try:
            producto = Producto.objects.get(id=producto_id)
            producto.delete()
            return True
        except ObjectDoesNotExist:
            return False

    @staticmethod
    def get_by_codigo_barras(codigo_barras):
        """
        Devuelve un producto por código de barras o None si no existe.
        """
        try:
            return Producto.objects.get(codigo_barras=codigo_barras)
        
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def get_by_nombre(nombre):
        """
        Devuelve un producto por nombre o None si no existe.
        """
        try:
            
            return Producto.objects.get(nombre=nombre)
        
        except ObjectDoesNotExist:
            return None


