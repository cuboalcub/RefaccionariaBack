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

        total_general = self.venta_repository.get_total_ventas_por_rango(
            fecha_inicio,
            fecha_fin
        )

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
                "vendedor": f"{venta.id_usuario.first_name} {venta.id_usuario.last_name}" if venta.id_usuario and (venta.id_usuario.first_name or venta.id_usuario.last_name) else str(venta.id_usuario),
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
        ahora = timezone.localtime()

        if tipo == "day":
            inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
            fin = inicio + timedelta(days=1)

        elif tipo == "week":
            inicio = ahora - timedelta(days=ahora.weekday())
            inicio = inicio.replace(hour=0, minute=0, second=0, microsecond=0)
            fin = inicio + timedelta(days=7)

        elif tipo == "quincena":
            if not year or not month:
                raise ValueError("Debe enviar year y month para quincena")

            inicio_mes = ahora.replace(
                year=year,
                month=month,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )

            if ahora.day <= 15:
                # Primera quincena
                inicio = inicio_mes
                fin = inicio_mes.replace(day=16)
            else:
                # Segunda quincena
                inicio = inicio_mes.replace(day=16)

                if month == 12:
                    fin = inicio.replace(year=year + 1, month=1, day=1)
                else:
                    fin = inicio.replace(month=month + 1, day=1)

        elif tipo == "month":

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

                if month == 12:
                    fin = inicio.replace(year=year + 1, month=1)
                else:
                    fin = inicio.replace(month=month + 1)

            else:
                inicio = ahora.replace(
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )
                fin = ahora

        elif tipo == "year":
            if not year:
                raise ValueError("Debe enviar year para reporte anual")

            inicio = ahora.replace(
                year=year,
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )

            fin = inicio.replace(year=year + 1)

        else:
            raise ValueError("Tipo de reporte inválido")

        return inicio, fin