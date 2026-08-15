# users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from usuario.controllers.usuario_controller import (
    UserDetailView,
    UserListCreateView,
    UserLoginView,
)
from usuario.controllers.perfil_controller import PerfilView

urlpatterns = [
    path("users", UserListCreateView.as_view(), name="user-list-create"),
    path("users/<int:user_id>", UserDetailView.as_view(), name="user-detail"),
    path("login", UserLoginView.as_view(), name="user-login"),
    path("token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("perfil/", PerfilView.as_view(), name="perfil"),
]
