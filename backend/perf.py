import time
from functools import wraps

from flask import request


def medir_tiempo(label=None):
    """Imprime en consola la latencia de un endpoint Flask en milisegundos."""

    def decorador(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            inicio = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duracion_ms = (time.perf_counter() - inicio) * 1000
                nombre = label or request.path or func.__name__
                print(f"[PERF] {nombre} tardó: {duracion_ms:.2f} ms")

        return wrapper

    return decorador
