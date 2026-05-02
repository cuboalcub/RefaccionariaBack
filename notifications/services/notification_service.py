from django.core.exceptions import ObjectDoesNotExist
from repository.base_service import BaseService
from notifications.models import Notification
from notifications.repositories.notification_repository import NotificationRepository


class NotificationService(BaseService):
    LOW_STOCK = Notification.NotificationType.LOW_STOCK
    OUT_OF_STOCK = Notification.NotificationType.OUT_OF_STOCK

    def __init__(self):
        super().__init__(model=Notification, repository=NotificationRepository())

    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "producto_id": instance.producto.id if instance.producto else None,
            "tipo": instance.tipo,
            "mensaje": instance.mensaje,
            "leido": instance.leido,
            "creado_en": instance.creado_en.isoformat() if instance.creado_en else None,
        }

    def get_all(self):
        try:
            instances = self.repository.get_all()
            return [self._to_dict(instance) for instance in instances]
        except Exception as e:
            raise ValueError(f"Error al obtener notificaciones: {str(e)}")

    def mark_as_read(self, id):
        notification = self.repository.get_by_id(id)
        if not notification:
            raise ValueError(f"Notificación con id {id} no encontrada")
        self.repository.update(notification, {"leido": True})
        return self._to_dict(notification)

    def create_if_not_exists(self, producto, tipo, mensaje):
        existing = self.repository.get_active_by_product_and_type(producto, tipo)
        if existing:
            return None
        notification = self.repository.create({
            "producto": producto,
            "tipo": tipo,
            "mensaje": mensaje,
        })
        return self._to_dict(notification)
