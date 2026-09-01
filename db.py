"""
db.py
-----
Capa de datos con soporte de estado de cobro/pago y cálculo fiscal trimestral.
"""

import os
import sqlite3
import hashlib
from contextlib import contextmanager
from datetime import datetime

from almacenamiento import get_ruta_datos

DB_NAME = os.path.join(get_ruta_datos(), "contabilidad.db")


@contextmanager
def _conexion():
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def inicializar_bd():
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT,
                concepto TEXT,
                base REAL DEFAULT 0.0,
                tipo_iva REAL DEFAULT 21.0,
                cuota_iva REAL DEFAULT 0.0,
                tipo_irpf REAL DEFAULT 0.0,
                cuota_irpf REAL DEFAULT 0.0,
                cuota_recargo REAL DEFAULT 0.0,
                importe REAL,
                fecha_hora TEXT,
                num_factura TEXT,
                cliente_info TEXT,
                hash_anterior TEXT,
                hash_actual TEXT,
                estado TEXT DEFAULT 'PENDIENTE'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                cif TEXT,
                direccion TEXT,
                es_proveedor INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventario (
                sku TEXT PRIMARY KEY,
                descripcion TEXT,
                categoria TEXT,
                stock_actual INTEGER,
                nivel_minimo INTEGER,
                costo_unitario REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contadores (
                serie TEXT,
                anio INTEGER,
                ultimo INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (serie, anio)
            )
        """)

        try:
            cursor.execute("ALTER TABLE movimientos ADD COLUMN estado TEXT DEFAULT 'PENDIENTE'")
        except sqlite3.OperationalError:
            pass


def guardar_contacto_db(nombre, cif, direccion, es_proveedor=0):
    try:
        with _conexion() as conn:
            conn.execute(
                "INSERT INTO clientes (nombre, cif, direccion, es_proveedor) VALUES (?, ?, ?, ?)",
                (nombre, cif, direccion, es_proveedor)
            )
        return True
    except sqlite3.IntegrityError:
        return False


def obtener_contactos_db(es_proveedor=None):
    with _conexion() as conn:
        cursor = conn.cursor()
        if es_proveedor is None:
            cursor.execute("SELECT id, nombre, cif, direccion, es_proveedor FROM clientes ORDER BY nombre ASC")
        else:
            cursor.execute(
                "SELECT id, nombre, cif, direccion, es_proveedor FROM clientes WHERE es_proveedor = ? ORDER BY nombre ASC",
                (es_proveedor,)
            )
        return cursor.fetchall()


def eliminar_contacto_db(id_contacto):
    with _conexion() as conn:
        conn.execute("DELETE FROM clientes WHERE id = ?", (id_contacto,))


def obtener_inventario_db():
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sku, descripcion, categoria, stock_actual, nivel_minimo, costo_unitario FROM inventario ORDER BY sku ASC"
        )
        return cursor.fetchall()


def guardar_producto_inventario_db(sku, descripcion, categoria, stock, minimo, costo):
    try:
        with _conexion() as conn:
            conn.execute("""
                INSERT INTO inventario (sku, descripcion, categoria, stock_actual, nivel_minimo, costo_unitario)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(sku) DO UPDATE SET
                    descripcion=excluded.descripcion,
                    categoria=excluded.categoria,
                    stock_actual=excluded.stock_actual,
                    nivel_minimo=excluded.nivel_minimo,
                    costo_unitario=excluded.costo_unitario
            """, (sku, descripcion, categoria, stock, minimo, costo))
        return True
    except Exception:
        return False


def eliminar_producto_inventario_db(sku):
    with _conexion() as conn:
        conn.execute("DELETE FROM inventario WHERE sku = ?", (sku,))


def vaciar_inventario_db():
    with _conexion() as conn:
        conn.execute("DELETE FROM inventario")


_PREFIJOS_SERIE = {
    "Facturas": "F",
    "Albaranes": "A",
    "Compras": "C",
}


def _siguiente_numero_documento(cursor, tipo: str) -> str:
    serie = next((s for clave, s in _PREFIJOS_SERIE.items() if clave in tipo), None)
    if serie is None:
        return "DOC_S_N"

    anio = datetime.now().year
    cursor.execute(
        """
        INSERT INTO contadores (serie, anio, ultimo) VALUES (?, ?, 1)
        ON CONFLICT(serie, anio) DO UPDATE SET ultimo = ultimo + 1
        RETURNING ultimo
        """,
        (serie, anio)
    )
    contador = cursor.fetchone()[0]
    return f"{serie}-{anio}-{contador:04d}"


def guardar_movimiento_db(tipo, concepto, base, tipo_iva, cuota_iva, tipo_irpf, cuota_irpf, cuota_recargo, importe, cliente_info="", estado="PENDIENTE"):
    with _conexion() as conn:
        cursor = conn.cursor()
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("SELECT hash_actual FROM movimientos ORDER BY id DESC LIMIT 1")
        fila = cursor.fetchone()
        hash_anterior = fila[0] if fila else "PRIMER_REGISTRO_LZ79"

        num_doc = _siguiente_numero_documento(cursor, tipo)

        cadena = f"{num_doc}|{fecha_hora}|{importe:.2f}|{hash_anterior}"
        hash_actual = hashlib.sha256(cadena.encode("utf-8")).hexdigest()

        cursor.execute("""
            INSERT INTO movimientos (
                tipo, concepto, base, tipo_iva, cuota_iva, tipo_irpf,
                cuota_irpf, cuota_recargo, importe, fecha_hora,
                num_factura, cliente_info, hash_anterior, hash_actual, estado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tipo, concepto, base, tipo_iva, cuota_iva, tipo_irpf,
            cuota_irpf, cuota_recargo, importe, fecha_hora,
            num_doc, cliente_info, hash_anterior, hash_actual, estado
        ))

        return num_doc, fecha_hora


