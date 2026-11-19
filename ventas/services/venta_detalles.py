ERRORES_EN_DETALLES_PREFIJO = "Errores en detalles: "


def validar_linea_detalle(indice, detalle):
    if not isinstance(detalle, dict):
        return f"Línea {indice}: formato inválido, se esperaba objeto", None, None
    pid = detalle.get("id_producto", detalle.get("producto", None))
    cant = detalle.get("cantidad", None)
    if pid is None:
        return f"Línea {indice}: falta id_producto/producto", None, None
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return f"Línea {indice} (producto {detalle.get('id_producto', detalle.get('producto'))}): id inválido", None, None
    if isinstance(cant, bool) or not isinstance(cant, int):
        return f"Línea {indice} (producto {pid}): cantidad debe ser entero positivo", None, None
    if cant <= 0:
        return f"Línea {indice} (producto {pid}): cantidad debe ser mayor a cero", None, None
    return None, pid, cant


def normalizar_detalles(detalles_raw):
    """Normaliza líneas a {indice, producto_id, cantidad} y acumula errores."""
    lineas = []
    errores = []
    for i, d in enumerate(detalles_raw):
        error, pid, cant = validar_linea_detalle(i, d)
        if error:
            errores.append(error)
            continue
        lineas.append({"indice": i, "producto_id": pid, "cantidad": cant})
    return lineas, errores
