# LZ79 Essential — main.py reestructurado

Reescritura del `main.py` que enviaste, dividida en módulos y con los
puntos que comentamos corregidos. Funcionalmente es la misma app:
mismas pantallas, mismos cálculos de IVA/IRPF/recargo, mismo asistente,
mismo diseño. Lo que cambia es la organización del código y estos
puntos concretos:

## Qué se corrigió

1. **Numeración de documentos** (`db.py`): antes se calculaba con
   `COUNT(*)`, así que borrar un movimiento podía hacer que el
   siguiente número se repitiera. Ahora hay una tabla `contadores`
   dedicada que solo incrementa.
2. **Verificación de la cadena de hashes** (`logica.py`,
   `verificar_cadena_movimientos()`): la cadena `hash_anterior` /
   `hash_actual` ya existía en tu código, pero nada la comprobaba.
   Añadí la función y un botón "🔒 Verificar integridad" en la
   pantalla de Historial.
3. **HTML de facturas/albaranes/informes escapado** (`logica.py`):
   `concepto` y `cliente_info` pasan por `html.escape()` antes de
   insertarse en el HTML generado.
4. **Conexión a SQLite centralizada** (`db.py`, `_conexion()`): un
   único context manager en vez de abrir/cerrar conexión en cada
   función.
5. **`print()` de depuración eliminado** del escáner.
6. **Consulta SQL suelta en la UI** (editar producto de inventario):
   ahora usa `db.obtener_producto_por_sku()` en vez de
   `sqlite3.connect` directo dentro de `main.py`.

## Qué se preparó para publicar en Apple / Amazon (pero NO se pudo terminar aquí)

No tengo acceso a internet en este entorno, así que no he podido
instalar Flet ni `flet_qr_scanner` para probar nada de esto en
ejecución. Lo que sí hice fue dejar la estructura lista:

- **`almacenamiento.py`**: centraliza las rutas de datos. Ahora mismo
  usa `FLET_APP_STORAGE_DATA` como variable de entorno de referencia
  para saber si está corriendo empaquetada, pero **no he podido
  confirmar contra la documentación actual de Flet si ese es el
  nombre vigente en tu versión**. Antes de compilar para Apple/Amazon,
  confírmalo tú y ajusta solo esa función si hace falta — el resto del
  proyecto no depende de esto directamente.
- **`escaner.py`**: separé el backend de escritorio (cv2 + pyzbar,
  funcional, sin tocar la lógica) del punto de enganche para
  `flet_qr_scanner` (`escanear_qr_movil`), que dejé como
  `NotImplementedError` con un ejemplo de la forma que probablemente
  tenga la API, pero sin verificar. Es el único sitio que hay que
  completar para que el escaneo funcione en móvil.
- **`exportacion.py`**: ya no hace `webbrowser.open()` a ciegas; en
  builds empaquetadas devuelve la ruta sin intentar abrir nada (habría
  que añadir un diálogo de compartir nativo de Flet ahí, no lo
  implementé porque no pude verificar esa API tampoco).

## Asistente ampliado (sin LLM, sigue siendo por palabras clave)

Se añadieron nuevos comandos a `logica.procesar_consulta_asistente()`,
todos sobre datos reales de tu BD (sin ningún modelo de IA de por
medio, tal y como pediste):

- Saludos (`hola`, `buenas`) y agradecimientos (`gracias`).
- `albaranes` → conteo y total.
- `compras` / `gastos` → conteo y total gastado.
- `clientes` / `proveedores` / `contactos` → directorio (nº de cada tipo).
- `trimestre` → en qué trimestre fiscal estás.
- `mejor cliente` / `ranking` → top 5 clientes por facturación
  acumulada (nueva función `db.obtener_top_clientes()`).

Nota de diseño: `"mejor cliente"` se comprueba **antes** que
`"cliente"` a secas, porque la primera contiene la palabra de la
segunda — si el orden fuera al revés, el bloque de contactos
interceptaría siempre la pregunta por el ranking. Lo até por si tocas
este bloque más adelante y añades más palabras clave: revisa siempre
que una clave nueva no sea substring de otra ya existente, o ponla
antes en la cadena de `if`.

## Estructura de archivos

```
almacenamiento.py   Rutas de datos (escritorio y punto de ajuste para móvil)
db.py                Acceso a SQLite: esquema, contactos, inventario, movimientos
exportacion.py       Exportar/importar inventario en CSV
logica.py            Asistente, generación de HTML, verificación de la cadena de hashes
escaner.py           Escaneo QR/código de barras (escritorio funcionando, móvil pendiente)
main.py              Solo la UI de Flet (vistas y rutas)
requirements.txt
```

## Cómo probarlo

```bash
pip install -r requirements.txt
python main.py
```

Se comprobó que los 6 archivos compilan sin errores de sintaxis
(`python3 -m py_compile`), pero **no se ha podido ejecutar la app**
porque este entorno no tiene acceso a red para instalar Flet. Antes
de darlo por bueno, ejecútalo tú en tu máquina y prueba especialmente
el flujo de facturas/albaranes/compras con el escáner, que es la
parte que más se tocó indirectamente (menos líneas cambiadas, pero es
donde vive el riesgo real).

## Lo que queda pendiente por tu cuenta

- Terminar `escaner.escanear_qr_movil()` con `flet_qr_scanner`.
- Confirmar el nombre de la variable de entorno de almacenamiento de
  Flet en `almacenamiento.py`.
- Decidir cómo compartir/exportar archivos en móvil (diálogo nativo
  de Flet) en vez de abrir con el navegador.
