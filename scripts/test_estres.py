import argparse
import json
import socket
import statistics
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta


def http_json(method, url, timeout, payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8") if hasattr(resp, "read") else ""
        body = json.loads(raw) if raw else None
        return resp.status, body


def normalize_error(exc):
    if isinstance(exc, TimeoutError) or isinstance(exc, socket.timeout):
        return "timeout"
    if isinstance(exc, urllib.error.URLError) and "timed out" in str(exc).lower():
        return "timeout"
    return str(exc)


def resolver_payload_disponibilidad(base_url, timeout):
    try:
        status, negocios = http_json("GET", f"{base_url}/negocios/?lat=40.4168&lon=-3.7038", timeout)
    except Exception as exc:
        raise RuntimeError(f"No se pudo consultar /negocios/ ({normalize_error(exc)})") from exc

    if status != 200 or not negocios:
        raise RuntimeError("No se pudo obtener un negocio válido para la prueba de disponibilidad")

    negocio_id = negocios[0]["id"]

    try:
        status, servicios = http_json("GET", f"{base_url}/negocios/{negocio_id}/servicios", timeout)
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo consultar /negocios/{negocio_id}/servicios ({normalize_error(exc)})"
        ) from exc

    if status != 200 or not servicios:
        raise RuntimeError(f"No hay servicios disponibles para el negocio {negocio_id}")

    servicio_id = servicios[0]["id"]

    # Buscar una fecha que devuelva 200 para disponibilidad (evita días cerrados/escenarios inválidos)
    for delta in range(0, 21):
        fecha = (datetime.now() + timedelta(days=delta)).strftime("%Y-%m-%d")
        payload = {"negocio_id": negocio_id, "servicio_id": servicio_id, "fecha": fecha}
        try:
            st, _ = http_json("POST", f"{base_url}/disponibilidad", timeout, payload)
            if st == 200:
                return payload
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue

    # Fallback: devuelve el payload con fecha de hoy para que, al menos, el error sea explícito.
    return {
        "negocio_id": negocio_id,
        "servicio_id": servicio_id,
        "fecha": datetime.now().strftime("%Y-%m-%d"),
    }


def worker(method, url, json_payload, timeout, results, index):
    inicio = time.perf_counter()
    status = None
    ok = False
    error = None

    try:
        if method == "GET":
            req = urllib.request.Request(url=url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                ok = 200 <= status < 400
        else:
            data = json.dumps(json_payload).encode("utf-8")
            req = urllib.request.Request(
                url=url,
                data=data,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                ok = 200 <= status < 400
    except urllib.error.HTTPError as exc:
        status = exc.code
        ok = False
    except urllib.error.URLError as exc:
        error = normalize_error(exc)
    except Exception as exc:
        error = normalize_error(exc)
    finally:
        duracion_ms = (time.perf_counter() - inicio) * 1000
        results[index] = {
            "ok": ok,
            "status": status,
            "error": error,
            "ms": duracion_ms,
        }


def percentile(values, p):
    if not values:
        return 0.0
    values_sorted = sorted(values)
    k = int(round((p / 100) * (len(values_sorted) - 1)))
    return values_sorted[k]


def main():
    parser = argparse.ArgumentParser(description="Prueba de carga simple para SectorMindAI")
    parser.add_argument("--base-url", default="http://localhost:5000", help="Base URL del backend")
    parser.add_argument(
        "--target",
        choices=["negocios", "disponibilidad"],
        default="negocios",
        help="Endpoint objetivo",
    )
    parser.add_argument("--concurrency", type=int, default=50, help="Peticiones simultáneas")
    parser.add_argument("--timeout", type=float, default=10.0, help="Timeout por petición (segundos)")
    parser.add_argument("--negocio-id", type=int, default=None, help="Negocio para disponibilidad")
    parser.add_argument("--servicio-id", type=int, default=None, help="Servicio para disponibilidad")
    parser.add_argument("--fecha", default=None, help="Fecha YYYY-MM-DD para disponibilidad")
    args = parser.parse_args()

    if args.target == "negocios":
        method = "GET"
        url = f"{args.base_url}/negocios/?lat=40.4168&lon=-3.7038"
        payload = None
    else:
        method = "POST"
        url = f"{args.base_url}/disponibilidad"
        if args.negocio_id and args.servicio_id:
            payload = {
                "negocio_id": args.negocio_id,
                "servicio_id": args.servicio_id,
                "fecha": args.fecha or datetime.now().strftime("%Y-%m-%d"),
            }
        else:
            try:
                payload = resolver_payload_disponibilidad(args.base_url, args.timeout)
            except Exception as exc:
                print("=== PRUEBA DE CARGA ===")
                print(f"Target: {args.target}")
                print(f"URL: {url}")
                print(f"Concurrencia: {args.concurrency}")
                print(f"Error de preparación: {exc}")
                print("Tip: pasa --negocio-id y --servicio-id manualmente, o carga datos en la BD.")
                return

    print("=== PRUEBA DE CARGA ===")
    print(f"Target: {args.target}")
    print(f"URL: {url}")
    print(f"Concurrencia: {args.concurrency}")
    if payload is not None:
        print(f"Payload: {payload}")

    results = [None] * args.concurrency
    threads = []
    inicio_total = time.perf_counter()
    for i in range(args.concurrency):
        t = threading.Thread(
            target=worker,
            args=(method, url, payload, args.timeout, results, i),
            daemon=True,
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    total_ms = (time.perf_counter() - inicio_total) * 1000

    latencias = [r["ms"] for r in results if r is not None]
    ok_count = sum(1 for r in results if r and r["ok"])
    err_count = len(results) - ok_count

    status_count = {}
    for r in results:
        if not r:
            continue
        key = r["status"] if r["status"] is not None else "EXC"
        status_count[key] = status_count.get(key, 0) + 1

    print("\n=== RESULTADOS ===")
    print(f"Peticiones totales: {len(results)}")
    print(f"Exitosas: {ok_count}")
    print(f"Con error: {err_count}")
    print(f"Tiempo total prueba: {total_ms:.2f} ms")
    if latencias:
        print(f"Latencia media: {statistics.mean(latencias):.2f} ms")
        print(f"Latencia mediana (p50): {statistics.median(latencias):.2f} ms")
        print(f"Latencia p95: {percentile(latencias, 95):.2f} ms")
        print(f"Latencia max: {max(latencias):.2f} ms")

    print("\nHTTP status / excepciones:")
    for k, v in sorted(status_count.items(), key=lambda x: str(x[0])):
        print(f"  {k}: {v}")

    error_count = {}
    for r in results:
        if not r or not r.get("error"):
            continue
        err = r["error"]
        error_count[err] = error_count.get(err, 0) + 1

    if error_count:
        print("\nErrores (detalle):")
        for k, v in sorted(error_count.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {k}: {v}")

    if ok_count == 0 and error_count.get("timeout"):
        print("\nSugerencia: aumenta --timeout (por ejemplo 30) o reduce --concurrency.")


if __name__ == "__main__":
    main()
