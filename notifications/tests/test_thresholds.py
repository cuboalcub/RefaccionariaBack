"""Umbral NOTIFICATIONS_LOW_STOCK_THRESHOLD: defecto y validación."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from notifications.services.thresholds import get_low_stock_threshold


@pytest.mark.django_db
class TestThreshold:
    def test_defecto_10_sin_setting(self, settings):
        del settings.NOTIFICATIONS_LOW_STOCK_THRESHOLD
        assert get_low_stock_threshold() == 10

    def test_acepta_entero(self, settings):
        settings.NOTIFICATIONS_LOW_STOCK_THRESHOLD = 10
        assert get_low_stock_threshold() == 10

    def test_acepta_cadena_numerica(self, settings):
        settings.NOTIFICATIONS_LOW_STOCK_THRESHOLD = "10"
        assert get_low_stock_threshold() == 10

    @pytest.mark.parametrize("valor", [0, 1, -3, "x", None, ""])
    def test_rechaza_invalidos(self, settings, valor):
        settings.NOTIFICATIONS_LOW_STOCK_THRESHOLD = valor
        with pytest.raises(ImproperlyConfigured):
            get_low_stock_threshold()
