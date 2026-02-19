from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
from ventas.services.reporte_ventas_service import ReporteVentasService


class ReporteVentasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tipo = request.query_params.get("tipo")
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        if not tipo:
            return HttpResponse("Debe enviar el parámetro 'tipo'", status=400)

        service = ReporteVentasService()

        try:
            reporte = service.generar_reporte(
                tipo=tipo,
                year=int(year) if year else None,
                month=int(month) if month else None
            )
        except ValueError as e:
            return HttpResponse(str(e), status=400)

        #Agarra el template
        html_string = render_to_string('ventas/reporte_ventas.html', context=reporte)

        # Genera el pdf desde el template
        pdf_file = HTML(string=html_string).write_pdf()

        #devuelve el pdf
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="reporte_ventas.pdf"'

        return response