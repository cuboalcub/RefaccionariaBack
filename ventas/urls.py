from django.urls import path
from ventas.controllers.metodo_pago_controller import MetodoPagoListCreateView, MetodoPagoDetailView
from ventas.controllers.venta_controller import VentaListController, VentaDetailController
from ventas.controllers.detalle_venta_controller import DetalleVentaListCreate, DetalleVentaDetail
from ventas.views.reporte_venta_view import ReporteVentaView
from ventas.controllers.venta_ticket_controller import VentaTicketController

urlpatterns = [
    path('metodopago/', MetodoPagoListCreateView.as_view(), name='metodopago-list-create'),
    path('metodopago/<int:pk>/', MetodoPagoDetailView.as_view(), name='metodopago-detail'),
    path('ventas/', VentaListController.as_view(), name='ventas-list'),
    path('ventas/<int:pk>/', VentaDetailController.as_view(), name='ventas-detail'),
    path('detalleventa/', DetalleVentaListCreate.as_view(), name='detalleventa-list-create'),
    path('detalleventa/<int:pk>/', DetalleVentaDetail.as_view(), name='detalleventa-detail'),
    path('reporte/', ReporteVentaView.as_view(), name='reporte-ventas'),
    path('ventas/<int:pk>/ticket/', VentaTicketController.as_view()),
]