def cambiar_estado_movimiento_db(id_mov: int, nuevo_estado: str):
    with _conexion() as conn:
        conn.execute("UPDATE movimientos SET estado = ? WHERE id = ?", (nuevo_estado, id_mov))


def obtener_todos_movimientos_db():
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, num_factura, tipo, fecha_hora, cliente_info, concepto, importe, estado FROM movimientos ORDER BY id DESC"
        )
        return cursor.fetchall()


def obtener_movimientos_para_cadena():
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, num_factura, fecha_hora, importe, hash_anterior, hash_actual FROM movimientos ORDER BY id ASC"
        )
        return cursor.fetchall()


def obtener_movimientos_periodo():
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT num_factura, fecha_hora, cliente_info, concepto, base, tipo_iva, cuota_iva, cuota_irpf, cuota_recargo, importe, tipo, estado 
            FROM movimientos ORDER BY id ASC
        """)
        return cursor.fetchall()


def obtener_resumen_trimestre_db(anio: int, trimestre: int):
    """Devuelve los movimientos filtrados y los totales fiscales del trimestre solicitado."""
    rangos = {
        1: (f"{anio}-01-01", f"{anio}-03-31 23:59:59"),
        2: (f"{anio}-04-01", f"{anio}-06-30 23:59:59"),
        3: (f"{anio}-07-01", f"{anio}-09-30 23:59:59"),
        4: (f"{anio}-10-01", f"{anio}-12-31 23:59:59"),
    }
    f_inicio, f_fin = rangos.get(trimestre, (f"{anio}-01-01", f"{anio}-12-31 23:59:59"))

    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, num_factura, tipo, fecha_hora, cliente_info, concepto,
                   base, tipo_iva, cuota_iva, tipo_irpf, cuota_irpf, cuota_recargo, importe, estado
            FROM movimientos
            WHERE fecha_hora BETWEEN ? AND ?
            ORDER BY id ASC
        """, (f_inicio, f_fin))
        filas = cursor.fetchall()

    base_ventas, iva_rep, ret_ventas = 0.0, 0.0, 0.0
    base_gastos, iva_sop, ret_gastos = 0.0, 0.0, 0.0

    for r in filas:
        tipo = r[2]
        base = r[6] or 0.0
        c_iva = r[8] or 0.0
        c_irpf = r[10] or 0.0

        if "Facturas" in tipo or "Ventas" in tipo:
            base_ventas += base
            iva_rep += c_iva
            ret_ventas += c_irpf
        elif "Compras" in tipo:
            base_gastos += base
            iva_sop += c_iva
            ret_gastos += c_irpf

    modelo_303 = iva_rep - iva_sop
    rendimiento_neto = base_ventas - base_gastos
    modelo_130 = max(0.0, (rendimiento_neto * 0.20) - ret_ventas)

    totales = {
        "base_ventas": base_ventas,
        "iva_repercutido": iva_rep,
        "retenciones_ventas": ret_ventas,
        "base_gastos": base_gastos,
        "iva_soportado": iva_sop,
        "retenciones_gastos": ret_gastos,
        "modelo_303": modelo_303,
        "rendimiento_neto": rendimiento_neto,
        "modelo_130": modelo_130,
    }

    return filas, totales


