# users/urls.py
from django.urls import path
from usuario.controllers.usuario_controller import UserListCreateView, UserDetailView, UserLoginView

urlpatterns = [
    path("users/", UserListCreateView.as_view(), name="user-list-create"),
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path("login", UserLoginView.as_view(), name="user-login"),
]
