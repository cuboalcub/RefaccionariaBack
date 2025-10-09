# users/urls.py
from django.urls import path
from usuario.controllers.usuario_controller import UserListCreateView, UserDetailView, UserLoginView
from rest_framework_simplejwt.views import (
    TokenRefreshView,      # Para obtener un nuevo access con el refresh
)

    
urlpatterns = [
    path("users", UserListCreateView.as_view(), name="user-list-create"),
    path("users/<int:user_id>", UserDetailView.as_view(), name="user-detail"),
    path("login", UserLoginView.as_view(), name="user-login"),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
]
