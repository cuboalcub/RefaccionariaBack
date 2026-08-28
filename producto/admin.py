from django.contrib import admin
from producto.models import Producto, Tipo, Proveedor

admin.site.register(Producto)
admin.site.register(Tipo)
admin.site.register(Proveedor)
