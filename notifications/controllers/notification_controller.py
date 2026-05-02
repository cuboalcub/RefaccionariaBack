from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from notifications.services.notification_service import NotificationService


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = NotificationService()

    def get(self, request):
        try:
            notifications = self.service.get_all()
            return Response(notifications, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = NotificationService()

    def _mark_as_read(self, pk):
        try:
            self.service.mark_as_read(pk)
            return Response({"message": "Notificación marcada como leída"}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        return self._mark_as_read(pk)

    def post(self, request, pk):
        return self._mark_as_read(pk)
