#!/usr/bin/env python3
"""Genera la colección Bruno para la Refaccionaria API a partir del backend Django."""

import json
import os
import pathlib
import shutil

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "bruno" / "RefaccionariaAPI"

COLLECTION_NAME = "Refaccionaria API"
BASE_URL_VAR = "base_url"
TOKEN_VAR = "token"

FRAMEWORK_ROUTES = [
    # ---- Auth ----
    {
        "folder": "Auth",
        "name": "Login",
        "method": "POST",
        "path": "/api/login",
        "auth": False,
        "query": [],
        "body": {
            "username": "admin",
            "password": "password123",
        },
        "docs": "Autentica al usuario y devuelve tokens refresh/access. Guarda el access token en {{token}} automáticamente.",
        "post_response": 'if (res.body.access) {\n  bru.setEnvVar("token", res.body.access);\n}',
    },
    {
        "folder": "Auth",
        "name": "Refresh Token",
        "method": "POST",
        "path": "/api/token/refresh",
        "auth": False,
        "query": [],
        "body": {
            "refresh": "{{token}}",
        },
        "docs": "Renueva el access token usando el refresh token.",
    },
    {
        "folder": "Auth",
        "name": "Registrar Usuario",
        "method": "POST",
        "path": "/api/users",
        "auth": False,
        "query": [],
        "body": {
            "username": "nuevo_usuario",
            "email": "usuario@correo.com",
            "first_name": "Nombre",
            "last_name": "Apellido",
            "password": "clave_segura",
        },
        "docs": "Registra un nuevo usuario (público, no requiere token).",
    },
    # ---- Usuarios ----
    {
        "folder": "Usuarios",
        "name": "Listar Usuarios",
        "method": "GET",
        "path": "/api/users",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve la lista de usuarios registrados. Requiere token.",
    },
    {
        "folder": "Usuarios",
        "name": "Crear Usuario",
        "method": "POST",
        "path": "/api/users",
        "auth": False,
        "query": [],
        "body": {
            "username": "nuevo_usuario",
            "email": "usuario@correo.com",
            "first_name": "Nombre",
            "last_name": "Apellido",
            "password": "clave_segura",
        },
        "docs": "Registra un nuevo usuario (público, no requiere token).",
    },
    {
        "folder": "Usuarios",
        "name": "Obtener Usuario",
        "method": "GET",
        "path": "/api/users/{{userId}}",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve los datos de un usuario por su id.",
    },
    {
        "folder": "Usuarios",
        "name": "Actualizar Usuario",
        "method": "PUT",
        "path": "/api/users/{{userId}}",
        "auth": True,
        "query": [],
        "body": {
            "username": "usuario_actualizado",
            "email": "actualizado@correo.com",
            "first_name": "Nombre",
            "last_name": "Apellido",
            "is_active": True,
            "password": "nueva_clave",
        },
        "docs": "Actualiza username, email, first_name, last_name, is_active y password (el password se hashea).",
    },
    {
        "folder": "Usuarios",
        "name": "Eliminar Usuario",
        "method": "DELETE",
        "path": "/api/users/{{userId}}",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Elimina un usuario. Solo disponible para usuarios staff.",
    },
    # ---- Productos ----
    {
        "folder": "Productos",
        "name": "Listar Productos",
        "method": "GET",
        "path": "/api/productos/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve todos los productos.",
    },
    {
        "folder": "Productos",
        "name": "Listar Productos Paginado",
        "method": "GET",
        "path": "/api/productos/",
        "auth": True,
        "query": [("page", "1"), ("page_size", "10")],
        "body": None,
        "docs": "Devuelve productos paginados con los parámetros page y page_size.",
    },
    {
        "folder": "Productos",
        "name": "Producto por Código de Barras",
        "method": "GET",
        "path": "/api/productos/codigo-barras/",
        "auth": True,
        "query": [("codigo_barras", "7501234567890")],
        "body": None,
        "docs": "Busca un producto por su código de barras. Devuelve 404 si no existe.",
    },
    {
        "folder": "Productos",
        "name": "Crear Producto",
        "method": "POST",
        "path": "/api/productos/",
        "auth": True,
        "query": [],
        "body": {
            "id_tipo": 1,
            "id_proveedor": 1,
            "clave": "PZA-001",
            "nombre": "Pastillas de Freno",
            "descripcion": "Pastillas de freno cerámicas",
            "codigo_barras": "7501234567890",
            "precio_venta": 599.99,
            "marca": "Bosch",
            "existencia": 50,
            "costo": 350.00,
            "codigoSAT": "84111500",
        },
        "docs": "Crea un producto. NO incluye id_movimientos; el inventario se gestiona con movimientos.",
    },
    {
        "folder": "Productos",
        "name": "Obtener Producto",
        "method": "GET",
        "path": "/api/productos/{{productoId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve un producto por su id.",
    },
    {
        "folder": "Productos",
        "name": "Actualizar Producto",
        "method": "PUT",
        "path": "/api/productos/{{productoId}}/",
        "auth": True,
        "query": [],
        "body": {
            "id_tipo": 1,
            "id_proveedor": 1,
            "clave": "PZA-001",
            "nombre": "Pastillas de Freno Actualizado",
            "descripcion": "Pastillas de freno cerámicas premium",
            "codigo_barras": "7501234567890",
            "precio_venta": 699.99,
            "marca": "Bosch",
            "existencia": 45,
            "costo": 350.00,
            "codigoSAT": "84111500",
        },
        "docs": "Actualiza los datos de un producto.",
    },
    {
        "folder": "Productos",
        "name": "Eliminar Producto",
        "method": "DELETE",
        "path": "/api/productos/{{productoId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Elimina un producto por su id.",
    },
    # ---- Tipos ----
    {
        "folder": "Tipos",
        "name": "Listar Tipos",
        "method": "GET",
        "path": "/api/tipos/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve todos los tipos de producto.",
    },
    {
        "folder": "Tipos",
        "name": "Crear Tipo",
        "method": "POST",
        "path": "/api/tipos/",
        "auth": True,
        "query": [],
        "body": {
            "nombre": "Frenos",
        },
        "docs": "Crea un tipo de producto.",
    },
    {
        "folder": "Tipos",
        "name": "Obtener Tipo",
        "method": "GET",
        "path": "/api/tipos/{{tipoId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve un tipo por su id.",
    },
    {
        "folder": "Tipos",
        "name": "Actualizar Tipo",
        "method": "PUT",
        "path": "/api/tipos/{{tipoId}}/",
        "auth": True,
        "query": [],
        "body": {
            "nombre": "Frenos y Embrague",
        },
        "docs": "Actualiza el nombre de un tipo.",
    },
    {
        "folder": "Tipos",
        "name": "Eliminar Tipo",
        "method": "DELETE",
        "path": "/api/tipos/{{tipoId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Elimina un tipo por su id.",
    },
    # ---- Proveedores ----
    {
        "folder": "Proveedores",
        "name": "Listar Proveedores",
        "method": "GET",
        "path": "/api/proveedores/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve todos los proveedores.",
    },
    {
        "folder": "Proveedores",
        "name": "Crear Proveedor",
        "method": "POST",
        "path": "/api/proveedores/",
        "auth": True,
        "query": [],
        "body": {
            "nombre": "Bosch México",
            "telefono": "5555555555",
            "correo": "ventas@bosch.mx",
            "direccion": "Av. Industria 123, CDMX",
        },
        "docs": "Crea un proveedor.",
    },
    {
        "folder": "Proveedores",
        "name": "Obtener Proveedor",
        "method": "GET",
        "path": "/api/proveedores/{{proveedorId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve un proveedor por su id.",
    },
    {
        "folder": "Proveedores",
        "name": "Actualizar Proveedor",
        "method": "PUT",
        "path": "/api/proveedores/{{proveedorId}}/",
        "auth": True,
        "query": [],
        "body": {
            "nombre": "Bosch México",
            "telefono": "5555555555",
            "correo": "contacto@bosch.mx",
            "direccion": "Av. Industria 123, CDMX",
        },
        "docs": "Actualiza los datos de un proveedor.",
    },
    {
        "folder": "Proveedores",
        "name": "Eliminar Proveedor",
        "method": "DELETE",
        "path": "/api/proveedores/{{proveedorId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Elimina un proveedor por su id.",
    },
    # ---- Sucursales ----
    {
        "folder": "Sucursales",
        "name": "Listar Sucursales",
        "method": "GET",
        "path": "/api/sucursales/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve todas las sucursales.",
    },
    {
        "folder": "Sucursales",
        "name": "Crear Sucursal",
        "method": "POST",
        "path": "/api/sucursales/",
        "auth": True,
        "query": [],
        "body": {
            "ubicacion": "Centro, Ciudad de México",
        },
        "docs": "Crea una sucursal.",
    },
    {
        "folder": "Sucursales",
        "name": "Obtener Sucursal",
        "method": "GET",
        "path": "/api/sucursales/{{sucursalId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve una sucursal por su id.",
    },
    {
        "folder": "Sucursales",
        "name": "Actualizar Sucursal",
        "method": "PUT",
        "path": "/api/sucursales/{{sucursalId}}/",
        "auth": True,
        "query": [],
        "body": {
            "ubicacion": "Norte, Monterrey",
        },
        "docs": "Actualiza la ubicación de una sucursal.",
    },
    {
        "folder": "Sucursales",
        "name": "Eliminar Sucursal",
        "method": "DELETE",
        "path": "/api/sucursales/{{sucursalId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Elimina una sucursal por su id.",
    },
    # ---- Inventario ----
    {
        "folder": "Inventario",
        "name": "Listar Inventarios",
        "method": "GET",
        "path": "/api/inventarios/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve todos los inventarios.",
    },
    {
        "folder": "Inventario",
        "name": "Crear Inventario",
        "method": "POST",
        "path": "/api/inventarios/",
        "auth": True,
        "query": [],
        "body": {
            "id_sucursal": 1,
            "descripcion": "Inventario general",
        },
        "docs": "Crea un inventario asociado a una sucursal.",
    },
    {
        "folder": "Inventario",
        "name": "Obtener Inventario",
        "method": "GET",
        "path": "/api/inventarios/{{inventarioId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve un inventario por su id.",
    },
    {
        "folder": "Inventario",
        "name": "Actualizar Inventario",
        "method": "PUT",
        "path": "/api/inventarios/{{inventarioId}}/",
        "auth": True,
        "query": [],
        "body": {
            "id_sucursal": 1,
            "descripcion": "Inventario actualizado",
        },
        "docs": "Actualiza un inventario.",
    },
    {
        "folder": "Inventario",
        "name": "Eliminar Inventario",
        "method": "DELETE",
        "path": "/api/inventarios/{{inventarioId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Elimina un inventario por su id.",
    },
    # ---- Movimientos de Inventario ----
    {
        "folder": "MovimientosInventario",
        "name": "Listar Movimientos de Inventario",
        "method": "GET",
        "path": "/api/movimientos-inventario/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve todos los movimientos de inventario.",
    },
    {
        "folder": "MovimientosInventario",
        "name": "Crear Movimiento de Inventario",
        "method": "POST",
        "path": "/api/movimientos-inventario/",
        "auth": True,
        "query": [],
        "body": {
            "tipo": "ENTRADA",
            "cantidad": 100,
            "razon": "Compra a proveedor",
            "observaciones": "Factura 1234",
        },
        "docs": "Crea un movimiento de inventario. tipo = ENTRADA o SALIDA. El stock se ajusta al crear el detalle.",
    },
    {
        "folder": "MovimientosInventario",
        "name": "Obtener Movimiento de Inventario",
        "method": "GET",
        "path": "/api/movimientos-inventario/{{movimientoInvId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve un movimiento de inventario por su id.",
    },
    {
        "folder": "MovimientosInventario",
        "name": "Actualizar Movimiento de Inventario",
        "method": "PUT",
        "path": "/api/movimientos-inventario/{{movimientoInvId}}/",
        "auth": True,
        "query": [],
        "body": {
            "tipo": "SALIDA",
            "cantidad": 5,
            "razon": "Ajuste de inventario",
            "observaciones": "",
        },
        "docs": "Actualiza un movimiento de inventario.",
    },
    {
        "folder": "MovimientosInventario",
        "name": "Eliminar Movimiento de Inventario",
        "method": "DELETE",
        "path": "/api/movimientos-inventario/{{movimientoInvId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Elimina un movimiento de inventario por su id.",
    },
    # ---- Detalles de Inventario ----
    {
        "folder": "DetallesInventario",
        "name": "Listar Detalles de Inventario",
        "method": "GET",
        "path": "/api/detalles-inventario/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve todos los detalles de inventario.",
    },
    {
        "folder": "DetallesInventario",
        "name": "Crear Detalle de Inventario",
        "method": "POST",
        "path": "/api/detalles-inventario/",
        "auth": True,
        "query": [],
        "body": {
            "id_producto": 1,
            "id_inventario": 1,
            "id_proveedor": 1,
            "id_movimiento": 1,
            "cantidad": 10,
        },
        "docs": "Crea un detalle de inventario y ajusta el stock del producto según el tipo de movimiento.",
    },
    {
        "folder": "DetallesInventario",
        "name": "Obtener Detalle de Inventario",
        "method": "GET",
        "path": "/api/detalles-inventario/{{detalleInvId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve un detalle de inventario por su id.",
    },
    {
        "folder": "DetallesInventario",
        "name": "Actualizar Detalle de Inventario",
        "method": "PUT",
        "path": "/api/detalles-inventario/{{detalleInvId}}/",
        "auth": True,
        "query": [],
        "body": {
            "id_producto": 1,
            "id_inventario": 1,
            "id_proveedor": 1,
            "id_movimiento": 1,
            "cantidad": 15,
        },
        "docs": "Actualiza un detalle de inventario y reajusta el stock del producto.",
    },
    {
        "folder": "DetallesInventario",
        "name": "Eliminar Detalle de Inventario",
        "method": "DELETE",
        "path": "/api/detalles-inventario/{{detalleInvId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Elimina un detalle de inventario y restituye el stock del producto.",
    },
    # ---- Perfil ----
    {
        "folder": "Perfil",
        "name": "Obtener Perfil",
        "method": "GET",
        "path": "/api/perfil/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve el perfil (con sucursal) del usuario autenticado. Lo crea si no existe.",
    },
    {
        "folder": "Perfil",
        "name": "Actualizar Perfil",
        "method": "PUT",
        "path": "/api/perfil/",
        "auth": True,
        "query": [],
        "body": {
            "id_sucursal": 1,
        },
        "docs": "Asigna la sucursal al perfil del usuario autenticado.",
    },
    # ---- MetodoPago ----
    {
        "folder": "MetodoPago",
        "name": "Listar Metodos de Pago",
        "method": "GET",
        "path": "/api/metodopago/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve todos los métodos de pago.",
    },
    {
        "folder": "MetodoPago",
        "name": "Crear Metodo de Pago",
        "method": "POST",
        "path": "/api/metodopago/",
        "auth": True,
        "query": [],
        "body": {
            "tipo": "Tarjeta",
            "descripcion": "Pago con tarjeta de crédito o débito",
        },
        "docs": "Crea un método de pago.",
    },
    {
        "folder": "MetodoPago",
        "name": "Obtener Metodo de Pago",
        "method": "GET",
        "path": "/api/metodopago/{{metodoPagoId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve un método de pago por su id.",
    },
    {
        "folder": "MetodoPago",
        "name": "Actualizar Metodo de Pago",
        "method": "PUT",
        "path": "/api/metodopago/{{metodoPagoId}}/",
        "auth": True,
        "query": [],
        "body": {
            "tipo": "Transferencia",
            "descripcion": "Pago por transferencia bancaria",
        },
        "docs": "Actualiza un método de pago.",
    },
    {
        "folder": "MetodoPago",
        "name": "Eliminar Metodo de Pago",
        "method": "DELETE",
        "path": "/api/metodopago/{{metodoPagoId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Elimina un método de pago por su id.",
    },
    # ---- Ventas ----
    {
        "folder": "Ventas",
        "name": "Listar Ventas",
        "method": "GET",
        "path": "/api/ventas/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve todas las ventas.",
    },
    {
        "folder": "Ventas",
        "name": "Crear Venta",
        "method": "POST",
        "path": "/api/ventas/",
        "auth": True,
        "query": [],
        "body": {
            "id_usuario": 1,
            "id_metodoPago": 1,
        },
        "docs": "Crea una venta con total 0. El total se calcula sumando los subtotales de sus detalles.",
    },
    {
        "folder": "Ventas",
        "name": "Obtener Venta",
        "method": "GET",
        "path": "/api/ventas/{{ventaId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve una venta por su id.",
    },
    {
        "folder": "Ventas",
        "name": "Actualizar Venta",
        "method": "PUT",
        "path": "/api/ventas/{{ventaId}}/",
        "auth": True,
        "query": [],
        "body": {
            "id_usuario": 1,
            "id_metodoPago": 2,
        },
        "docs": "Actualiza usuario y método de pago de una venta. El total se recalcula desde los detalles.",
    },
    {
        "folder": "Ventas",
        "name": "Eliminar Venta",
        "method": "DELETE",
        "path": "/api/ventas/{{ventaId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Elimina una venta por su id.",
    },
    # ---- DetalleVenta ----
    {
        "folder": "DetalleVenta",
        "name": "Listar Detalles",
        "method": "GET",
        "path": "/api/detalle/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve todos los detalles de venta.",
    },
    {
        "folder": "DetalleVenta",
        "name": "Crear Detalle",
        "method": "POST",
        "path": "/api/detalle/",
        "auth": True,
        "query": [],
        "body": {
            "id_producto": 1,
            "id_venta": 1,
            "cantidad": 1,
            "subtotal": 599.99,
        },
        "docs": "Crea un detalle de venta, descuenta stock del producto y recalcula el total de la venta.",
    },
    {
        "folder": "DetalleVenta",
        "name": "Obtener Detalle",
        "method": "GET",
        "path": "/api/detalle/{{detalleId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Devuelve un detalle de venta por su id.",
    },
    {
        "folder": "DetalleVenta",
        "name": "Actualizar Detalle",
        "method": "PUT",
        "path": "/api/detalle/{{detalleId}}/",
        "auth": True,
        "query": [],
        "body": {
            "id_producto": 1,
            "id_venta": 1,
            "cantidad": 3,
            "subtotal": 1799.97,
        },
        "docs": "Actualiza un detalle, ajusta el stock del producto y recalcula el total de la venta.",
    },
    {
        "folder": "DetalleVenta",
        "name": "Eliminar Detalle",
        "method": "DELETE",
        "path": "/api/detalle/{{detalleId}}/",
        "auth": True,
        "query": [],
        "body": None,
        "docs": "Elimina un detalle, restituye el stock del producto y recalcula el total de la venta.",
    },
    # ---- Reportes ----
    {
        "folder": "Reportes",
        "name": "Generar Reporte Diario",
        "method": "GET",
        "path": "/api/reporte/",
        "auth": True,
        "query": [("tipo", "day")],
        "body": None,
        "docs": "Genera el reporte diario de ventas en PDF.",
    },
    {
        "folder": "Reportes",
        "name": "Generar Reporte Semanal",
        "method": "GET",
        "path": "/api/reporte/",
        "auth": True,
        "query": [("tipo", "week")],
        "body": None,
        "docs": "Genera el reporte semanal de ventas en PDF.",
    },
    {
        "folder": "Reportes",
        "name": "Generar Reporte Quincenal",
        "method": "GET",
        "path": "/api/reporte/",
        "auth": True,
        "query": [("tipo", "quincena")],
        "body": None,
        "docs": "Genera el reporte quincenal de ventas en PDF.",
    },
    {
        "folder": "Reportes",
        "name": "Generar Reporte Mensual",
        "method": "GET",
        "path": "/api/reporte/",
        "auth": True,
        "query": [("tipo", "month"), ("year", "2026"), ("month", "8")],
        "body": None,
        "docs": "Genera el reporte mensual de ventas en PDF. Parámetros: tipo, year, month.",
    },
    {
        "folder": "Reportes",
        "name": "Generar Reporte Anual",
        "method": "GET",
        "path": "/api/reporte/",
        "auth": True,
        "query": [("tipo", "year"), ("year", "2026")],
        "body": None,
        "docs": "Genera el reporte anual de ventas en PDF. Parámetros: tipo, year.",
    },
]


