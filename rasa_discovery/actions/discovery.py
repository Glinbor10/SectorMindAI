"""
Acciones para el bot de descubrimiento (búsqueda escalable por tipo dinámico).
"""
import os
import re
import unicodedata
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
        try:
            intent = tracker.get_intent_of_latest_message()
            mensaje = tracker.latest_message.get("text", "").lower().strip()

            # Slots de estado
            esperando_confirmacion = tracker.get_slot("esperando_confirmacion_ubicacion")
            ubicacion_pendiente = tracker.get_slot("ubicacion_pendiente_confirmar")
            slot_ubicacion = tracker.get_slot("ubicacion_texto")
            opciones_negocio = tracker.get_slot("opciones_negocio")
            ubicacion_confirmada = tracker.get_slot("ubicacion_confirmada")
            ubicacion_confirmada_texto = tracker.get_slot("ubicacion_confirmada_texto")
            meta = tracker.latest_message.get("metadata") or {}
            meta_ubicacion = meta.get("ubicacion_texto") if meta else None
            ubicacion_actual = slot_ubicacion or meta_ubicacion
            auto_confirmada = False

            # Si existe una ubicacion confirmada guardada, fijarla y no permitir cambios
            if ubicacion_confirmada_texto and not esperando_confirmacion:
                if not ubicacion_confirmada:
                    ubicacion_confirmada = True
                ubicacion_actual = ubicacion_confirmada_texto

            # Si ya hay ubicacion guardada y el usuario pide un negocio, no volver a pedir ubicacion
            if ubicacion_actual and not ubicacion_confirmada and not esperando_confirmacion:
                if intent == "buscar_negocio" or self._mensaje_parece_buscar_negocio(mensaje):
                    ubicacion_confirmada = True
                    auto_confirmada = True

            # ========================================
            # FLUJO 1: ESPERANDO CONFIRMACIÓN DE UBICACIÓN
            # Estado: esperando_confirmacion_ubicacion = True
            # Acción: Solo acepta afirmar/negar para confirmar ubicación
            # ========================================
            if esperando_confirmacion:
                # Solo aceptar afirmar/negar
                if intent == "afirmar":
                    # Usuario confirma → guardar ubicación
                    dispatcher.utter_message(
                        text=f"✅ Ubicación confirmada: **{ubicacion_pendiente}**\n\nAhora dime qué necesitas (**peluquería**, **dentista**, **fisio**, etc.)."
                    )
                    return [
                        SlotSet("ubicacion_texto", ubicacion_pendiente),
                        SlotSet("esperando_confirmacion_ubicacion", False),
                        SlotSet("ubicacion_pendiente_confirmar", None),
                        SlotSet("ubicacion_confirmada", True),
                        SlotSet("ubicacion_confirmada_texto", ubicacion_pendiente),
                        SlotSet("opciones_negocio", None)
                    ]
                
                elif intent == "negar":
                    # Usuario rechaza → pedir ubicación más precisa
                    dispatcher.utter_message(
                        text="📍 Por favor, dame tu ubicación de forma más precisa: **Calle, número, municipio, ciudad** (Ejemplo: 'Calle Betis 25, Estepa, Sevilla')"
                    )
                    return [
                        SlotSet("esperando_confirmacion_ubicacion", False),
                        SlotSet("ubicacion_pendiente_confirmar", None),
                        SlotSet("ubicacion_texto", None),
                        SlotSet("ubicacion_confirmada", False),
                        SlotSet("ubicacion_confirmada_texto", None),
                        SlotSet("opciones_negocio", None)
                    ]
                
                else:
                    # Usuario dice otra cosa → recordar que solo aceptamos sí/no
                    dispatcher.utter_message(
                        text="⚠️ Por favor, responde **sí** o **no** para confirmar la ubicación."
                    )
                    return []

            # ========================================
            # FLUJO 2: SELECCIÓN DE NEGOCIO (número)
            # Estado: opciones_negocio tiene lista de negocios
            # Acción: Detecta número (1,2,3...) o nombre y redirige
            # ========================================
            if opciones_negocio and isinstance(opciones_negocio, list):
                def _norm_text(value: str) -> str:
                    if not value:
                        return ""
                    value = value.lower()
                    value = unicodedata.normalize("NFD", value)
                    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
                    value = re.sub(r"[^a-z0-9\s]", " ", value)
                    return re.sub(r"\s+", " ", value).strip()

                matched = False
                try:
                    # Buscar número en el mensaje (ej: "1", "el 1", "la cuatro", "número tres")
                    numero_detectado = self._extraer_numero(mensaje)
                    if numero_detectado is not None:
                        idx = numero_detectado - 1
                        if 0 <= idx < len(opciones_negocio):
                            seleccionado = opciones_negocio[idx]
                            negocio_id = seleccionado.get("id")
                            link = f"detalle.html?id={negocio_id}" if negocio_id is not None else "detalle.html"
                            # Usar etiqueta especial para que el frontend redirija automáticamente
                            dispatcher.utter_message(
                                text=f"[REDIRECT:{link}]"
                            )
                            return [
                                SlotSet("opciones_negocio", None),
                                SlotSet("ubicacion_texto", ubicacion_actual or slot_ubicacion),
                            ]
                    # Detectar nombre del negocio en el mensaje (parcial o fuzzy)
                    mensaje_norm = _norm_text(mensaje)
                    if mensaje_norm:
                        best_score = 0
                        best_id = None
                        for opcion in opciones_negocio:
                            nombre = opcion.get("nombre") or ""
                            nombre_norm = _norm_text(nombre)
                            if not nombre_norm:
                                continue
                            if nombre_norm in mensaje_norm:
                                best_id = opcion.get("id")
                                best_score = 100
                                break
                            score = fuzz.token_set_ratio(mensaje_norm, nombre_norm)
                            if score > best_score:
                                best_score = score
                                best_id = opcion.get("id")
                        if best_id is not None and best_score >= 80:
                            link = f"detalle.html?id={best_id}"
                            dispatcher.utter_message(text=f"[REDIRECT:{link}]")
                            matched = True
                    if matched:
                        return [
                            SlotSet("opciones_negocio", None),
                            SlotSet("ubicacion_texto", ubicacion_actual or slot_ubicacion),
                        ]
                except Exception:
                    pass

                dispatcher.utter_message(
                    text="👉 DI EL NÚMERO (1, 2, 3, 4, 5...) o el nombre del negocio que quieres."
                )
                return []

            # ========================================
            # FLUJO 3: SALUDOS O RESET
            # Estado: Sin opciones pendientes
            # Intent: greet o detección de saludo
            # Acción: Resetea todo y pide ubicación desde cero
            # ========================================
            if not opciones_negocio and (
                intent == "greet" or self._es_saludo_simple(mensaje) or self._es_saludo_fuzzy(mensaje)
                or self._quiere_cambiar_ubicacion(mensaje)):
                if ubicacion_confirmada_texto:
                    dispatcher.utter_message(
                        text="¿Qué necesitas (**peluquería**, **dentista**, **fisio**, etc.)?"
                    )
                    return []
                dispatcher.utter_message(
                    text="📍 ¿Desde dónde sales para tu cita? Así te recomiendo negocios cerca."
                )
                return [
                    SlotSet("ubicacion_texto", None),
                    SlotSet("esperando_confirmacion_ubicacion", False),
                    SlotSet("ubicacion_pendiente_confirmar", None),
                    SlotSet("ubicacion_confirmada", False),
                    SlotSet("ubicacion_confirmada_texto", None),
                    SlotSet("opciones_negocio", None)
                ]

            # Si la ubicacion ya esta confirmada, no reabrir el flujo de geocodificacion
            if (
                ubicacion_confirmada
                and not opciones_negocio
                and (intent == "informar_ubicacion" or self._mensaje_parece_ubicacion(mensaje, intent))
            ):
                if ubicacion_actual:
                    dispatcher.utter_message(
                        text=f"✅ Ubicación confirmada: **{ubicacion_actual}**\n\nAhora dime qué necesitas (**peluquería**, **dentista**, **fisio**, etc.)."
                    )
                else:
                    dispatcher.utter_message(
                        text="Ahora dime qué necesitas (**peluquería**, **dentista**, **fisio**, etc.)."
                    )
                return [
                    SlotSet("ubicacion_texto", ubicacion_actual),
                    SlotSet("ubicacion_confirmada", True),
                    SlotSet("ubicacion_confirmada_texto", ubicacion_actual),
                ]

            # ========================================
            # FLUJO 4: CAPTURA Y CONFIRMACIÓN DE UBICACIÓN
            # Estado: ubicacion_confirmada = False
            # Intent: informar_ubicacion o texto que parece ubicación
            # Acción: Geocodifica → Muestra mapa → Pide confirmación
            # ========================================
            full_text = tracker.latest_message.get("text", "").strip()
            if (
                not ubicacion_confirmada
                and (intent == "informar_ubicacion" or self._mensaje_parece_ubicacion(mensaje, intent))
                and not opciones_negocio
            ):
                if full_text:
                    try:
                        geo_resultados = self._geocodificar_con_opciones(full_text)
                        
                        # Si hay múltiples opciones, tomar la primera (más relevante)
                        if isinstance(geo_resultados, list) and len(geo_resultados) > 0:
                            geo_resultados = geo_resultados[0]
                        
                        # Si se encontró resultado, PEDIR CONFIRMACIÓN
                        if isinstance(geo_resultados, dict):
                            display_guardado = geo_resultados["display"]
                            
                            # Enviar mensaje de confirmación
                            dispatcher.utter_message(
                                text=(
                                    f"📍 He encontrado: **{display_guardado}**\n\n"
                                    f"🗺️ Vista previa: {geo_resultados['display']}\n"
                                    f"[MAP:{geo_resultados['lat']},{geo_resultados['lon']}]\n\n"
                                    "¿Es correcta esta ubicación? (Responde **sí** o **no**)"
                                )
                            )
                            
                            # Activar modo "esperando confirmación"
                            return [
                                SlotSet("ubicacion_pendiente_confirmar", display_guardado),
                                SlotSet("esperando_confirmacion_ubicacion", True),
                                SlotSet("ubicacion_confirmada", False),
                                SlotSet("opciones_negocio", None)
                            ]
                            
                    except Exception as e:
                        print(f"⚠️ Error en geocodificación: {e}")

                    dispatcher.utter_message(
                        text="❌ No pude localizar esa ubicación. ¿Puedes ser más específico? Di tu **ciudad y provincia** (ej: Córdoba, Andalucía) o una **dirección completa** (calle, número, ciudad)."
                    )
                    return [
                        SlotSet("ubicacion_texto", None),
                        SlotSet("ubicacion_confirmada", False),
                        SlotSet("ubicacion_confirmada_texto", None),
                        SlotSet("opciones_negocio", None)
                    ]

            # ========================================
            # FLUJO 5: BÚSQUEDA DE NEGOCIOS
            # Estado: ubicacion_confirmada = True y ubicacion_texto existe
            # Intent: buscar_negocio o mensaje con tipo de negocio
            # Acción: Busca negocios cercanos y lista opciones
            # ========================================
            if not ubicacion_actual or not ubicacion_confirmada:
                dispatcher.utter_message(
                    text="📍 ¿Desde dónde sales para tu cita? Así te recomiendo negocios cerca."
                )
                return [
                    SlotSet("ubicacion_texto", None),
                    SlotSet("ubicacion_confirmada", False),
                    SlotSet("ubicacion_confirmada_texto", None)
                ]

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
                return [SlotSet("ubicacion_texto", None)]

            # Detectar tipo de negocio del mensaje
            tipo_detectado = self._detectar_tipo_negocio(mensaje)

            # Detectar si busca disponibilidad hoy / urgente
            busca_hoy = any(
                palabra in mensaje
                for palabra in ["hoy", "ahora", "disponible", "hueco", "cita", "urgente", "urgencia", "pronto"]
            )
            
            # Detectar si busca disponibilidad mañana
            busca_manana = any(
                palabra in mensaje
                for palabra in ["mañana", "manana", "tomorrow"]
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

            # Filtrar por disponibilidad según el día solicitado
            if busca_manana:
                negocios, detalles = self._filtrar_con_hueco_manana(negocios)
            elif busca_hoy:
                negocios, detalles = self._filtrar_con_hueco_hoy(negocios)
            else:
                detalles = {}

            if not negocios:
                if busca_manana:
                    dispatcher.utter_message(text="⏱️ No hay **huecos mañana** en tu zona. ¿Quieres ver todos los negocios disponibles?")
                elif busca_hoy:
                    dispatcher.utter_message(text="⏱️ No hay **huecos hoy** en tu zona. Puedo buscar **mañana** si lo prefieres.")
                return [SlotSet("ubicacion_texto", ubicacion_actual)]

            max_items = 5
            # Detectar números en dígitos
            dig = re.search(r"\b(\d{1,2})\b", mensaje)
            if dig:
                try:
                    solicitado = int(dig.group(1))
                    if solicitado >= 1:
                        max_items = min(solicitado, 5)
                except Exception:
                    pass
            else:
                # Detectar números en palabras básicas (es) hasta cinco
                palabras_num = {
                    "uno": 1, "una": 1,
                    "dos": 2,
                    "tres": 3,
                    "cuatro": 4,
                    "cinco": 5
                }
                patron = r"\b(" + "|".join(palabras_num.keys()) + r")\b"
                match = re.search(patron, mensaje)
                if match:
                    max_items = min(palabras_num[match.group(1)], 5)

            mensaje = self._formatear_respuesta(negocios[:max_items], detalles, busca_hoy or busca_manana, tipo_detectado)
            lista_opciones = [
                {"id": n.get("id"), "nombre": n.get("nombre", "Negocio")} for n in negocios[:max_items]
            ]
            dispatcher.utter_message(text=mensaje)
            return [
                SlotSet("ubicacion_texto", ubicacion_actual),
                SlotSet("opciones_negocio", lista_opciones),
                SlotSet("ubicacion_confirmada", True) if auto_confirmada else SlotSet("ubicacion_confirmada", ubicacion_confirmada),
                SlotSet("ubicacion_confirmada_texto", ubicacion_actual) if ubicacion_actual else SlotSet("ubicacion_confirmada_texto", ubicacion_confirmada_texto),
            ]
        
        except Exception as e:
            print(f"❌ Error en action_discovery_buscar_negocios: {e}")
            import traceback
            traceback.print_exc()
            dispatcher.utter_message(
                text="⚠️ Hubo un problema. Por favor, intenta de nuevo o di tu ubicación de otra forma."
            )
            return [SlotSet("ubicacion_texto", None)]

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

    def _extraer_numero(self, texto: str) -> Optional[int]:
        """Extrae un número del texto, soportando dígitos y palabras en español (1-10)."""
        texto_lower = texto.lower()
        
        # Primero intentar dígitos puros (1, 2, 3...)
        match = re.search(r'\b(\d{1,2})\b', texto_lower)
        if match:
            try:
                num = int(match.group(1))
                if 1 <= num <= 10:
                    return num
            except ValueError:
                pass
        
        # Mapeo de palabras españolas a números
        palabras_a_numero = {
            # Números cardinales
            'uno': 1, 'una': 1,
            'dos': 2,
            'tres': 3,
            'cuatro': 4,
            'cinco': 5,
            'seis': 6,
            'siete': 7,
            'ocho': 8,
            'nueve': 9,
            'diez': 10,
            # Números ordinales
            'primero': 1, 'primera': 1, 'primer': 1,
            'segundo': 2, 'segunda': 2,
            'tercero': 3, 'tercera': 3, 'tercer': 3,
            'cuarto': 4, 'cuarta': 4,
            'quinto': 5, 'quinta': 5,
            'sexto': 6, 'sexta': 6,
            'séptimo': 7, 'séptima': 7, 'septimo': 7, 'septima': 7,
            'octavo': 8, 'octava': 8,
            'noveno': 9, 'novena': 9,
            'décimo': 10, 'décima': 10, 'decimo': 10, 'decima': 10,
        }
        
        # Buscar palabras numéricas
        for palabra, numero in palabras_a_numero.items():
            if re.search(r'\b' + re.escape(palabra) + r'\b', texto_lower):
                return numero
        
        return None

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
                    elegido = self._seleccionar_geocodificado(data, direccion)
                    if elegido:
                        return {
                            "lat": float(elegido["lat"]),
                            "lon": float(elegido["lon"]),
                            "display": elegido.get("display_name", direccion),
                        }
            except Exception:
                continue
        
        return None

    def _geocodificar_con_opciones(self, direccion: str) -> any:
        """Geocodifica y retorna opciones si hay múltiples resultados buenos, o un solo resultado si es único."""
        estrategias = [
            direccion,
            self._limpiar_ubicacion(direccion),
        ]
        
        palabras = direccion.split()
        
        # Para "cordoba capital", probar "cordoba" primero antes que "capital"
        if len(palabras) == 2:
            estrategias.append(palabras[0])  # Primera palabra
            estrategias.append(palabras[1])  # Segunda palabra
        elif len(palabras) > 2:
            estrategias.append(palabras[0])  # Primera palabra
            sin_primera = ' '.join(palabras[1:])
            estrategias.append(sin_primera)
            estrategias.append(' '.join(palabras[-3:]))
            estrategias.append(' '.join(palabras[-2:]))
            estrategias.append(palabras[-1])
        
        estrategias = list(dict.fromkeys(estrategias))
        
        for estrategia in estrategias:
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
                    # Filtrar y puntuar resultados de España
                    candidatos_puntuados = []
                    for item in data:
                        display = str(item.get("display_name", "")).lower()
                        addr = item.get("address") or {}
                        es_es = "españa" in display or (addr.get("country_code") or "").lower() == "es"
                        
                        if not es_es:
                            continue
                        
                        # Aplicar scoring como en _seleccionar_geocodificado
                        es_ciudad = any(addr.get(k) for k in ["city", "town", "village", "municipality", "hamlet"])
                        es_provincia = any(addr.get(k) for k in ["state", "province"])
                        es_localidad = 2 if es_ciudad else (1 if es_provincia else 0)
                        importancia = float(item.get("importance") or 0)
                        
                        score = (1 if es_es else 0, es_localidad, 1 if importancia > 0.5 else 0, importancia)
                        
                        candidatos_puntuados.append({
                            "lat": float(item["lat"]),
                            "lon": float(item["lon"]),
                            "display": item.get("display_name", direccion),
                            "score": score,
                            "es_ciudad": es_ciudad,
                            "importancia": importancia
                        })
                    
                    # Ordenar por score (mayor a menor)
                    candidatos_puntuados.sort(key=lambda x: x["score"], reverse=True)
                    
                    # Filtrar preferiblemente ciudades con alta importancia, pero si no hay, tomar los mejores
                    candidatos_excelentes = [
                        c for c in candidatos_puntuados 
                        if c["es_ciudad"] and c["importancia"] >= 0.5
                    ]
                    
                    candidatos_buenos = [
                        c for c in candidatos_puntuados 
                        if c["es_ciudad"] or c["importancia"] >= 0.4
                    ]
                    
                    # Preferir excelentes si existen, sino buenos, sino top 5
                    lista_final = candidatos_excelentes[:5] if candidatos_excelentes else (candidatos_buenos[:5] if candidatos_buenos else candidatos_puntuados[:5])
                    
                    if len(lista_final) > 1:
                        # Retornar múltiples opciones (sin el campo score)
                        return [{k: v for k, v in c.items() if k not in ["score", "es_ciudad", "importancia"]} 
                                for c in lista_final]
                    elif len(lista_final) == 1:
                        c = lista_final[0]
                        return {
                            "lat": c["lat"],
                            "lon": c["lon"],
                            "display": c["display"]
                        }
            except Exception:
                continue
        
        return None

    def _seleccionar_geocodificado(self, candidatos: List[Dict[str, Any]], direccion: str) -> Optional[Dict[str, Any]]:
        """Elige el mejor resultado priorizando España, localidades y lugares más poblados."""
        mejor = None
        mejor_score: Tuple[int, int, int, float] = (-1, -1, -1, -1.0)

        for item in candidatos:
            display = str(item.get("display_name", "")).lower()
            addr = item.get("address") or {}
            es_es = "españa" in display or (addr.get("country_code") or "").lower() == "es"
            
            # Priorizar ciudad/pueblo sobre provincia/estado
            es_ciudad = any(addr.get(k) for k in ["city", "town", "village", "municipality", "hamlet"])
            es_provincia = any(addr.get(k) for k in ["state", "province"])
            es_localidad = 2 if es_ciudad else (1 if es_provincia else 0)
            
            importancia = float(item.get("importance") or 0)

            score = (1 if es_es else 0, es_localidad, 1 if importancia > 0.5 else 0, importancia)
            if score > mejor_score:
                mejor_score = score
                mejor = item

        # Si el mejor es de España, aceptarlo incluso con baja importancia
        if mejor:
            addr = mejor.get("address") or {}
            es_es = "españa" in str(mejor.get("display_name", "")).lower() or (addr.get("country_code") or "").lower() == "es"
            if not es_es:
                importancia = float(mejor.get("importance") or 0)
                if importancia < 0.25:
                    return None

        if not mejor and candidatos:
            mejor = candidatos[0]
        return mejor

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
        saludos = [
            "hola",
            "holaa",
            "holi",
            "buenas",
            "hey",
        ]
        try:
            return any(fuzz.partial_ratio(norm, s) >= 85 for s in saludos)
        except Exception:
            return False

    def _quiere_cambiar_ubicacion(self, mensaje: str) -> bool:
        """Detecta si el usuario quiere cambiar o corregir la ubicación."""
        if not mensaje:
            return False
        norm = mensaje.strip().lower()
        palabras_cambio = [
            "cambiar", "cambio", "cambiala", "cámbiala", "cambiala",
            "otra ubicacion", "otra ubicación", "otra direccion", "otra dirección",
            "quiero cambiar", "quiero otra", "pon otra", "pon otra ubicacion",
            "desde otro sitio", "salgo de otro sitio", "salgo de otro lugar"
        ]
        return any(palabra in norm for palabra in palabras_cambio)

    def _mensaje_parece_ubicacion(self, mensaje: str, intent: Optional[str] = None) -> bool:
        """Heurística conservadora para decidir si el texto es probablemente una ubicación."""
        if not mensaje:
            return False
        if self._es_saludo_simple(mensaje) or self._es_saludo_fuzzy(mensaje):
            return False
        if intent == "greet":
            return False

        mensaje = mensaje.strip().lower()
        palabras = mensaje.split()
        if len(palabras) == 0 or len(palabras) > 6:
            return False

        # Si contiene keywords claras de servicios, no lo tratamos como ubicación
        for kws in TIPO_KEYWORDS.values():
            for kw in kws:
                if kw in mensaje:
                    return False

        if re.search(r"\d", mensaje):
            return True  # Direcciones con números
        if any(pref in mensaje for pref in ["calle", "c/", "avenida", "av ", "av.", "plaza", "pza", "cl.", "desde", "en"]):
            return True

        # Palabra/s cortas sin keywords ni saludo: intentar geocodificar (ciudades, pueblos)
        return True

    def _mensaje_parece_buscar_negocio(self, mensaje: str) -> bool:
        """Heurística simple para detectar peticiones de negocio sin depender solo del intent."""
        if not mensaje:
            return False
        msg = mensaje.lower().strip()
        for kws in TIPO_KEYWORDS.values():
            for kw in kws:
                if kw in msg:
                    return True
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

    def _filtrar_con_hueco_manana(
        self, negocios: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
        """Filtra negocios con huecos disponibles mañana."""
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

                # Tomar el primer slot del día
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
        for idx, n in enumerate(negocios, start=1):
            distancia = n.get("distancia_km")
            etiqueta_dist = f" · 📍 {distancia:.1f} km" if distancia is not None else ""
            tipo_txt = (n.get('tipo_negocio') or '').capitalize()
            icono = self._emoji_tipo(n.get('tipo_negocio'))
            
            # Construir foto HTML
            foto_html = ""
            if n.get("foto_base64"):
                foto_html = f'<img src="{n["foto_base64"]}" alt="{n.get("nombre", "Negocio")}" style="max-width:100%; height:120px; object-fit:cover; border-radius:8px; margin-bottom:8px;">'
            else:
                # Placeholder con emoji si no hay foto
                foto_html = f'<div style="width:100%; height:120px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:3rem; margin-bottom:8px;">{icono}</div>'
            
            # Construir línea con foto + info + link (HTML puro, sin markdown)
            negocio_id = n.get("id")
            nombre = n.get('nombre', 'Negocio')
            
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
