import os
import ctypes
from ctypes import wintypes
from datetime import datetime
import flet as ft

from db import (
    inicializar_bd,
    guardar_contacto_db,
    obtener_contactos_db,
    eliminar_contacto_db,
    obtener_inventario_db,
    guardar_producto_inventario_db,
    eliminar_producto_inventario_db,
    obtener_producto_por_sku,
    vaciar_inventario_db,
    guardar_movimiento_db,
    obtener_todos_movimientos_db,
    cargar_totales_db,
    cambiar_estado_movimiento_db,
    obtener_trimestre_actual,
)
from exportacion import (
    exportar_inventario_excel,
    importar_inventario_excel,
    exportar_informe_gestoria_excel,
    exportar_informe_gestoria_html,
)
from logica import (
    procesar_texto_factura_qr,
    procesar_consulta_asistente,
    generar_html_documento_individual,
    verificar_cadena_movimientos,
    procesar_imagen_factura_ocr,
)
from escaner import escanear_qr

COLOR_FONDO = "#0F172A"
COLOR_PANEL = "#1E293B"
COLOR_ACCENTO = "#38BDF8"
COLOR_TEXTO = "#F8FAFC"


def seleccionar_archivo_nativo() -> str:
    try:
        class OPENFILENAMEW(ctypes.Structure):
            _fields_ = [
                ("lStructSize", wintypes.DWORD),
                ("hwndOwner", wintypes.HWND),
                ("hInstance", wintypes.HINSTANCE),
                ("lpstrFilter", wintypes.LPCWSTR),
                ("lpstrCustomFilter", wintypes.LPWSTR),
                ("nMaxCustFilter", wintypes.DWORD),
                ("nFilterIndex", wintypes.DWORD),
                ("lpstrFile", wintypes.LPWSTR),
                ("nMaxFile", wintypes.DWORD),
                ("lpstrFileTitle", wintypes.LPWSTR),
                ("nMaxFileTitle", wintypes.DWORD),
                ("lpstrInitialDir", wintypes.LPCWSTR),
                ("lpstrTitle", wintypes.LPCWSTR),
                ("Flags", wintypes.DWORD),
                ("nFileOffset", wintypes.WORD),
                ("nFileExtension", wintypes.WORD),
                ("lpstrDefExt", wintypes.LPCWSTR),
                ("lCustData", wintypes.LPARAM),
                ("lpfnHook", wintypes.LPVOID),
                ("lpTemplateName", wintypes.LPCWSTR),
                ("pvReserved", wintypes.LPVOID),
                ("dwReserved", wintypes.DWORD),
                ("FlagsEx", wintypes.DWORD),
            ]

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        buffer = ctypes.create_unicode_buffer(1024)
        filtro = "Imágenes (*.jpg;*.png;*.jpeg;*.webp)\0*.jpg;*.png;*.jpeg;*.webp\0Todos (*.*)\0*.*\0\0"

        ofn = OPENFILENAMEW()
        ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
        ofn.hwndOwner = hwnd
        ofn.lpstrFilter = filtro
        ofn.lpstrFile = ctypes.cast(buffer, wintypes.LPWSTR)
        ofn.nMaxFile = 1024
        ofn.lpstrTitle = "Seleccionar Factura o Tique"
        ofn.Flags = 0x00000800 | 0x00000008 | 0x00080000

        if ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
            return buffer.value
    except Exception:
        pass
    return ""


