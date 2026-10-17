from datetime import timedelta
from django.utils import timezone
from ventas.repositories.venta_repository import VentaRepository


class ReporteVentaService:

    def __init__(self):
        self.venta_repository = VentaRepository()

    def generar_reporte(self, tipo: str, year=None, month=None, quincena=None):
        fecha_inicio, fecha_fin = self._calcular_rango(tipo, year, month, quincena)

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
                "metodo_pago": venta.id_metodo_pago.tipo if venta.id_metodo_pago else None,
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

    def _inicio_de_mes(self, ahora, year, month):
        return ahora.replace(
            year=year,
            month=month,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

    def _rango_dia(self, ahora):
        inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        return inicio, inicio + timedelta(days=1)

    def _rango_semana(self, ahora):
        inicio = ahora - timedelta(days=ahora.weekday())
        inicio = inicio.replace(hour=0, minute=0, second=0, microsecond=0)
        return inicio, inicio + timedelta(days=7)

    def _rango_quincena(self, ahora, year=None, month=None, quincena=None):
        if not year or not month or not quincena:
            raise ValueError("Debe enviar year, month y quincena (1 o 2)")

        inicio_mes = self._inicio_de_mes(ahora, year, month)

        if int(quincena) == 1:
            return inicio_mes, inicio_mes.replace(day=16)

        if int(quincena) == 2:
            inicio = inicio_mes.replace(day=16)
            return inicio, self._fin_de_quincena(inicio, year, month)

        raise ValueError("Quincena debe ser 1 o 2")

    def _fin_de_quincena(self, inicio, year, month):
        if month == 12:
            return inicio.replace(year=year + 1, month=1, day=1)
        return inicio.replace(month=month + 1, day=1)

    def _rango_mes(self, ahora, year=None, month=None):
        if year and month:
            inicio = self._inicio_de_mes(ahora, year, month)
            return inicio, self._fin_de_mes(inicio, year, month)

        inicio = ahora.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )
        return inicio, ahora

    def _fin_de_mes(self, inicio, year, month):
        if month == 12:
            return inicio.replace(year=year + 1, month=1)
        return inicio.replace(month=month + 1)

    def _rango_year(self, ahora, year=None):
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
        return inicio, inicio.replace(year=year + 1)

    def _calcular_rango(self, tipo: str, year=None, month=None, quincena=None):
        ahora = timezone.localtime()

        if tipo == "day":
            return self._rango_dia(ahora)

        if tipo == "week":
            return self._rango_semana(ahora)

        if tipo == "quincena":
            return self._rango_quincena(ahora, year, month, quincena)

        if tipo == "month":
            return self._rango_mes(ahora, year, month)

        if tipo == "year":
            return self._rango_year(ahora, year)

        raise ValueError("Tipo de reporte inválido")