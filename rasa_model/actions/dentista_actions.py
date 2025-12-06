from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests
from datetime import datetime, timedelta

API_URL = "http://localhost:5000"


class ActionUrgenciaDental(Action):
    """Maneja urgencias dentales con respuestas específicas según el tipo de emergencia"""

    def name(self) -> Text:
        return "action_urgencia_dental"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Obtener el intent que disparó esta acción
        intent = tracker.latest_message.get('intent', {}).get('name')
        negocio_id = tracker.get_slot("negocio_id")
        cliente_id = tracker.get_slot("cliente_id")
        tipo_negocio = tracker.get_slot("tipo_negocio")

        # Validar que el negocio es del tipo correcto
        if tipo_negocio != "dentista":
            dispatcher.utter_message(text="⚠️ Este negocio no ofrece servicios dentales. ¿En qué puedo ayudarte?")
            return []

        if not negocio_id or not cliente_id:
            dispatcher.utter_message(text="⚠️ Necesito que inicies sesión para ayudarte con urgencias.")
            return []

        # Respuestas específicas según el tipo de urgencia
        respuestas = {
            "urgencia_dental_dolor": {
                "mensaje": "🚨 **Urgencia por dolor intenso**\n\n"
                          "Entiendo que es muy molesto. Te voy a buscar el hueco más cercano disponible.\n\n"
                          "**Mientras tanto:**\n"
                          "• Toma un analgésico si tienes (ibuprofeno 400mg)\n"
                          "• Aplica frío en la mejilla (nunca directamente al diente)\n"
                          "• Evita alimentos muy calientes o fríos\n\n"
                          "¿Cuándo puedes venir? ¿Hoy, mañana, o pasado?",
                "es_urgencia": True
            },
            "urgencia_dental_bracket": {
                "mensaje": "🦷 **Bracket despegado/caído**\n\n"
                          "¡Tranquilo/a! Es algo común con la ortodoncia.\n\n"
                          "**Importante:** Si lo tienes, guárdalo en una bolsita.\n\n"
                          "Te voy a buscar una cita de urgencia próxima para que te lo vuelvan a pegar.\n\n"
                          "¿Cuándo te viene mejor? ¿Puedes hoy o prefieres mañana?",
                "es_urgencia": True
            },
            "urgencia_dental_diente": {
                "mensaje": "🚨 **URGENCIA: Diente roto/caído**\n\n"
                          "Esto es importante. Necesitas atención rápida.\n\n"
                          "**MUY IMPORTANTE:**\n"
                          "• Si encontraste el diente o el pedazo, GUÁRDALO\n"
                          "• Mantenlo en leche o saliva (nunca en agua)\n"
                          "• No lo limpies con productos químicos\n"
                          "• Tráelo a la cita\n\n"
                          "Te voy a buscar el primer hueco disponible HOY si es posible.\n\n"
                          "¿Puedes venir en las próximas horas?",
                "es_urgencia": True
            },
            "perdida_empaste": {
                "mensaje": "🔧 **Empaste perdido**\n\n"
                          "No te preocupes, te busco una cita próxima para reponértelo.\n\n"
                          "**Consejos hasta la cita:**\n"
                          "• Evita masticar por ese lado\n"
                          "• No tomes alimentos muy dulces\n"
                          "• Cepilla con cuidado la zona\n\n"
                          "¿Prefieres venir hoy, mañana o pasado mañana?",
                "es_urgencia": False
            }
        }

        respuesta_config = respuestas.get(intent, {
            "mensaje": "Veo que tienes una urgencia dental. Déjame buscarte el primer hueco disponible.\n\n¿Cuándo puedes venir?",
            "es_urgencia": True
        })

        dispatcher.utter_message(text=respuesta_config["mensaje"])

        # Marcar como urgencia en el slot para priorizar disponibilidad
        return [
            SlotSet("es_urgencia", respuesta_config["es_urgencia"]),
            SlotSet("servicio", "Urgencia" if respuesta_config["es_urgencia"] else None)
        ]

class ActionBuscarUrgenciaProxima(Action):
    """Busca específicamente huecos de urgencia (hoy o mañana)"""

    def name(self) -> Text:
        return "action_buscar_urgencia_proxima"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        negocio_id = tracker.get_slot("negocio_id")
        
        if not negocio_id:
            dispatcher.utter_message(text="No puedo buscar disponibilidad sin saber el negocio.")
            return []

        try:
            # Buscar huecos para HOY
            hoy = datetime.now().strftime('%Y-%m-%d')
            response_hoy = requests.get(
                f"{API_URL}/negocios/{negocio_id}/disponibilidad",
                params={"fecha": hoy},
                timeout=5
            )

            # Buscar huecos para MAÑANA
            manana = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            response_manana = requests.get(
                f"{API_URL}/negocios/{negocio_id}/disponibilidad",
                params={"fecha": manana},
                timeout=5
            )

            huecos_hoy = response_hoy.json() if response_hoy.status_code == 200 else []
            huecos_manana = response_manana.json() if response_manana.status_code == 200 else []

            mensaje = "📅 **Huecos de urgencia disponibles:**\n\n"

            if huecos_hoy:
                mensaje += f"🔴 **HOY ({hoy}):**\n"
                for hueco in huecos_hoy[:3]:  # Solo mostrar primeros 3
                    mensaje += f"   • {hueco}\n"
                mensaje += "\n"

            if huecos_manana:
                mensaje += f"🟡 **MAÑANA ({manana}):**\n"
                for hueco in huecos_manana[:3]:
                    mensaje += f"   • {hueco}\n"
                mensaje += "\n"

            if not huecos_hoy and not huecos_manana:
                mensaje = "😔 No hay huecos disponibles hoy ni mañana.\n\n"
                mensaje += "Déjame buscar en los próximos días. ¿Qué día te vendría bien?"
            else:
                mensaje += "Dime cuál te viene mejor y te lo reservo. 🦷"

            dispatcher.utter_message(text=mensaje)
            return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al buscar huecos de urgencia: {str(e)}")
            return []
