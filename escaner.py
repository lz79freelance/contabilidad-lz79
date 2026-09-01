"""
escaner.py
----------
Escaneo de códigos QR y de barras con cámara (OpenCV + pyzbar).
"""

import time


def escanear_qr(callback_resultado):
    """Lanza la captura de vídeo para escanear QR / códigos de barras en escritorio."""
    try:
        import cv2
        from pyzbar import pyzbar
    except ImportError:
        callback_resultado("ERROR_LIB: cv2 o pyzbar no están instalados.")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        callback_resultado("ERROR_CAMARA: No se pudo abrir la cámara.")
        return

    encontrado = False
    while not encontrado:
        ret, frame = cap.read()
        if not ret:
            break

        codigos = pyzbar.decode(frame)
        for codigo in codigos:
            datos = codigo.data.decode("utf-8")
            if datos:
                encontrado = True
                callback_resultado(datos)
                break

        cv2.imshow("Escaneando QR / Codigo de Barras - Pulsa 'q' para salir", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
