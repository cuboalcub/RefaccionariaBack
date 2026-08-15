from django.urls import path

from inventario.controllers.inventario_controller import InventarioListCreateView, InventarioDetailView
from inventario.controllers.movimiento_inventario_controller import MovimientoInventarioListCreateView, MovimientoInventarioDetailView
from inventario.controllers.detalle_inventario_controller import DetalleInventarioListCreateView, DetalleInventarioDetailView

urlpatterns = [
    path('inventarios/', InventarioListCreateView.as_view(), name='inventario-list-create'),
    path('inventarios/<int:pk>/', InventarioDetailView.as_view(), name='inventario-detail'),
    path('movimientos-inventario/', MovimientoInventarioListCreateView.as_view(), name='movimiento-inventario-list-create'),
    path('movimientos-inventario/<int:pk>/', MovimientoInventarioDetailView.as_view(), name='movimiento-inventario-detail'),
    path('detalles-inventario/', DetalleInventarioListCreateView.as_view(), name='detalle-inventario-list-create'),
    path('detalles-inventario/<int:pk>/', DetalleInventarioDetailView.as_view(), name='detalle-inventario-detail'),
]
