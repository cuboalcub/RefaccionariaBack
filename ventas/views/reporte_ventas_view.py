from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
from ventas.services.reporte_ventas_service import ReporteVentasService

from django.core.files.base import ContentFile
from ventas.models import Reporte


class ReporteVentasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tipo = request.query_params.get("tipo")
        year = request.query_params.get("year")
        month = request.query_params.get("month")
        quincena = request.query_params.get("quincena")

        if not tipo:
            return HttpResponse("Debe enviar el parámetro 'tipo'", status=400)

        service = ReporteVentasService()

        try:
            reporte = service.generar_reporte(
                tipo=tipo,
                year=int(year) if year else None,
                month=int(month) if month else None,
                quincena=int(quincena) if quincena else None
            )
        except ValueError as e:
            return HttpResponse(str(e), status=400)

        #Agarra el template
        html_string = render_to_string('ventas/reporte_ventas.html', context=reporte)

        # Genera el pdf desde el template
        pdf_file = HTML(string=html_string).write_pdf()

        # Crear registro en DB
        reporte_obj = Reporte.objects.create(
        tipo=tipo,
        fecha_inicio=reporte["fecha_inicio"],
        fecha_fin=reporte["fecha_fin"]
        )

        # Nombre del archivo
        nombre_archivo = f"reporte_{tipo}_{reporte['fecha_inicio'].date()}_{reporte['fecha_fin'].date()}.pdf"

        # Guardar archivo
        reporte_obj.archivo.save(nombre_archivo, ContentFile(pdf_file))

        # Responder al usuario (opcional)
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{nombre_archivo}"'

        return response