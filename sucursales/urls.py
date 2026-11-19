from django.urls import path

from sucursales.controllers.sucursal_controller import SucursalListCreateView, SucursalDetailView

urlpatterns = [
    path('sucursales/', SucursalListCreateView.as_view(), name='sucursal-list-create'),
    path('sucursales/<int:pk>/', SucursalDetailView.as_view(), name='sucursal-detail'),
]
