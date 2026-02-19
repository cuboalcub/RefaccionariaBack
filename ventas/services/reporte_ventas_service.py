from datetime import timedelta
from django.utils import timezone
from ventas.repositories.ventas_repository import VentaRepository


class ReporteVentasService:

    def __init__(self):
        self.venta_repository = VentaRepository()

    def generar_reporte(self, tipo: str, year=None, month=None):
        fecha_inicio, fecha_fin = self._calcular_rango(tipo, year, month)

        ventas = self.venta_repository.get_ventas_por_rango(
            fecha_inicio,
            fecha_fin
        )

        total_general = sum(v.total for v in ventas)

        data = []

        for venta in ventas:
            detalles = []
            for detalle in venta.detalleventa_set.all():
                detalles.append({
                    "producto": str(detalle.id_producto),
                    "cantidad": detalle.cantidad,
                    "subtotal": detalle.subtotal
                })

            data.append({
                "id": venta.id,
                "fecha": venta.fecha,
                "vendedor": str(venta.id_usuario),
                "metodo_pago": venta.id_metodoPago.tipo if venta.id_metodoPago else None,
                "total": venta.total,
                "detalles": detalles
            })

        return {
            "tipo": tipo,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "total_general": total_general,
            "ventas": data
        }

    def _calcular_rango(self, tipo: str, year=None, month=None):
        ahora = timezone.now()

        if tipo == "day":
            inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
            fin = inicio + timedelta(days=1)

        elif tipo == "week":
            inicio = ahora - timedelta(days=ahora.weekday())
            inicio = inicio.replace(hour=0, minute=0, second=0, microsecond=0)
            fin = inicio + timedelta(days=7)

        elif tipo == "biweek":
            inicio = ahora - timedelta(days=14)
            fin = ahora

        elif tipo == "month":

            # Si se pasan year y month → usar esos
            if year and month:
                inicio = ahora.replace(
                    year=year,
                    month=month,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )

                # Calcular primer día del siguiente mes
                if month == 12:
                    fin = inicio.replace(year=year + 1, month=1)
                else:
                    fin = inicio.replace(month=month + 1)

            else:
                # Mes actual
                inicio = ahora.replace(
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )
                fin = ahora

        else:
            raise ValueError("Tipo de reporte inválido")

        return inicio, fin