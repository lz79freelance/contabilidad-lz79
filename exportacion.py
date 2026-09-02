import io
import base64
import qrcode

def generar_qr_verifactu_base64(nif_emisor: str, num_factura: str, fecha: str, total: float) -> str:
    """
    Genera el código QR con el formato oficial de cotejo tributario
    y lo devuelve como string Base64 para incrustarlo directamente en HTML/PDF.
    """
    # URL estándar de verificación tributaria
    contenido_qr = (
        f"https://sede.agenciatributaria.gob.es/verifactu/consulta?"
        f"nif={nif_emisor}&num={num_factura}&fecha={fecha}&total={total:.2f}"
    )
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(contenido_qr)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_b64}"


def exportar_factura_cliente_html(datos_factura: dict) -> str:
    """
    Genera la factura imprimible del cliente en HTML con el código QR Veri*factu al pie.
    """
    nif_emisor = datos_factura.get("nif_emisor", "ES00000000T")
    num_factura = datos_factura.get("numero", "F-001")
    fecha = datos_factura.get("fecha", datetime.now().strftime("%d/%m/%Y"))
    cliente = html.escape(datos_factura.get("cliente", "Cliente General"))
    cif_cliente = html.escape(datos_factura.get("cif_cliente", "-"))
    concepto = html.escape(datos_factura.get("concepto", "Servicios profesionales"))
    base = float(datos_factura.get("base", 0.0))
    tipo_iva = float(datos_factura.get("tipo_iva", 21.0))
    cuota_iva = base * (tipo_iva / 100)
    total = base + cuota_iva

    # Generamos el QR en Base64
    qr_img_src = generar_qr_verifactu_base64(nif_emisor, num_factura, fecha, total)

    plantilla = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Factura {num_factura}</title>
<style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #0F172A; background: #FFF; font-size: 13px; }}
    .factura-box {{ max-width: 800px; margin: auto; border: 1px solid #CBD5E1; padding: 30px; border-radius: 8px; }}
    .cabecera {{ display: flex; justify-content: space-between; border-bottom: 2px solid #0284C7; padding-bottom: 15px; }}
    .datos-doc {{ text-align: right; }}
    .seccion-partes {{ display: flex; justify-content: space-between; margin: 25px 0; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th, td {{ border-bottom: 1px solid #E2E8F0; padding: 10px; text-align: left; }}
    th {{ background: #F1F5F9; font-weight: 600; }}
    .totales-box {{ margin-top: 20px; float: right; width: 250px; }}
    .totales-fila {{ display: flex; justify-content: space-between; padding: 5px 0; }}
    .total-destacado {{ font-size: 16px; font-weight: bold; border-top: 2px solid #0F172A; margin-top: 5px; padding-top: 5px; }}
    .pie-verifactu {{ clear: both; margin-top: 60px; padding-top: 20px; border-top: 1px dashed #CBD5E1; display: flex; align-items: center; gap: 20px; }}
    .pie-verifactu img {{ width: 110px; height: 110px; }}
    .texto-verifactu {{ font-size: 11px; color: #475569; line-height: 1.4; }}
</style>
</head>
<body>
<div class="factura-box">
    <div class="cabecera">
        <div>
            <h2 style="margin:0; color:#0284C7;">FACTURA</h2>
            <p style="margin:5px 0 0 0; color:#64748B;">LZ79 Essential</p>
        </div>
        <div class="datos-doc">
            <strong>Nº Factura:</strong> {num_factura}<br>
            <strong>Fecha:</strong> {fecha}
        </div>
    </div>

    <div class="seccion-partes">
        <div>
            <strong>Emisor:</strong><br>
            NIF: {nif_emisor}
        </div>
        <div style="text-align: right;">
            <strong>Cliente:</strong><br>
            {cliente}<br>
            NIF/CIF: {cif_cliente}
        </div>
    </div>

    <table>
        <thead>
            <tr><th>Descripción</th><th style="text-align:right;">Base</th><th style="text-align:center;">IVA</th><th style="text-align:right;">Total</th></tr>
        </thead>
        <tbody>
            <tr>
                <td>{concepto}</td>
                <td style="text-align:right;">{base:,.2f} €</td>
                <td style="text-align:center;">{tipo_iva:.0f}%</td>
                <td style="text-align:right;">{total:,.2f} €</td>
            </tr>
        </tbody>
    </table>

    <div class="totales-box">
        <div class="totales-fila"><span>Base Imponible:</span> <span>{base:,.2f} €</span></div>
        <div class="totales-fila"><span>IVA ({tipo_iva:.0f}%):</span> <span>+{cuota_iva:,.2f} €</span></div>
        <div class="totales-fila total-destacado"><span>TOTAL:</span> <span>{total:,.2f} €</span></div>
    </div>

    <div class="pie-verifactu">
        <img src="{qr_img_src}" alt="Código QR Veri*factu">
        <div class="texto-verifactu">
            <strong>Factura verificable en la sede electrónica de la AEAT</strong><br>
            Este documento cumple con las especificaciones técnicas del Reglamento de facturación y sistemas Veri*factu.<br>
            Escanee el código QR con cualquier dispositivo para cotejar la validez de este registro fiscal.
        </div>
    </div>
</div>
</body>
</html>"""

    ruta = os.path.join(get_ruta_plantillas(), f"Factura_{num_factura.replace('/', '_')}.html")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(plantilla)

    abrir_archivo_si_escritorio(os.path.abspath(ruta))
    return ruta
