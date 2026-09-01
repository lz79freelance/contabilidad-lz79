"""
logica.py
---------
Lógica de negocio, asistente por palabras clave, OCR tolerante y generación de HTML.
"""

import html
import os
import re
from datetime import datetime

from almacenamiento import get_ruta_plantillas, abrir_archivo_si_escritorio
from db import (
    cargar_totales_db,
    obtener_inventario_db,
    buscar_en_inventario,
    contar_facturas_emitidas,
    contar_movimientos_por_tipo,
    contar_contactos,
    obtener_top_clientes,
    obtener_trimestre_actual,
    obtener_movimientos_para_cadena,
)


def procesar_texto_factura_qr(texto_qr: str):
    partes = [p.strip() for p in texto_qr.replace(";", "|").split("|")]
    importe_encontrado = 0.0
    concepto_encontrado = texto_qr

    for parte in partes:
        try:
            limpio = parte.replace("€", "").replace(",", ".").strip()
            val = float(limpio)
            if val > 0:
                importe_encontrado = val
        except ValueError:
            pass

    return concepto_encontrado, importe_encontrado


def procesar_imagen_factura_ocr(ruta_imagen: str) -> dict:
    """Extrae datos de la imagen con soporte de Tesseract automático y fallback de rescate."""
    texto = ""
    try:
        from PIL import Image
        import pytesseract

        # Intentar ruta estándar de Tesseract en Windows si no está en PATH
        rutas_posibles = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
        ]
        for r in rutas_posibles:
            if os.path.exists(r):
                pytesseract.pytesseract.tesseract_cmd = r
                break

        img = Image.open(ruta_imagen)
        texto = pytesseract.image_to_string(img, lang="spa+eng")
    except Exception:
        texto = ""

    # Si no hubo texto del OCR, leer al menos el nombre del archivo
    texto_total = texto + " " + os.path.basename(ruta_imagen)

    patron_cif = r"\b([A-HJ-NP-SUVWXYZ]\d{7}[0-9A-J]|\d{8}[TRWAGMYFPDXBNJZSQVHLCKE])\b"
    match_cif = re.search(patron_cif, texto_total, re.IGNORECASE)
    cif_detectado = match_cif.group(1).upper() if match_cif else "CIF / NIF No detectado"

    # Buscar importes con decimales (ej. 45.50, 120,00, 15.99)
    candidatos = re.findall(r"\b\d{1,5}[.,]\d{2}\b", texto_total)
    valores = []
    for c in candidatos:
        try:
            val = float(c.replace(",", "."))
            if 0 < val < 50000:
                valores.append(val)
        except ValueError:
            pass

    valores_unicos = sorted(list(set(valores)), reverse=True)
    total_estimado = valores_unicos[0] if valores_unicos else 0.0

    return {
        "texto_crudo": texto.strip(),
        "cif": cif_detectado,
        "total_estimado": total_estimado,
        "valores_encontrados": valores_unicos[:4] if valores_unicos else [],
    }