def buscar_en_inventario(busqueda: str):
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sku, descripcion, stock_actual, costo_unitario FROM inventario WHERE sku LIKE ? OR descripcion LIKE ?",
            (f"%{busqueda}%", f"%{busqueda}%")
        )
        return cursor.fetchall()


def contar_facturas_emitidas():
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(importe) FROM movimientos WHERE tipo LIKE 'Facturas%'")
        total_num, total_imp = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*), SUM(importe) FROM movimientos WHERE tipo LIKE 'Facturas%' AND estado = 'PENDIENTE'")
        pend_num, pend_imp = cursor.fetchone()

    return (total_num or 0, total_imp or 0.0, pend_num or 0, pend_imp or 0.0)


def contar_movimientos_por_tipo(prefijo_tipo: str):
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*), SUM(importe) FROM movimientos WHERE tipo LIKE ?",
            (f"{prefijo_tipo}%",)
        )
        total_num, total_imp = cursor.fetchone()
        return total_num or 0, total_imp or 0.0


def contar_contactos():
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT es_proveedor, COUNT(*) FROM clientes GROUP BY es_proveedor")
        filas = dict(cursor.fetchall())
    return filas.get(0, 0), filas.get(1, 0)


def obtener_top_clientes(limite=5):
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cliente_info, SUM(importe) as total
            FROM movimientos
            WHERE tipo LIKE 'Facturas%' AND cliente_info != ''
            GROUP BY cliente_info
            ORDER BY total DESC
            LIMIT ?
        """, (limite,))
        return cursor.fetchall()


def cargar_totales_db():
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tipo, estado, SUM(base), SUM(cuota_iva), SUM(importe) FROM movimientos GROUP BY tipo, estado"
        )
        filas = cursor.fetchall()

    ingresos, gastos = 0.0, 0.0
    iva_rep, iva_sop = 0.0, 0.0
    ingresos_pendientes = 0.0

    for tipo, estado, base, c_iva, total in filas:
        total = total or 0.0
        c_iva = c_iva or 0.0
        if "Facturas" in tipo or "Ventas" in tipo:
            if estado == "COBRADO":
                ingresos += total
            else:
                ingresos_pendientes += total
            iva_rep += c_iva
        elif "Compras" in tipo:
            gastos += total
            iva_sop += c_iva

    return ingresos, gastos, iva_rep, iva_sop, ingresos_pendientes


def obtener_producto_por_sku(sku):
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sku, descripcion, categoria, stock_actual, nivel_minimo, costo_unitario FROM inventario WHERE sku = ?",
            (sku,)
        )
        return cursor.fetchone()


def obtener_trimestre_actual():
    mes = datetime.now().month
    if mes in (1, 2, 3):
        return 1
    elif mes in (4, 5, 6):
        return 2
    elif mes in (7, 8, 9):
        return 3
    else:
        return 4
