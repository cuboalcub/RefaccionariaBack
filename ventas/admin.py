from django.contrib import admin
from ventas.models import metodoPago, venta, detalleVenta, Reporte

admin.site.register(metodoPago)
admin.site.register(venta)
admin.site.register(detalleVenta)
admin.site.register(Reporte)
