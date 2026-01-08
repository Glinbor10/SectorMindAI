"""
Acciones para el bot de descubrimiento (búsqueda escalable por tipo dinámico).
"""
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional, Tuple

import requests
from fuzzywuzzy import fuzz, process
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

API_URL = os.getenv("API_URL", "http://backend:5000")

# Palabras clave para identificar tipos de negocio de forma flexible
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
        intent = tracker.get_intent_of_latest_message()
        mensaje = tracker.latest_message.get("text", "").lower().strip()

        # Obtener slots
        slot_ubicacion = tracker.get_slot("ubicacion_texto")
        meta = tracker.latest_message.get("metadata") or {}
        ubicacion_texto = slot_ubicacion or meta.get("ubicacion_texto")
        ubicacion_actual = ubicacion_texto

        # Heurística rápida: pueblo/ciudad corta sin ubicación previa
        if not ubicacion_actual and mensaje and len(mensaje.split()) <= 3 and intent not in ["afirmar", "negar"]:
            try:
                posible = self._geocodificar(mensaje)
                if posible:
                    dispatcher.utter_message(
                        text=f"📍 Ubicación guardada: {mensaje.title()}. Ahora dime qué necesitas (peluquería, dentista, fisio...) y busco cerca."
                    )
                    return [SlotSet("ubicacion_texto", mensaje)]
            except Exception:
                pass

        # Captura explícita de ubicación: mostrar mapa pero guardar directo (sin confirmación)
        if intent == "informar_ubicacion":
            full_text = tracker.latest_message.get("text", "").strip()
            if full_text:
                geo = self._geocodificar_detallado(full_text)
                if geo:
                    # Si el texto original es diferente del display de Nominatim, mostrar ambos
                    display_completo = full_text if full_text.lower() != geo['display'].lower() else geo['display']
                    dispatcher.utter_message(
                        text=(
                            f"📍 Ubicación guardada: **{display_completo}**\n"
                            f"🗺️ Vista previa: {geo['display']}\n"
                            f"[MAP:{geo['lat']},{geo['lon']}]\n"
                            "Ahora dime qué necesitas (**peluquería**, **dentista**, **fisio**, etc.)."
                        )
                    )
                    return [SlotSet("ubicacion_texto", full_text)]
                dispatcher.utter_message(
                    text="❌ No pude localizar esa **dirección**. Prueba con **calle**, **número** y **ciudad**."
                )
                return []
            return []

        # Si busca negocio pero no hay ubicación
        if not ubicacion_actual:
            dispatcher.utter_message(
                text="📍 ¿Desde dónde sales para tu cita? Así te recomiendo negocios cerca."
            )
            return []

        # Geocodificar ubicación (intento directo y luego limpiando frases tipo "estoy en ...")
        lat_lon = self._geocodificar(ubicacion_actual)
        if not lat_lon:
            ubicacion_limpia = self._limpiar_ubicacion(ubicacion_actual)
            if ubicacion_limpia != ubicacion_actual:
                lat_lon = self._geocodificar(ubicacion_limpia)

        if not lat_lon:
            dispatcher.utter_message(
                text="❌ No pude localizar esa **dirección**. Prueba con **calle**, **número** y **ciudad**."
            )
            return []

        # Detectar tipo de negocio del mensaje
        tipo_detectado = self._detectar_tipo_negocio(mensaje)

        # Detectar si busca disponibilidad hoy / urgente
        busca_hoy = any(
            palabra in mensaje
            for palabra in ["hoy", "ahora", "disponible", "hueco", "cita", "urgente", "urgencia", "pronto"]
        )

        try:
            negocios = self._fetch_negocios(lat_lon)
        except Exception:
            dispatcher.utter_message(text="⚠️ No pude conectarme al **buscador** ahora mismo. Inténtalo de nuevo en unos segundos.")
            return []

        # Limitar a distancia prudente y ordenar por cercanía
        negocios = self._filtrar_por_distancia(negocios, max_km=50)

        # Filtrar por tipo si se detectó (coincidencia flexible)
        if tipo_detectado:
            negocios = [n for n in negocios if self._match_tipo(n.get("tipo_negocio"), tipo_detectado)]

        if not negocios:
            if tipo_detectado:
                dispatcher.utter_message(text=f"🔎 No encontré negocios de tipo **{tipo_detectado}** cerca de tu **ubicación**.")
            else:
                dispatcher.utter_message(text="🔎 No encontré **negocios** cerca de tu **ubicación**.")
            return [SlotSet("ubicacion_texto", ubicacion_actual)]

        # Filtrar por disponibilidad hoy si lo requiere
        if busca_hoy:
            negocios, detalles = self._filtrar_con_hueco_hoy(negocios)
        else:
            detalles = {}

        if not negocios:
            dispatcher.utter_message(text="⏱️ No hay **huecos hoy** en tu zona. Puedo buscar **mañana** si lo prefieres.")
            return [SlotSet("ubicacion_texto", ubicacion_actual)]

        max_items = 10
        # Detectar números en dígitos
        dig = re.search(r"\b(\d{1,2})\b", mensaje)
        if dig:
            try:
                solicitado = int(dig.group(1))
                if solicitado >= 1:
                    max_items = min(solicitado, 10)
            except Exception:
                pass
        else:
            # Detectar números en palabras básicas (es) hasta diez
            palabras_num = {
                "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
                "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
                "nueve": 9, "diez": 10
            }
            for w, val in palabras_num.items():
                if f" {w} " in f" {mensaje} ":
                    max_items = min(val, 10)
                    break

        mensaje = self._formatear_respuesta(negocios[:max_items], detalles, busca_hoy, tipo_detectado)
        dispatcher.utter_message(text=mensaje)
        return [SlotSet("ubicacion_texto", ubicacion_actual)]

    def _detectar_tipo_negocio(self, mensaje: str) -> Optional[str]:
        """Detecta el tipo de negocio usando fuzzy matching y keywords."""
        try:
            tipos = self._obtener_tipos_bd()
        except Exception:
            tipos = []

        # Si no hay tipos de la BD, usar los conocidos
        if not tipos:
            tipos = list(TIPO_KEYWORDS.keys())

        # Fuzzy contra tipos (mensajes con errores: "peluqueria", "peluqeria", "pelarme")
        try:
            best = process.extractOne(mensaje, tipos, scorer=fuzz.token_set_ratio)
            if best and best[1] >= 75:
                return best[0]
        except Exception:
            pass

        # Fallback por keywords
        for tipo, keywords in TIPO_KEYWORDS.items():
            for kw in keywords:
                if kw in mensaje:
                    return tipo
        return None

    def _match_tipo(self, tipo_negocio: Optional[str], tipo_detectado: str) -> bool:
        """Coincidencia flexible de tipo: exacta, contains o fuzzy >=70."""
        a = (tipo_negocio or "").lower().strip()
        b = (tipo_detectado or "").lower().strip()
        if not a or not b:
            return False
        if a == b:
            return True
        if b in a or a in b:
            return True
        try:
            return fuzz.token_set_ratio(a, b) >= 70
        except Exception:
            return False

    def _obtener_tipos_bd(self) -> List[str]:
        """Obtiene el listado de tipos disponibles desde la API y los normaliza."""
        res = requests.get(f"{API_URL}/negocios/", timeout=8)
        res.raise_for_status()
        data = res.json() or []
        tipos = { (n.get("tipo_negocio") or "").lower().strip() for n in data }
        return [t for t in tipos if t]

    def _geocodificar(self, direccion: str) -> Optional[Tuple[float, float]]:
        data = self._geocodificar_detallado(direccion)
        if data:
            return data["lat"], data["lon"]
        return None

    def _geocodificar_detallado(self, direccion: str) -> Optional[Dict[str, Any]]:
        """Geocodifica dirección usando Nominatim con múltiples estrategias de fallback."""
        
        # Lista de estrategias a intentar
        estrategias = [
            direccion,  # 1. Intentar dirección completa tal cual
            self._limpiar_ubicacion(direccion),  # 2. Limpiar prefijos
        ]
        
        # 3-4. Intentar extrayendo últimas palabras
        palabras = direccion.split()
        if len(palabras) > 2:
            # Si tiene 4+ palabras, probablemente sea "calle X número ciudad"
            # Intentar remover la primera palabra (desde/en/etc) y usar las restantes
            sin_primera = ' '.join(palabras[1:]) if len(palabras) > 1 else None
            if sin_primera:
                estrategias.append(sin_primera)
            # Últimas 3 palabras
            estrategias.append(' '.join(palabras[-3:]))
            # Últimas 2 palabras
            estrategias.append(' '.join(palabras[-2:]))
        if len(palabras) > 1:
            estrategias.append(palabras[-1])  # Última palabra (ciudad)
        
        # Remover duplicados manteniendo orden
        estrategias = list(dict.fromkeys(estrategias))
        
        for intento, estrategia in enumerate(estrategias):
            if not estrategia.strip():
                continue
            try:
                url = "https://nominatim.openstreetmap.org/search"
                params = {
                    "q": estrategia,
                    "format": "json",
                    "limit": 10,
                    "countrycodes": "ES",
                    "accept-language": "es",
                    "addressdetails": 1,
                }
                headers = {"User-Agent": "SectorMindAI/1.0"}
                res = requests.get(url, params=params, headers=headers, timeout=8)
                data = res.json()
                
                if data:
                    # Priorizar resultado en España
                    elegido = None
                    for item in data:
                        if str(item.get("display_name", "")).lower().find("españa") != -1:
                            elegido = item
                            break
                    if not elegido:
                        elegido = data[0]
                    
                    return {
                        "lat": float(elegido["lat"]),
                        "lon": float(elegido["lon"]),
                        "display": elegido.get("display_name", direccion),
                    }
            except Exception:
                continue
        
        return None

    def _limpiar_ubicacion(self, texto: str) -> str:
        """Limpia texto de ubicación removiendo saludos y prefijos comunes."""
        # Limpiar saludos y formas comunes de responder
        t = re.sub(r"^(hola|buenas|hey|holi|buenos días|buenas tardes|buenas noches|qué tal)\s*,?\s*", "", texto, flags=re.IGNORECASE)
        # Limpiar prefijos de ubicación
        t = re.sub(r"^(desde|salgo de|salgo desde|voy desde|me voy desde|parto de|parto desde|estoy en|me encuentro en|estoy|me encuentro|vivo en|en la|en el|en los|en las|en)\s+", "", t, flags=re.IGNORECASE)
        # Segunda pasada para casos de "en la/el"
        t = re.sub(r"^(en|en la|en el|en los|en las)\s+", "", t, flags=re.IGNORECASE)
        t = t.strip(",. ")
        return t or texto
    def _map_url(self, lat: float, lon: float) -> str:
        return (
            f"https://maps.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=16&layers=M"
        )

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

                # Tomar el primer slot FUTURO (>= ahora); si ninguno futuro, saltar negocio
                slot_dt_valida = None
                slot_texto_valido = None
                for slot in slots:
                    slot_dt = self._parse_slot_time(slot)
                    if slot_dt and slot_dt >= ahora:
                        slot_dt_valida = slot_dt
                        slot_texto_valido = slot
                        break
                # Fallback: si no se pudieron parsear fechas, usar el primer slot
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
        # Ordenar por hora más próxima y luego distancia
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
                json={
                    "negocio_id": negocio_id,
                    "servicio_id": servicio_id,
                    "fecha": fecha,
                },
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
    ) -> str:
        tipo_str = f" de **{tipo_detectado}**" if tipo_detectado else ""
        intro = f"⏱️ Disponibilidad hoy{tipo_str}:" if busca_hoy else f"🔎 Negocios{tipo_str} **cerca de ti**:"
        
        lineas = []
        for n in negocios:
            distancia = n.get("distancia_km")
            etiqueta_dist = f" \u00b7 📍 {distancia:.1f} km" if distancia is not None else ""
            tipo_txt = (n.get('tipo_negocio') or '').capitalize()
            icono = self._emoji_tipo(n.get('tipo_negocio'))
            
            # Construir foto HTML
            foto_html = ""
            if n.get("foto_base64"):
                foto_html = f'<img src="{n["foto_base64"]}" alt="{n.get("nombre", "Negocio")}" style="max-width:100%; height:120px; object-fit:cover; border-radius:8px; margin-bottom:8px;">'
            else:
                # Placeholder con emoji si no hay foto
                foto_html = f'<div style="width:100%; height:120px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:3rem; margin-bottom:8px;">{icono}</div>'
            
            # Construir línea con foto + info + link
            negocio_id = n.get("id")
            nombre = n.get('nombre', 'Negocio')
            
            linea = f"""[BUSINESS_CARD]
{foto_html}
<a href="detalle.html?id={negocio_id}" style="text-decoration:none; color:#4f46e5; font-weight:bold;">{icono} {nombre}</a> ({tipo_txt}){etiqueta_dist}"""
            
            if busca_hoy and n.get("id") in detalles:
                slot = detalles[n["id"]]["slot"]
                hora = slot.split(" ")[1][:5] if " " in slot else slot[-5:]
                servicio = detalles[n["id"]].get("servicio", "servicio")
                linea += f"<br><small style='color:#666;'>{servicio} a las {hora}</small>"
            
            linea += "[/BUSINESS_CARD]"
            lineas.append(linea)
        
        return intro + "\n" + "\n".join(lineas)

    def _filtrar_por_distancia(self, negocios: List[Dict[str, Any]], max_km: float) -> List[Dict[str, Any]]:
        # Sin límite de distancia: solo ordenar por cercanía cuando exista el dato
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
            # Fallback: aproximar a CET/CEST (+1/+2). Usamos +1 para no quedarnos en UTC.
            return datetime.utcnow() + timedelta(hours=1)

    def _emoji_tipo(self, tipo: Optional[str]) -> str:
        t = (tipo or '').lower()
        if t == 'peluqueria':
            return '✂️'
        if t == 'dentista':
            return '🦷'
        if t == 'fisioterapia':
            return '💪'
        return '🏪'
