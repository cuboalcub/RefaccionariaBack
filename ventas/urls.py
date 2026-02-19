from django.urls import path
from ventas.controllers.metodopago_controller import MetodoPagoListCreateView, MetodoPagoDetailView
from ventas.controllers.ventas_controller import VentasListController, VentasDetailController
from ventas.controllers.detalleventas_controller import DetalleVentaListCreate, DetalleVentaDetail
from ventas.views.reporte_ventas_view import ReporteVentasView

urlpatterns = [
    path('metodopago/', MetodoPagoListCreateView.as_view(), name='metodopago-list-create'),
    path('metodopago/<int:pk>/', MetodoPagoDetailView.as_view(), name='metodopago-detail'),
    path('ventas/', VentasListController.as_view(), name='ventas-list'),
    path('ventas/<int:pk>/', VentasDetailController.as_view(), name='ventas-detail'),
    path('detalle/', DetalleVentaListCreate.as_view(), name='detalleventa-list-create'),
    path('detalle/<int:pk>/', DetalleVentaDetail.as_view(), name='detalleventa-detail'),
    path('reporte/', ReporteVentasView.as_view(), name='reporte-ventas')
]
