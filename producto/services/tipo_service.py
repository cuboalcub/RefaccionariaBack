from producto.models import Tipo
from producto.repositories.tipo_repository import TipoRepository
from django.core.exceptions import ValidationError
from usuario.repositories.usuario_repositorie import UserRepository     

class TipoService:
    
    @staticmethod
    def create_tipo(tipo_data):
        """
        Lógica para crear un nuevo tipo.
        tipo_data debería ser un diccionario con los campos necesarios.
        """
        required_fields = ['nombre']
        for field in required_fields:
            if field not in tipo_data:
                raise ValueError(f"Faltan campos obligatorios: {field}")
        
        tipo = TipoRepository.create(tipo_data)
        return TipoService._to_dict(tipo)
    
    @staticmethod
    def get_all_tipos():
        """
        Devuelve una lista de todos los tipos.
        """
        tipos = TipoRepository.get_all()
        return [TipoService._to_dict(tipo) for tipo in tipos]
    
    @staticmethod
    def get_tipo_by_id(tipo_id):
        """
        Devuelve un tipo por su ID.
        """
        tipo = TipoRepository.get_by_id(tipo_id)
        return TipoService._to_dict(tipo)
    
    @staticmethod
    def update_tipo(tipo_id, update_data):
        """
        Actualiza un tipo existente.
        update_data debería ser un diccionario con los campos a actualizar.
        """
        tipo = TipoRepository.get_by_id(tipo_id)
        if not tipo:
            raise ValueError("Tipo no encontrado")
        
        for key, value in update_data.items():
            setattr(tipo, key, value)
        
        tipo.save()
        return TipoService._to_dict(tipo)
    
    @staticmethod
    def delete_tipo(tipo_id):
        """
        Elimina un tipo por su ID.
        """
        tipo = TipoRepository.get_by_id(tipo_id)
        if not tipo:
            raise ValueError("Tipo no encontrado")
        
        tipo.delete()
        return {"message": "Tipo eliminado exitosamente"}
    
    @staticmethod
    def _to_dict(tipo):
        """
        Convierte una instancia de Tipo a un diccionario.
        """
        return {
            "id": tipo.id,
            "nombre": tipo.nombre
        }