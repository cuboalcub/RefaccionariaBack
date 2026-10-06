"""Factories factory_boy para inventario/ventas (patrón django-tdd)."""

import factory
from factory import fuzzy
from django.contrib.auth.models import User

from sucursales.models import Sucursal
from inventario.models import Inventario, MovimientoInventario
from producto.models import Tipo, Proveedor, Producto
from ventas.models import metodoPago
from usuario.models import Perfil


class SucursalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Sucursal

    ubicacion = factory.Sequence(lambda n: f"Sucursal {n}")
    nombre_sucursal = factory.Sequence(lambda n: f"Sucursal {n}")


class InventarioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Inventario

    id_sucursal = factory.SubFactory(SucursalFactory)
    descripcion = factory.Faker("sentence", nb_words=3)


class TipoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tipo

    nombre = factory.Sequence(lambda n: f"Tipo {n}")


class ProveedorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Proveedor

    nombre = factory.Sequence(lambda n: f"Proveedor {n}")
    telefono = factory.Sequence(lambda n: f"555{n:07d}")
    correo = factory.Sequence(lambda n: f"prov{n}@mail.com")
    direccion = factory.Faker("address")


class ProductoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Producto

    clave = factory.Sequence(lambda n: f"CLAVE-{n}")
    nombre = factory.Sequence(lambda n: f"Producto {n}")
    codigo_barras = factory.Sequence(lambda n: f"CB{n:08d}")
    precio_venta = fuzzy.FuzzyDecimal(10.00, 1000.00, 2)
    marca = factory.Faker("word")
    costo = fuzzy.FuzzyDecimal(5.00, 500.00, 2)
    id_tipo = factory.SubFactory(TipoFactory)
    id_proveedor = factory.SubFactory(ProveedorFactory)


class MovimientoEntradaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MovimientoInventario

    tipo = MovimientoInventario.TipoMovimiento.ENTRADA
    cantidad = 10
    razon = "Compra inicial"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class PerfilFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Perfil

    usuario = factory.SubFactory(UserFactory)
    id_sucursal = factory.SubFactory(SucursalFactory)


class MetodoPagoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = metodoPago

    tipo = "EFECTIVO"
    descripcion = "Pago en efectivo"
