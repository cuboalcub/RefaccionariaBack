from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.services.notification_service import NotificationService
from repository.exceptions import NotFoundError


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = NotificationService().list_for_user(request.user)
        return Response(items, status=status.HTTP_200_OK)


class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk: int):
        try:
            item = NotificationService().mark_read(pk, request.user)
            return Response(item, status=status.HTTP_200_OK)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk: int):
        try:
            result = NotificationService().delete_for_user(pk, request.user)
            return Response(result, status=status.HTTP_200_OK)
        except NotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class NotificationMarkAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = NotificationService().mark_all_read(request.user)
        return Response(result, status=status.HTTP_200_OK)
