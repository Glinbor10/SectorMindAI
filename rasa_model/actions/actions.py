from typing import Any, Text, Dict, List
import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from fuzzywuzzy import fuzz
from datetime import datetime
import json

# URL base de tu API de Flask (Terminal 1)
FLASK_API_BASE_URL = "http://localhost:5000"

# --- UTILIDADES DE CONEXIÓN ---

def get_negocios_y_servicios():
    """Obtiene la lista completa de negocios y servicios desde la API de Flask."""
    try:
        # 1. Obtener todos los negocios
        response_negocios = requests.get(f"{FLASK_API_BASE_URL}/negocios")
        response_negocios.raise_for_status() # Lanza error si el estado no es 200
        negocios_data = response_negocios.json()

        # 2. Obtener los servicios para cada negocio
        servicios_por_negocio = {}
        for negocio in negocios_data:
            response_servicios = requests.get(f"{FLASK_API_BASE_URL}/negocios/{negocio['id']}/servicios")
            response_servicios.raise_for_status()
            negocio['servicios'] = response_servicios.json()
            servicios_por_negocio[negocio['nombre']] = negocio['servicios']

        return negocios_data, servicios_por_negocio

    except requests.exceptions.RequestException as e:
        print(f"ERROR: No se pudo conectar con la API de Flask: {e}")
        return [], {}

# --- ACCIONES PERSONALIZADAS ---

class ActionValidarEntidades(Action):
    """
    Valida el negocio y el servicio usando FuzzyWuzzy y obtiene los IDs reales de la BD.
    Guarda los IDs y los nombres corregidos en los slots.
    """
    def name(self) -> Text:
        return "action_validar_entidades"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        negocio_nombre = tracker.get_slot("negocio")
        servicio_nombre = tracker.get_slot("servicio")
        
        # Slots que se actualizarán
        slots = []

        # Obtener datos de la BD
        negocios_list, servicios_map = get_negocios_y_servicios()
        if not negocios_list:
            dispatcher.utter_message(text="Lo siento, el sistema de reservas está caído. Por favor, inténtalo más tarde.")
            return [] # Detiene la conversación

        # 1. VALIDAR NEGOCIO
        negocio_encontrado = None
        mejor_score_negocio = 0
        
        # Buscar el mejor match usando FuzzyWuzzy
        for negocio in negocios_list:
            # Usamos el ratio Parcial para manejar negocios con nombres largos o cortos
            score = fuzz.partial_ratio(negocio_nombre.lower(), negocio['nombre'].lower())
            
            if score > mejor_score_negocio:
                mejor_score_negocio = score
                negocio_encontrado = negocio

        # Si el score es alto (ej. 80 o más), asumimos que es correcto.
        if negocio_encontrado and mejor_score_negocio >= 80:
            slots.append(SlotSet("negocio", negocio_encontrado['nombre']))
            slots.append(SlotSet("negocio_id", negocio_encontrado['id']))
            print(f"DEBUG: Negocio corregido a {negocio_encontrado['nombre']} (ID: {negocio_encontrado['id']})")
        else:
            # Si no se encuentra o el score es muy bajo
            dispatcher.utter_message(text=f"No encontré el negocio '{negocio_nombre}'. ¿Podrías deletrearlo o darme un nombre más exacto?")
            return [SlotSet("negocio", None)] # Resetea el slot para volver a preguntar


        # 2. VALIDAR SERVICIO (Solo si el negocio fue validado)
        if negocio_encontrado and servicio_nombre:
            servicios_negocio = servicios_map.get(negocio_encontrado['nombre'], [])
            servicio_encontrado = None
            mejor_score_servicio = 0

            for servicio in servicios_negocio:
                score = fuzz.ratio(servicio_nombre.lower(), servicio['nombre'].lower())
                
                if score > mejor_score_servicio:
                    mejor_score_servicio = score
                    servicio_encontrado = servicio

            # Si el score es alto (ej. 85 o más), asumimos que es correcto.
            if servicio_encontrado and mejor_score_servicio >= 85:
                slots.append(SlotSet("servicio", servicio_encontrado['nombre']))
                slots.append(SlotSet("servicio_id", servicio_encontrado['id']))
                print(f"DEBUG: Servicio corregido a {servicio_encontrado['nombre']} (ID: {servicio_encontrado['id']})")
            else:
                # Si no se encuentra un match claro
                nombres_servicios = ", ".join([s['nombre'] for s in servicios_negocio])
                dispatcher.utter_message(text=f"No reconozco el servicio '{servicio_nombre}' en {negocio_encontrado['nombre']}. Los servicios disponibles son: {nombres_servicios}")
                return slots + [SlotSet("servicio", None)] # Resetea el slot para volver a preguntar

        # Si todo fue validado (o faltaba el servicio, que se pedirá después)
        return slots


