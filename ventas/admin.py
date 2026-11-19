from django.contrib import admin
from ventas.models import MetodoPago, Venta, DetalleVenta, Reporte

admin.site.register(MetodoPago)
admin.site.register(Venta)
admin.site.register(DetalleVenta)
admin.site.register(Reporte)
