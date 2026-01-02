"""
Acciones para reservar citas
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from datetime import datetime

from .utils import limpiar_flujo, obtener_horarios_disponibles, formatear_horarios_display
from .extractores import ExtractorFechaHora


class ActionReservarCita(Action):
    """PASO 2: Extrae SOLO fecha, muestra horarios del día y pide hora"""

    def name(self) -> Text:
        return "action_reservar_cita"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        flujo_activo = tracker.get_slot("flujo_activo")
        
        if flujo_activo != "reserva_fecha":
            print(f"⚠️ ActionReservarCita: flujo_activo={flujo_activo}, ignorando")
            return []

        servicio = tracker.get_slot("servicio")
        horarios_disponibles = tracker.get_slot("horarios_disponibles")
        fecha_texto = tracker.latest_message.get('text', '')

        print(f"🔄 ActionReservarCita - Fecha: '{fecha_texto}'")

        if not horarios_disponibles:
            dispatcher.utter_message(text="No hay horarios disponibles.")
            return limpiar_flujo()

        try:
            # Detectar cancelación
            if self._detectar_cambio_intencion(fecha_texto):
                dispatcher.utter_message(text="Entendido, cancelamos la reserva. ¿En qué más puedo ayudarte?")
                return limpiar_flujo()

            # Extraer SOLO fecha (sin hora)
            fecha_str = ExtractorFechaHora.extraer_solo_fecha(fecha_texto, horarios_disponibles)

            if not fecha_str:
                dispatcher.utter_message(text="No entendí la fecha. Dime 'viernes 30', 'mañana' o un día específico.")
                return []

            # Obtener horarios del día seleccionado
            horarios_dia = horarios_disponibles.get(fecha_str, [])
            
            if not horarios_dia:
                dispatcher.utter_message(text=f"No hay horarios disponibles para ese día. Elige otro.")
                return []

            # Formatear fecha legible
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
            dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            dia_texto = f"{dias_es[fecha_obj.weekday()]} {fecha_obj.day:02d}/{fecha_obj.month:02d}"
            
            # Extraer horas (sin fecha)
            horas = [h.split()[1][:5] for h in horarios_dia]
            
            mensaje = f"📅 <b>Fecha seleccionada:</b> {dia_texto}\n\n"
            mensaje += f"⏰ <b>Horarios disponibles:</b> {', '.join(horas)}\n\n"
            mensaje += "¿A qué hora prefieres?"
            
            dispatcher.utter_message(text=mensaje)
            
            return [
                SlotSet("flujo_activo", "reserva_hora"),
                SlotSet("fecha_reserva", fecha_str),
                SlotSet("horarios_dia", horarios_dia)
            ]

        except Exception as e:
            dispatcher.utter_message(text=f"Error: {str(e)}")
            return limpiar_flujo()

    def _detectar_cambio_intencion(self, texto):
        texto_lower = texto.lower()
        palabras_salir = ['anular', 'cancelar', 'no quiero', 'cambiar', 'salir', 'nada', 'olvidar']
        return any(palabra in texto_lower for palabra in palabras_salir)


class ActionConfirmarHoraReserva(Action):
    """PASO 3: Extrae hora y crea la reserva final"""

    def name(self) -> Text:
        return "action_confirmar_hora_reserva"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        import requests
        import os

        API_URL = os.getenv("API_URL", "http://backend:5000")
        flujo_activo = tracker.get_slot("flujo_activo")
        
        if flujo_activo != "reserva_hora":
            print(f"⚠️ ActionConfirmarHoraReserva: flujo_activo={flujo_activo}, ignorando")
            return []

        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        servicio = tracker.get_slot("servicio")
        fecha_str = tracker.get_slot("fecha_reserva")
        horarios_dia = tracker.get_slot("horarios_dia")
        hora_texto = tracker.latest_message.get('text', '')

        print(f"🔄 ActionConfirmarHoraReserva - Hora: '{hora_texto}'")

        if not all([cliente_id, negocio_id, servicio_id, fecha_str, horarios_dia]):
            dispatcher.utter_message(text="Falta información para completar la reserva.")
            return limpiar_flujo()

        try:
            # Extraer SOLO hora
            slot_completo = ExtractorFechaHora.extraer_solo_hora(hora_texto, horarios_dia)

            if not slot_completo:
                dispatcher.utter_message(text="No entendí la hora. ¿Cuál prefieres?")
                return []

            # Crear cita
            payload = {
                "cliente_id": cliente_id,
                "negocio_id": negocio_id,
                "servicio_id": servicio_id,
                "fecha_hora_cita": slot_completo
            }
            print(f"📤 POST /citas payload: {payload}")
            
            response = requests.post(
                f"{API_URL}/citas",
                json=payload,
                timeout=5
            )
            
            print(f"📥 Response status: {response.status_code}, body: {response.text}")

            if response.status_code in (200, 201):
                fecha_obj = datetime.strptime(slot_completo, '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                dispatcher.utter_message(
                    text=f"✅ <b>¡Reserva confirmada!</b>\n\n"
                         f"<b>Servicio:</b> {servicio}\n"
                         f"<b>Fecha:</b> {fecha_legible}\n\n"
                         f"¡Gracias por confiar en nosotros!"
                )
                return limpiar_flujo()
            else:
                error_msg = response.json().get('error', 'Error desconocido') if response.text else 'Sin respuesta'
                dispatcher.utter_message(text=f"❌ No se pudo crear la reserva: {error_msg}")
                return limpiar_flujo()

        except Exception as e:
            dispatcher.utter_message(text=f"Error: {str(e)}")
            return limpiar_flujo()
