from django.urls import path

from clientes.controllers.cliente_controller import ClienteListCreateView, ClienteDetailView

urlpatterns = [
    path('clientes/', ClienteListCreateView.as_view(), name='cliente-list-create'),
    path('clientes/<int:pk>/', ClienteDetailView.as_view(), name='cliente-detail'),
]
