from decimal import ROUND_HALF_UP, Decimal

IVA_TASA = Decimal("0.16")
_CENTAVOS = Decimal("0.01")


def calcular_iva(base):
    """IVA de una base (suma de subtotales) redondeado a centavos."""
    return (Decimal(base) * IVA_TASA).quantize(_CENTAVOS, rounding=ROUND_HALF_UP)
