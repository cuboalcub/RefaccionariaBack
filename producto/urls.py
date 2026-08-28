from django.urls import path
from producto.controllers.producto_controller import ProductoListCreateView, ProductoDetailView, ProductoPorCodigoBarrasView
from producto.controllers.tipo_controller import TipoListCreateView, TipoDetailView
from producto.controllers.proveedor_controller import ProveedorListCreateView, ProveedorDetailView
urlpatterns = [
    path('productos/', ProductoListCreateView.as_view(), name='producto-list-create'),
    path('productos/<int:pk>/', ProductoDetailView.as_view(), name='producto-detail'),
    path('productos/codigo-barras/', ProductoPorCodigoBarrasView.as_view(), name='producto-codigo-barras'),
    path('tipos/', TipoListCreateView.as_view(), name='tipo-list-create'),
    path('tipos/<int:pk>/', TipoDetailView.as_view(), name='tipo-detail'),
    path('proveedores/', ProveedorListCreateView.as_view(), name='proveedor-list-create'),
    path('proveedores/<int:pk>/', ProveedorDetailView.as_view(), name='proveedor-detail'),
]
