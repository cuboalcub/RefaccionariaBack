from decimal import Decimal

from ventas.services.iva import calcular_iva


def test_calcular_iva_16_por_ciento():
    assert calcular_iva(Decimal("200.00")) == Decimal("32.00")


def test_calcular_iva_redondea_half_up():
    assert calcular_iva(Decimal("0.01")) == Decimal("0.00")
    assert calcular_iva(Decimal("0.04")) == Decimal("0.01")


def test_calcular_iva_base_cero():
    assert calcular_iva(0) == Decimal("0.00")
