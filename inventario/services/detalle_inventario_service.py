from django.db import transaction

from inventario.models import DetalleInventario, Inventario, MovimientoInventario
from inventario.repositories.detalle_inventario_repository import DetalleInventarioRepository
from producto.models import Producto, Proveedor
from repository.base_service import BaseService
from repository.exceptions import NotFoundError

MSG_TIPO_MOVIMIENTO_INVALIDO = "tipo_movimiento debe ser ENTRADA o SALIDA"
MSG_CANTIDAD_NEGATIVA = "La cantidad no puede ser negativa"
MSG_PROVEEDOR_INEXISTENTE = "El proveedor indicado no existe"
MSG_AJUSTE_MANUAL = "Ajuste manual"
CAMPOS_OBLIGATORIOS = ("id_producto", "id_inventario", "cantidad")


def _programar_alerta(producto_id, inventario_id):
    """Programa la evaluación de alertas de stock tras el commit.

    Importación diferida para no acoplar el inventario a la app de
    notificaciones a nivel de módulo. La evaluación corre en on_commit y
    sus fallos solo quedan en el log (ver stock_alerts).
    """
    from notifications.services.stock_alerts import programar_evaluacion

    programar_evaluacion(producto_id, inventario_id)


class DetalleInventarioService(BaseService):
    def __init__(self):
        super().__init__(model=DetalleInventario, repository=DetalleInventarioRepository())

    def _validar(self, data):
        self._validar_campos_obligatorios(data)
        if not Producto.objects.filter(id=data["id_producto"]).exists():
            raise ValueError("El producto indicado no existe")
        if not Inventario.objects.filter(id=data["id_inventario"]).exists():
            raise ValueError("El inventario indicado no existe")
        self._validar_movimiento_referenciado(data)
        if data["cantidad"] < 0:
            raise ValueError(MSG_CANTIDAD_NEGATIVA)

    def _validar_campos_obligatorios(self, data):
        faltantes = [f for f in CAMPOS_OBLIGATORIOS if f not in data or data[f] is None]
        if faltantes:
            raise ValueError(f"Faltan campos obligatorios: {faltantes[0]}")

    def _validar_movimiento_referenciado(self, data):
        if "id_movimiento" in data and data["id_movimiento"] is not None:
            if not MovimientoInventario.objects.filter(id=data["id_movimiento"]).exists():
                raise ValueError("El movimiento indicado no existe")
        else:
            tipo = data.get("tipo_movimiento") or data.get("tipo") or "ENTRADA"
            if tipo not in ["ENTRADA", "SALIDA"]:
                raise ValueError(MSG_TIPO_MOVIMIENTO_INVALIDO)

    def get_stock(self, producto_id, inventario_id=None):
        return self.repository.get_stock(producto_id, inventario_id)

    def _validar_salida(self, producto_id, inventario_id, cantidad):
        stock = self.get_stock(producto_id, inventario_id)
        if stock < cantidad:
            raise ValueError(
                f"Stock insuficiente: disponible {stock}, solicitado {cantidad}"
            )

    @transaction.atomic
    def create(self, data):
        data = dict(data)
        self._validar_campos_obligatorios(data)
        if data["cantidad"] < 0:
            raise ValueError(MSG_CANTIDAD_NEGATIVA)
        data = self._auto_crear_movimiento(data)
        self._validar(data)
        movimiento = MovimientoInventario.objects.get(id=data["id_movimiento"])

        if movimiento.tipo == MovimientoInventario.TipoMovimiento.SALIDA:
            Producto.objects.select_for_update().get(id=data["id_producto"])
            self._validar_salida(data["id_producto"], data["id_inventario"], data["cantidad"])

        data = self._resolver_fks_create(data, movimiento)
        resultado = super().create(data)
        _programar_alerta(data["id_producto"].id, data["id_inventario"].id)
        return resultado

    def _auto_crear_movimiento(self, data):
        if "id_movimiento" not in data or data["id_movimiento"] is None:
            tipo = data.pop("tipo_movimiento", None) or data.pop("tipo", None) or "ENTRADA"
            razon = data.pop("razon", None) or data.pop("razón", None) or MSG_AJUSTE_MANUAL
            observaciones = data.pop("observaciones", None)
            if tipo not in ["ENTRADA", "SALIDA"]:
                raise ValueError(MSG_TIPO_MOVIMIENTO_INVALIDO)
            movimiento = MovimientoInventario.objects.create(
                tipo=tipo,
                cantidad=data["cantidad"],
                razon=razon,
                observaciones=observaciones or "",
            )
            data["id_movimiento"] = movimiento.id
        return data

    def _resolver_fks_create(self, data, movimiento):
        data["id_producto"] = Producto.objects.get(id=data["id_producto"])
        data["id_inventario"] = Inventario.objects.get(id=data["id_inventario"])
        data["id_movimiento"] = movimiento
        return self._resolver_proveedor(data)

    def _resolver_proveedor(self, data):
        if "id_proveedor" in data and data["id_proveedor"]:
            if not Proveedor.objects.filter(id=data["id_proveedor"]).exists():
                raise ValueError(MSG_PROVEEDOR_INEXISTENTE)
            data["id_proveedor"] = Proveedor.objects.get(id=data["id_proveedor"])
        else:
            data.pop("id_proveedor", None)
        return data

    @transaction.atomic
    def update(self, id, data):
        detalle = self.repository.get_by_id(id)
        if not detalle:
            raise NotFoundError(f"{self.model.__name__} con id {id} no encontrado")

        movimiento_id = self._resolver_movimiento_id(detalle, data)
        movimiento = MovimientoInventario.objects.get(id=movimiento_id)
        nueva_cantidad = data.get("cantidad", detalle.cantidad)
        if nueva_cantidad < 0:
            raise ValueError(MSG_CANTIDAD_NEGATIVA)

        nuevo_producto_id = data.get("id_producto", detalle.id_producto_id)
        nuevo_inventario_id = data.get("id_inventario", detalle.id_inventario_id)

        self._validar_stock_update(detalle, movimiento, nuevo_producto_id, nuevo_inventario_id, nueva_cantidad)

        if not Producto.objects.filter(id=nuevo_producto_id).exists():
            raise ValueError("El producto indicado no existe")
        if not Inventario.objects.filter(id=nuevo_inventario_id).exists():
            raise ValueError("El inventario indicado no existe")

        data["id_producto"] = Producto.objects.get(id=nuevo_producto_id)
        data["id_inventario"] = Inventario.objects.get(id=nuevo_inventario_id)
        data["id_movimiento"] = movimiento

        data = self._resolver_proveedor_update(data)

        resultado = super().update(id, data)
        _programar_alerta(detalle.id_producto_id, detalle.id_inventario_id)
        _programar_alerta(data["id_producto"].id, data["id_inventario"].id)
        return resultado

    def _resolver_movimiento_id(self, detalle, data):
        if "id_movimiento" in data and data["id_movimiento"] is not None:
            movimiento_id = data["id_movimiento"]
        elif any(k in data for k in ("tipo_movimiento", "tipo", "razon", "observaciones")):
            self._actualizar_movimiento(detalle.id_movimiento, data)
            movimiento_id = detalle.id_movimiento_id
        else:
            movimiento_id = data.get("id_movimiento", detalle.id_movimiento_id)
        return movimiento_id

    def _actualizar_movimiento(self, mov, data):
        if "tipo_movimiento" in data or "tipo" in data:
            nuevo_tipo = data.pop("tipo_movimiento", None) or data.pop("tipo", None)
            if nuevo_tipo not in ["ENTRADA", "SALIDA"]:
                raise ValueError(MSG_TIPO_MOVIMIENTO_INVALIDO)
            mov.tipo = nuevo_tipo
        if "razon" in data:
            mov.razon = data.pop("razon")
        if "observaciones" in data:
            mov.observaciones = data.pop("observaciones")
        if "cantidad" in data:
            mov.cantidad = data["cantidad"]
        mov.save()

    def _validar_stock_update(self, detalle, movimiento, producto_id, inventario_id, nueva_cantidad):
        if movimiento.tipo != MovimientoInventario.TipoMovimiento.SALIDA:
            return
        Producto.objects.select_for_update().get(id=producto_id)
        stock = self.get_stock(producto_id, inventario_id)
        stock_sin_este = stock - (-detalle.cantidad if detalle.id_movimiento.tipo == MovimientoInventario.TipoMovimiento.SALIDA else detalle.cantidad)
        if stock_sin_este < nueva_cantidad:
            raise ValueError(
                f"Stock insuficiente: disponible {stock_sin_este}, solicitado {nueva_cantidad}"
            )

    def _resolver_proveedor_update(self, data):
        if "id_proveedor" in data:
            if not data["id_proveedor"]:
                data["id_proveedor"] = None
            elif not Proveedor.objects.filter(id=data["id_proveedor"]).exists():
                raise ValueError(MSG_PROVEEDOR_INEXISTENTE)
            else:
                data["id_proveedor"] = Proveedor.objects.get(id=data["id_proveedor"])
        return data

    def delete(self, id, user=None):
        detalle = self.repository.get_by_id(id)
        if not detalle:
            raise NotFoundError(f"{self.model.__name__} con id {id} no encontrado")
        return super().delete(id, user)

    def crear_salida_por_venta(self, detalle_venta, producto, inventario, cantidad):
        movimiento = MovimientoInventario.objects.create(
            tipo=MovimientoInventario.TipoMovimiento.SALIDA,
            cantidad=cantidad,
            razon="Venta",
            observaciones=f"Venta {detalle_venta.id_venta_id}",
        )
        instance = self.repository.create({
            "id_producto": producto,
            "id_inventario": inventario,
            "id_movimiento": movimiento,
            "id_detalle_venta": detalle_venta,
            "cantidad": cantidad,
        })
        _programar_alerta(producto.id, inventario.id)
        return instance

    def ajustar_salida_por_venta(self, detalle_venta, nueva_cantidad, producto=None, inventario=None):
        detalle = self.repository.get_by_detalle_venta(detalle_venta.id)
        if not detalle:
            return None

        producto = producto or detalle.id_producto
        inventario = inventario or detalle.id_inventario

        stock = self.get_stock(producto.id, inventario.id)
        stock_sin_este = stock + detalle.cantidad
        if stock_sin_este < nueva_cantidad:
            raise ValueError(
                f"Stock insuficiente: disponible {stock_sin_este}, solicitado {nueva_cantidad}"
            )

        detalle.cantidad = nueva_cantidad
        previo_producto_id = detalle.id_producto_id
        previo_inventario_id = detalle.id_inventario_id
        detalle.id_producto = producto
        detalle.id_inventario = inventario
        detalle.save(update_fields=["cantidad", "id_producto", "id_inventario", "update_at"])
        try:
            mov = detalle.id_movimiento
            if mov.cantidad != nueva_cantidad:
                mov.cantidad = nueva_cantidad
                mov.save(update_fields=["cantidad"])
        except Exception:
            pass
        _programar_alerta(previo_producto_id, previo_inventario_id)
        _programar_alerta(producto.id, inventario.id)
        return detalle

    def revertir_salida_por_venta(self, detalle_venta):
        detalle = self.repository.get_by_detalle_venta(detalle_venta.id)
        if not detalle:
            return None
        producto_id = detalle.id_producto_id
        inventario_id = detalle.id_inventario_id
        movimiento = detalle.id_movimiento
        detalle.delete()
        movimiento.delete()
        _programar_alerta(producto_id, inventario_id)
        return True

    def get_inventario_por_sucursal(self, sucursal_id):
        inventarios = Inventario.objects.filter(id_sucursal=sucursal_id).prefetch_related('detalles__id_producto', 'detalles__id_movimiento')
        from inventario.models import PrecioSucursal
        precio_map = {
            ps.id_producto_id: ps for ps in PrecioSucursal.objects.filter(id_sucursal_id=sucursal_id, activo=True)
        }
        resultado = []
        for inv in inventarios:
            productos = {}
            for d in inv.detalles.all():
                producto = d.id_producto
                entrada = d.id_movimiento.tipo == MovimientoInventario.TipoMovimiento.ENTRADA
                signo = 1 if entrada else -1
                ps = precio_map.get(producto.id)
                productos.setdefault(producto.id, {
                    "id": d.id,
                    "id_producto": producto.id,
                    "nombre": producto.nombre,
                    "clave": producto.clave,
                    "marca": producto.marca,
                    "codigo_barras": producto.codigo_barras,
                    "precio_venta": str(producto.precio_venta),
                    "precio_sucursal": str(ps.precio_venta) if ps else None,
                    "vigente_desde": ps.vigente_desde.isoformat() if ps and ps.vigente_desde else None,
                    "precio_base": str(producto.precio_venta),
                    "costo": str(producto.costo),
                    "cantidad": 0,
                })
                productos[producto.id]["cantidad"] += signo * d.cantidad

            resultado.append({
                "id_inventario": inv.id,
                "descripcion": inv.descripcion,
                "id_sucursal": inv.id_sucursal_id,
                "detalles": sorted(productos.values(), key=lambda p: p["nombre"]),
            })
        return resultado

    @transaction.atomic
    def bulk_create(self, data):
        """Crea múltiples DetalleInventario en una transacción.
        Formatos soportados:
        1) {"id_inventario":1,"id_movimiento":1,"id_proveedor":1,"items":[{"id_producto":1,"cantidad":5},...]}
        2) {"id_inventario":1,"id_movimiento":1,"detalles":[...]}  (alias)
        3) [{"id_producto":1,"id_inventario":1,"id_movimiento":1,"cantidad":5}, ...] (lista plana)
        """
        if isinstance(data, dict) and not (isinstance(data.get('items'), list) or isinstance(data.get('detalles'), list)):
            return [self.create(data)]

        items, common_inventario, common_movimiento, common_proveedor = self._normalizar_bulk(data)
        if items is None:
            raise ValueError("Formato bulk inválido. Use {'id_inventario':1,'id_movimiento':1,'items':[...]} o lista de objetos")
        if not items:
            raise ValueError("La lista de items no puede estar vacía")

        estado = {"movimiento": None}
        if common_movimiento is not None:
            estado["movimiento"] = self._buscar_movimiento(common_movimiento)
        common_tipo, common_razon, common_observaciones = self._comunes_de_data(data)

        resultados = []
        for idx, item in enumerate(items):
            resultados.append(self._procesar_item_bulk(idx, item, items, common_inventario, common_movimiento, common_proveedor, common_tipo, common_razon, common_observaciones, estado))

        for item in resultados:
            _programar_alerta(item["id_producto"], item["id_inventario"])
        return resultados

    @staticmethod
    def _comunes_de_data(data):
        if isinstance(data, dict):
            return (data.get('tipo_movimiento') or data.get('tipo'), data.get('razon'), data.get('observaciones'))
        return None, None, None

    def _procesar_item_bulk(self, idx, item, items, common_inventario, common_movimiento, common_proveedor, common_tipo, common_razon, common_observaciones, estado):
        if not isinstance(item, dict):
            raise ValueError(f"Item {idx} debe ser un objeto")
        cur = self._fusionar_comunes(item, common_inventario, common_movimiento, common_proveedor)
        if 'id_movimiento' not in cur or cur['id_movimiento'] is None:
            return self._crear_item_auto(cur, items, common_tipo, common_razon, common_observaciones, common_movimiento, estado)
        movimiento = self._resolver_movimiento_bulk(cur, estado["movimiento"], common_movimiento)
        self._validar(cur)
        self._validar_salida_bulk(cur, movimiento)
        return self._crear_detalle(cur, movimiento)

    @staticmethod
    def _normalizar_bulk(data):
        if isinstance(data, list):
            return data, None, None, None
        if isinstance(data, dict):
            for key in ('items', 'detalles'):
                if isinstance(data.get(key), list):
                    return (
                        data[key],
                        data.get('id_inventario'),
                        data.get('id_movimiento'),
                        data.get('id_proveedor'),
                    )
        return None, None, None, None

    @staticmethod
    def _buscar_movimiento(common_movimiento):
        try:
            return MovimientoInventario.objects.get(id=common_movimiento)
        except MovimientoInventario.DoesNotExist:
            raise ValueError("El movimiento indicado no existe")

    @staticmethod
    def _fusionar_comunes(item, common_inventario, common_movimiento, common_proveedor):
        cur = dict(item)
        if common_inventario is not None and 'id_inventario' not in cur:
            cur['id_inventario'] = common_inventario
        if common_movimiento is not None and 'id_movimiento' not in cur:
            cur['id_movimiento'] = common_movimiento
        if common_proveedor is not None and 'id_proveedor' not in cur:
            cur['id_proveedor'] = common_proveedor
        return cur

    @staticmethod
    def _resolver_movimiento_bulk(cur, movimiento_comun, common_movimiento):
        if movimiento_comun is not None and cur.get('id_movimiento') == common_movimiento:
            return movimiento_comun
        return MovimientoInventario.objects.get(id=cur['id_movimiento'])

    def _validar_salida_bulk(self, cur, movimiento):
        if movimiento.tipo == MovimientoInventario.TipoMovimiento.SALIDA:
            Producto.objects.select_for_update().get(id=cur['id_producto'])
            self._validar_salida(cur['id_producto'], cur['id_inventario'], cur['cantidad'])

    def _crear_detalle(self, cur, movimiento):
        cur['id_producto'] = Producto.objects.get(id=cur['id_producto'])
        cur['id_inventario'] = Inventario.objects.get(id=cur['id_inventario'])
        cur['id_movimiento'] = movimiento
        data = self._resolver_proveedor(cur)
        instance = self.repository.create(data)
        return self._to_dict(instance)

    def _crear_item_auto(self, cur, items, common_tipo, common_razon, common_observaciones, common_movimiento, estado):
        tipo = cur.pop('tipo_movimiento', None) or cur.pop('tipo', None) or common_tipo or 'ENTRADA'
        if tipo not in ['ENTRADA', 'SALIDA']:
            raise ValueError(MSG_TIPO_MOVIMIENTO_INVALIDO)
        razon = cur.pop('razon', None) or common_razon or MSG_AJUSTE_MANUAL
        observaciones = cur.pop('observaciones', None) or common_observaciones
        if common_movimiento is None and common_tipo is not None:
            if estado["movimiento"] is None:
                estado["movimiento"] = self._crear_movimiento_comun(items, common_tipo, common_razon, common_observaciones)
            cur['id_movimiento'] = estado["movimiento"].id
        else:
            movimiento = MovimientoInventario.objects.create(
                tipo=tipo,
                cantidad=cur['cantidad'],
                razon=razon,
                observaciones=observaciones or "",
            )
            cur['id_movimiento'] = movimiento.id
        movimiento = self._resolver_movimiento_bulk(cur, estado["movimiento"], common_movimiento)
        self._validar(cur)
        self._validar_salida_bulk(cur, movimiento)
        return self._crear_detalle(cur, movimiento)

    @staticmethod
    def _crear_movimiento_comun(items, common_tipo, common_razon, common_observaciones):
        total_cantidad = sum(
            int(it.get('cantidad', 0)) for it in items
            if ('id_movimiento' not in it or it['id_movimiento'] is None) and ('tipo_movimiento' not in it and 'tipo' not in it or True)
        )
        return MovimientoInventario.objects.create(
            tipo=common_tipo if common_tipo in ['ENTRADA', 'SALIDA'] else 'ENTRADA',
            cantidad=total_cantidad,
            razon=common_razon or MSG_AJUSTE_MANUAL,
            observaciones=common_observaciones or "",
        )

    def _to_dict(self, instance):
        if not instance:
            return None
        return {
            "id": instance.id,
            "id_producto": instance.id_producto_id,
            "id_inventario": instance.id_inventario_id,
            "id_proveedor": instance.id_proveedor_id,
            "id_movimiento": instance.id_movimiento_id,
            "id_detalle_venta": instance.id_detalle_venta_id,
            "cantidad": instance.cantidad,
            "update_at": instance.update_at.isoformat() if instance.update_at else None,
        }
