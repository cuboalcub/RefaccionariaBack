from django.urls import path
from producto.controllers.producto_controller import ProductoListCreateView, ProductoDetailView
from producto.controllers.tipo_controller import TipoListCreateView, TipoDetailView
from producto.controllers.proveedor_controller import ProveedorListCreateView, ProveedorDetailView
from producto.controllers.movimiento_controller import MovimientoListCreateView, MovimientoDetailView
urlpatterns = [
    path('productos/', ProductoListCreateView.as_view(), name='producto-list-create'),
    path('productos/<int:producto_id>/', ProductoDetailView.as_view(), name='producto-detail'),
    path('tipos/', TipoListCreateView.as_view(), name='tipo-list-create'),
    path('tipos/<int:tipo_id>/', TipoDetailView.as_view(), name='tipo-detail'),
    path('proveedores/', ProveedorListCreateView.as_view(), name='proveedor-list-create'),
    path('proveedores/<int:proveedor_id>/', ProveedorDetailView.as_view(), name='proveedor-detail'),
    path('movimientos/', MovimientoListCreateView.as_view(), name='movimiento-list-create'),
    path('movimientos/<int:movimiento_id>/', MovimientoDetailView.as_view(), name='movimiento-detail'),
]