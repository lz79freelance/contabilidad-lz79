"""
almacenamiento.py
-----------------
Gestión de rutas de datos y plantillas, compatible con entorno local y empaquetado.
"""

import os
import sys
import webbrowser


def get_ruta_datos() -> str:
    """Devuelve el directorio base para guardar la base de datos y archivos."""
    ruta_env = os.getenv("FLET_APP_STORAGE_DATA")
    if ruta_env and os.path.exists(ruta_env):
        return ruta_env

    # Ruta por defecto: el directorio actual de la aplicación
    ruta_base = os.path.dirname(os.path.abspath(__file__))
    return ruta_base


def get_ruta_plantillas() -> str:
    """Devuelve la ruta donde se guardan los HTML generados, creándola si no existe."""
    ruta = os.path.join(get_ruta_datos(), "documentos_generados")
    os.makedirs(ruta, exist_ok=True)
    return ruta


def abrir_archivo_si_escritorio(ruta_archivo: str):
    """Abre el archivo en el navegador del sistema si no es móvil."""
    try:
        webbrowser.open(f"file://{os.path.abspath(ruta_archivo)}")
    except Exception:
        pass
