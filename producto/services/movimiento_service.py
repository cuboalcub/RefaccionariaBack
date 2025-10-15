from producto.models import Movimiento
from producto.repositories.movimiento_repository import MovimientoRepository
from django.core.exceptions import ValidationError
from usuario.repositories.usuario_repositorie import UserRepository 

class MovimientoService:

    @staticmethod
    def create_movimiento(movimiento_data):
        """
        Lógica para crear un nuevo movimiento.
        movimiento_data debería ser un diccionario con los campos necesarios.
        """
        required_fields = ['tipo', 'cantidad', 'razon', 'observacion']
        for field in required_fields:
            if field not in movimiento_data:
                raise ValueError(f"Faltan campos obligatorios: {field}")
        
        movimiento = MovimientoRepository.create(movimiento_data)
        return MovimientoService._to_dict(movimiento)
    
    @staticmethod
    def get_all_movimientos():
        """
        Devuelve una lista de todos los movimientos.
        """
        movimientos = MovimientoRepository.get_all()
        return [MovimientoService._to_dict(movimiento) for movimiento in movimientos]

    @staticmethod
    def get_movimiento_by_id(movimiento_id):
        """
        Devuelve un movimiento por su ID.
        """
        movimiento = MovimientoRepository.get_by_id(movimiento_id)
        return MovimientoService._to_dict(movimiento)
        raise ValueError("Tipo no encontrado")
        tipo.delete()
        return {"message": "Tipo eliminado correctamente"}
        if not movimiento:
            raise ValueError("Movimiento no encontrado")


    @staticmethod
    def update_movimiento(movimiento_id, update_data):
        """
        Actualiza un movimiento existente.
        update_data debería ser un diccionario con los campos a actualizar.
        """
        movimiento = MovimientoRepository.get_by_id(movimiento_id)
        if not movimiento:
            raise ValueError("Movimiento no encontrado")
        
        for key, value in update_data.items():
            setattr(movimiento, key, value)
        
        movimiento.save()
        return MovimientoService._to_dict(movimiento)
    
    @staticmethod
    def delete_movimiento(movimiento_id):
        """
        Elimina un movimiento por su ID.
        """
        movimiento = MovimientoRepository.get_by_id(movimiento_id)
        if not movimiento:
            raise ValueError("Movimiento no encontrado")
        movimiento.delete()
        return {"message": "Movimiento eliminado correctamente"}

    @staticmethod
    def _to_dict(movimiento):
        """
        Convierte una instancia de Movimiento a un diccionario.
        """
        return {
            "id": movimiento.id,
            "tipo": movimiento.tipo,
            "cantidad": movimiento.cantidad,
            "fecha": movimiento.fecha,
            "razon": movimiento.razon,
            "observacion": movimiento.observacion,
        }   