from django.urls import path

from inventario.controllers.inventario_controller import InventarioListCreateView, InventarioDetailView, InventarioPorSucursalView
from inventario.controllers.movimiento_inventario_controller import MovimientoInventarioListCreateView, MovimientoInventarioDetailView
from inventario.controllers.detalle_inventario_controller import DetalleInventarioBulkCreateView, DetalleInventarioListCreateView, DetalleInventarioDetailView
from inventario.controllers.precio_sucursal_controller import HistorialPrecioView, PrecioActivoView, PrecioSucursalDetailView, PrecioSucursalListCreateView

urlpatterns = [
    path('inventarios/mi-sucursal/', InventarioPorSucursalView.as_view(), name='inventario-por-sucursal'),
    path('inventarios/', InventarioListCreateView.as_view(), name='inventario-list-create'),
    path('inventarios/<int:pk>/', InventarioDetailView.as_view(), name='inventario-detail'),
    path('movimientos-inventario/', MovimientoInventarioListCreateView.as_view(), name='movimiento-inventario-list-create'),
    path('movimientos-inventario/<int:pk>/', MovimientoInventarioDetailView.as_view(), name='movimiento-inventario-detail'),
    path('detalles-inventario/', DetalleInventarioListCreateView.as_view(), name='detalle-inventario-list-create'),
    path('detalles-inventario/bulk/', DetalleInventarioBulkCreateView.as_view(), name='detalle-inventario-bulk-create'),
    path('detalles-inventario/<int:pk>/', DetalleInventarioDetailView.as_view(), name='detalle-inventario-detail'),
    path('precios-sucursal/', PrecioSucursalListCreateView.as_view(), name='precio-sucursal-list-create'),
    path('precios-sucursal/<int:pk>/', PrecioSucursalDetailView.as_view(), name='precio-sucursal-detail'),
    path('precios-sucursal/activo/', PrecioActivoView.as_view(), name='precio-sucursal-activo'),
    path('precios-sucursal/historial/', HistorialPrecioView.as_view(), name='precio-sucursal-historial'),
]
