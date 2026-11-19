from typing import List, Optional

from repository.base_repository import BaseRepository
from notifications.models import Notification


class NotificationRepository(BaseRepository):
    def __init__(self):
        super().__init__(Notification)

    def list_for_user(self, user_id: int) -> List[Notification]:
        return list(
            self.model_class.objects.filter(destinatario_id=user_id).order_by(
                "-creada_en", "-id"
            )
        )

    def get_owned(self, notification_id: int, user_id: int) -> Optional[Notification]:
        return (
            self.model_class.objects.filter(
                id=notification_id, destinatario_id=user_id
            ).first()
        )