def procesar_consulta_asistente(consulta_usuario: str) -> str:
    texto = consulta_usuario.lower().strip()

    if any(k in texto for k in ["hola", "buenas", "buenos dias", "hey"]):
        return "👋 ¡Hola! Pregúntame por **balance**, **cobros**, **pendientes**, **stock**, **facturas**, **albaranes** o **compras**."

    if any(k in texto for k in ["balance", "iva", "beneficio", "ganancia", "cuanto gane", "303", "130"]):
        ing, gas, iva_rep, iva_sop, ing_pend = cargar_totales_db()
        dif = ing - gas
        return (f"📊 **Resumen Financiero Real:**\n\n"
                f"• **Ingresos Cobrados:** +{ing:.2f} €\n"
                f"• **Pendiente de Cobro:** ⏳ {ing_pend:.2f} €\n"
                f"• **Gastos / Compras:** -{gas:.2f} €\n"
                f"• **Rendimiento Neto:** {dif:.2f} €\n\n"
                f"• **IVA Repercutido:** +{iva_rep:.2f} €\n"
                f"• **IVA Soportado:** -{iva_sop:.2f} €\n"
                f"• **Estimación Modelo 303:** {(iva_rep - iva_sop):.2f} €")

    if any(k in texto for k in ["pendiente", "por cobrar", "cobrar", "deben"]):
        _tot, _imp, pend_num, pend_imp = contar_facturas_emitidas()
        return f"⏳ Tienes **{pend_num} facturas pendientes de cobro** por un total de **{pend_imp:.2f} €**."

    if any(k in texto for k in ["alerta", "minimo", "reponer", "falta"]):
        items = obtener_inventario_db()
        criticos = [f"• {desc} (Stock: {stock} | Mín: {minimo})" for sku,
                    desc, cat, stock, minimo, costo in items if stock < minimo]
        if criticos:
            return "⚠️ **Artículos en stock crítico:**\n" + "\n".join(criticos)
        return "✅ Todo el stock se encuentra por encima del umbral mínimo."

    if any(k in texto for k in ["stock", "inventario", "buscar", "precio"]):
        palabras = [w for w in texto.split() if w not in ["stock", "de", "el", "la", "buscar", "precio", "cuanto", "hay"]]
        if not palabras:
            total_items = len(obtener_inventario_db())
            return f"📦 Tienes {total_items} referencias registradas en inventario."

        busqueda = " ".join(palabras)
        resultados = buscar_en_inventario(busqueda)
        if resultados:
            lineas = [f"• **{sku}** - {desc}: {stock} uds a {costo:.2f} €" for sku, desc, stock, costo in resultados]
            return "📦 **Resultados de Inventario:**\n" + "\n".join(lineas)
        return f"❌ No se encontraron productos con '{busqueda}'."

    if any(k in texto for k in ["factura", "ventas", "total facturado"]):
        total_num, total_imp, pend_num, pend_imp = contar_facturas_emitidas()
        cobradas_imp = total_imp - pend_imp
        return (f"🧾 **Resumen de Facturas:**\n\n"
                f"• **Total Emitidas:** {total_num} ({total_imp:.2f} €)\n"
                f"• **Cobradas:** {(total_num - pend_num)} ({cobradas_imp:.2f} €)\n"
                f"• **Pendientes:** {pend_num} ({pend_imp:.2f} €)")

    if "albaran" in texto or "albarán" in texto:
        total_num, total_imp = contar_movimientos_por_tipo("Albaranes")
        return f"📦 Llevas **{total_num} albaranes** registrados por un total de **{total_imp:.2f} €**."

    if any(k in texto for k in ["compra", "gasto", "gastado"]):
        total_num, total_imp = contar_movimientos_por_tipo("Compras")
        return f"🧮 Tienes **{total_num} compras/gastos** registrados por un total de **{total_imp:.2f} €**."

    if any(k in texto for k in ["mejor cliente", "top cliente", "ranking"]):
        top = obtener_top_clientes(5)
        if not top:
            return "📊 Todavía no hay facturas asociadas a clientes."
        lineas = [f"{i+1}. **{cli}** — {total:.2f} €" for i, (cli, total) in enumerate(top)]
        return "🏆 **Ranking de Clientes:**\n" + "\n".join(lineas)

    if any(k in texto for k in ["cliente", "proveedor", "contacto"]):
        num_clientes, num_proveedores = contar_contactos()
        return f"👥 **Directorio:** {num_clientes} Clientes | {num_proveedores} Proveedores"

    if "trimestre" in texto:
        trimestre = obtener_trimestre_actual()
        return f"📅 Estás en el **{trimestre}º trimestre** del año fiscal."

    return ("🤖 Comandos disponibles:\n\n"
            "• *'Balance'* → Estado de ingresos, gastos e IVA.\n"
            "• *'Pendientes'* → Facturas por cobrar.\n"
            "• *'Facturas'* → Total facturado y desglose.\n"
            "• *'Stock [nombre]'* → Búsqueda de inventario.\n"
            "• *'Compras'* / *'Albaranes'* → Registros acumulados.")


def verificar_cadena_movimientos():
    import hashlib

    filas = obtener_movimientos_para_cadena()
    if not filas:
        return True, "No hay movimientos registrados todavía.", None

    hash_esperado = "PRIMER_REGISTRO_LZ79"
    for _id, num_doc, fecha_hora, importe, hash_anterior, hash_actual in filas:
        if hash_anterior != hash_esperado:
            return False, f"Rotura en doc {num_doc}: hash_anterior no coincide.", num_doc

        cadena = f"{num_doc}|{fecha_hora}|{importe:.2f}|{hash_anterior}"
        recalculado = hashlib.sha256(cadena.encode("utf-8")).hexdigest()
        if recalculado != hash_actual:
            return False, f"Rotura en doc {num_doc}: contenido modificado.", num_doc

        hash_esperado = hash_actual

    return True, f"Cadena íntegra: {len(filas)} registros verificados.", None


