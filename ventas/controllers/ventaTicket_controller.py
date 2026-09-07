from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ventas.services.ventaTicket_service import VentaTicketService
from repository.exceptions import NotFoundError


class VentaTicketController(APIView):

    def get(self, request, pk):
        try:
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