class ActionMostrarDisponibilidad(Action):
    """
    Llama al endpoint /disponibilidad de Flask para obtener y mostrar los tramos horarios libres.
    """
    def name(self) -> Text:
        return "action_mostrar_disponibilidad"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Obtenemos los IDs y la fecha extraída por Rasa
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        fecha_bruta = tracker.get_slot("fecha") # Rasa devuelve una fecha o un token temporal

        # 1. PRE-PROCESAR LA FECHA (Rasa Duckling)
        # Rasa extrae la fecha en formato ISO8601 (YYYY-MM-DD), o una referencia temporal.
        # Aquí simplificamos, asumiendo que ya tenemos un YYYY-MM-DD del slot 'fecha'.
        # Si la entidad 'fecha' es un objeto complejo (entidad Duckling), debemos parsearlo:
        
        # En la práctica real, 'fecha' es una lista de diccionarios del NLU.
        # Simplificamos asumiendo que si el slot tiene valor, es la fecha a consultar.
        
        # Intentamos obtener solo la parte YYYY-MM-DD
        if isinstance(fecha_bruta, str):
            # Asumimos que la fecha es el primer token (ej. '2025-11-28')
            try:
                # Esto es una simplificación. Duckling puede devolver más info.
                fecha_consulta = datetime.strptime(fecha_bruta.split('T')[0], '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                # Si no es un formato esperado, volvemos a preguntar
                dispatcher.utter_message(text="No entendí bien la fecha. Por favor, especifica el día (ej. 'el martes' o '25 de diciembre').")
                return [SlotSet("fecha", None)] # Resetea el slot

        # 2. LLAMAR A LA API DE DISPONIBILIDAD
        payload = {
            "negocio_id": negocio_id,
            "servicio_id": servicio_id,
            "fecha": fecha_consulta # YYYY-MM-DD
        }

        try:
            response = requests.post(f"{FLASK_API_BASE_URL}/disponibilidad", json=payload)
            response.raise_for_status()
            disponibilidad = response.json()
        except requests.exceptions.RequestException as e:
            dispatcher.utter_message(text="Hubo un error al consultar la disponibilidad. ¿Podrías probar con otra fecha?")
            return []

        # 3. PROCESAR Y MOSTRAR RESULTADO
        tramos_libres = disponibilidad.get('tramos_libres', [])
        
        if not tramos_libres:
            dispatcher.utter_message(text=f"Lo siento, no hay huecos disponibles para ese servicio el {fecha_consulta}. ¿Quieres probar otro día?")
            return [SlotSet("fecha", None)]
        
        # Mostrar las primeras 5 opciones (para no saturar)
        opciones_mostrar = tramos_libres[:5]
        
        mensaje = f"Encontré {len(tramos_libres)} huecos el {fecha_consulta}. Estas son las primeras opciones:\n"
        for i, tramo in enumerate(opciones_mostrar):
            # Formato: 2025-11-28 10:00:00 -> 10:00
            hora = datetime.strptime(tramo, '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
            mensaje += f"  - {hora}\n"
            
        mensaje += "¿Qué hora prefieres? Dime, por ejemplo, 'la de las 10:30'."
        
        # Guardamos la lista completa en un slot para usarla en la reserva
        return [
            SlotSet("disponibilidad", tramos_libres),
            SlotSet("fecha_consulta", fecha_consulta), # Guardamos la fecha limpia
            SlotSet("fecha", None), # Reseteamos el slot 'fecha' para que el usuario pueda responder con la HORA
            SlotSet("tramos_mostrar", opciones_mostrar) # Guardamos las 5 opciones mostradas
        ]

        
class ActionReservarCita(Action):
    """
    Finaliza la reserva llamando al endpoint POST /citas de Flask.
    """
    def name(self) -> Text:
        return "action_reservar_cita"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Obtenemos todos los datos necesarios
        negocio = tracker.get_slot("negocio")
        servicio = tracker.get_slot("servicio")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        
        # El slot 'fecha' después de action_mostrar_disponibilidad contiene la HORA elegida
        hora_elegida_bruta = tracker.get_slot("fecha") 
        fecha_consulta = tracker.get_slot("fecha_consulta") # Contiene YYYY-MM-DD

        # 1. COMBINAR FECHA Y HORA (y encontrar el match en la lista de disponibilidad)
        tramos_libres = tracker.get_slot("disponibilidad")

        # Esto es una simplificación: asumimos que el usuario dice la HORA exacta (ej. "las 10 y media")
        # En la práctica, necesitarías un extractor de hora más robusto.
        
        # Intentamos encontrar la hora elegida dentro de los tramos disponibles.
        cita_final = None
        for tramo in tramos_libres:
            # Si el texto de la hora elegida (ej. "10:30") se parece a la hora del tramo (ej. "10:30:00")
            if hora_elegida_bruta in tramo or datetime.strptime(tramo, '%Y-%m-%d %H:%M:%S').strftime('%H:%M') == hora_elegida_bruta:
                 cita_final = tramo
                 break

        if not cita_final:
            dispatcher.utter_message(text="No he podido confirmar la hora exacta. Por favor, selecciona una de las horas que te di.")
            return [SlotSet("fecha", None)]

        # 2. LLAMAR A LA API DE RESERVA
        payload = {
            "negocio_id": negocio_id,
            "servicio_id": servicio_id,
            "fecha_hora_cita": cita_final # Formato YYYY-MM-DD HH:MM:SS
        }

        try:
            response = requests.post(f"{FLASK_API_BASE_URL}/citas", json=payload)
            response.raise_for_status() 
            
            # Si la API devuelve éxito
            dispatcher.utter_message(text=f"¡Reserva confirmada! Tienes una cita para {servicio} en {negocio} el día {cita_final}."
                                          " ¡Te esperamos! ¿Necesitas algo más?")

        except requests.exceptions.HTTPError as e:
            # Si el backend lanza un error (ej. solapamiento 409)
            error_msg = response.json().get('error', 'Error desconocido en el servidor.')
            dispatcher.utter_message(text=f"Lo siento, la reserva no pudo completarse. El servidor dice: {error_msg}. Por favor, vuelve a intentarlo.")
        except requests.exceptions.RequestException as e:
            dispatcher.utter_message(text="Error de conexión con el sistema de reservas. El backend no responde.")

        # Limpiar slots de reserva después de intentar
        return [
            SlotSet("negocio", None), 
            SlotSet("servicio", None), 
            SlotSet("fecha", None), 
            SlotSet("disponibilidad", None),
            SlotSet("negocio_id", None),
            SlotSet("servicio_id", None),
            SlotSet("fecha_consulta", None),
            SlotSet("tramos_mostrar", None)
        ]