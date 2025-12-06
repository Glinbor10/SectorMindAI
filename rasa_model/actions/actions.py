from typing import Any, Text, Dict, List
import requests
import json
from datetime import datetime, timedelta
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from fuzzywuzzy import fuzz, process 

# URL base de tu API de Flask
FLASK_API_BASE_URL = "http://localhost:5000"

# --- UTILIDADES ---

def get_negocios_y_servicios():
    """Obtiene la lista completa de negocios y servicios desde la API de Flask."""
    try:
        response_negocios = requests.get(f"{FLASK_API_BASE_URL}/negocios")
        response_negocios.raise_for_status()
        negocios_data = response_negocios.json()

        for negocio in negocios_data:
            try:
                # Llamada al nuevo endpoint que acabas de crear
                response_servicios = requests.get(f"{FLASK_API_BASE_URL}/negocios/{negocio['id']}/servicios")
                if response_servicios.status_code == 200:
                    negocio['servicios'] = response_servicios.json()
                else:
                    negocio['servicios'] = []
            except:
                negocio['servicios'] = []

        return negocios_data, None
    except Exception as e:
        print(f"Error conectando con Flask: {e}")
        return [], None

def parse_fecha_relativa(texto_fecha):
    """Convierte 'hoy', 'mañana' a YYYY-MM-DD. Si no sabe, devuelve el texto original."""
    if not texto_fecha:
        return None
    
    texto = texto_fecha.lower().strip()
    hoy = datetime.now()

    if "hoy" in texto:
        return hoy.strftime("%Y-%m-%d")
    elif "mañana" in texto and "pasado" not in texto:
        return (hoy + timedelta(days=1)).strftime("%Y-%m-%d")
    elif "pasado mañana" in texto:
        return (hoy + timedelta(days=2)).strftime("%Y-%m-%d")
    
    # Si ya parece una fecha YYYY-MM-DD, la dejamos igual
    # (Aquí podrías añadir más lógica si quieres)
    return texto

# --- ACCIONES ---

class ActionValidarEntidades(Action):
    def name(self) -> Text:
        return "action_validar_entidades"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        negocio_slot = tracker.get_slot("negocio")
        servicio_slot = tracker.get_slot("servicio")
        
        negocios_data, _ = get_negocios_y_servicios()
        eventos_a_retornar = []
        negocio_validado = None

        # 1. Validar Negocio
        if negocio_slot:
            if negocios_data:
                nombres_reales = [n['nombre'] for n in negocios_data]
                mejor_coincidencia, puntaje = process.extractOne(negocio_slot, nombres_reales)
                
                if puntaje > 80:
                    negocio_validado = mejor_coincidencia
                    eventos_a_retornar.append(SlotSet("negocio", negocio_validado))
                    negocio_obj = next((n for n in negocios_data if n['nombre'] == negocio_validado), None)
                    if negocio_obj:
                        eventos_a_retornar.append(SlotSet("negocio_id", negocio_obj['id']))
                else:
                    dispatcher.utter_message(text=f"No encuentro el negocio '{negocio_slot}'. ¿Quizás {mejor_coincidencia}?")
                    return [SlotSet("negocio", None)]
            else:
                 dispatcher.utter_message(text="Error de conexión con la base de datos.")

        # 2. Validar Servicio (Contextual)
        if servicio_slot and negocio_validado:
            negocio_obj = next((n for n in negocios_data if n['nombre'] == negocio_validado), None)
            
            if negocio_obj and 'servicios' in negocio_obj and negocio_obj['servicios']:
                servicios_validos = [s['nombre'] for s in negocio_obj['servicios']]
                mejor_servicio, puntaje_serv = process.extractOne(servicio_slot, servicios_validos)

                if puntaje_serv > 80:
                    eventos_a_retornar.append(SlotSet("servicio", mejor_servicio))
                    servicio_obj = next((s for s in negocio_obj['servicios'] if s['nombre'] == mejor_servicio), None)
                    if servicio_obj:
                        eventos_a_retornar.append(SlotSet("servicio_id", servicio_obj['id']))
                else:
                    dispatcher.utter_message(text=f"En **{negocio_validado}** no hacemos '{servicio_slot}'. "
                                                  f"Ofrecemos: {', '.join(servicios_validos)}.")
                    eventos_a_retornar.append(SlotSet("servicio", None))
                    eventos_a_retornar.append(SlotSet("servicio_id", None))
            else:
                 dispatcher.utter_message(text=f"El negocio {negocio_validado} no tiene servicios disponibles ahora.")

        return eventos_a_retornar


