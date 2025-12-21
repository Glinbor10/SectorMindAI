from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests
from datetime import datetime, timedelta
from .base_actions import ActionUrgenciaBase
import os

API_URL = os.getenv("API_URL", "http://backend:5000")


class ActionUrgenciaPeluqueria(Action, ActionUrgenciaBase):
    """Maneja urgencias de peluquería (eventos, desastres de tinte)"""

    def name(self) -> Text:
        return "action_urgencia_peluqueria"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if not self.validar_tipo_negocio("peluqueria", tracker, dispatcher):
            return []

        intent = tracker.latest_message.get('intent', {}).get('name')
        
        respuestas = {
            "corte_urgente_evento": {
                "mensaje": "🎉 **¡Evento Importante!**\n\n"
                          "Entiendo, necesitas verte impecable para tu evento.\n\n"
                          "Te voy a buscar el hueco más cercano posible. ¿Es para hoy o mañana?\n\n"
                          "**Tip:** Si es mañana, mejor venir hoy para evitar imprevistos. 💇‍♀️",
                "es_urgencia": True
            },
            "desastre_tinte": {
                "mensaje": "😰 **Emergencia Capilar - Tinte**\n\n"
                          "¡Tranquila/o! Esto tiene solución.\n\n"
                          "**Importante:** \n"
                          "• NO te laves el pelo más\n"
                          "• NO apliques más productos\n"
                          "• Trae foto del color original si tienes\n\n"
                          "Te busco hueco de urgencia. Tenemos experiencia arreglando estos casos.\n\n"
                          "¿Cuándo puedes venir? ¿Hoy mismo?",
                "es_urgencia": False
            }
        }

        respuesta_config = respuestas.get(intent, {
            "mensaje": "Entiendo que necesitas atención urgente. ¿Cuándo puedes venir?",
            "es_urgencia": True
        })

        dispatcher.utter_message(text=respuesta_config["mensaje"])
        
        return [
            SlotSet("es_urgencia", respuesta_config["es_urgencia"]),
            SlotSet("servicio", "Urgencia Peluquería")
        ]
