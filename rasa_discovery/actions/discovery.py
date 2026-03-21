"""
Acciones para el bot de descubrimiento.
Usa exclusivamente coordenadas precisas del dispositivo (lat/lon).
"""

import os
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import requests
from fuzzywuzzy import fuzz, process
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

API_URL = os.getenv("API_URL", "http://backend:5000")

TIPO_KEYWORDS = {
    "peluqueria": ["pelo", "pelar", "pelu", "peluque", "cortar", "corte", "barber", "afeit"],
    "dentista": ["dent", "odonto", "muela", "diente", "ortodo", "boca", "limpieza dental"],
    "fisioterapia": ["fisio", "masaje", "lesion", "dolor", "rehabilita", "terapeut"],
}


class ActionDiscoveryBuscarNegocios(Action):
    def name(self) -> str:
        return "action_discovery_buscar_negocios"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        try:
            intent = tracker.get_intent_of_latest_message()
            mensaje = (tracker.latest_message.get("text") or "").lower().strip()
            meta = tracker.latest_message.get("metadata") or {}

            opciones_negocio = tracker.get_slot("opciones_negocio")
            lat = self._safe_float(meta.get("ubicacion_lat"))
            lon = self._safe_float(meta.get("ubicacion_lon"))
            precision_m = self._safe_float(meta.get("ubicacion_precision_m"))
            slot_lat = self._safe_float(tracker.get_slot("ubicacion_lat"))
            slot_lon = self._safe_float(tracker.get_slot("ubicacion_lon"))
            slot_precision = self._safe_float(tracker.get_slot("ubicacion_precision_m"))

            if lat is None or lon is None:
                lat = slot_lat
                lon = slot_lon
                precision_m = slot_precision

            # Flujo de selección por número/nombre cuando ya se listaron opciones
            if opciones_negocio and isinstance(opciones_negocio, list):
                seleccionado_id = self._resolver_opcion_negocio(mensaje, opciones_negocio)
                if seleccionado_id is not None:
                    dispatcher.utter_message(text=f"[REDIRECT:detalle.html?id={seleccionado_id}]")
                    return [
                        SlotSet("opciones_negocio", None),
                        SlotSet("ubicacion_lat", lat),
                        SlotSet("ubicacion_lon", lon),
                        SlotSet("ubicacion_precision_m", precision_m),
                    ]

                dispatcher.utter_message(
                    text="👉 DI EL NÚMERO (1, 2, 3, 4, 5...) o el nombre del negocio que quieres."
                )
                return []

            # Mensajes de entrada/saludo
            if intent == "greet" or self._es_saludo_simple(mensaje) or self._es_saludo_fuzzy(mensaje):
                if lat is None or lon is None:
                    dispatcher.utter_message(
                        text=(
                            "📍 Para recomendar negocios cercanos necesito tu ubicación precisa del dispositivo. "
                            "Pulsa **Usar ubicación precisa** y vuelve a pedirme un tipo de negocio."
                        )
                    )
                else:
                    dispatcher.utter_message(
                        text="¡Hola! ¿Qué necesitas hoy? (**peluquería**, **dentista**, **fisio**...)."
                    )
                return [
                    SlotSet("ubicacion_lat", lat),
                    SlotSet("ubicacion_lon", lon),
                    SlotSet("ubicacion_precision_m", precision_m),
                    SlotSet("opciones_negocio", None),
                ]

            # Sin coordenadas no se puede continuar
            if lat is None or lon is None:
                geodisponible = meta.get("geolocalizacion_disponible")
                if geodisponible is False:
                    dispatcher.utter_message(
                        text=(
                            "⚠️ Este dispositivo no expone geolocalización. "
                            "Sin coordenadas precisas no puedo ordenar por cercanía."
                        )
                    )
                else:
                    dispatcher.utter_message(
                        text=(
                            "📍 No tengo tu ubicación precisa todavía. "
                            "Pulsa **Usar ubicación precisa** y te muestro negocios cercanos."
                        )
                    )
                return [
                    SlotSet("ubicacion_lat", None),
                    SlotSet("ubicacion_lon", None),
                    SlotSet("ubicacion_precision_m", None),
                    SlotSet("opciones_negocio", None),
                ]

            tipo_detectado = self._detectar_tipo_negocio(mensaje)
            busca_hoy = any(
                palabra in mensaje
                for palabra in ["hoy", "ahora", "disponible", "hueco", "cita", "urgente", "urgencia", "pronto"]
            )
            busca_manana = any(palabra in mensaje for palabra in ["mañana", "manana", "tomorrow"])

            try:
                negocios = self._fetch_negocios((lat, lon))
            except Exception:
                dispatcher.utter_message(
                    text="⚠️ No pude conectarme al buscador ahora mismo. Inténtalo de nuevo en unos segundos."
                )
                return []

            negocios = self._filtrar_por_distancia(negocios, max_km=50)
            if tipo_detectado:
                negocios = [n for n in negocios if self._match_tipo(n.get("tipo_negocio"), tipo_detectado)]

            if not negocios:
                if tipo_detectado:
                    dispatcher.utter_message(
                        text=f"🔎 No encontré negocios de tipo **{tipo_detectado}** cerca de tu ubicación actual."
                    )
                else:
                    dispatcher.utter_message(text="🔎 No encontré negocios cerca de tu ubicación actual.")
                return [
                    SlotSet("ubicacion_lat", lat),
                    SlotSet("ubicacion_lon", lon),
                    SlotSet("ubicacion_precision_m", precision_m),
                    SlotSet("opciones_negocio", None),
                ]

            if busca_manana:
                negocios, detalles = self._filtrar_con_hueco_manana(negocios)
            elif busca_hoy:
                negocios, detalles = self._filtrar_con_hueco_hoy(negocios)
            else:
                detalles = {}

            if not negocios:
                if busca_manana:
                    dispatcher.utter_message(text="⏱️ No hay huecos mañana en tu zona. ¿Quieres ver todos los negocios disponibles?")
                elif busca_hoy:
                    dispatcher.utter_message(text="⏱️ No hay huecos hoy en tu zona. Puedo buscar mañana si lo prefieres.")
                return [
                    SlotSet("ubicacion_lat", lat),
                    SlotSet("ubicacion_lon", lon),
                    SlotSet("ubicacion_precision_m", precision_m),
                    SlotSet("opciones_negocio", None),
                ]

            max_items = self._extraer_limite_resultados(mensaje)
            mensaje_respuesta = self._formatear_respuesta(
                negocios[:max_items], detalles, busca_hoy or busca_manana, tipo_detectado, precision_m
            )
            lista_opciones = [{"id": n.get("id"), "nombre": n.get("nombre", "Negocio")} for n in negocios[:max_items]]

            dispatcher.utter_message(text=mensaje_respuesta)
            return [
                SlotSet("ubicacion_lat", lat),
                SlotSet("ubicacion_lon", lon),
                SlotSet("ubicacion_precision_m", precision_m),
                SlotSet("opciones_negocio", lista_opciones),
            ]

        except Exception as e:
            print(f"❌ Error en action_discovery_buscar_negocios: {e}")
            dispatcher.utter_message(
                text="⚠️ Hubo un problema al buscar negocios cercanos. Inténtalo de nuevo."
            )
            return [SlotSet("opciones_negocio", None)]

    def _safe_float(self, value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _resolver_opcion_negocio(self, mensaje: str, opciones_negocio: List[Dict[str, Any]]) -> Optional[int]:
        numero_detectado = self._extraer_numero(mensaje)
        if numero_detectado is not None:
            idx = numero_detectado - 1
            if 0 <= idx < len(opciones_negocio):
                return opciones_negocio[idx].get("id")

        mensaje_norm = self._norm_text(mensaje)
        if not mensaje_norm:
            return None

        best_score = 0
        best_id = None
        for opcion in opciones_negocio:
            nombre_norm = self._norm_text(opcion.get("nombre") or "")
            if not nombre_norm:
                continue
            if nombre_norm in mensaje_norm:
                return opcion.get("id")
            score = fuzz.token_set_ratio(mensaje_norm, nombre_norm)
            if score > best_score:
                best_score = score
                best_id = opcion.get("id")

        if best_id is not None and best_score >= 80:
            return best_id
        return None

    def _norm_text(self, value: str) -> str:
        if not value:
            return ""
        value = value.lower()
        value = unicodedata.normalize("NFD", value)
        value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
        value = re.sub(r"[^a-z0-9\s]", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    def _detectar_tipo_negocio(self, mensaje: str) -> Optional[str]:
        try:
            tipos = self._obtener_tipos_bd()
        except Exception:
            tipos = []

        if not tipos:
            tipos = list(TIPO_KEYWORDS.keys())

        try:
            best = process.extractOne(mensaje, tipos, scorer=fuzz.token_set_ratio)
            if best and best[1] >= 75:
                return best[0]
        except Exception:
            pass

        for tipo, keywords in TIPO_KEYWORDS.items():
            for kw in keywords:
                if kw in mensaje:
                    return tipo
        return None

    def _match_tipo(self, tipo_negocio: Optional[str], tipo_detectado: str) -> bool:
        a = (tipo_negocio or "").lower().strip()
        b = (tipo_detectado or "").lower().strip()
        if not a or not b:
            return False
        if a == b or b in a or a in b:
            return True
        try:
            return fuzz.token_set_ratio(a, b) >= 70
        except Exception:
            return False

    def _extraer_numero(self, texto: str) -> Optional[int]:
        texto_lower = texto.lower()
        match = re.search(r"\b(\d{1,2})\b", texto_lower)
        if match:
            try:
                num = int(match.group(1))
                if 1 <= num <= 10:
                    return num
            except ValueError:
                pass

        palabras_a_numero = {
            "uno": 1,
            "una": 1,
            "dos": 2,
            "tres": 3,
            "cuatro": 4,
            "cinco": 5,
            "seis": 6,
            "siete": 7,
            "ocho": 8,
            "nueve": 9,
            "diez": 10,
            "primero": 1,
            "primera": 1,
            "primer": 1,
            "segundo": 2,
            "segunda": 2,
            "tercero": 3,
            "tercera": 3,
            "tercer": 3,
            "cuarto": 4,
            "cuarta": 4,
            "quinto": 5,
            "quinta": 5,
        }
        for palabra, numero in palabras_a_numero.items():
            if re.search(r"\b" + re.escape(palabra) + r"\b", texto_lower):
                return numero
        return None

    def _extraer_limite_resultados(self, mensaje: str) -> int:
        max_items = 5
        dig = re.search(r"\b(\d{1,2})\b", mensaje)
        if dig:
            try:
                solicitado = int(dig.group(1))
                if solicitado >= 1:
                    return min(solicitado, 5)
            except Exception:
                pass

        palabras_num = {"uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5}
        patron = r"\b(" + "|".join(palabras_num.keys()) + r")\b"
        match = re.search(patron, mensaje)
        if match:
            max_items = min(palabras_num[match.group(1)], 5)
        return max_items

    def _obtener_tipos_bd(self) -> List[str]:
        res = requests.get(f"{API_URL}/negocios/", timeout=8)
        res.raise_for_status()
        data = res.json() or []
        tipos = {(n.get("tipo_negocio") or "").lower().strip() for n in data}
        return [t for t in tipos if t]

    def _es_saludo_simple(self, mensaje: str) -> bool:
        if not mensaje:
            return False
        norm = mensaje.strip().lower()
        saludos = [
            "hola",
            "holi",
            "buenas",
            "buenos dias",
            "buenos días",
            "buenas tardes",
            "buenas noches",
            "hey",
            "que tal",
            "qué tal",
        ]
        return any(norm == s or norm.startswith(f"{s} ") for s in saludos)

    def _es_saludo_fuzzy(self, mensaje: str) -> bool:
        if not mensaje:
            return False
        norm = mensaje.strip().lower()
        saludos = ["hola", "holaa", "holi", "buenas", "hey"]
        try:
            return any(fuzz.partial_ratio(norm, s) >= 85 for s in saludos)
        except Exception:
            return False

    def _fetch_negocios(self, lat_lon: Optional[Tuple[float, float]] = None) -> List[Dict[str, Any]]:
        params = {}
        if lat_lon:
            params = {"lat": lat_lon[0], "lon": lat_lon[1]}
        res = requests.get(f"{API_URL}/negocios/", params=params, timeout=8)
        res.raise_for_status()
        return res.json()

    def _filtrar_con_hueco_hoy(
        self, negocios: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
        ahora = self._now_local()
        fecha = ahora.strftime("%Y-%m-%d")
        con_hueco = []
        detalles: Dict[int, Dict[str, Any]] = {}
        for negocio in negocios:
            servicios = self._fetch_servicios(negocio["id"])
            for servicio in servicios:
                dispo = self._fetch_disponibilidad(negocio["id"], servicio["id"], fecha)
                slots = dispo.get("disponibles", []) if dispo else []
                if not slots:
                    continue

                slot_dt_valida = None
                slot_texto_valido = None
                for slot in slots:
                    slot_dt = self._parse_slot_time(slot)
                    if slot_dt and slot_dt >= ahora:
                        slot_dt_valida = slot_dt
                        slot_texto_valido = slot
                        break

                if not slot_dt_valida and slots:
                    slot_texto_valido = slots[0]
                    slot_dt_valida = self._parse_slot_time(slot_texto_valido)

                if slot_texto_valido:
                    con_hueco.append(negocio)
                    detalles[negocio["id"]] = {
                        "servicio": servicio.get("nombre"),
                        "slot": slot_texto_valido,
                        "slot_dt": slot_dt_valida,
                    }
                    break

        con_hueco.sort(
            key=lambda n: (
                detalles.get(n["id"], {}).get("slot_dt") or datetime.max,
                n.get("distancia_km") or 1e9,
            )
        )
        return con_hueco, detalles

    def _filtrar_con_hueco_manana(
        self, negocios: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
        ahora = self._now_local()
        manana = ahora + timedelta(days=1)
        fecha = manana.strftime("%Y-%m-%d")
        con_hueco = []
        detalles: Dict[int, Dict[str, Any]] = {}
        for negocio in negocios:
            servicios = self._fetch_servicios(negocio["id"])
            for servicio in servicios:
                dispo = self._fetch_disponibilidad(negocio["id"], servicio["id"], fecha)
                slots = dispo.get("disponibles", []) if dispo else []
                if not slots:
                    continue

                slot_texto_valido = slots[0]
                slot_dt_valida = self._parse_slot_time(slot_texto_valido)

                con_hueco.append(negocio)
                detalles[negocio["id"]] = {
                    "servicio": servicio.get("nombre"),
                    "slot": slot_texto_valido,
                    "slot_dt": slot_dt_valida,
                }
                break

        con_hueco.sort(
            key=lambda n: (
                detalles.get(n["id"], {}).get("slot_dt") or datetime.max,
                n.get("distancia_km") or 1e9,
            )
        )
        return con_hueco, detalles

    def _fetch_servicios(self, negocio_id: int) -> List[Dict[str, Any]]:
        res = requests.get(f"{API_URL}/negocios/{negocio_id}/servicios", timeout=8)
        if res.status_code != 200:
            return []
        return res.json()

    def _fetch_disponibilidad(self, negocio_id: int, servicio_id: int, fecha: str) -> Optional[Dict[str, Any]]:
        try:
            res = requests.post(
                f"{API_URL}/disponibilidad",
                json={"negocio_id": negocio_id, "servicio_id": servicio_id, "fecha": fecha},
                timeout=8,
            )
            if res.status_code != 200:
                return None
            return res.json()
        except Exception:
            return None

    def _formatear_respuesta(
        self,
        negocios: List[Dict[str, Any]],
        detalles: Dict[int, Dict[str, Any]],
        busca_hoy: bool,
        tipo_detectado: Optional[str] = None,
        precision_m: Optional[float] = None,
    ) -> str:
        tipo_str = f" de **{tipo_detectado}**" if tipo_detectado else ""
        precision_txt = f" (precisión aprox. ±{int(precision_m)}m)" if precision_m is not None else ""
        intro = (
            f"⏱️ Disponibilidad hoy{tipo_str}{precision_txt}:"
            if busca_hoy
            else f"🔎 Negocios{tipo_str} cerca de ti{precision_txt}:"
        )

        lineas = []
        for idx, n in enumerate(negocios, start=1):
            distancia = n.get("distancia_km")
            etiqueta_dist = f" · 📍 {distancia:.1f} km" if distancia is not None else ""
            tipo_txt = (n.get("tipo_negocio") or "").capitalize()
            icono = self._emoji_tipo(n.get("tipo_negocio"))

            if n.get("foto_base64"):
                foto_html = (
                    f'<img src="{n["foto_base64"]}" alt="{n.get("nombre", "Negocio")}" '
                    'style="max-width:100%; height:120px; object-fit:cover; border-radius:8px; margin-bottom:8px;">'
                )
            else:
                foto_html = (
                    f'<div style="width:100%; height:120px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
                    f'border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:3rem; margin-bottom:8px;">{icono}</div>'
                )

            negocio_id = n.get("id")
            nombre = n.get("nombre", "Negocio")
            linea = f"""[BUSINESS_CARD]
{foto_html}
<div style="font-size:0.95rem; line-height:1.4;">
<span style="font-weight:bold; color:#1e293b;">{idx}. {icono} <a href="detalle.html?id={negocio_id}" style="text-decoration:none; color:#4f46e5; font-weight:bold; cursor:pointer;">{nombre}</a></span> <span style="color:#666; font-size:0.85rem;">({tipo_txt}){etiqueta_dist}</span>"""

            if busca_hoy and n.get("id") in detalles:
                slot = detalles[n["id"]]["slot"]
                hora = slot.split(" ")[1][:5] if " " in slot else slot[-5:]
                servicio = detalles[n["id"]].get("servicio", "servicio")
                linea += f"<br><span style='color:#666; font-size:0.85rem;'>{servicio} a las {hora}</span>"

            linea += "</div>[/BUSINESS_CARD]"
            lineas.append(linea)

        return intro + "\n" + "\n".join(lineas)

    def _filtrar_por_distancia(self, negocios: List[Dict[str, Any]], max_km: float) -> List[Dict[str, Any]]:
        ordenados = list(negocios)
        ordenados.sort(key=lambda n: n.get("distancia_km") if n.get("distancia_km") is not None else 1e9)
        return ordenados

    def _parse_slot_time(self, slot: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(slot)
        except Exception:
            return None

    def _now_local(self) -> datetime:
        tz_name = os.getenv("TZ", "Europe/Madrid")
        try:
            return datetime.now(ZoneInfo(tz_name)).replace(tzinfo=None)
        except Exception:
            return datetime.utcnow() + timedelta(hours=1)

    def _emoji_tipo(self, tipo: Optional[str]) -> str:
        t = (tipo or "").lower()
        if t == "peluqueria":
            return "✂️"
        if t == "dentista":
            return "🦷"
        if t == "fisioterapia":
            return "💪"
        return "🏪"