def clean_dir(path: pathlib.Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_manifest(output_dir: pathlib.Path) -> None:
    manifest = {
        "version": "1",
        "name": COLLECTION_NAME,
        "type": "collection",
        "ignore": ["node_modules", ".git"],
    }
    with open(output_dir / "bruno.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def write_environments(envs_dir: pathlib.Path) -> None:
    clean_dir(envs_dir)
    envs = [
        {
            "name": "Local",
            "base_url": "http://localhost:8000",
        },
        {
            "name": "Produccion",
            "base_url": "https://refaccionariaback.onrender.com",
        },
    ]
    for env in envs:
        content = (
            f"meta {{\n"
            f"  name: {env['name']}\n"
            f"  type: env\n"
            f"}}\n"
            f"vars {{\n"
            f"  base_url: {env['base_url']}\n"
            f"  token:\n"
            f"}}\n"
            f"\n"
            f"vars:secret [\n"
            f"  token\n"
            f"]\n"
        )
        with open(envs_dir / f'{env["name"]}.bru', "w", encoding="utf-8") as f:
            f.write(content)


def generate_bru(route: dict, seq: int) -> str:
    method = route["method"].lower()
    url = f"{{{{{BASE_URL_VAR}}}}}{route['path']}"
    body_mode = "json" if route["body"] is not None else "none"
    auth = f"bearer" if route["auth"] else "none"

    lines = []
    lines.append("meta {")
    lines.append(f"  name: {route['name']}")
    lines.append("  type: http")
    lines.append(f"  seq: {seq}")
    lines.append("}")
    lines.append("")

    lines.append(f"{method} {{")
    lines.append(f"  url: {url}")
    lines.append(f"  body: {body_mode}")
    lines.append(f"  auth: {auth}")
    lines.append("}")
    lines.append("")

    if route["auth"]:
        lines.append("auth:bearer {")
        lines.append("  token: {{" + TOKEN_VAR + "}}")
        lines.append("}")
        lines.append("")

    if route["query"]:
        lines.append("query {")
        for key, value in route["query"]:
            lines.append(f"  {key}: {value}")
        lines.append("}")
        lines.append("")

    lines.append("headers {")
    lines.append("  Accept: application/json")
    if method in ("post", "put", "patch"):
        lines.append("  Content-Type: application/json")
    lines.append("}")
    lines.append("")

    if route["body"] is not None:
        lines.append("body:json {")
        lines.append(json.dumps(route["body"], indent=2, ensure_ascii=False))
        lines.append("}")
        lines.append("")

    if route.get("post_response"):
        lines.append("script:post-response {")
        lines.append(route["post_response"])
        lines.append("}")
        lines.append("")

    if route.get("docs"):
        lines.append("docs {")
        lines.append(f"  {route['docs']}")
        lines.append("}")

    return "\n".join(lines) + "\n"


def sanitize_filename(name: str) -> str:
    return name.replace(" ", " ").strip()


def main(output_dir: pathlib.Path) -> None:
    clean_dir(output_dir)
    write_manifest(output_dir)
    write_environments(output_dir / "environments")

    folders: dict[str, list] = {}
    for route in FRAMEWORK_ROUTES:
        folders.setdefault(route["folder"], []).append(route)

    for folder, routes in folders.items():
        folder_dir = output_dir / folder
        folder_dir.mkdir(parents=True, exist_ok=True)

        with open(folder_dir / "folder.bru", "w", encoding="utf-8") as f:
            f.write(f"meta {{\n  name: {folder}\n}}\n")

        for seq, route in enumerate(routes, start=1):
            filename = sanitize_filename(route["name"]) + ".bru"
            with open(folder_dir / filename, "w", encoding="utf-8") as f:
                f.write(generate_bru(route, seq))

    total = sum(len(r) for r in folders.values())
    print(f"Colección '{COLLECTION_NAME}' generada en {output_dir}")
    print(f"{len(folders)} carpetas, {total} peticiones")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Genera la colección Bruno de la API")
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directorio de salida de la colección",
    )
    args = parser.parse_args()
    main(args.output)
