"""
Acciones para cambiar horario de citas
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from datetime import datetime
import requests

from .utils import limpiar_flujo, obtener_horarios_disponibles, formatear_horarios_display, API_URL
from .extractores import ExtractorFechaHora


class ActionCambiarHorario(Action):
    def name(self) -> Text:
        return "action_cambiar_horario"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        cliente_id = tracker.get_slot("cliente_id")
        if not cliente_id:
            dispatcher.utter_message(text="Por favor, inicia sesión primero para cambiar tu cita.")
            return limpiar_flujo()

        try:
            response = requests.get(
                f"{API_URL}/citas",
                params={"cliente_id": cliente_id, "negocio_id": tracker.get_slot("negocio_id")},
                timeout=5
            )
            
            if response.status_code == 200:
                citas = response.json()  # Backend returns list directly
                citas_futuras = [c for c in citas if datetime.fromisoformat(c["fecha_hora_cita"]) > datetime.now()]
                
                if not citas_futuras:
                    dispatcher.utter_message(text="No tienes citas futuras para cambiar.")
                    return limpiar_flujo()
                
                if len(citas_futuras) == 1:
                    cita = citas_futuras[0]
                    fecha_actual = datetime.fromisoformat(cita["fecha_hora_cita"])
                    
                    # Obtener horarios disponibles para el servicio
                    horarios = obtener_horarios_disponibles(cita.get("negocio_id"), cita.get("servicio_id"))
                    
                    msg = (f"Tienes una cita el {fecha_actual.strftime('%d/%m/%Y a las %H:%M')} "
                           f"para {cita.get('servicio_nombre', 'tu servicio')}.\n")
                    
                    if horarios:
                        msg += "\n" + formatear_horarios_display(horarios)
                    
                    msg += "\n¿Para qué día quieres cambiarla?"
                    
                    dispatcher.utter_message(text=msg)
                    return [
                        SlotSet("flujo_activo", "cambiar_fecha"),
                        SlotSet("cita_id_cambio", cita["id"]),
                        SlotSet("servicio_id", cita.get("servicio_id")),
                        SlotSet("servicio_nombre", cita.get("servicio_nombre")),
                        SlotSet("negocio_id", cita.get("negocio_id")),
                        SlotSet("horarios_disponibles", horarios)
                    ]
                else:
                    msg_citas = "Tienes varias citas. ¿Cuál quieres cambiar?\n"
                    for idx, cita in enumerate(citas_futuras, 1):
                        fecha = datetime.fromisoformat(cita["fecha_hora_cita"])
                        servicio_nombre = cita.get('servicio_nombre', 'Servicio')
                        msg_citas += f"{idx}. {servicio_nombre} - {fecha.strftime('%d/%m/%Y a las %H:%M')}\n"
                    
                    msg_citas += "\nResponde con el número de la cita."
                    dispatcher.utter_message(text=msg_citas)
                    
                    return [
                        SlotSet("flujo_activo", "cambiar_seleccion"),
                        SlotSet("citas_disponibles", citas_futuras)
                    ]
            else:
                dispatcher.utter_message(text="No pude consultar tus citas. Intenta de nuevo.")
                return limpiar_flujo()
                
        except Exception as e:
            print(f"Error en cambiar_horario: {e}")
            dispatcher.utter_message(text="Hubo un problema. Intenta de nuevo más tarde.")
            return limpiar_flujo()


class ActionSeleccionarCitaCambio(Action):
    def name(self) -> Text:
        return "action_seleccionar_cita_cambio"

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
                fecha_actual = datetime.fromisoformat(cita["fecha_hora_cita"])
                
                msg = (f"Seleccionaste la cita del {fecha_actual.strftime('%d/%m/%Y a las %H:%M')} "
                       f"para {cita.get('servicio_nombre', 'tu servicio')}.\n"
                       f"¿Para qué día quieres cambiarla?")
                
                dispatcher.utter_message(text=msg)
                return [
                    SlotSet("flujo_activo", "cambiar_fecha"),
                    SlotSet("cita_id_cambio", cita["id"]),
                    SlotSet("servicio_id", cita.get("servicio_id")),
                    SlotSet("negocio_id", cita.get("negocio_id")),
                    SlotSet("citas_disponibles", None)
                ]
            else:
                dispatcher.utter_message(text="Número inválido. Selecciona un número de la lista.")
                return []
        except ValueError:
            dispatcher.utter_message(text="Por favor, responde con el número de la cita que quieres cambiar.")
            return []


class ActionConfirmarFechaCambio(Action):
    def name(self) -> Text:
        return "action_confirmar_fecha_cambio"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        cita_id_cambio = tracker.get_slot("cita_id_cambio")
        
        if not all([negocio_id, servicio_id, cita_id_cambio]):
            dispatcher.utter_message(text="Falta información. Intenta cambiar la cita de nuevo.")
            return limpiar_flujo()
        
        ultimo_mensaje = tracker.latest_message.get("text", "")
        
        horarios_disponibles = obtener_horarios_disponibles(negocio_id, servicio_id)
        if not horarios_disponibles:
            dispatcher.utter_message(text="No hay horarios disponibles. Contacta con el negocio.")
            return limpiar_flujo()
        
        fecha_objetivo = ExtractorFechaHora.extraer_solo_fecha(ultimo_mensaje, horarios_disponibles)
        
        if fecha_objetivo:
            fecha_str = fecha_objetivo.strftime("%Y-%m-%d")
            horarios_dia = horarios_disponibles.get(fecha_str, [])
            
            if horarios_dia:
                nombre_dia = fecha_objetivo.strftime("%A")
                dia_numero = fecha_objetivo.strftime("%d/%m")
                
                msg_horarios = formatear_horarios_display({fecha_str: horarios_dia}, incluir_fecha=False)
                
                msg = f"📅 Fecha seleccionada: {nombre_dia.capitalize()} {dia_numero}\n\n{msg_horarios}\n¿A qué hora prefieres?"
                dispatcher.utter_message(text=msg)
                
                return [
                    SlotSet("fecha_reserva", fecha_str),
                    SlotSet("horarios_dia", horarios_dia),
                    SlotSet("flujo_activo", "cambiar_hora")
                ]
            else:
                dispatcher.utter_message(text=f"No hay horarios disponibles para el {fecha_objetivo.strftime('%d/%m')}. Prueba con otra fecha.")
                return []
        else:
            dispatcher.utter_message(text="No entendí la fecha. Por favor, especifica el día (ej: 'lunes 15', 'para el 20', 'mañana').")
            return []


class ActionConfirmarHoraCambio(Action):
    def name(self) -> Text:
        return "action_confirmar_hora_cambio"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        fecha_reserva = tracker.get_slot("fecha_reserva")
        horarios_dia = tracker.get_slot("horarios_dia")
        cita_id_cambio = tracker.get_slot("cita_id_cambio")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        
        if not all([fecha_reserva, horarios_dia, cita_id_cambio, negocio_id, servicio_id]):
            dispatcher.utter_message(text="Falta información. Reinicia el proceso de cambio.")
            return limpiar_flujo()
        
        ultimo_mensaje = tracker.latest_message.get("text", "")
        
        hora_objetivo = ExtractorFechaHora.extraer_solo_hora(ultimo_mensaje, horarios_dia)
        
        print(f"🔍 Debug cambio hora:")
        print(f"   fecha_reserva: '{fecha_reserva}'")
        print(f"   hora_objetivo: '{hora_objetivo}'")
        
        if hora_objetivo:
            # hora_objetivo es un timestamp completo "YYYY-MM-DD HH:MM:SS"
            # Extraer solo la hora HH:MM:SS
            hora_str = hora_objetivo.split()[1]  # "HH:MM:SS"
            fecha_hora_str = f"{fecha_reserva} {hora_str}"
            
            print(f"   hora_str extraída: '{hora_str}'")
            print(f"   fecha_hora_str final: '{fecha_hora_str}'")
            print(f"📝 Cambiar cita {cita_id_cambio} a: {fecha_hora_str}")
            
            try:
                response = requests.put(
                    f"{API_URL}/citas/{cita_id_cambio}",
                    json={"fecha_hora_cita": fecha_hora_str, "servicio_id": servicio_id},
                    timeout=5
                )
                
                print(f"📥 PUT Response: {response.status_code}, {response.text}")
                
                if response.status_code == 200:
                    # Extraer solo hora para mostrar (HH:MM)
                    hora_display = hora_str[:5]
                    fecha_dt = datetime.strptime(fecha_reserva, "%Y-%m-%d")
                    msg = f"✅ ¡Cita cambiada exitosamente!\n📅 Nueva fecha: {fecha_dt.strftime('%d/%m/%Y')} a las {hora_display}"
                    dispatcher.utter_message(text=msg)
                    return limpiar_flujo()
                else:
                    error_msg = response.json().get('error', 'Error desconocido') if response.text else 'Sin respuesta'
                    dispatcher.utter_message(text=f"No pude cambiar la cita: {error_msg}")
                    return limpiar_flujo()
                    
            except Exception as e:
                print(f"Error al cambiar cita: {e}")
                dispatcher.utter_message(text="Hubo un problema al cambiar la cita. Intenta más tarde.")
                return limpiar_flujo()
        else:
            dispatcher.utter_message(text="No entendí la hora. Especifica una hora disponible (ej: '10', '14:30', 'las diez y media').")
            return []
