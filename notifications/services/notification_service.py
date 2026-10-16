from typing import List

from notifications.models import Notification
from notifications.repositories.notification_repository import (
    NotificationRepository,
)
from repository.base_service import BaseService
from repository.exceptions import NotFoundError


class NotificationService(BaseService):
    def __init__(self):
        super().__init__(model=Notification, repository=NotificationRepository())

    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "titulo": instance.titulo,
            "mensaje": instance.mensaje,
            "tipo": instance.tipo,
            "leida": instance.leida,
            "creado_en": instance.creada_en.isoformat(),
        }

    def list_for_user(self, user) -> List[dict]:
        return [
            self._to_dict(n) for n in self.repository.list_for_user(user.id)
        ]

    def mark_read(self, notification_id: int, user) -> dict:
        instance = self.repository.get_owned(notification_id, user.id)
        if not instance:
            raise NotFoundError(
                f"Notification con id {notification_id} no encontrado"
            )
        if not instance.leida:
            instance.leida = True
            instance.save(update_fields=["leida"])
        return self._to_dict(instance)

    def mark_all_read(self, user) -> dict:
        updated = Notification.objects.filter(
            destinatario_id=user.id, leida=False
        ).update(leida=True)
        return {"actualizadas": updated}

    def delete_for_user(self, notification_id: int, user) -> dict:
        instance = self.repository.get_owned(notification_id, user.id)
        if not instance:
            raise NotFoundError(
                f"Notification con id {notification_id} no encontrado"
            )
        instance.delete()
        return {"message": "Notificación eliminada exitosamente"}
