from django.contrib import admin
from inventario.models import Inventario, MovimientoInventario, DetalleInventario

admin.site.register(Inventario)
admin.site.register(MovimientoInventario)
admin.site.register(DetalleInventario)
