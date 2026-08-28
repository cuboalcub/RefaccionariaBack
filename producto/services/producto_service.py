from django.db.models import Q

from producto.repositories.producto_repository import ProductoRepository
from producto.models import Producto
from repository.base_service import BaseService
from producto.repositories.tipo_repository import TipoRepository
from producto.repositories.proveedor_repository import ProveedorRepository

class ProductoService(BaseService):
    def __init__(self, producto_repo=None, tipo_repo=None, proveedor_repo=None):
        super().__init__(model=Producto, repository=producto_repo or ProductoRepository())
        self.tipo_repo = tipo_repo or TipoRepository()
        self.proveedor_repo = proveedor_repo or ProveedorRepository()

    def create(self, data):
        data = dict(data)
        tipo = self.tipo_repo.get_by_id(data["id_tipo"])
        proveedor = self.proveedor_repo.get_by_id(data["id_proveedor"])
        data["id_tipo"] = tipo
        data["id_proveedor"] = proveedor
        return super().create(data)

    def update(self, id, data):
        data = dict(data)
        if "id_tipo" in data:
            data["id_tipo"] = self.tipo_repo.get_by_id(data["id_tipo"])
        if "id_proveedor" in data:
            data["id_proveedor"] = self.proveedor_repo.get_by_id(data["id_proveedor"])
        return super().update(id, data)

    def get_all(self, page: int = None, page_size: int = 10, sucursal_id: int = None, search: str = None, clave: str = None, marca: str = None, codigo_barras: str = None, tipo_id: int = None, proveedor_id: int = None):
        """Devuelve productos con paginación opcional. Si sucursal_id se indica, filtra solo productos
        con stock >0 en esa sucursal y enriquece con precio_sucursal (null si no existe)."""
        try:
            # Flujo sucursal: stock + precio_sucursal
            if sucursal_id is not None:
                from inventario.repositories.detalle_inventario_repository import DetalleInventarioRepository
                from inventario.models import PrecioSucursal
                from sucursales.models import Sucursal

                if not Sucursal.objects.filter(id=sucursal_id).exists():
                    raise ValueError(f"Sucursal con id {sucursal_id} no encontrada")

                detalle_repo = DetalleInventarioRepository()
                stock_map = detalle_repo.get_stock_map_por_sucursal(sucursal_id)
                if not stock_map:
                    if page is not None:
                        import math
                        return {"total": 0, "page": page, "page_size": page_size, "total_pages": 0, "results": []}
                    return []

                # Filtra productos base por ids con stock
                qs = Producto.objects.filter(id__in=stock_map.keys()).select_related('id_tipo', 'id_proveedor')
                # Filtros adicionales
                if search:
                    qs = qs.filter(Q(nombre__icontains=search) | Q(clave__icontains=search) | Q(marca__icontains=search) | Q(codigo_barras__icontains=search) | Q(descripcion__icontains=search))
                if clave:
                    qs = qs.filter(clave__icontains=clave)
                if marca:
                    qs = qs.filter(marca__icontains=marca)
                if codigo_barras:
                    qs = qs.filter(codigo_barras__icontains=codigo_barras)
                if tipo_id:
                    qs = qs.filter(id_tipo_id=tipo_id)
                if proveedor_id:
                    qs = qs.filter(id_proveedor_id=proveedor_id)

                qs = qs.order_by('id')
                # Evaluar queryset a lista
                filtered = list(qs)
                # Mantener solo los que siguen con stock >0 tras filtros (ya filtrado por ids)
                # Aplicar paginación
                # Precargar precios activos de la sucursal para los productos filtrados
                precio_map = {
                    ps.id_producto_id: ps for ps in PrecioSucursal.objects.filter(id_sucursal_id=sucursal_id, activo=True, id_producto_id__in=[p.id for p in filtered])
                }
                # Construir dicts enriquecidos
                enriched = []
                for p in filtered:
                    d = self._to_dict(p)
                    ps = precio_map.get(p.id)
                    d['precio_sucursal'] = str(ps.precio_venta) if ps else None
                    d['vigente_desde'] = ps.vigente_desde.isoformat() if ps and ps.vigente_desde else None
                    d['cantidad'] = stock_map.get(p.id, 0)
                    d['id_sucursal'] = sucursal_id
                    # Mantener precio_base como precio_venta original para referencia
                    d['precio_base'] = d['precio_venta']
                    enriched.append(d)

                total = len(enriched)
                if page is not None:
                    start = (page - 1) * page_size
                    end = start + page_size
                    instances = enriched[start:end]
                    import math
                    return {
                        "total": total,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": math.ceil(total / page_size) if total else 0,
                        "results": instances,
                    }
                return enriched

            # Flujo normal sin sucursal (compatibilidad)
            all_instances = self.repository.get_all()
            # Aplicar filtros también en flujo sin sucursal si se envían (search etc)
            if search or clave or marca or codigo_barras or tipo_id or proveedor_id:
                # Reusar queryset para filtrar eficientemente
                qs = Producto.objects.all()
                if search:
                    qs = qs.filter(Q(nombre__icontains=search) | Q(clave__icontains=search) | Q(marca__icontains=search) | Q(codigo_barras__icontains=search) | Q(descripcion__icontains=search))
                if clave:
                    qs = qs.filter(clave__icontains=clave)
                if marca:
                    qs = qs.filter(marca__icontains=marca)
                if codigo_barras:
                    qs = qs.filter(codigo_barras__icontains=codigo_barras)
                if tipo_id:
                    qs = qs.filter(id_tipo_id=tipo_id)
                if proveedor_id:
                    qs = qs.filter(id_proveedor_id=proveedor_id)
                qs = qs.order_by('id').select_related('id_tipo', 'id_proveedor')
                all_instances = list(qs)

            total = len(all_instances)

            if page is not None:
                start = (page - 1) * page_size
                end = start + page_size
                instances = all_instances[start:end]
                import math

                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": math.ceil(total / page_size),
                    "results": [self._to_dict(i) for i in instances],
                }

            return [self._to_dict(i) for i in all_instances]
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error al obtener productos: {str(e)}") from e

    def get_by_codigo_barras(self, codigo_barras):
        producto = self.repository.get_by_codigo_barras(codigo_barras)
        if producto:
            return self._to_dict(producto)
        return None

    def _to_dict(self, instance):
        return {
            "id": instance.id,
            "id_tipo": instance.id_tipo.id if instance.id_tipo else None,
            "id_proveedor": instance.id_proveedor.id if instance.id_proveedor else None,
            "clave": instance.clave,
            "nombre": instance.nombre,
            "descripcion": instance.descripcion,
            "codigo_barras": instance.codigo_barras,
            "precio_venta": str(instance.precio_venta),
            "marca": instance.marca,
            "costo": str(instance.costo)
        }
