from django.urls import path

from clientes.controllers.cliente_controller import ClienteListCreateView, ClienteDetailView
from clientes.controllers.adeudo_controller import (
    AdeudoListCreateView,
    AdeudoDetailView,
    AbonoAdeudoListCreateView,
)

urlpatterns = [
    path('clientes/', ClienteListCreateView.as_view(), name='cliente-list-create'),
    path('clientes/<int:pk>/', ClienteDetailView.as_view(), name='cliente-detail'),
    path('adeudos/', AdeudoListCreateView.as_view(), name='adeudo-list-create'),
    path('adeudos/<int:pk>/', AdeudoDetailView.as_view(), name='adeudo-detail'),
    path(
        'adeudos/<int:pk>/abonos/',
        AbonoAdeudoListCreateView.as_view(),
        name='adeudo-abonos',
    ),
]
