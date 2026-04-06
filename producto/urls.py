from django.urls import path

from producto.controllers.movimiento_controller import (
    MovimientoDetailView,
    MovimientoListCreateView,
)
from producto.controllers.producto_controller import (
    ProductoDetailView,
    ProductoListCreateView,
)
from producto.controllers.proveedor_controller import (
    ProveedorDetailView,
    ProveedorListCreateView,
)
from producto.controllers.tipo_controller import (
    TipoDetailView,
    TipoListCreateView,
)

urlpatterns = [
    path(
        "productos/",
        ProductoListCreateView.as_view(),
        name="producto-list-create",
    ),
    path(
        "productos/<int:pk>/",
        ProductoDetailView.as_view(),
        name="producto-detail",
    ),
    path(
        "tipos/",
        TipoListCreateView.as_view(),
        name="tipo-list-create",
    ),
    path(
        "tipos/<int:pk>/",
        TipoDetailView.as_view(),
        name="tipo-detail",
    ),
    path(
        "proveedores/",
        ProveedorListCreateView.as_view(),
        name="proveedor-list-create",
    ),
    path(
        "proveedores/<int:pk>/",
        ProveedorDetailView.as_view(),
        name="proveedor-detail",
    ),
    path(
        "movimientos/",
        MovimientoListCreateView.as_view(),
        name="movimiento-list-create",
    ),
    path(
        "movimientos/<int:pk>/",
        MovimientoDetailView.as_view(),
        name="movimiento-detail",
    ),
    path(
        "productos/by_categoria/",
        ProductoListCreateView.as_view(),
        name="producto-get-by-categoria",
    ),
    path(
        "productos/search/",
        ProductoListCreateView.as_view(),
        name="producto-search",
    ),
]
