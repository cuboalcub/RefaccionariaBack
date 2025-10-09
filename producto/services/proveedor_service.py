from producto.models import Proveedor
from producto.repositories.proveedor_repository import ProveedorRepository
from django.core.exceptions import ValidationError
from usuario.repositories.usuario_repositorie import UserRepository


class ProveedorService:

    @staticmethod
    def create_proveedor(proveedor_data):
        """
        Lógica para crear un nuevo proveedor.
        proveedor_data debería ser un diccionario con los campos necesarios.
        """
        required_fields = ['nombre', 'direccion', 'telefono', 'email', 'contacto']
        for field in required_fields:
            if field not in proveedor_data:
                raise ValueError(f"Faltan campos obligatorios: {field}")
        
        proveedor = ProveedorRepository.create(proveedor_data)
        return ProveedorService._to_dict(proveedor)
    
    @staticmethod
    def get_all_proveedores():
        """
        Devuelve una lista de todos los proveedores.
        """
        proveedores = ProveedorRepository.get_all()
        return [ProveedorService._to_dict(proveedor) for proveedor in proveedores]
    
    @staticmethod
    def get_proveedor_by_id(proveedor_id):
        """
        Devuelve un proveedor por su ID.
        """
        proveedor = ProveedorRepository.get_by_id(proveedor_id)
        return ProveedorService._to_dict(proveedor)
    
    @staticmethod
    def update_proveedor(proveedor_id, update_data):
        """
        Actualiza un proveedor existente.
        update_data debería ser un diccionario con los campos a actualizar.
        """
        proveedor = ProveedorRepository.get_by_id(proveedor_id)
        if not proveedor:
            raise ValueError("Proveedor no encontrado")
        
        for key, value in update_data.items():
            setattr(proveedor, key, value)
        
        proveedor.save()
        return ProveedorService._to_dict(proveedor)
    
    @staticmethod
    def delete_proveedor(proveedor_id):
        """
        Elimina un proveedor por su ID.
        """
        proveedor = ProveedorRepository.get_by_id(proveedor_id)
        if not proveedor:
            raise ValueError("Proveedor no encontrado")
        
        proveedor.delete()
        return {"message": "Proveedor eliminado exitosamente"}
    
    @staticmethod
    def _to_dict(proveedor):
        """
        Convierte una instancia de Proveedor a un diccionario.
        """
        return {
            "id": proveedor.id,
            "nombre": proveedor.nombre,
            "direccion": proveedor.direccion,
            "telefono": proveedor.telefono,
            "email": proveedor.email,
            "contacto": proveedor.contacto,
            "created_at": proveedor.created_at,
            "updated_at": proveedor.updated_at,
        }