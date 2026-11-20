# users/serializers.py

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings

from usuario.authentication import ERROR_SESION
from usuario.models import SesionActiva


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "is_active"]


class SessionTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        ahora = timezone.now()
        sesion = SesionActiva.objects.filter(
            usuario_id=refresh.get(api_settings.USER_ID_CLAIM),
            session_jti=refresh.get("sid"),
        ).first()
        if not sesion:
            raise InvalidToken(ERROR_SESION)
        if ahora - sesion.ultima_actividad >= timedelta(
            minutes=settings.SESSION_IDLE_MINUTES
        ):
            sesion.delete()
            raise InvalidToken(ERROR_SESION)
        data = super().validate(attrs)
        SesionActiva.objects.filter(pk=sesion.pk).update(ultima_actividad=ahora)
        return data
