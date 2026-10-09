from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from ventas.services.detalleventa_service import DetalleVentaService
from ventas.models import venta
from ventas.repositories.ventas_repository import VentaRepository
from usuario.repositories.usuario_repositorie import UserRepository
from ventas.repositories.metodopago_repository import MetodoPagoRepository
from repository.base_service import BaseService
from repository.exceptions import NotFoundError
from producto.repositories.producto_repository import ProductoRepository
from inventario.models import Inventario

class VentaService(BaseService):
    def __init__(self, venta_repo=None, user_repo=None, metodopago_repo=None, producto_repo=None):
        super().__init__(model=venta, repository=venta_repo or VentaRepository())
        self.user_repo = user_repo or UserRepository()
        self.metodopago_repo = metodopago_repo or MetodoPagoRepository()
        self.producto_repo = producto_repo or ProductoRepository()

    def _to_dict(self, instance):
        id_inventario = instance.id_inventario.id if instance.id_inventario else None
        id_sucursal = None
        try:
            if instance.id_inventario is not None:
                id_sucursal = instance.id_inventario.id_sucursal_id
        except Exception:
            id_sucursal = None
        return {
            "id": instance.id,
            "id_usuario": instance.id_usuario.id if instance.id_usuario else None,
            "id_metodoPago": instance.id_metodoPago.id if instance.id_metodoPago else None,
            "id_inventario": id_inventario,
            "id_sucursal": id_sucursal,
            "total": str(instance.total),
            "fecha": instance.fecha.isoformat() if instance.fecha else None
        }

    def get_all(self, page: int = None, page_size: int = 10, sucursal_id: int = None,
                id_inventario: int = None):
        """Devuelve ventas divididas por sucursal con paginación opcional.

        - Filtra por ``sucursal_id`` vía ``id_inventario__id_sucursal_id``.
        - Filtra por ``id_inventario`` si se indica (más específico).
        - Si ``page`` es None devuelve lista plana (compatibilidad).
        - Si ``page`` se indica devuelve dict {total, page, page_size, total_pages, results}.
        """
        try:
            import math

            if page is not None:
                try:
                    page = int(page)
                    page_size = int(page_size)
                except (TypeError, ValueError):
                    raise ValueError("page y page_size deben ser enteros")
                if page < 1 or page_size < 1:
                    raise ValueError("page y page_size deben ser >= 1")

            if sucursal_id is not None:
                try:
                    sucursal_id = int(sucursal_id)
                except (TypeError, ValueError):
                    raise ValueError("sucursal_id debe ser entero")
                from sucursales.models import Sucursal
                if not Sucursal.objects.filter(id=sucursal_id).exists():
                    raise ValueError(f"Sucursal con id {sucursal_id} no encontrada")

            if id_inventario is not None:
                try:
                    id_inventario = int(id_inventario)
                except (TypeError, ValueError):
                    raise ValueError("id_inventario debe ser entero")

            qs = venta.objects.all().select_related(
                'id_usuario', 'id_metodoPago', 'id_inventario__id_sucursal'
            ).order_by('-fecha', '-id')

            if sucursal_id is not None:
                qs = qs.filter(id_inventario__id_sucursal_id=sucursal_id)
            if id_inventario is not None:
                qs = qs.filter(id_inventario_id=id_inventario)

            if page is None:
                return [self._to_dict(v) for v in qs]

            total = qs.count()
            total_pages = math.ceil(total / page_size) if total else 0
            start = (page - 1) * page_size
            end = start + page_size
            instances = list(qs[start:end])
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "sucursal_id": sucursal_id,
                "results": [self._to_dict(v) for v in instances],
            }
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error al obtener ventas: {str(e)}") from e

    def _resolve_inventario_for_user(self, user):
        """Resuelve el Inventario a partir del Perfil.sucursal del usuario autenticado.
        - 1 sucursal -> 1..N inventarios: toma el primero por id (determinístico).
        - Lanza ValueError si el usuario no tiene sucursal o la sucursal no tiene inventario.
        """
        # Intentar obtener id_sucursal_id sin query extra si perfil está cacheado
        perfil = getattr(user, 'perfil', None)
        user_sucursal_id = None
        if perfil is not None:
            try:
                user_sucursal_id = getattr(perfil, 'id_sucursal_id', None)
            except Exception:
                user_sucursal_id = None
        # Fallback: fetch fresco si no se obtuvo (perfil no cacheado o DoesNotExist)
        if user_sucursal_id is None:
            try:
                from usuario.models import Perfil
                p = Perfil.objects.filter(usuario_id=user.id).first()
                if p:
                    user_sucursal_id = p.id_sucursal_id
            except Exception:
                user_sucursal_id = None
        if user_sucursal_id is None:
            raise ValueError("El usuario no tiene una sucursal asignada. Asigne una sucursal al perfil")
        qs = Inventario.objects.filter(id_sucursal_id=user_sucursal_id).order_by('id')
        inventario = qs.first()
        if not inventario:
            raise ValueError(f"La sucursal {user_sucursal_id} no tiene un inventario asignado")
        return inventario

    def _resolver_cabecera(self, data, user=None):
        """Resuelve (usuario, método de pago, inventario) con las mismas
        reglas que :meth:`create` (JWT vs legacy, staff override)."""
        via_jwt = user is not None and getattr(user, "is_authenticated", False)
        if via_jwt:
            auth_user = user
        elif "id_usuario" in data and data["id_usuario"] is not None:
            auth_user = self.user_repo.get_by_id(data['id_usuario'])
            if not auth_user:
                raise ValueError(f"Usuario con id {data['id_usuario']} no encontrado")
        else:
            if "id_metodoPago" not in data:
                raise ValueError("Faltan campos obligatorios: id_usuario, id_metodoPago")
            raise ValueError("Faltan campos obligatorios: id_usuario (autenticación requerida)")

        if "id_metodoPago" not in data or data["id_metodoPago"] is None:
            raise ValueError("Faltan campos obligatorios: id_metodoPago")

        user = auth_user
        metodoPago = self.metodopago_repo.get_by_id(data['id_metodoPago'])
        if not metodoPago:
            raise ValueError(f"Metodo de pago con id {data['id_metodoPago']} no encontrado")

        is_staff = getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)
        inventario = None
        if via_jwt:
            if is_staff and "id_inventario" in data and data["id_inventario"] is not None:
                inventario = Inventario.objects.filter(id=data['id_inventario']).first()
                if not inventario:
                    raise ValueError(f"Inventario con id {data['id_inventario']} no encontrado")
            else:
                try:
                    inventario = self._resolve_inventario_for_user(user)
                except ValueError as e:
                    if is_staff:
                        raise ValueError(str(e) + " (staff: envíe id_inventario explícito)")
                    raise
        else:
            if "id_inventario" not in data or data["id_inventario"] is None:
                raise ValueError("Faltan campos obligatorios: id_inventario")
            inventario = Inventario.objects.filter(id=data['id_inventario']).first()
            if not inventario:
                raise ValueError(f"Inventario con id {data['id_inventario']} no encontrado")
        return user, metodoPago, inventario

    def create(self, data, user=None):
        user, metodoPago, inventario = self._resolver_cabecera(data, user=user)
        venta_data = {
            "id_usuario": user,
            "id_metodoPago": metodoPago,
            "id_inventario": inventario,
            "total": 0
        }
        venta = super().create(venta_data)

        return venta

    @transaction.atomic
    def crear_venta_completa(self, data, user=None):
        """Crea cabecera + detalles en una sola transacción (todo o nada).

        Acepta ``detalles`` como lista de ``{"producto"|"id_producto", "cantidad"}``.
        Bloquea productos en orden determinista (evita deadlocks), valida
        TODO antes de escribir y devuelve errores por línea. Si cualquier
        detalle falla no queda venta huérfana, ni detalles, ni movimientos.
        """
        from decimal import Decimal as _Decimal
        from inventario.models import DetalleInventario as _DetalleInv
        from inventario.services.detalle_inventario_service import (
            DetalleInventarioService as _InvService,
        )
        from inventario.services.precio_sucursal_service import (
            PrecioSucursalService as _PrecioService,
        )
        from producto.models import Producto as _Producto
        from ventas.models import detalleVenta as _DetalleVenta

        detalles_raw = data.get("detalles", None)
        if not isinstance(detalles_raw, list) or not detalles_raw:
            raise ValueError("Faltan campos obligatorios: detalles (lista no vacía)")

        user_obj, metodoPago, inventario = self._resolver_cabecera(data, user=user)
        inv_service = _InvService()

        # Normalizar líneas: índice + producto + cantidad.
        lineas = []
        errores = []
        for i, d in enumerate(detalles_raw):
            if not isinstance(d, dict):
                errores.append(f"Línea {i}: formato inválido, se esperaba objeto")
                continue
            pid = d.get("id_producto", d.get("producto", None))
            cant = d.get("cantidad", None)
            if pid is None:
                errores.append(f"Línea {i}: falta id_producto/producto")
                continue
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                errores.append(f"Línea {i} (producto {d.get('id_producto', d.get('producto'))}): id inválido")
                continue
            if isinstance(cant, bool) or not isinstance(cant, int):
                errores.append(f"Línea {i} (producto {pid}): cantidad debe ser entero positivo")
                continue
            if cant <= 0:
                errores.append(f"Línea {i} (producto {pid}): cantidad debe ser mayor a cero")
                continue
            lineas.append({"indice": i, "producto_id": pid, "cantidad": cant})
        if errores:
            raise ValueError("Errores en detalles: " + "; ".join(errores))

        # Bloqueo determinista: ordena IDs para evitar deadlocks entre
        # transacciones concurrentes.
        ids_ordenados = sorted({ln["producto_id"] for ln in lineas})
        productos_qs = list(
            _Producto.objects.select_for_update().filter(id__in=ids_ordenados)
        )
        productos = {p.id: p for p in productos_qs}
        # Serializar también las filas de stock del inventario para que dos
        # ventas concurrentes no lean el mismo stock a la vez.
        list(
            _DetalleInv.objects.select_for_update().filter(
                id_producto_id__in=ids_ordenados,
                id_inventario_id=inventario.id,
            )
        )
        for ln in lineas:
            if ln["producto_id"] not in productos:
                errores.append(
                    f"Línea {ln['indice']} (producto {ln['producto_id']}): no existe"
                )
        if errores:
            raise ValueError("Errores en detalles: " + "; ".join(errores))

        # Validación de sucursal/stock. Acumula cantidades por producto para
        # detectar el caso de producto repetido que excede el stock en total.
        stocks = {}
        for pid in ids_ordenados:
            stocks[pid] = inv_service.get_stock(pid, inventario.id)
        acumulado = {}
        for ln in lineas:
            acumulado[ln["producto_id"]] = acumulado.get(ln["producto_id"], 0) + ln["cantidad"]
        sucursal_id = getattr(inventario, "id_sucursal_id", None)
        for ln in lineas:
            pid = ln["producto_id"]
            if stocks.get(pid, 0) == 0:
                nombre = productos[pid].nombre
                errores.append(
                    f"Línea {ln['indice']} (producto {pid} '{nombre}'): "
                    f"no disponible en inventario {inventario.id} - stock 0"
                )
        for pid, total_pid in acumulado.items():
            if total_pid > stocks.get(pid, 0):
                indices = [str(ln["indice"]) for ln in lineas if ln["producto_id"] == pid]
                errores.append(
                    f"Producto {pid} (líneas {', '.join(indices)}): "
                    f"stock insuficiente: disponible {stocks.get(pid, 0)}, "
                    f"solicitado {total_pid}"
                )
        # Nota sucursal: el inventario ya viene derivado del perfil del
        # usuario (no-staff) o del override explícito de staff en
        # _resolver_cabecera, y el stock se mide en ese inventario, por lo
        # que un cross-sucursal es imposible en este camino. No se duplica
        # el chequeo del flujo por detalle.
        if errores:
            raise ValueError("Errores en detalles: " + "; ".join(errores))

        # Escritura: una venta + N detalles + N SALIDA, total en un save.
        venta_obj = venta.objects.create(
            id_usuario=user_obj,
            id_metodoPago=metodoPago,
            id_inventario=inventario,
            total=_Decimal("0"),
        )
        total = _Decimal("0")
        detalles_out = []
        for ln in lineas:
            producto = productos[ln["producto_id"]]
            precio = _PrecioService.resolver_precio_venta(producto, sucursal_id)
            subtotal = (_Decimal(precio) * ln["cantidad"]).quantize(_Decimal("0.01"))
            det = _DetalleVenta.objects.create(
                id_venta=venta_obj,
                id_producto=producto,
                cantidad=ln["cantidad"],
                subtotal=subtotal,
            )
            inv_service.crear_salida_por_venta(
                det, producto, inventario, ln["cantidad"]
            )
            total += subtotal
            detalles_out.append(
                {
                    "id": det.id,
                    "id_producto": producto.id,
                    "cantidad": ln["cantidad"],
                    "subtotal": str(subtotal),
                }
            )
        venta_obj.total = total.quantize(_Decimal("0.01"))
        venta_obj.save(update_fields=["total"])
        resultado = self._to_dict(venta_obj)
        resultado["detalles"] = detalles_out
        return resultado

    def update(self, entity_id: int, data, user=None):
        """Actualiza una venta. Solo ``id_metodoPago`` es mutable: ``total``
        se recalcula desde los detalles y ``id_inventario``/``id_usuario``/
        ``fecha`` se ignoran para evitar manipulación (antes un PUT podía
        fijar cualquier total).
        """
        data = dict(data)
        for campo in ("total", "id_inventario", "id_usuario", "fecha"):
            data.pop(campo, None)
        if "id_metodoPago" in data and data["id_metodoPago"] is not None:
            mp_val = data["id_metodoPago"]
            try:
                mp = self.metodopago_repo.get_by_id(
                    mp_val.id if hasattr(mp_val, "id") else mp_val
                )
            except Exception:
                mp = None
            if not mp:
                raise ValueError(f"Metodo de pago con id {mp_val} no encontrado")
            data["id_metodoPago"] = mp
        return super().update(entity_id, data)

    def delete(self, entity_id: int, user=None):
        """Elimina una venta revirtiendo sus efectos sobre el inventario.

        Sin este override, ``BaseService.delete`` borraba la venta y por
        CASCADE sus detalles, pero los ``DetalleInventario``/``Movimiento``
        SALIDA quedaban huérfanos (``id_detalle_venta`` es SET_NULL) y el
        stock nunca se restauraba. Todo se ejecuta en un único
        ``transaction.atomic`` con bloqueo de la venta.
        """
        from ventas.models import detalleVenta
        from inventario.services.detalle_inventario_service import (
            DetalleInventarioService,
        )

        with transaction.atomic():
            try:
                instance = venta.objects.select_for_update().get(id=entity_id)
            except (venta.DoesNotExist, ObjectDoesNotExist):
                raise NotFoundError(
                    f"venta con id {entity_id} no encontrado"
                )
            detalles = list(
                detalleVenta.objects.select_for_update().filter(
                    id_venta_id=entity_id
                )
            )
            inventario_service = DetalleInventarioService()
            for detalle in detalles:
                inventario_service.revertir_salida_por_venta(detalle)
            instance.delete()
            return {"message": "venta eliminado exitosamente"}
