from django.db import transaction

from inventario.models import DetalleInventario, Inventario, MovimientoInventario
from inventario.repositories.detalle_inventario_repository import DetalleInventarioRepository
from producto.models import Producto, Proveedor
from repository.base_service import BaseService
from repository.exceptions import NotFoundError


class DetalleInventarioService(BaseService):
    def __init__(self):
        super().__init__(model=DetalleInventario, repository=DetalleInventarioRepository())

    def _validar(self, data):
        if "id_producto" not in data or data["id_producto"] is None:
            raise ValueError("Faltan campos obligatorios: id_producto")
        if "id_inventario" not in data or data["id_inventario"] is None:
            raise ValueError("Faltan campos obligatorios: id_inventario")
        if "cantidad" not in data or data["cantidad"] is None:
            raise ValueError("Faltan campos obligatorios: cantidad")
        if not Producto.objects.filter(id=data["id_producto"]).exists():
            raise ValueError("El producto indicado no existe")
        if not Inventario.objects.filter(id=data["id_inventario"]).exists():
            raise ValueError("El inventario indicado no existe")
        # id_movimiento es opcional: si se envía, debe existir; si no, se auto-creará
        if "id_movimiento" in data and data["id_movimiento"] is not None:
            if not MovimientoInventario.objects.filter(id=data["id_movimiento"]).exists():
                raise ValueError("El movimiento indicado no existe")
        else:
            # Validar campos para auto-creación
            tipo = data.get("tipo_movimiento") or data.get("tipo") or "ENTRADA"
            if tipo not in ["ENTRADA", "SALIDA"]:
                raise ValueError("tipo_movimiento debe ser ENTRADA o SALIDA")
            # razon es requerida para auto-crear; si no viene, se usará default en create
        if data["cantidad"] < 0:
            raise ValueError("La cantidad no puede ser negativa")

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
        # Auto-crear movimiento si no se envió id_movimiento
        if "id_movimiento" not in data or data["id_movimiento"] is None:
            tipo = data.pop("tipo_movimiento", None) or data.pop("tipo", None) or "ENTRADA"
            razon = data.pop("razon", None) or data.pop("razón", None) or "Ajuste manual"
            observaciones = data.pop("observaciones", None)
            # Validar tipo
            if tipo not in ["ENTRADA", "SALIDA"]:
                raise ValueError("tipo_movimiento debe ser ENTRADA o SALIDA")
            movimiento = MovimientoInventario.objects.create(
                tipo=tipo,
                cantidad=data["cantidad"],
                razon=razon,
                observaciones=observaciones,
            )
            data["id_movimiento"] = movimiento.id

        self._validar(data)
        movimiento = MovimientoInventario.objects.get(id=data["id_movimiento"])

        if movimiento.tipo == MovimientoInventario.TipoMovimiento.SALIDA:
            Producto.objects.select_for_update().get(id=data["id_producto"])
            self._validar_salida(data["id_producto"], data["id_inventario"], data["cantidad"])

        data["id_producto"] = Producto.objects.get(id=data["id_producto"])
        data["id_inventario"] = Inventario.objects.get(id=data["id_inventario"])
        data["id_movimiento"] = movimiento
        if "id_proveedor" in data and data["id_proveedor"]:
            if not Proveedor.objects.filter(id=data["id_proveedor"]).exists():
                raise ValueError("El proveedor indicado no existe")
            data["id_proveedor"] = Proveedor.objects.get(id=data["id_proveedor"])
        else:
            data.pop("id_proveedor", None)

        return super().create(data)

    @transaction.atomic
    def update(self, id, data):
        detalle = self.repository.get_by_id(id)
        if not detalle:
            raise NotFoundError(f"{self.model.__name__} con id {id} no encontrado")

        # Si se quiere actualizar el movimiento via tipo_movimiento/razon sin id_movimiento, actualizar el movimiento existente
        if "id_movimiento" not in data or data["id_movimiento"] is None:
            if any(k in data for k in ("tipo_movimiento", "tipo", "razon", "observaciones")):
                # Actualizar movimiento existente con nuevos datos
                mov = detalle.id_movimiento
                if "tipo_movimiento" in data or "tipo" in data:
                    nuevo_tipo = data.pop("tipo_movimiento", None) or data.pop("tipo", None)
                    if nuevo_tipo not in ["ENTRADA", "SALIDA"]:
                        raise ValueError("tipo_movimiento debe ser ENTRADA o SALIDA")
                    mov.tipo = nuevo_tipo
                if "razon" in data:
                    mov.razon = data.pop("razon")
                if "observaciones" in data:
                    mov.observaciones = data.pop("observaciones")
                if "cantidad" in data:
                    mov.cantidad = data["cantidad"]
                mov.save()
            movimiento_id = detalle.id_movimiento_id
        else:
            movimiento_id = data.get("id_movimiento", detalle.id_movimiento_id)
        movimiento = MovimientoInventario.objects.get(id=movimiento_id)
        nueva_cantidad = data.get("cantidad", detalle.cantidad)
        if nueva_cantidad < 0:
            raise ValueError("La cantidad no puede ser negativa")

        nuevo_producto_id = data.get("id_producto", detalle.id_producto_id)
        nuevo_inventario_id = data.get("id_inventario", detalle.id_inventario_id)

        if movimiento.tipo == MovimientoInventario.TipoMovimiento.SALIDA:
            Producto.objects.select_for_update().get(id=nuevo_producto_id)
            stock = self.get_stock(nuevo_producto_id, nuevo_inventario_id)
            stock_sin_este = stock - (-detalle.cantidad if detalle.id_movimiento.tipo == MovimientoInventario.TipoMovimiento.SALIDA else detalle.cantidad)
            if stock_sin_este < nueva_cantidad:
                raise ValueError(
                    f"Stock insuficiente: disponible {stock_sin_este}, solicitado {nueva_cantidad}"
                )

        if not Producto.objects.filter(id=nuevo_producto_id).exists():
            raise ValueError("El producto indicado no existe")
        if not Inventario.objects.filter(id=nuevo_inventario_id).exists():
            raise ValueError("El inventario indicado no existe")

        data["id_producto"] = Producto.objects.get(id=nuevo_producto_id)
        data["id_inventario"] = Inventario.objects.get(id=nuevo_inventario_id)
        data["id_movimiento"] = movimiento

        if "id_proveedor" in data:
            if not data["id_proveedor"]:
                data["id_proveedor"] = None
            elif not Proveedor.objects.filter(id=data["id_proveedor"]).exists():
                raise ValueError("El proveedor indicado no existe")
            else:
                data["id_proveedor"] = Proveedor.objects.get(id=data["id_proveedor"])

        return super().update(id, data)

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
        return self.repository.create({
            "id_producto": producto,
            "id_inventario": inventario,
            "id_movimiento": movimiento,
            "id_detalle_venta": detalle_venta,
            "cantidad": cantidad,
        })

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
        detalle.id_producto = producto
        detalle.id_inventario = inventario
        detalle.save(update_fields=["cantidad", "id_producto", "id_inventario", "update_at"])
        # Sincronizar cantidad del movimiento vinculado
        try:
            mov = detalle.id_movimiento
            if mov.cantidad != nueva_cantidad:
                mov.cantidad = nueva_cantidad
                mov.save(update_fields=["cantidad"])
        except Exception:
            pass
        return detalle

    def revertir_salida_por_venta(self, detalle_venta):
        detalle = self.repository.get_by_detalle_venta(detalle_venta.id)
        if not detalle:
            return None
        movimiento = detalle.id_movimiento
        detalle.delete()
        movimiento.delete()
        return True

    def get_inventario_por_sucursal(self, sucursal_id):
        inventarios = Inventario.objects.filter(id_sucursal=sucursal_id).prefetch_related('detalles__id_producto', 'detalles__id_movimiento')
        # Precargar precios activos de la sucursal para enriquecer respuesta
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
                # precio_sucursal: null si no hay PrecioSucursal activo
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

            # Incluir también productos con stock 0 (ya están en dict, no se filtran)
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
        # Normalizar a lista de dicts completos para cada detalle
        items = None
        common_inventario = None
        common_movimiento = None
        common_proveedor = None

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if 'items' in data and isinstance(data['items'], list):
                items = data['items']
                common_inventario = data.get('id_inventario')
                common_movimiento = data.get('id_movimiento')
                common_proveedor = data.get('id_proveedor')
            elif 'detalles' in data and isinstance(data['detalles'], list):
                items = data['detalles']
                common_inventario = data.get('id_inventario')
                common_movimiento = data.get('id_movimiento')
                common_proveedor = data.get('id_proveedor')
            else:
                # Caso dict único: delega a create
                return [self.create(data)]

        if items is None:
            raise ValueError("Formato bulk inválido. Use {'id_inventario':1,'id_movimiento':1,'items':[...]} o lista de objetos")

        if not items:
            raise ValueError("La lista de items no puede estar vacía")

        # Pre-cargar movimiento común si existe (para validar tipo SALIDA)
        movimiento_comun = None
        if common_movimiento is not None:
            try:
                movimiento_comun = MovimientoInventario.objects.get(id=common_movimiento)
            except MovimientoInventario.DoesNotExist:
                raise ValueError("El movimiento indicado no existe")

        # Campos comunes para auto-creación
        common_tipo = data.get('tipo_movimiento') or data.get('tipo') if isinstance(data, dict) else None
        common_razon = data.get('razon') if isinstance(data, dict) else None
        common_observaciones = data.get('observaciones') if isinstance(data, dict) else None

        # Validación previa: si es SALIDA, verificar stock para cada item acumulativamente
        # Para evitar N queries de get_stock, validamos secuencialmente dentro del loop pero dentro de transaction
        resultados = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(f"Item {idx} debe ser un objeto")

            # Construir data completa para cada item
            cur = dict(item)
            if common_inventario is not None and 'id_inventario' not in cur:
                cur['id_inventario'] = common_inventario
            if common_movimiento is not None and 'id_movimiento' not in cur:
                cur['id_movimiento'] = common_movimiento
            if common_proveedor is not None and 'id_proveedor' not in cur:
                cur['id_proveedor'] = common_proveedor

            # Auto-crear movimiento si no se envió id_movimiento
            if 'id_movimiento' not in cur or cur['id_movimiento'] is None:
                tipo = cur.pop('tipo_movimiento', None) or cur.pop('tipo', None) or common_tipo or 'ENTRADA'
                if tipo not in ['ENTRADA', 'SALIDA']:
                    raise ValueError("tipo_movimiento debe ser ENTRADA o SALIDA")
                razon = cur.pop('razon', None) or common_razon or 'Ajuste manual'
                observaciones = cur.pop('observaciones', None) or common_observaciones
                # Usar movimiento_comun si el tipo/razon coinciden y ya existe comun auto? Crear uno por item o compartir común
                # Si hay common_tipo y no hay movimiento_comun, crear uno compartido para todos los items sin movimiento
                if common_movimiento is None and common_tipo is not None:
                    if movimiento_comun is None:
                        total_cantidad = sum(
                            int(it.get('cantidad', 0)) for it in items
                            if ('id_movimiento' not in it or it['id_movimiento'] is None) and ('tipo_movimiento' not in it and 'tipo' not in it or True)
                        )
                        movimiento_comun = MovimientoInventario.objects.create(
                            tipo=common_tipo if common_tipo in ['ENTRADA', 'SALIDA'] else 'ENTRADA',
                            cantidad=total_cantidad,
                            razon=common_razon or 'Ajuste manual',
                            observaciones=common_observaciones,
                        )
                    # Para bulk compartido, reusar mismo movimiento pero actualizar cantidad no es relevante; creamos detalle con mismo movimiento
                    # Para simplificar, si es bulk compartido sin id_movimiento, cada detalle comparte el mismo movimiento_comun
                    # Pero cantidad del movimiento debe reflejar suma? No se usa para stock, solo informativo. Creamos uno nuevo por item si no hay común
                    # Si common_tipo existe, reusar movimiento_comun
                    movimiento = movimiento_comun
                    cur['id_movimiento'] = movimiento.id
                else:
                    # Crear movimiento individual por item
                    movimiento = MovimientoInventario.objects.create(
                        tipo=tipo,
                        cantidad=cur['cantidad'],
                        razon=razon,
                        observaciones=observaciones,
                    )
                    cur['id_movimiento'] = movimiento.id
                    # No asignar movimiento_comun para no reutilizar
                    # Continuar para no re-buscar
                    self._validar(cur)
                    if movimiento.tipo == MovimientoInventario.TipoMovimiento.SALIDA:
                        Producto.objects.select_for_update().get(id=cur['id_producto'])
                        self._validar_salida(cur['id_producto'], cur['id_inventario'], cur['cantidad'])
                    cur['id_producto'] = Producto.objects.get(id=cur['id_producto'])
                    cur['id_inventario'] = Inventario.objects.get(id=cur['id_inventario'])
                    cur['id_movimiento'] = movimiento
                    if 'id_proveedor' in cur and cur['id_proveedor']:
                        if not Proveedor.objects.filter(id=cur['id_proveedor']).exists():
                            raise ValueError("El proveedor indicado no existe")
                        cur['id_proveedor'] = Proveedor.objects.get(id=cur['id_proveedor'])
                    else:
                        cur.pop('id_proveedor', None)
                    instance = self.repository.create(cur)
                    resultados.append(self._to_dict(instance))
                    continue

            # Reusar lógica de create pero sin commit separado (usamos transacción externa)
            self._validar(cur)
            # Determinar movimiento
            if 'id_movimiento' in cur and cur['id_movimiento'] is not None:
                if movimiento_comun is not None and cur.get('id_movimiento') == common_movimiento:
                    movimiento = movimiento_comun
                else:
                    movimiento = MovimientoInventario.objects.get(id=cur['id_movimiento'])
            else:
                # Ya manejado arriba, pero por seguridad
                movimiento = MovimientoInventario.objects.get(id=cur['id_movimiento'])

            if movimiento.tipo == MovimientoInventario.TipoMovimiento.SALIDA:
                Producto.objects.select_for_update().get(id=cur['id_producto'])
                self._validar_salida(cur['id_producto'], cur['id_inventario'], cur['cantidad'])

            cur['id_producto'] = Producto.objects.get(id=cur['id_producto'])
            cur['id_inventario'] = Inventario.objects.get(id=cur['id_inventario'])
            cur['id_movimiento'] = movimiento
            if 'id_proveedor' in cur and cur['id_proveedor']:
                if not Proveedor.objects.filter(id=cur['id_proveedor']).exists():
                    raise ValueError("El proveedor indicado no existe")
                cur['id_proveedor'] = Proveedor.objects.get(id=cur['id_proveedor'])
            else:
                cur.pop('id_proveedor', None)

            instance = self.repository.create(cur)
            resultados.append(self._to_dict(instance))

        return resultados

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