class ActionMostrarDisponibilidad(Action):
    def name(self) -> Text:
        return "action_mostrar_disponibilidad"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        negocio_id = tracker.get_slot("negocio_id")
        fecha_raw = tracker.get_slot("fecha")

        if not negocio_id or not fecha_raw:
            dispatcher.utter_message(text="Necesito saber el negocio y la fecha.")
            return []

        # TRADUCCIÓN DE FECHA ("mañana" -> "2025-12-07")
        fecha_real = parse_fecha_relativa(fecha_raw)
        
        # Guardamos la fecha convertida en el slot para usarla luego al reservar
        eventos = [SlotSet("fecha", fecha_real)]

        try:
            payload = {"negocio_id": negocio_id, "fecha": fecha_real}
            # Llamada al nuevo endpoint de citas.py
            response = requests.post(f"{FLASK_API_BASE_URL}/disponibilidad", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                horarios = data.get('horarios', [])
                
                if horarios:
                    lista_horas = ", ".join(horarios[:5]) # Mostramos solo los 5 primeros para no saturar
                    dispatcher.utter_message(text=f"Para el {fecha_real}, tengo libres: {lista_horas}...")
                    eventos.append(SlotSet("disponibilidad", horarios))
                else:
                    dispatcher.utter_message(text=f"Lo siento, el {fecha_real} está completo.")
            else:
                 dispatcher.utter_message(text="Error consultando horarios en el servidor.")
        
        except Exception as e:
            dispatcher.utter_message(text=f"Error de conexión: {e}")

        return eventos


class ActionReservarCita(Action):
    def name(self) -> Text:
        return "action_reservar_cita"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Recuperamos los datos limpios
        negocio = tracker.get_slot("negocio")
        servicio = tracker.get_slot("servicio")
        fecha_dia = tracker.get_slot("fecha") # "2025-12-07"
        
        # OJO: Aquí Rasa debería haber preguntado la hora exacta en otro paso, 
        # pero para esta demo, asumiremos que el usuario dijo la hora en el último mensaje
        # o simplificaremos cogiendo la primera hora disponible si no se especificó (riesgo).
        
        # En un flujo real, deberías tener un slot 'hora'. 
        # Vamos a intentar coger la última entidad de hora detectada o usar un default.
        
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")

        # Simulamos que el usuario eligió la primera hora libre si no dijo nada más
        # (Esto es solo para que la demo no falle, en prod necesitas slot de hora)
        disponibilidad = tracker.get_slot("disponibilidad")
        hora_elegida = "10:00" # Default
        
        if disponibilidad and len(disponibilidad) > 0:
             hora_elegida = disponibilidad[0]

        # Construimos el timestamp final: "2025-12-07 10:00:00"
        fecha_hora_final = f"{fecha_dia} {hora_elegida}:00"

        payload = {
            "negocio_id": negocio_id,
            "servicio_id": servicio_id,
            "fecha_hora_cita": fecha_hora_final
        }

        try:
            response = requests.post(f"{FLASK_API_BASE_URL}/citas", json=payload)
            if response.status_code == 201 or response.status_code == 200:
                dispatcher.utter_message(text=f"¡Hecho! Reserva confirmada: {servicio} en {negocio} para el {fecha_hora_final}.")
            else:
                dispatcher.utter_message(text="No pude guardar la reserva. Quizás alguien te quitó el hueco.")
        except Exception as e:
            dispatcher.utter_message(text="Error crítico conectando con el servidor de reservas.")

        # Limpiamos slots para la siguiente reserva
        return [SlotSet("negocio", None), SlotSet("servicio", None), SlotSet("fecha", None), SlotSet("disponibilidad", None)]