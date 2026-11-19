from django.contrib import admin
from inventario.models import Stock, MovimientoInventario, PrecioSucursal

admin.site.register(Stock)
admin.site.register(MovimientoInventario)
admin.site.register(PrecioSucursal)
