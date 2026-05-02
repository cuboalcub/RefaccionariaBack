from notifications.models import Notification
from repository.base_repository import BaseRepository


class NotificationRepository(BaseRepository):
    def __init__(self):
        super().__init__(Notification)

    def get_unread(self):
        return list(self.model_class.objects.filter(leido=False))

    def get_active_by_product_and_type(self, producto, tipo):
        return list(self.model_class.objects.filter(producto=producto, tipo=tipo, leido=False))

    def mark_as_read(self, entity):
        return self.update(entity, {"leido": True})
