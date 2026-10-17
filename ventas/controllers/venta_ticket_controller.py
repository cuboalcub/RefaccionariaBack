from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ventas.services.venta_ticket_service import VentaTicketService
from repository.exceptions import NotFoundError
from repository.permissions import exigir_permiso


class VentaTicketController(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            exigir_permiso(request.user, "ventas.vender")
            service = VentaTicketService()
            ticket = service.get_ticket(pk)

            return Response(
                ticket,
                status=status.HTTP_200_OK
            )

        except NotFoundError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )