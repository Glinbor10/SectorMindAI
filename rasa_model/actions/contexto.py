"""
Acciones para contexto y normalización de servicios
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests

from .utils import limpiar_flujo, obtener_horarios_disponibles, formatear_horarios_display, calcular_similitud, API_URL
from fuzzywuzzy import fuzz


class ActionSetContexto(Action):
    def name(self) -> Text:
        return "action_set_contexto"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        metadata = tracker.latest_message.get("metadata", {})
        cliente_id = metadata.get("cliente_id")
        negocio_id = metadata.get("negocio_id")
        
        slots = []
        if cliente_id:
            slots.append(SlotSet("cliente_id", cliente_id))
        if negocio_id:
            slots.append(SlotSet("negocio_id", negocio_id))
            
            # Obtener el nombre del negocio
            try:
                response = requests.get(f"{API_URL}/negocios/{negocio_id}", timeout=5)
                if response.status_code == 200:
                    negocio_data = response.json()
                    negocio_nombre = negocio_data.get("nombre")
                    if negocio_nombre:
                        slots.append(SlotSet("negocio", negocio_nombre))
            except Exception:
                pass  # Si falla, no pasa nada, solo no se establece el nombre
        
        return slots


class ActionNormalizarServicio(Action):
    def name(self) -> Text:
        return "action_normalizar_servicio"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        negocio_id = tracker.get_slot("negocio_id")
        if not negocio_id:
            dispatcher.utter_message(text="No encontré información del negocio. Por favor, inicia sesión primero.")
            return limpiar_flujo()
        
        try:
            response = requests.get(
                f"{API_URL}/negocios/{negocio_id}/servicios",
                timeout=5
            )
            
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude obtener los servicios disponibles. Intenta de nuevo.")
                return limpiar_flujo()
            
            servicios = response.json()  # Backend returns list directly, not {"servicios": [...]}
            if not servicios:
                dispatcher.utter_message(text="No hay servicios disponibles en este momento.")
                return limpiar_flujo()
            
            ultimo_mensaje = tracker.latest_message.get("text", "").lower()
            
            # Palabras clave para servicios
            palabras_clave_servicios = {
                "corte": ["corte", "cortar", "pelo", "cabello"],
                "tinte": ["tinte", "teñir", "color", "mechas"],
                "manicura": ["manicura", "uñas", "pedicura"],
                "barba": ["barba", "afeitar", "recortar"]
            }
            
            servicio_encontrado = None
            mejor_similitud = 0
            
            # Buscar por palabras clave primero
            for servicio in servicios:
                nombre_servicio = servicio["nombre"].lower()
                
                # Coincidencia exacta
                if nombre_servicio in ultimo_mensaje:
                    servicio_encontrado = servicio
                    break
                
                # Coincidencia por palabras clave
                for categoria, palabras in palabras_clave_servicios.items():
                    if any(palabra in ultimo_mensaje for palabra in palabras):
                        if categoria in nombre_servicio:
                            servicio_encontrado = servicio
                            break
                
                if servicio_encontrado:
                    break
                
                # Similitud difusa con fuzzywuzzy - comparar cada palabra del usuario
                # contra cada palabra del servicio
                palabras_usuario = ultimo_mensaje.split()
                palabras_servicio = nombre_servicio.split()
                
                for palabra_usuario in palabras_usuario:
                    if len(palabra_usuario) >= 3:
                        # Comparar contra el nombre completo del servicio
                        similitud = fuzz.ratio(palabra_usuario, nombre_servicio) / 100.0
                        if similitud > mejor_similitud and similitud > 0.60:
                            mejor_similitud = similitud
                            servicio_encontrado = servicio
                        
                        # Comparar contra cada palabra individual del servicio
                        for palabra_servicio in palabras_servicio:
                            if len(palabra_servicio) >= 3:
                                similitud = fuzz.ratio(palabra_usuario, palabra_servicio) / 100.0
                                if similitud > mejor_similitud and similitud > 0.70:  # Umbral más alto para palabras individuales
                                    mejor_similitud = similitud
                                    servicio_encontrado = servicio
            
            if not servicio_encontrado:
                # Listar servicios disponibles
                msg = "No estoy seguro de qué servicio te interesa. Tenemos:\n"
                for idx, serv in enumerate(servicios, 1):
                    msg += f"{idx}. {serv['nombre']}\n"
                msg += "\n¿Cuál te interesa?"
                dispatcher.utter_message(text=msg)
                return []
            
            servicio_id = servicio_encontrado["id"]
            servicio_nombre = servicio_encontrado["nombre"]
            
            # Obtener horarios disponibles
            horarios_disponibles = obtener_horarios_disponibles(negocio_id, servicio_id)
            
            if not horarios_disponibles:
                dispatcher.utter_message(
                    text=f"Lo siento, no hay horarios disponibles para {servicio_nombre}. "
                         "Contacta directamente con el negocio."
                )
                return limpiar_flujo()
            
            msg_horarios = formatear_horarios_display(horarios_disponibles)
            
            msg = f"Perfecto, te interesa: {servicio_nombre}\n\n{msg_horarios}\n\n¿Para qué día te gustaría reservar?"
            dispatcher.utter_message(text=msg)
            
            return [
                SlotSet("servicio_id", servicio_id),
                SlotSet("servicio_nombre", servicio_nombre),
                SlotSet("horarios_disponibles", horarios_disponibles),
                SlotSet("flujo_activo", "reserva_fecha")
            ]
            
        except Exception as e:
            print(f"Error en normalizar_servicio: {e}")
            dispatcher.utter_message(text="Hubo un problema. Intenta de nuevo más tarde.")
            return limpiar_flujo()
