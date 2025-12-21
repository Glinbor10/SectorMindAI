from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests
from datetime import datetime, timedelta
from .base_actions import ActionUrgenciaBase

API_URL = "http://localhost:5000"


class ActionUrgenciaFisioterapia(Action, ActionUrgenciaBase):
    """Maneja urgencias de fisioterapia (dolor agudo, lesiones)"""

    def name(self) -> Text:
        return "action_urgencia_fisioterapia"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        if not self.validar_tipo_negocio("fisioterapia", tracker, dispatcher):
            return []

        negocio_id, cliente_id = self.obtener_slots_basicos(tracker)
        if not self.validar_slots_basicos(negocio_id, cliente_id, dispatcher):
            return []

        intent = tracker.latest_message.get('intent', {}).get('name')

        intent = tracker.latest_message.get('intent', {}).get('name')
        
        respuestas = {
            "dolor_agudo_espalda": {
                "mensaje": "🚨 **Dolor Agudo de Espalda**\n\n"
                          "Entiendo que el dolor es fuerte y limitante.\n\n"
                          "Te voy a buscar el hueco más cercano posible para valoración urgente.\n\n"
                          "**Mientras tanto:**\n"
                          "• Aplica frío 15 min cada 2 horas (primeras 48h)\n"
                          "• Evita reposo absoluto (movimiento suave ayuda)\n"
                          "• No cargues peso\n"
                          "• Mantén posturas cómodas\n\n"
                          "¿Puedes venir hoy o prefieres mañana temprano?",
                "es_urgencia": True
            },
            "lesion_deportiva": {
                "mensaje": "⚽ **Lesión Deportiva**\n\n"
                          "Las lesiones deportivas requieren atención rápida para buena recuperación.\n\n"
                          "**Protocolo RICE (primeras 48-72h):**\n"
                          "• **R**eposo relativo (no absoluto)\n"
                          "• **I**ce (hielo 15 min/2h)\n"
                          "• **C**ompresión (vendaje)\n"
                          "• **E**levación de la zona\n\n"
                          "Te busco cita urgente para valoración y tratamiento.\n\n"
                          "¿Cuándo puedes venir?",
                "es_urgencia": True
            },
            "contractura_muscular": {
                "mensaje": "💪 **Contractura Muscular**\n\n"
                          "Las contracturas son molestas pero tienen buen pronóstico.\n\n"
                          "**Alivio inmediato:**\n"
                          "• Calor local (bolsa térmica 15-20 min)\n"
                          "• Estiramientos suaves\n"
                          "• Evita la postura que la causó\n"
                          "• Mantente activo/a sin forzar\n\n"
                          "Te busco cita en los próximos días para tratamiento específico.\n\n"
                          "¿Qué día te viene mejor?",
                "es_urgencia": False
            }
        }

        respuesta_config = respuestas.get(intent, {
            "mensaje": "Veo que tienes molestias. ¿Cuándo puedes venir para valoración?",
            "es_urgencia": False
        })

        dispatcher.utter_message(text=respuesta_config["mensaje"])
        
        return [
            SlotSet("es_urgencia", respuesta_config["es_urgencia"]),
            SlotSet("servicio", "Urgencia Fisioterapia" if respuesta_config["es_urgencia"] else None)
        ]
