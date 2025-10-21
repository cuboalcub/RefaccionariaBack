
from producto.repositories.producto_repository import ProductoRepository
from django.core.exceptions import ValidationError
from producto.models import Producto, Tipo, Proveedor, Movimiento
from usuario.repositories.usuario_repositorie import UserRepository
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

class ProductoService:
    
    @staticmethod
    def create_producto(producto_data):
        """
        Lógica para crear un nuevo producto.
        producto_data debería ser un diccionario con los campos necesarios.
        """
        required_fields = ['id_tipo', 'id_proveedor', 'clave', 'nombre', 'descripcion', 'codigo_barras', 'precio_venta', 'marca', 'existencia', 'costo']
        for field in required_fields:
            if field not in producto_data:
                raise ValueError(f"Faltan campos obligatorios: {field}")
        
        # Validar que el tipo y proveedor existen
        try:
            tipo = Tipo.objects.get(id=producto_data['id_tipo'])
        except Tipo.DoesNotExist:
            raise ValueError("El tipo especificado no existe")
        
        try:
            proveedor = Proveedor.objects.get(id=producto_data['id_proveedor'])
        except Proveedor.DoesNotExist:
            raise ValueError("El proveedor especificado no existe")
        
        producto = ProductoRepository.create(producto_data)
        return ProductoService._to_dict(producto)
    
    @staticmethod
    def get_all_productos():
        """
        Devuelve una lista de todos los productos.
        """
        productos = ProductoRepository.get_all()
        return [ProductoService._to_dict(producto) for producto in productos]
    
    @staticmethod
    def get_producto_by_id(producto_id):
        """
        Devuelve un producto por su ID.
        """
        producto = ProductoRepository.get_by_id(producto_id)
        return ProductoService._to_dict(producto)
    
    @staticmethod
    def update_producto(producto_id, update_data):
        """
        Actualiza un producto existente.
        update_data debería ser un diccionario con los campos a actualizar.
        """
        producto = ProductoRepository.get_by_id(producto_id)
        if not producto:
            raise ValueError("Producto no encontrado")
        
        # Si se actualiza el tipo o proveedor, validar que existen
        if 'id_tipo' in update_data:
            try:
                tipo = Tipo.objects.get(id=update_data['id_tipo'])
            except Tipo.DoesNotExist:
                raise ValueError("El tipo especificado no existe")
        
        if 'id_proveedor' in update_data:
            try:
                proveedor = Proveedor.objects.get(id=update_data['id_proveedor'])
            except Proveedor.DoesNotExist:
                raise ValueError("El proveedor especificado no existe")
