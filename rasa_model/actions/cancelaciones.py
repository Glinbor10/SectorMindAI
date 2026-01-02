"""
Acciones para cancelar citas
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from datetime import datetime
import requests

from .utils import limpiar_flujo, API_URL


class ActionCancelarCita(Action):
    def name(self) -> Text:
        return "action_cancelar_cita"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        cliente_id = tracker.get_slot("cliente_id")
        if not cliente_id:
            dispatcher.utter_message(text="Por favor, inicia sesión primero para cancelar una cita.")
            return limpiar_flujo()

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
                    dispatcher.utter_message(text="No tienes citas futuras para cancelar.")
                    return limpiar_flujo()
                
                if len(citas_futuras) == 1:
                    cita = citas_futuras[0]
                    fecha = datetime.fromisoformat(cita["fecha_hora_cita"])
                    servicio_nombre = cita.get('servicio_nombre', 'tu servicio')
                    
                    msg = (f"Tienes una cita el {fecha.strftime('%d/%m/%Y a las %H:%M')} "
                           f"para {servicio_nombre}.\n"
                           f"¿Estás seguro de que quieres cancelarla? (sí/no)")
                    
                    dispatcher.utter_message(text=msg)
                    return [
                        SlotSet("flujo_activo", "cancelar_confirmacion"),
                        SlotSet("cita_id_cancelar", cita["id"])
                    ]
                else:
                    msg_citas = "Tienes varias citas. ¿Cuál quieres cancelar?\n"
                    for idx, cita in enumerate(citas_futuras, 1):
                        fecha = datetime.fromisoformat(cita["fecha_hora_cita"])
                        servicio_nombre = cita.get('servicio_nombre', 'Servicio')
                        msg_citas += f"{idx}. {servicio_nombre} - {fecha.strftime('%d/%m/%Y a las %H:%M')}\n"
                    
                    msg_citas += "\nResponde con el número de la cita."
                    dispatcher.utter_message(text=msg_citas)
                    
                    return [
                        SlotSet("flujo_activo", "cancelar_seleccion"),
                        SlotSet("citas_disponibles", citas_futuras)
                    ]
            else:
                dispatcher.utter_message(text="No pude consultar tus citas. Intenta de nuevo.")
                return limpiar_flujo()
                
        except Exception as e:
            print(f"Error en cancelar_cita: {e}")
            dispatcher.utter_message(text="Hubo un problema. Intenta de nuevo más tarde.")
            return limpiar_flujo()


class ActionSeleccionarCitaCancelar(Action):
    def name(self) -> Text:
        return "action_seleccionar_cita_cancelar"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ultimo_mensaje = tracker.latest_message.get("text", "").strip()
        citas_disponibles = tracker.get_slot("citas_disponibles")
        
        if not citas_disponibles:
            dispatcher.utter_message(text="No hay citas disponibles para seleccionar.")
            return limpiar_flujo()
        
        try:
            seleccion = int(ultimo_mensaje)
            if 1 <= seleccion <= len(citas_disponibles):
                cita = citas_disponibles[seleccion - 1]
                fecha = datetime.fromisoformat(cita["fecha_hora_cita"])
                servicio_nombre = cita.get('servicio_nombre', 'tu servicio')
                
                msg = (f"Seleccionaste la cita del {fecha.strftime('%d/%m/%Y a las %H:%M')} "
                       f"para {servicio_nombre}.\n"
                       f"¿Estás seguro de que quieres cancelarla? (sí/no)")
                
                dispatcher.utter_message(text=msg)
                return [
                    SlotSet("flujo_activo", "cancelar_confirmacion"),
                    SlotSet("cita_id_cancelar", cita["id"]),
                    SlotSet("citas_disponibles", None)
                ]
            else:
                dispatcher.utter_message(text="Número inválido. Selecciona un número de la lista.")
                return []
        except ValueError:
            dispatcher.utter_message(text="Por favor, responde con el número de la cita que quieres cancelar.")
            return []


class ActionProcesarConfirmacionCancelar(Action):
    def name(self) -> Text:
        return "action_procesar_confirmacion_cancelar"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        cita_id = tracker.get_slot("cita_id_cancelar")
        if not cita_id:
            dispatcher.utter_message(text="No encontré la cita para cancelar. Intenta de nuevo.")
            return limpiar_flujo()
        
        ultimo_mensaje = tracker.latest_message.get("text", "").lower().strip()
        
        if any(palabra in ultimo_mensaje for palabra in ["sí", "si", "confirmo", "seguro", "ok", "vale"]):
            try:
                response = requests.delete(
                    f"{API_URL}/citas/{cita_id}",
                    timeout=5
                )
                
                if response.status_code == 200:
                    dispatcher.utter_message(text="✅ Cita cancelada exitosamente.")
                    return limpiar_flujo()
                else:
                    dispatcher.utter_message(text="No pude cancelar la cita. Contacta con el negocio.")
                    return limpiar_flujo()
                    
            except Exception as e:
                print(f"Error al cancelar cita: {e}")
                dispatcher.utter_message(text="Hubo un problema al cancelar. Intenta más tarde.")
                return limpiar_flujo()
        else:
            dispatcher.utter_message(text="Cancelación no confirmada. Tu cita sigue activa.")
            return limpiar_flujo()