def main(page: ft.Page):
    inicializar_bd()

    page.title = "LZ79 Essential - Gestión y Contabilidad"
    page.bgcolor = COLOR_FONDO
    page.theme = ft.Theme(color_scheme_seed="sky")
    page.window_width = 520
    page.window_height = 840

    def navegar_a(nueva_ruta: str):
        page.route = nueva_ruta
        page.views.clear()
        page.views.append(crear_vista(nueva_ruta))
        page.update()

    def wrap_responsive(content):
        return ft.Container(
            content=ft.Container(
                content=content,
                width=460,
                alignment=ft.Alignment(0, 0)
            ),
            padding=15,
            alignment=ft.Alignment(0, -1),
            expand=True
        )

    def crear_vista(route):
        if route == "/":
            tarjetas_menu = [
                ("Facturas", "/facturas", ft.Icons.RECEIPT_LONG_ROUNDED, False),
                ("Inventario", "/almacen", ft.Icons.INVENTORY_2_ROUNDED, True),
                ("Albaranes", "/albaranes", ft.Icons.LOCAL_SHIPPING_ROUNDED, False),
                ("Compras", "/compras", ft.Icons.SHOPPING_BAG_ROUNDED, False),
                ("Asistente IA", "/asistente", ft.Icons.SMART_TOY_ROUNDED, False),
                ("Historial", "/historial", ft.Icons.HISTORY_ROUNDED, False),
                ("Contactos", "/clientes", ft.Icons.PEOPLE_ALT_ROUNDED, False),
                ("Balance Gestoría", "/gastos", ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, False),
            ]

            def construir_tarjeta(titulo, r_ruta, icono, destacada):
                bg_normal = "#FFFFFF" if destacada else "#1E293B"
                bg_hover = "#F1F5F9" if destacada else "#2D3748"
                icon_color = "#0284C7" if destacada else "#38BDF8"
                text_color = "#0F172A" if destacada else "#F8FAFC"
                borde_color = "#0284C7" if destacada else "#334155"
                ancho_borde = 2 if destacada else 1

                card_container = ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(icono, size=40, color=icon_color),
                            ft.Text(titulo, size=13, weight=ft.FontWeight.W_600,
                                    color=text_color, text_align=ft.TextAlign.CENTER)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8
                    ),
                    alignment=ft.Alignment(0, 0),
                    bgcolor=bg_normal,
                    border=ft.Border.all(ancho_borde, borde_color),
                    border_radius=16,
                    height=120,
                    animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
                    ink=True,
                    on_click=lambda e, r=r_ruta: navegar_a(r)
                )

                def on_hover(e):
                    try:
                        card_container.bgcolor = bg_hover if e.data == "true" else bg_normal
                        card_container.update()
                    except Exception:
                        pass

                card_container.on_hover = on_hover
                return ft.Column(controls=[card_container], col={"xs": 6, "sm": 4, "md": 3})

            columnas_grid = [construir_tarjeta(t, r, i, d) for t, r, i, d in tarjetas_menu]

            return ft.View(
                route="/",
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Container(height=15),
                                ft.Row(
                                    controls=[
                                        ft.Text("LZ79", size=28, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                                        ft.Text("Freelance", size=22, weight=ft.FontWeight.W_400, color="#94A3B8")
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=8
                                ),
                                ft.Container(height=3, width=80, bgcolor=COLOR_ACCENTO,
                                             border_radius=2, margin=ft.Margin(0, 4, 0, 15)),
                                ft.ResponsiveRow(controls=columnas_grid, spacing=14, run_spacing=14),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            scroll=ft.ScrollMode.AUTO,
                            expand=True
                        ),
                        padding=20,
                        expand=True
                    )
                ],
                vertical_alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                bgcolor=COLOR_FONDO
            )

        elif route == "/asistente":
            lista_mensajes = ft.ListView(expand=True, spacing=10, auto_scroll=True)
            txt_pregunta = ft.TextField(
                hint_text="Pregunta por balance, 303, inventario o adjunta documento...",
                border_color=COLOR_ACCENTO,
                expand=True
            )

            def agregar_burbuja(autor: str, texto_m: str, es_bot: bool, controles_extra: list = None):
                bg_c = "#1E293B" if es_bot else "#0284C7"
                align = ft.CrossAxisAlignment.START if es_bot else ft.CrossAxisAlignment.END

                elementos = [
                    ft.Text(autor, size=10, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO if es_bot else "#E0F2FE"),
                    ft.Markdown(texto_m, selectable=True)
                ]
                if controles_extra:
                    elementos.append(ft.Container(height=4))
                    for c in controles_extra:
                        elementos.append(c)

                burbuja = ft.Container(
                    content=ft.Column(elementos, spacing=4),
                    bgcolor=bg_c,
                    padding=10,
                    border_radius=12,
                    width=400
                )
                lista_mensajes.controls.append(ft.Column([burbuja], horizontal_alignment=align))
                page.update()

            def registrar_desde_asistente(tipo: str, total: float, contacto: str, concepto: str):
                base = round(total / 1.21, 2)
                cuota_iva = round(total - base, 2)
                estado_reg = "PENDIENTE" if "Facturas" in tipo else "COBRADO"

                num_doc, fecha_hora = guardar_movimiento_db(
                    tipo, concepto, base, 21.0, cuota_iva, 0.0, 0.0, 0.0, total, contacto, estado_reg
                )
                generar_html_documento_individual(
                    num_doc, tipo, concepto, base, cuota_iva, 21.0, 0.0, 0.0, 0.0, total, contacto, fecha_hora, estado_reg
                )
                agregar_burbuja(
                    "Asistente LZ79",
                    f"✅ **{tipo} {num_doc} registrada.**\n\n• **Base:** {base:.2f} € | **IVA:** {cuota_iva:.2f} €\n• **Total:** {total:.2f} €\n• **Contacto:** {contacto}",
                    True
                )

            def abrir_dialogo_foto(e):
                ruta = seleccionar_archivo_nativo()
                if ruta:
                    nombre_arch = os.path.basename(ruta)
                    burbuja_usr = ft.Container(
                        content=ft.Column([
                            ft.Text("Tú", size=10, weight=ft.FontWeight.BOLD, color="#E0F2FE"),
                            ft.Markdown(f"📎 *Documento adjunto:* `{nombre_arch}`", selectable=True)
                        ], spacing=4),
                        bgcolor="#0284C7",
                        padding=10,
                        border_radius=12,
                        width=400
                    )
                    lista_mensajes.controls.append(ft.Column([burbuja_usr], horizontal_alignment=ft.CrossAxisAlignment.END))

                    res = procesar_imagen_factura_ocr(ruta)
                    cif = res.get("cif", "B-76543210")
                    tot = res.get("total_estimado", 0.0)

                    txt_cif_in = ft.TextField(label="NIF / CIF", value=cif if "No detectado" not in cif else "B-76543210", height=40, text_size=12, expand=True)
                    txt_imp_in = ft.TextField(label="Importe (€)", value=f"{tot:.2f}" if tot > 0 else "0.00", height=40, text_size=12, width=110)

                    def confirmar_reg(tipo):
                        try:
                            t_val = float(txt_imp_in.value.replace(",", "."))
                            c_val = txt_cif_in.value.strip()
                            registrar_desde_asistente(tipo, t_val, c_val, f"{nombre_arch}")
                        except ValueError:
                            pass

                    btn_c = ft.Button(content=ft.Text("📥 Guardar Compra", color="#FCA5A5", weight="bold", size=12), bgcolor="#7F1D1D", on_click=lambda e: confirmar_reg("Compras / Gastos"))
                    btn_f = ft.Button(content=ft.Text("🧾 Emitir Factura", color="#4ADE80", weight="bold", size=12), bgcolor="#064E3B", on_click=lambda e: confirmar_reg("Facturas"))

                    burbuja_bot = ft.Container(
                        content=ft.Column([
                            ft.Text("Asistente LZ79", size=10, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                            ft.Markdown("📄 **Datos detectados:**\nPuedes ajustar datos y registrar con 1 clic:", selectable=True),
                            ft.Container(height=4),
                            ft.Row([txt_cif_in, txt_imp_in], spacing=8),
                            ft.Row([btn_c, btn_f], spacing=8)
                        ], spacing=4),
                        bgcolor="#1E293B",
                        padding=10,
                        border_radius=12,
                        width=400
                    )
                    lista_mensajes.controls.append(ft.Column([burbuja_bot], horizontal_alignment=ft.CrossAxisAlignment.START))
                    page.update()

            agregar_burbuja(
                "Asistente LZ79",
                "¡Hola! Adjunta una factura con el clip 📎 o escanea un código para registrar movimientos directamente.",
                True
            )

            def enviar_mensaje_click(e=None):
                val = txt_pregunta.value.strip()
                if not val:
                    return
                txt_pregunta.value = ""
                agregar_burbuja("Tú", val, False)

                respuesta = procesar_consulta_asistente(val)
                agregar_burbuja("Asistente LZ79", respuesta, True)

            txt_pregunta.on_submit = enviar_mensaje_click

            return ft.View(
                route="/asistente",
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Asistente & Escáner", size=22, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                            ft.Divider(color="#334155"),
                            lista_mensajes,
                            ft.Row([
                                txt_pregunta,
                                ft.IconButton(
                                    icon=ft.Icons.ATTACH_FILE_ROUNDED,
                                    icon_color=COLOR_ACCENTO,
                                    tooltip="Adjuntar foto/documento",
                                    on_click=abrir_dialogo_foto
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.SEND_ROUNDED,
                                    icon_color=COLOR_ACCENTO,
                                    on_click=lambda e: enviar_mensaje_click()
                                )
                            ]),
                            ft.Button(content=ft.Text("← Volver al Menú", color="#94A3B8"),
                                      on_click=lambda e: navegar_a("/"), width=float("inf"))
                        ], expand=True),
                        padding=15,
                        expand=True
                    )
                ],
                bgcolor=COLOR_FONDO
            )

        elif route == "/historial":
            movs = obtener_todos_movimientos_db()
            filas_historial = []

            for m_id, num, tipo, f_hora, cli, conc, imp, estado in movs:
                es_v = "Facturas" in tipo or "Ventas" in tipo
                col_imp = "#4ADE80" if es_v else "#F87171"
                es_cobrado = estado == "COBRADO"

                def toggle_estado(id_m=m_id, est_act=estado):
                    nuevo = "PENDIENTE" if est_act == "COBRADO" else "COBRADO"
                    cambiar_estado_movimiento_db(id_m, nuevo)
                    navegar_a("/historial")

                btn_estado = ft.Button(
                    content=ft.Text("✅ Cobrado" if es_cobrado else "⏳ Pendiente", size=10,
                                    color="#4ADE80" if es_cobrado else "#FB923C", weight="bold"),
                    on_click=lambda e, id_m=m_id, est=estado: toggle_estado(id_m, est)
                )

                filas_historial.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(num, size=11, weight="bold", color=COLOR_ACCENTO)),
                        ft.DataCell(ft.Text(tipo[:8], size=11, color=COLOR_TEXTO)),
                        ft.DataCell(ft.Text(f_hora[:10], size=11, color="#94A3B8")),
                        ft.DataCell(ft.Text(cli[:12] if cli else "-", size=11, color=COLOR_TEXTO)),
                        ft.DataCell(ft.Text(f"{imp:.2f} €", size=11, weight="bold", color=col_imp)),
                        ft.DataCell(btn_estado)
                    ])
                )

            tabla_historial = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Nº Doc", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("Tipo", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("Fecha", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("Contacto", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("Total", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("Estado (Clic)", size=11, weight="bold")),
                ],
                rows=filas_historial,
                heading_row_color="#334155",
            )

            lbl_integridad = ft.Text("", size=12)

            def verificar_integridad_click(e):
                integra, mensaje, _num_doc = verificar_cadena_movimientos()
                lbl_integridad.value = ("🔒 " if integra else "🚨 ") + mensaje
                lbl_integridad.color = "#4ADE80" if integra else "#F87171"
                page.update()

            return ft.View(
                route="/historial",
                controls=[
                    ft.Column([
                        ft.Text("Historial de Registros", size=24, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                        ft.Row([tabla_historial], scroll=ft.ScrollMode.ALWAYS),
                        ft.Container(height=6),
                        ft.Button(
                            content=ft.Text("🔒 Verificar integridad de la cadena", color=COLOR_ACCENTO, weight="bold"),
                            on_click=verificar_integridad_click,
                            width=float("inf"), bgcolor="#1E293B"
                        ),
                        lbl_integridad,
                        ft.Container(height=10),
                        ft.Button(content=ft.Text("← Volver al Menú", color="#94A3B8"),
                                  on_click=lambda e: navegar_a("/"), width=float("inf"))
                    ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                ],
                bgcolor=COLOR_FONDO
            )

        elif route == "/facturas":
            lista_clientes = obtener_contactos_db(es_proveedor=0)
            dd_cliente_factura = ft.Dropdown(
                label="Cliente", border_color=COLOR_ACCENTO, width=460,
                options=[ft.dropdown.Option(c[1]) for c in lista_clientes]
            )
            txt_concepto_factura = ft.TextField(label="Concepto", border_color=COLOR_ACCENTO, width=460)
            txt_importe_base_f = ft.TextField(label="Base Imponible (€)", border_color=COLOR_ACCENTO, width=460)

            dd_iva_factura = ft.Dropdown(
                label="IVA", value="21", border_color=COLOR_ACCENTO, width=140,
                options=[
                    ft.dropdown.Option("21", "21%"),
                    ft.dropdown.Option("10", "10%"),
                    ft.dropdown.Option("4", "4%"),
                    ft.dropdown.Option("0", "0%")
                ]
            )

            dd_irpf_factura = ft.Dropdown(
                label="IRPF", value="0", border_color=COLOR_ACCENTO, width=140,
                options=[
                    ft.dropdown.Option("0", "0%"),
                    ft.dropdown.Option("7", "7%"),
                    ft.dropdown.Option("15", "15%"),
                    ft.dropdown.Option("19", "19%")
                ]
            )

            dd_recargo_factura = ft.Dropdown(
                label="Recargo", value="0", border_color=COLOR_ACCENTO, width=140,
                options=[
                    ft.dropdown.Option("0", "0%"),
                    ft.dropdown.Option("5.2", "5.2%"),
                    ft.dropdown.Option("1.4", "1.4%"),
                    ft.dropdown.Option("0.5", "0.5%")
                ]
            )

            rg_estado_cobro = ft.RadioGroup(
                content=ft.Row([
                    ft.Radio(value="PENDIENTE", label="⏳ Pendiente de cobro"),
                    ft.Radio(value="COBRADO", label="✅ Cobrada")
                ], alignment=ft.MainAxisAlignment.CENTER),
                value="PENDIENTE"
            )

            lbl_desglose_calc = ft.Text("IVA: 0.00 € | IRPF: 0.00 € | RE: 0.00 €", size=12, color=COLOR_ACCENTO)
            lbl_total_calc_f = ft.Text("Total Factura: 0.00 €", size=18, weight=ft.FontWeight.BOLD, color="#4ADE80")
            lbl_msg_factura = ft.Text("", size=13)

            def calcular_totales_factura(e):
                try:
                    base = float(txt_importe_base_f.value.replace(",", "."))
                    tipo_iva = float(dd_iva_factura.value)
                    tipo_irpf = float(dd_irpf_factura.value)
                    tipo_rec = float(dd_recargo_factura.value)

                    c_iva = round(base * (tipo_iva / 100.0), 2)
                    c_irpf = round(base * (tipo_irpf / 100.0), 2)
                    c_rec = round(base * (tipo_rec / 100.0), 2)
                    total = round(base + c_iva + c_rec - c_irpf, 2)

                    lbl_desglose_calc.value = f"IVA: +{c_iva:.2f} €  |  IRPF: -{c_irpf:.2f} €  |  RE: +{c_rec:.2f} €"
                    lbl_total_calc_f.value = f"Total a Cobrar: {total:.2f} €"
                except ValueError:
                    lbl_desglose_calc.value = "IVA: 0.00 € | IRPF: 0.00 € | RE: 0.00 €"
                    lbl_total_calc_f.value = "Total Factura: 0.00 €"
                page.update()

            txt_importe_base_f.on_change = calcular_totales_factura
            dd_iva_factura.on_change = calcular_totales_factura
            dd_irpf_factura.on_change = calcular_totales_factura
            dd_recargo_factura.on_change = calcular_totales_factura

            def guardar_factura_click(e):
                try:
                    base = float(txt_importe_base_f.value.replace(",", "."))
                    tipo_iva = float(dd_iva_factura.value)
                    tipo_irpf = float(dd_irpf_factura.value)
                    tipo_rec = float(dd_recargo_factura.value)

                    c_iva = round(base * (tipo_iva / 100.0), 2)
                    c_irpf = round(base * (tipo_irpf / 100.0), 2)
                    c_rec = round(base * (tipo_rec / 100.0), 2)
                    total = round(base + c_iva + c_rec - c_irpf, 2)

                    cli = dd_cliente_factura.value if dd_cliente_factura.value else "Cliente Genérico"
                    conc = txt_concepto_factura.value.strip() if txt_concepto_factura.value else "Factura de Servicios"
                    estado_f = rg_estado_cobro.value

                    num_doc, fecha_hora = guardar_movimiento_db(
                        "Facturas", conc, base, tipo_iva, c_iva, tipo_irpf, c_irpf, c_rec, total, cli, estado_f
                    )
                    generar_html_documento_individual(
                        num_doc, "Factura", conc, base, c_iva, tipo_iva, c_irpf, tipo_irpf, c_rec, total, cli, fecha_hora, estado_f
                    )

                    lbl_msg_factura.value = f"✅ Factura {num_doc} guardada ({estado_f})."
                    lbl_msg_factura.color = "green"
                    txt_importe_base_f.value = ""
                    txt_concepto_factura.value = ""
                    page.update()
                except ValueError:
                    lbl_msg_factura.value = "⚠️ Importe inválido."
                    lbl_msg_factura.color = "red"
                    page.update()

            return ft.View(
                route="/facturas",
                controls=[
                    wrap_responsive(ft.Column([
                        ft.Text("Nueva Factura", size=24, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                        ft.Container(height=5),
                        dd_cliente_factura,
                        txt_concepto_factura,
                        txt_importe_base_f,
                        ft.Row([dd_iva_factura, dd_irpf_factura, dd_recargo_factura], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=5),
                        rg_estado_cobro,
                        lbl_desglose_calc,
                        lbl_total_calc_f,
                        lbl_msg_factura,
                        ft.Button(content=ft.Text("Emitir Factura", weight="bold"),
                                  on_click=guardar_factura_click, width=float("inf"), height=45),
                        ft.Button(content=ft.Text("← Volver", color="#94A3B8"),
                                  on_click=lambda e: navegar_a("/"), width=float("inf")),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10))
                ],
                bgcolor=COLOR_FONDO
            )

        elif route == "/albaranes":
            lista_clientes = obtener_contactos_db(es_proveedor=0)
            dd_cliente_alb = ft.Dropdown(
                label="Cliente", border_color=COLOR_ACCENTO, width=460,
                options=[ft.dropdown.Option(c[1]) for c in lista_clientes]
            )
            txt_concepto_alb = ft.TextField(label="Concepto Albarán", border_color=COLOR_ACCENTO, width=460)
            txt_importe_base_a = ft.TextField(label="Importe Base (€)", border_color=COLOR_ACCENTO, width=460)

            dd_iva_alb = ft.Dropdown(
                label="IVA", value="21", border_color=COLOR_ACCENTO, width=460,
                options=[
                    ft.dropdown.Option("21", "21% General"),
                    ft.dropdown.Option("10", "10% Reducido"),
                    ft.dropdown.Option("4", "4% Superreducido"),
                    ft.dropdown.Option("0", "0% Exento")
                ]
            )

            lbl_total_calc_a = ft.Text("Total: 0.00 €", size=18, weight=ft.FontWeight.BOLD, color="#4ADE80")
            lbl_msg_alb = ft.Text("", size=13)

            def calcular_totales_alb(e):
                try:
                    base = float(txt_importe_base_a.value.replace(",", "."))
                    porcentaje = float(dd_iva_alb.value)
                    total = base + (base * (porcentaje / 100.0))
                    lbl_total_calc_a.value = f"Total con IVA: {total:.2f} €"
                except ValueError:
                    lbl_total_calc_a.value = "Total con IVA: 0.00 €"
                page.update()

            txt_importe_base_a.on_change = calcular_totales_alb
            dd_iva_alb.on_change = calcular_totales_alb

            def guardar_albaran_click(e):
                try:
                    base = float(txt_importe_base_a.value.replace(",", "."))
                    porcentaje = float(dd_iva_alb.value)
                    c_iva = round(base * (porcentaje / 100.0), 2)
                    total = base + c_iva
                    cli = dd_cliente_alb.value if dd_cliente_alb.value else "Cliente Genérico"
                    conc = txt_concepto_alb.value if txt_concepto_alb.value else "Albarán"

                    num_doc, fecha_hora = guardar_movimiento_db(
                        "Albaranes", conc, base, porcentaje, c_iva, 0.0, 0.0, 0.0, total, cli, "COBRADO"
                    )
                    generar_html_documento_individual(
                        num_doc, "Albarán", conc, base, c_iva, porcentaje, 0.0, 0.0, 0.0, total, cli, fecha_hora, "COBRADO"
                    )

                    lbl_msg_alb.value = f"✅ Albarán {num_doc} guardado."
                    lbl_msg_alb.color = "green"
                    txt_importe_base_a.value = ""
                    txt_concepto_alb.value = ""
                    page.update()
                except ValueError:
                    lbl_msg_alb.value = "⚠️ Importe inválido."
                    lbl_msg_alb.color = "red"
                    page.update()

            return ft.View(
                route="/albaranes",
                controls=[
                    wrap_responsive(ft.Column([
                        ft.Text("Nuevo Albarán", size=24, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                        ft.Container(height=5),
                        dd_cliente_alb,
                        txt_concepto_alb,
                        txt_importe_base_a,
                        dd_iva_alb,
                        lbl_total_calc_a,
                        lbl_msg_alb,
                        ft.Button(content=ft.Text("Guardar Albarán", weight="bold"),
                                  on_click=guardar_albaran_click, width=float("inf"), height=45),
                        ft.Button(content=ft.Text("← Volver", color="#94A3B8"),
                                  on_click=lambda e: navegar_a("/"), width=float("inf")),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10))
                ],
                bgcolor=COLOR_FONDO
            )

        elif route == "/compras":
            lista_prov = obtener_contactos_db(es_proveedor=1)
            dd_prov = ft.Dropdown(
                label="Proveedor", border_color=COLOR_ACCENTO, width=460,
                options=[ft.dropdown.Option(p[1]) for p in lista_prov]
            )
            txt_concepto_compra = ft.TextField(label="Concepto Compra / Gasto", border_color=COLOR_ACCENTO, width=460)
            txt_importe_base_c = ft.TextField(label="Base Imponible (€)", border_color=COLOR_ACCENTO, width=460)

            dd_iva_compra = ft.Dropdown(
                label="IVA Soportado", value="21", border_color=COLOR_ACCENTO, width=220,
                options=[
                    ft.dropdown.Option("21", "21% General"),
                    ft.dropdown.Option("10", "10%"),
                    ft.dropdown.Option("4", "4%"),
                    ft.dropdown.Option("0", "0%")
                ]
            )

            dd_irpf_compra = ft.Dropdown(
                label="Retención (IRPF)", value="0", border_color=COLOR_ACCENTO, width=220,
                options=[
                    ft.dropdown.Option("0", "0%"),
                    ft.dropdown.Option("15", "15%"),
                    ft.dropdown.Option("19", "19%")
                ]
            )

            lbl_total_calc_c = ft.Text("Total Gasto: 0.00 €", size=18, weight=ft.FontWeight.BOLD, color="#F87171")
            lbl_compra_status = ft.Text("", size=13, color=COLOR_ACCENTO)

            def calcular_totales_compra(e):
                try:
                    base = float(txt_importe_base_c.value.replace(",", "."))
                    tipo_iva = float(dd_iva_compra.value)
                    tipo_irpf = float(dd_irpf_compra.value)

                    c_iva = round(base * (tipo_iva / 100.0), 2)
                    c_irpf = round(base * (tipo_irpf / 100.0), 2)
                    total = round(base + c_iva - c_irpf, 2)

                    lbl_total_calc_c.value = f"Total a Pagar: {total:.2f} €"
                except ValueError:
                    lbl_total_calc_c.value = "Total Gasto: 0.00 €"
                page.update()

            txt_importe_base_c.on_change = calcular_totales_compra
            dd_iva_compra.on_change = calcular_totales_compra
            dd_irpf_compra.on_change = calcular_totales_compra

            def guardar_compra_click(e):
                try:
                    base = float(txt_importe_base_c.value.replace(",", "."))
                    tipo_iva = float(dd_iva_compra.value)
                    tipo_irpf = float(dd_irpf_compra.value)

                    c_iva = round(base * (tipo_iva / 100.0), 2)
                    c_irpf = round(base * (tipo_irpf / 100.0), 2)
                    total = round(base + c_iva - c_irpf, 2)

                    prov = dd_prov.value if dd_prov.value else "Proveedor Genérico"
                    conc = txt_concepto_compra.value if txt_concepto_compra.value else "Gasto"

                    num_doc, fecha_hora = guardar_movimiento_db(
                        "Compras / Gastos", conc, base, tipo_iva, c_iva, tipo_irpf, c_irpf, 0.0, total, prov, "COBRADO"
                    )
                    generar_html_documento_individual(
                        num_doc, "Compra", conc, base, c_iva, tipo_iva, c_irpf, tipo_irpf, 0.0, total, prov, fecha_hora, "COBRADO"
                    )

                    lbl_compra_status.value = f"✅ Registrado {num_doc}."
                    lbl_compra_status.color = "green"
                    txt_concepto_compra.value = ""
                    txt_importe_base_c.value = ""
                    page.update()
                except ValueError:
                    lbl_compra_status.value = "⚠️ Importe inválido."
                    page.update()

            return ft.View(
                route="/compras",
                controls=[
                    wrap_responsive(ft.Column([
                        ft.Text("Módulo Compras / Gastos", size=24, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                        ft.Container(height=5),
                        dd_prov,
                        txt_concepto_compra,
                        txt_importe_base_c,
                        ft.Row([dd_iva_compra, dd_irpf_compra], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        lbl_total_calc_c,
                        lbl_compra_status,
                        ft.Button(content=ft.Text("Guardar Compra", weight="bold"),
                                  on_click=guardar_compra_click, width=float("inf"), height=45),
                        ft.Button(content=ft.Text("← Volver", color="#94A3B8"),
                                  on_click=lambda e: navegar_a("/"), width=float("inf")),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10))
                ],
                bgcolor=COLOR_FONDO
            )

        elif route == "/almacen" or route == "/almacen/nuevo":
            if route == "/almacen/nuevo":
                txt_sku = ft.TextField(label="SKU / Código Producto", border_color=COLOR_ACCENTO, width=460)
                txt_desc = ft.TextField(label="Descripción del Producto", border_color=COLOR_ACCENTO, width=460)
                txt_cat = ft.TextField(label="Categoría", border_color=COLOR_ACCENTO, width=460)
                txt_stock = ft.TextField(label="Stock Actual", border_color=COLOR_ACCENTO, width=460)
                txt_min = ft.TextField(label="Stock Mínimo Alerta", border_color=COLOR_ACCENTO, width=460)
                txt_costo = ft.TextField(label="Costo Unitario (€)", border_color=COLOR_ACCENTO, width=460)
                lbl_msg_prod = ft.Text("", size=13)

                def guardar_prod_click(e):
                    try:
                        sku = txt_sku.value.strip()
                        desc = txt_desc.value.strip()
                        cat = txt_cat.value.strip()
                        stock = int(txt_stock.value.strip())
                        minimo = int(txt_min.value.strip())
                        costo = float(txt_costo.value.replace(",", ".").strip())

                        if sku and desc:
                            if guardar_producto_inventario_db(sku, desc, cat, stock, minimo, costo):
                                lbl_msg_prod.value = "✅ Producto guardado con éxito."
                                lbl_msg_prod.color = "green"
                                txt_sku.value = ""
                                txt_desc.value = ""
                                txt_cat.value = ""
                                txt_stock.value = ""
                                txt_min.value = ""
                                txt_costo.value = ""
                            else:
                                lbl_msg_prod.value = "⚠️ Error al guardar."
                                lbl_msg_prod.color = "red"
                        else:
                            lbl_msg_prod.value = "⚠️ Rellene al menos SKU y Descripción."
                            lbl_msg_prod.color = "orange"
                        page.update()
                    except ValueError:
                        lbl_msg_prod.value = "⚠️ Revise que stock, mínimo y costo sean numéricos."
                        lbl_msg_prod.color = "red"
                        page.update()

                return ft.View(
                    route="/almacen/nuevo",
                    controls=[
                        wrap_responsive(ft.Column([
                            ft.Text("Nuevo Producto", size=24, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                            txt_sku, txt_desc, txt_cat, txt_stock, txt_min, txt_costo, lbl_msg_prod,
                            ft.Container(height=10),
                            ft.Button(content=ft.Text("Guardar Producto", weight="bold"),
                                      on_click=guardar_prod_click, width=float("inf"), height=45),
                            ft.Button(content=ft.Text("← Volver", color="#94A3B8"),
                                      on_click=lambda e: navegar_a("/almacen"), width=float("inf"))
                        ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
                    ],
                    bgcolor=COLOR_FONDO
                )

            lbl_msg_inv = ft.Text("", size=12)

            def exportar_y_avisar(e):
                ruta = exportar_inventario_excel()
                lbl_msg_inv.value = f"📁 Guardado en: {ruta}"
                lbl_msg_inv.color = COLOR_ACCENTO
                page.update()

            def sincronizar_excel_click(e):
                exito, mensaje = importar_inventario_excel()
                lbl_msg_inv.value = mensaje
                lbl_msg_inv.color = "green" if exito else "red"
                navegar_a("/almacen")

            def vaciar_todo_click(e):
                vaciar_inventario_db()
                lbl_msg_inv.value = "⚠️ Inventario vaciado."
                lbl_msg_inv.color = "orange"
                navegar_a("/almacen")

            items_inventario = obtener_inventario_db()
            filas_tabla = []

            for sku, desc, cat, stock, min_val, costo in items_inventario:
                estado = "✅ OK" if stock >= min_val else "⚠️ REPOSICIÓN"
                color_estado = "green" if stock >= min_val else "red"
                total_val = stock * costo

                def hacer_borrado(s=sku):
                    eliminar_producto_inventario_db(s)
                    navegar_a("/almacen")

                filas_tabla.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(sku, size=11, color=COLOR_TEXTO)),
                        ft.DataCell(ft.Text(desc, size=11, color=COLOR_TEXTO)),
                        ft.DataCell(ft.Text(str(stock), size=11, color=COLOR_TEXTO)),
                        ft.DataCell(ft.Text(f"{total_val:.2f} €", size=11, color=COLOR_TEXTO)),
                        ft.DataCell(ft.Text(estado, size=11, color=color_estado, weight="bold")),
                        ft.DataCell(ft.Button(content=ft.Text("❌", color="#F87171"),
                                              on_click=lambda e, s=sku: hacer_borrado(s)))
                    ])
                )

            tabla_stock = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("SKU", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("Producto", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("Stock", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("Valor", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("Estado", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("Borrar", size=11, weight="bold")),
                ],
                rows=filas_tabla,
                heading_row_color="#334155",
            )

            return ft.View(
                route="/almacen",
                controls=[
                    ft.Column([
                        ft.Text("Inventario", size=24, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                        lbl_msg_inv,
                        ft.Row([tabla_stock], scroll=ft.ScrollMode.ALWAYS),
                        ft.Container(height=10),
                        ft.ResponsiveRow([
                            ft.Column([ft.Button(content=ft.Text("➕ Añadir", color="#4ADE80", weight="bold"),
                                                 on_click=lambda e: navegar_a("/almacen/nuevo"), width=float("inf"), bgcolor="#064E3B")], col={"xs": 6, "sm": 3}),
                            ft.Column([ft.Button(content=ft.Text("📤 Exportar", color=COLOR_ACCENTO, weight="bold"),
                                                 on_click=exportar_y_avisar, width=float("inf"), bgcolor="#1E293B")], col={"xs": 6, "sm": 3}),
                            ft.Column([ft.Button(content=ft.Text("📥 Sinc", color="#4ADE80", weight="bold"),
                                                 on_click=sincronizar_excel_click, width=float("inf"), bgcolor="#064E3B")], col={"xs": 6, "sm": 3}),
                            ft.Column([ft.Button(content=ft.Text("🗑️ Vaciar", color="#F87171", weight="bold"),
                                                 on_click=vaciar_todo_click, width=float("inf"), bgcolor="#7F1D1D")], col={"xs": 6, "sm": 3}),
                        ]),
                        ft.Button(content=ft.Text("← Volver al Menú", color="#94A3B8"),
                                  on_click=lambda e: navegar_a("/"), width=float("inf"))
                    ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                ],
                bgcolor=COLOR_FONDO
            )

        elif route == "/clientes":
            in_nombre = ft.TextField(label="Nombre / Empresa", border_color=COLOR_ACCENTO, width=460)
            in_cif = ft.TextField(label="CIF / NIF", border_color=COLOR_ACCENTO, width=460)
            in_dir = ft.TextField(label="Dirección", border_color=COLOR_ACCENTO, width=460)

            rg_tipo_contacto = ft.RadioGroup(content=ft.Row([
                ft.Radio(value="cliente", label="Cliente"),
                ft.Radio(value="proveedor", label="Proveedor")
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=20), value="cliente")

            lbl_cli_msg = ft.Text("", size=13)

            def guardar_contacto_click(e):
                if in_nombre.value and in_cif.value:
                    es_p = 1 if rg_tipo_contacto.value == "proveedor" else 0
                    if guardar_contacto_db(in_nombre.value.strip(), in_cif.value.strip(), in_dir.value.strip(), es_p):
                        lbl_cli_msg.value = "✅ Guardado correctamente."
                        lbl_cli_msg.color = "green"
                        in_nombre.value = ""
                        in_cif.value = ""
                        in_dir.value = ""
                        navegar_a("/clientes")
                    else:
                        lbl_cli_msg.value = "⚠️ Ya existe un contacto con ese nombre."
                        lbl_cli_msg.color = "red"
                else:
                    lbl_cli_msg.value = "⚠️ Rellena Nombre y CIF."
                    lbl_cli_msg.color = "orange"
                page.update()

            contactos_db = obtener_contactos_db()
            filas_contactos = []
            for c_id, nom, cif_val, direc, es_prov in contactos_db:
                tipo_str = "Proveedor" if es_prov == 1 else "Cliente"
                color_tag = "#38BDF8" if es_prov == 1 else "#4ADE80"

                def borrar_contacto(id_c=c_id):
                    eliminar_contacto_db(id_c)
                    navegar_a("/clientes")

                filas_contactos.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(nom, size=11, color=COLOR_TEXTO)),
                        ft.DataCell(ft.Text(cif_val, size=11, color=COLOR_TEXTO)),
                        ft.DataCell(ft.Text(tipo_str, size=11, color=color_tag, weight="bold")),
                        ft.DataCell(ft.Button(content=ft.Text("❌", color="#F87171"),
                                              on_click=lambda e, id_c=c_id: borrar_contacto(id_c)))
                    ])
                )

            tabla_contactos = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Nombre", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("CIF", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("Tipo", size=11, weight="bold")),
                    ft.DataColumn(ft.Text("Borrar", size=11, weight="bold")),
                ],
                rows=filas_contactos,
                heading_row_color="#334155",
            )

            return ft.View(
                route="/clientes",
                controls=[
                    wrap_responsive(ft.Column([
                        ft.Text("Gestión de Contactos", size=24, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                        in_nombre, in_cif, in_dir,
                        rg_tipo_contacto, lbl_cli_msg,
                        ft.Button(content=ft.Text("Guardar Contacto", weight="bold"),
                                  on_click=guardar_contacto_click, width=float("inf"), height=45),
                        ft.Container(height=10),
                        ft.Text("Directorio Existente", size=16, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                        ft.Row([tabla_contactos], scroll=ft.ScrollMode.ALWAYS),
                        ft.Button(content=ft.Text("← Volver al Menú", color="#94A3B8"),
                                  on_click=lambda e: navegar_a("/"), width=float("inf"))
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10))
                ],
                bgcolor=COLOR_FONDO
            )

        elif route == "/gastos":
            ing, gas, iva_rep, iva_sop, ing_pend = cargar_totales_db()
            dif = ing - gas
            color_dif = "#4ADE80" if dif >= 0 else "#F87171"
            signo_dif = "+" if dif >= 0 else ""

            anio_actual = datetime.now().year
            trim_actual = obtener_trimestre_actual()

            dd_trimestre = ft.Dropdown(
                label="Trimestre Fiscal",
                value=str(trim_actual),
                options=[
                    ft.dropdown.Option("1", "1T (Ene - Mar)"),
                    ft.dropdown.Option("2", "2T (Abr - Jun)"),
                    ft.dropdown.Option("3", "3T (Jul - Sep)"),
                    ft.dropdown.Option("4", "4T (Oct - Dic)"),
                ],
                width=220,
                border_color=COLOR_ACCENTO
            )

            dd_anio = ft.Dropdown(
                label="Año Fiscal",
                value=str(anio_actual),
                options=[
                    ft.dropdown.Option(str(anio_actual)),
                    ft.dropdown.Option(str(anio_actual - 1)),
                ],
                width=220,
                border_color=COLOR_ACCENTO
            )

            lbl_gestoria_status = ft.Text("", size=12, color=COLOR_ACCENTO)

            def exportar_gestoria_excel_click(e):
                t = int(dd_trimestre.value)
                a = int(dd_anio.value)
                ruta = exportar_informe_gestoria_excel(a, t)
                lbl_gestoria_status.value = f"📊 Excel Gestoría generado en: {ruta}"
                page.update()

            def exportar_gestoria_html_click(e):
                t = int(dd_trimestre.value)
                a = int(dd_anio.value)
                ruta = exportar_informe_gestoria_html(a, t)
                lbl_gestoria_status.value = f"📄 Informe Gestoría generado en: {ruta}"
                page.update()

            return ft.View(
                route="/gastos",
                controls=[
                    wrap_responsive(ft.Column([
                        ft.Text("Balance y Cierre Gestoría", size=26, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                        ft.Container(height=5),
                        ft.ResponsiveRow([
                            ft.Column([ft.Container(content=ft.Column([ft.Text("COBRADO", size=10), ft.Text(f"+{ing:,.2f}€", size=14, color="#4ADE80", weight="bold")]), padding=10, bgcolor="#064E3B", border_radius=8)], col={"xs": 12, "sm": 4}),
                            ft.Column([ft.Container(content=ft.Column([ft.Text("PENDIENTE", size=10), ft.Text(f"+{ing_pend:,.2f}€", size=14, color="#FB923C", weight="bold")]), padding=10, bgcolor="#7C2D12", border_radius=8)], col={"xs": 12, "sm": 4}),
                            ft.Column([ft.Container(content=ft.Column([ft.Text("GASTOS", size=10), ft.Text(f"-{gas:,.2f}€", size=14, color="#F87171", weight="bold")]), padding=10, bgcolor="#7F1D1D", border_radius=8)], col={"xs": 12, "sm": 4}),
                        ], spacing=10),
                        ft.Container(height=5),
                        ft.ResponsiveRow([
                            ft.Column([ft.Container(content=ft.Column([ft.Text("RENDIMIENTO NETO REAL", size=10), ft.Text(f"{signo_dif}{dif:,.2f}€", size=14, color=color_dif, weight="bold")]), padding=10, bgcolor="#1E293B", border_radius=8)], col={"xs": 12, "sm": 12}),
                        ]),
                        ft.Container(height=10),
                        ft.Text("📋 Exportación Trimestral para Asesoría / AEAT", size=14, weight=ft.FontWeight.BOLD, color=COLOR_ACCENTO),
                        ft.Row([dd_trimestre, dd_anio], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.ResponsiveRow([
                            ft.Column([ft.Button(content=ft.Text("📊 Exportar Excel (.xlsx)", color="#4ADE80", weight="bold"), on_click=exportar_gestoria_excel_click, bgcolor="#064E3B", width=float("inf"))], col={"xs": 12, "sm": 6}),
                            ft.Column([ft.Button(content=ft.Text("📄 Informe Imprimible (HTML)", color=COLOR_ACCENTO, weight="bold"), on_click=exportar_gestoria_html_click, bgcolor="#1E293B", width=float("inf"))], col={"xs": 12, "sm": 6}),
                        ], spacing=8),
                        lbl_gestoria_status,
                        ft.Container(height=15),
                        ft.Button(content=ft.Text("← Volver al Menú", color="#94A3B8"),
                                  on_click=lambda e: navegar_a("/"), width=float("inf"))
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER))
                ],
                bgcolor=COLOR_FONDO
            )

        return ft.View(route="/", controls=[ft.Text("Página no encontrada", color="white")])

    def view_pop(view):
        try:
            if len(page.views) > 1:
                page.views.pop()
                top_view = page.views[-1]
                navegar_a(top_view.route)
        except Exception:
            pass

    page.on_view_pop = view_pop

    try:
        page.views.clear()
        page.views.append(crear_vista("/"))
        page.update()
    except Exception:
        pass


if __name__ == "__main__":
    ft.app(main)
