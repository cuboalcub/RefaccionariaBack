from django.contrib import admin

from clientes.models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'apellido_paterno', 'apellido_materno', 'telefono', 'correo', 'rfc', 'id_sucursal')
    search_fields = ('nombre', 'apellido_paterno', 'apellido_materno', 'rfc', 'correo')
    list_filter = ('id_sucursal',)