def generar_html_documento_individual(num_doc, tipo, concepto, base, cuota_iva, tipo_iva=21.0,
                                       cuota_irpf=0.0, tipo_irpf=0.0, cuota_recargo=0.0,
                                       total=None, cliente_info="", fecha_hora="", estado="PENDIENTE"):
    if total is None:
        total = base + cuota_iva + cuota_recargo - cuota_irpf

    concepto = html.escape(str(concepto))
    cliente_info = html.escape(str(cliente_info))
    num_doc_html = html.escape(str(num_doc))

    es_venta = "Facturas" in tipo or "Ventas" in tipo
    color_tipo = "#0284C7" if es_venta else "#DC2626"
    badge_estado = f"<span style='color:{'#16A34A' if estado=='COBRADO' else '#EA580C'}; font-weight:bold;'>[{estado}]</span>"

    filas_impuestos = f"<tr><td><strong>IVA ({tipo_iva:.0f}%):</strong></td><td style='text-align:right;'>+{cuota_iva:.2f} €</td></tr>"
    if cuota_recargo > 0:
        filas_impuestos += f"<tr><td><strong>Recargo Equivalencia:</strong></td><td style='text-align:right;'>+{cuota_recargo:.2f} €</td></tr>"
    if cuota_irpf > 0:
        filas_impuestos += f"<tr><td><strong>Retención IRPF ({tipo_irpf:.0f}%):</strong></td><td style='text-align:right;'>-{cuota_irpf:.2f} €</td></tr>"

    plantilla = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Documento {num_doc_html}</title>
<style>
    body {{ font-family: Arial, sans-serif; margin: 40px; color: #222; }}
    .header {{ border-bottom: 2px solid #444; padding-bottom: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; }}
    .empresa {{ font-size: 20px; font-weight: bold; color: #0F172A; }}
    .titulo {{ text-align: right; font-size: 22px; font-weight: bold; color: {color_tipo}; }}
    .datos-cliente {{ margin-top: 20px; font-size: 14px; border: 1px solid #ddd; padding: 12px; border-radius: 6px; background: #F8FAFC; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 25px; font-size: 13px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background-color: #1E293B; color: white; }}
    .num {{ text-align: right; }}
    .totales {{ margin-top: 20px; width: 50%; margin-left: auto; font-size: 14px; }}
    .footer {{ margin-top: 40px; font-size: 11px; color: #666; text-align: center; }}
</style></head>
<body>
    <div class="header">
        <div>
            <div class="empresa">LZ79 ESSENTIAL</div>
            <div style="font-size: 12px; color: #64748B;">Software de Gestión y Contabilidad</div>
        </div>
        <div class="titulo">
            {html.escape(tipo.upper())} {badge_estado}<br>
            <span style="font-size: 16px; color: #333;">Nº {num_doc_html}</span><br>
            <span style="font-size: 12px; color: #666;">Fecha: {html.escape(str(fecha_hora))}</span>
        </div>
    </div>
    <div class="datos-cliente">
        <strong>Asignado a:</strong> {cliente_info}<br>
        <strong>Concepto:</strong> {concepto}
    </div>
    <table>
        <thead>
            <tr>
                <th>Concepto</th>
                <th class="num">Base</th>
                <th class="num">IVA ({tipo_iva:.0f}%)</th>
                <th class="num">Total</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>{concepto}</td>
                <td class="num">{base:.2f} €</td>
                <td class="num">{cuota_iva:.2f} €</td>
                <td class="num">{(base + cuota_iva):.2f} €</td>
            </tr>
        </tbody>
    </table>
    <table class="totales">
        <tr><td><strong>Base Imponible:</strong></td><td class="num">{base:.2f} €</td></tr>
        {filas_impuestos}
        <tr><td style="font-size: 15px;"><strong>TOTAL:</strong></td><td class="num" style="font-size: 15px;"><strong>{total:.2f} €</strong></td></tr>
    </table>
    <div class="footer">Documento generado automáticamente por LZ79 Essential.</div>
</body>
</html>"""

    ruta_plantillas = get_ruta_plantillas()
    nombre_archivo = os.path.join(ruta_plantillas, f"Doc_{str(num_doc).replace('/', '_')}.html")
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(plantilla)

    abrir_archivo_si_escritorio(os.path.abspath(nombre_archivo))
    return nombre_archivo
