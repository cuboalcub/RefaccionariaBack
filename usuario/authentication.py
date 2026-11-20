from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from usuario.models import SesionActiva

ERROR_SESION = "Sesión expirada o iniciada en otro dispositivo"


class SessionJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result
        ahora = timezone.now()
        sesion = SesionActiva.objects.filter(
            usuario=user, session_jti=token.get("sid")
        ).first()
        if not sesion or self._expirada(sesion, ahora):
            raise AuthenticationFailed(ERROR_SESION, code="session_expired")
        # Actualiza como máximo cada minuto para no escribir en cada request.
        if (
            ahora - sesion.ultima_actividad
        ).total_seconds() >= settings.SESSION_ACTIVITY_TOUCH_SECONDS:
            SesionActiva.objects.filter(pk=sesion.pk).update(ultima_actividad=ahora)
        return result

    @staticmethod
    def _expirada(sesion, ahora):
        return ahora - sesion.ultima_actividad >= timedelta(
            minutes=settings.SESSION_IDLE_MINUTES
        )
