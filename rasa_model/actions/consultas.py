"""
Acciones para consultar información
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from datetime import datetime
import requests

from .utils import limpiar_flujo, API_URL


class ActionConsultarCitasUsuario(Action):
    def name(self) -> Text:
        return "action_consultar_citas_usuario"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        cliente_id = tracker.get_slot("cliente_id")
        if not cliente_id:
            dispatcher.utter_message(text="Por favor, inicia sesión primero.")
            return []

        try:
            response = requests.get(
                f"{API_URL}/citas",
                params={"cliente_id": cliente_id},
                timeout=5
            )
            
            if response.status_code == 200:
                citas = response.json()  # Backend returns list directly
                citas_futuras = [c for c in citas if datetime.fromisoformat(c["fecha_hora_cita"]) > datetime.now()]
                
                if not citas_futuras:
                    dispatcher.utter_message(text="No tienes citas próximas.")
                    return []
                
                msg = "📅 Tus próximas citas:\n\n"
                for cita in citas_futuras:
                    fecha = datetime.fromisoformat(cita["fecha_hora_cita"])
                    servicio_nombre = cita.get('servicio_nombre', 'Servicio')
                    msg += f"• {servicio_nombre} - {fecha.strftime('%d/%m/%Y a las %H:%M')}\n"
                
                dispatcher.utter_message(text=msg)
                return []
            else:
                dispatcher.utter_message(text="No pude consultar tus citas. Intenta de nuevo.")
                return []
                
        except Exception as e:
            print(f"Error consultando citas: {e}")
            dispatcher.utter_message(text="Hubo un problema. Intenta de nuevo más tarde.")
            return []


class ActionListarServicios(Action):
    def name(self) -> Text:
        return "action_listar_servicios"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        negocio_id = tracker.get_slot("negocio_id")
        if not negocio_id:
            dispatcher.utter_message(text="No encontré información del negocio.")
            return []

        try:
            response = requests.get(
                f"{API_URL}/negocios/{negocio_id}/servicios",
                timeout=5
            )
            
            if response.status_code == 200:
                servicios = response.json()  # Backend returns list directly
                
                if not servicios:
                    dispatcher.utter_message(text="No hay servicios disponibles.")
                    return []
                
                msg = "💇 Nuestros servicios:\n\n"
                for serv in servicios:
                    precio = serv.get('precio', 0)
                    duracion = serv.get('duracion', 0)
                    msg += f"• {serv['nombre']} - {precio}€ ({duracion} min)\n"
                    if serv.get('descripcion'):
                        msg += f"  {serv['descripcion']}\n"
                
                dispatcher.utter_message(text=msg)
                return []
            else:
                dispatcher.utter_message(text="No pude obtener los servicios.")
                return []
                
        except Exception as e:
            print(f"Error listando servicios: {e}")
            dispatcher.utter_message(text="Hubo un problema consultando los servicios.")
            return []


class ActionMostrarHorarios(Action):
    def name(self) -> Text:
        return "action_mostrar_horarios"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        negocio_id = tracker.get_slot("negocio_id")
        if not negocio_id:
            dispatcher.utter_message(text="No encontré información del negocio.")
            return []

        try:
            response = requests.get(
                f"{API_URL}/negocios/{negocio_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                negocio = response.json()  # Backend returns dict directly
                horarios = negocio.get("horarios", "No disponible")
                
                msg = f"🕒 Horarios:\n{horarios}"
                dispatcher.utter_message(text=msg)
                return []
            else:
                dispatcher.utter_message(text="No pude obtener los horarios.")
                return []
                
        except Exception as e:
            print(f"Error mostrando horarios: {e}")
            dispatcher.utter_message(text="Hubo un problema consultando los horarios.")
            return []


class ActionMostrarUbicacion(Action):
    def name(self) -> Text:
        return "action_mostrar_ubicacion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        negocio_id = tracker.get_slot("negocio_id")
        if not negocio_id:
            dispatcher.utter_message(text="No encontré información del negocio.")
            return []

        try:
            response = requests.get(
                f"{API_URL}/negocios/{negocio_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                negocio = response.json()  # Backend returns dict directly
                direccion = negocio.get("direccion", "No disponible")
                
                msg = f"📍 Ubicación:\n{direccion}"
                dispatcher.utter_message(text=msg)
                return []
            else:
                dispatcher.utter_message(text="No pude obtener la ubicación.")
                return []
                
        except Exception as e:
            print(f"Error mostrando ubicación: {e}")
            dispatcher.utter_message(text="Hubo un problema consultando la ubicación.")
            return []


class ActionInfoNegocio(Action):
    def name(self) -> Text:
        return "action_info_negocio"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        negocio_id = tracker.get_slot("negocio_id")
        if not negocio_id:
            dispatcher.utter_message(text="No encontré información del negocio.")
            return []

        try:
            response = requests.get(
                f"{API_URL}/negocios/{negocio_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                negocio = response.json()  # Backend returns dict directly
                
                msg = f"ℹ️ {negocio.get('nombre', 'Negocio')}\n\n"
                msg += f"📍 {negocio.get('direccion', 'Dirección no disponible')}\n"
                msg += f" {negocio.get('horarios', 'Horarios no disponibles')}"
                
                if negocio.get('descripcion'):
                    msg += f"\n\n{negocio['descripcion']}"
                
                dispatcher.utter_message(text=msg)
                return []
            else:
                dispatcher.utter_message(text="No pude obtener la información del negocio.")
                return []
                
        except Exception as e:
            print(f"Error obteniendo info negocio: {e}")
            dispatcher.utter_message(text="Hubo un problema consultando la información.")
            return []


class ActionMostrarDisponibilidad(Action):
    def name(self) -> Text:
        return "action_mostrar_disponibilidad"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        negocio_id = tracker.get_slot("negocio_id")
        if not negocio_id:
            dispatcher.utter_message(text="Primero selecciona un servicio para ver disponibilidad.")
            return []

        dispatcher.utter_message(text="Para ver disponibilidad, dime qué servicio te interesa (corte, tinte, manicura, etc.)")
        return []
