CAMPOS_BULK = (
    "id_sucursal",
    "id_proveedor",
    "tipo_movimiento",
    "tipo",
    "razon",
    "razón",
    "observaciones",
    "id_movimiento",  # se propaga para que create() lo rechace como deprecado
)


class MovimientoBulkService:
    """Crea N movimientos a partir de los formatos bulk soportados.

    Recibe ``crear_movimiento`` (normalmente ``MovimientoInventarioService.create``)
    para reutilizar toda la validación de un movimiento individual.
    """

    def __init__(self, crear_movimiento):
        self.crear_movimiento = crear_movimiento

    def bulk_create(self, data, user=None):
        """Crea múltiples movimientos (1 por línea).
        Formatos soportados:
        1) {"id_sucursal":1,"id_proveedor":1,"items":[{"id_producto":1,"cantidad":5},...]}
        2) {"id_sucursal":1,"detalles":[...]}  (alias)
        3) [{"id_producto":1,"id_sucursal":1,"cantidad":5}, ...] (lista plana)
        """
        if isinstance(data, dict) and not (
            isinstance(data.get("items"), list) or isinstance(data.get("detalles"), list)
        ):
            return [self.crear_movimiento(data, user=user)]

        items, comun = self._normalizar(data)
        if items is None:
            raise ValueError(
                "Formato bulk inválido. Use {'id_sucursal':1,'items':[...]} o lista de objetos"
            )
        if not items:
            raise ValueError("La lista de items no puede estar vacía")

        resultados = []
        for idx, item in enumerate(items):
            resultados.append(self._procesar_item(idx, item, comun, user))
        return resultados

    @staticmethod
    def _normalizar(data):
        if isinstance(data, list):
            return data, {}
        if isinstance(data, dict):
            for key in ("items", "detalles"):
                if isinstance(data.get(key), list):
                    return data[key], {
                        k: data[k] for k in CAMPOS_BULK if k in data
                    }
        return None, None

    def _procesar_item(self, idx, item, comun, user):
        if not isinstance(item, dict):
            raise ValueError(f"Item {idx} debe ser un objeto")
        cur = dict(item)
        for k in CAMPOS_BULK:
            if cur.get(k) is None and comun.get(k) is not None:
                cur[k] = comun[k]
        return self.crear_movimiento(cur, user=user)
