from django.contrib import admin

from clientes.models import Cliente, Adeudo, AbonoAdeudo


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'apellido_paterno', 'apellido_materno', 'telefono', 'correo', 'rfc', 'id_sucursal')
    search_fields = ('nombre', 'apellido_paterno', 'apellido_materno', 'rfc', 'correo')
    list_filter = ('id_sucursal',)


@admin.register(Adeudo)
class AdeudoAdmin(admin.ModelAdmin):
    list_display = ('id', 'id_cliente', 'id_venta', 'monto_total', 'saldo', 'estado', 'fecha')
    search_fields = ('concepto',)
    list_filter = ('estado', 'id_cliente__id_sucursal')


@admin.register(AbonoAdeudo)
class AbonoAdeudoAdmin(admin.ModelAdmin):
    list_display = ('id', 'id_adeudo', 'monto', 'id_metodo_pago', 'id_usuario', 'fecha')
    list_filter = ('id_metodo_pago',)
