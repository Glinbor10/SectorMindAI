from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests
from datetime import datetime, timedelta

# --- CONFIGURACIÓN API ---
API_URL = "http://localhost:5000"


class ActionSetContexto(Action):
    """Captura los metadatos del frontend (cliente_id, negocio_id) al iniciar conversación"""

    def name(self) -> Text:
        return "action_set_contexto"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Obtener metadatos del mensaje inicial
        metadata = tracker.latest_message.get('metadata', {})
        
        cliente_id = metadata.get('cliente_id')
        negocio_id = metadata.get('negocio_id')
        negocio_nombre = metadata.get('negocio_nombre')

        # Guardar en slots para usar en las siguientes actions
        return [
            SlotSet("cliente_id", cliente_id),
            SlotSet("negocio_id", negocio_id),
            SlotSet("negocio", negocio_nombre)
        ]


class ActionNormalizarServicio(Action):
    """Detecta el servicio que quiere el usuario y lo normaliza"""

    def name(self) -> Text:
        return "action_normalizar_servicio"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        mensaje_usuario = tracker.latest_message.get('text', '').lower()
        negocio_nombre = tracker.get_slot("negocio")
        negocio_id = tracker.get_slot("negocio_id")

        if not negocio_id:
            dispatcher.utter_message(text="No sé en qué negocio estás. Por favor, selecciona uno desde la web.")
            return []

        try:
            # Consultar servicios reales del negocio desde la API
            response = requests.get(f"{API_URL}/negocios/{negocio_id}/servicios", timeout=5)
            
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude cargar los servicios. Intenta de nuevo.")
                return []

            servicios_disponibles = response.json()
            
            if not servicios_disponibles:
                dispatcher.utter_message(text="Este negocio no tiene servicios configurados.")
                return []

            # Buscar coincidencia fuzzy
            servicio_detectado = None
            servicio_id = None
            
            for servicio in servicios_disponibles:
                nombre_servicio = servicio['nombre'].lower()
                # Búsqueda flexible: si alguna palabra clave coincide
                palabras = nombre_servicio.split()
                if any(palabra in mensaje_usuario for palabra in palabras if len(palabra) > 3):
                    servicio_detectado = servicio['nombre']
                    servicio_id = servicio['id']
                    break
            
            if servicio_detectado:
                return [
                    SlotSet("servicio", servicio_detectado),
                    SlotSet("servicio_id", servicio_id)
                ]
            else:
                # No se encontró, ofrecer opciones
                opciones = ", ".join([s['nombre'] for s in servicios_disponibles])
                dispatcher.utter_message(
                    text=f"No entendí qué servicio quieres. Tenemos: {opciones}"
                )
                return [SlotSet("servicio", None)]

        except Exception as e:
            dispatcher.utter_message(text=f"Error al conectar con el servidor: {str(e)}")
            return []


class ActionMostrarDisponibilidad(Action):
    """Muestra los horarios disponibles para el servicio seleccionado"""

    def name(self) -> Text:
        return "action_mostrar_disponibilidad"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        servicio = tracker.get_slot("servicio")

        if not negocio_id or not servicio_id:
            dispatcher.utter_message(text="Necesito saber qué servicio quieres primero.")
            return []

        try:
            # Consultar disponibilidad para los próximos 7 días
            horarios_por_dia = {}
            hoy = datetime.now().date()

            for i in range(7):  # Próximos 7 días
                fecha = hoy + timedelta(days=i)
                fecha_str = fecha.strftime('%Y-%m-%d')

                response = requests.post(
                    f"{API_URL}/disponibilidad",
                    json={
                        "negocio_id": negocio_id,
                        "servicio_id": servicio_id,
                        "fecha": fecha_str
                    },
                    timeout=5
                )

                if response.status_code == 200:
                    data = response.json()
                    horarios = data.get('disponibles', [])
                    if horarios:
                        # Guardar solo los primeros 5 horarios por día
                        horarios_por_dia[fecha_str] = horarios[:5]

            if not horarios_por_dia:
                dispatcher.utter_message(
                    text=f"Lo siento, no hay horarios disponibles para {servicio} en los próximos días."
                )
                return []

            # Formatear mensaje de disponibilidad
            mensaje = f"📅 Horarios disponibles para **{servicio}**:\n\n"
            for fecha_str, horarios in list(horarios_por_dia.items())[:3]:  # Solo mostrar 3 días
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                dia_texto = self._formatear_dia(fecha_obj)
                horas = [h.split()[1][:5] for h in horarios[:3]]  # Solo hora HH:MM
                mensaje += f"**{dia_texto}**: {', '.join(horas)}\n"

            mensaje += "\n¿Para qué día quieres reservar? (Ej: 'mañana', 'hoy', 'el lunes')"

            dispatcher.utter_message(text=mensaje)
            
            # Guardar disponibilidad en slot para uso posterior
            return [SlotSet("horarios_disponibles", horarios_por_dia)]

        except Exception as e:
            dispatcher.utter_message(text=f"Error al consultar disponibilidad: {str(e)}")
            return []

    def _formatear_dia(self, fecha: datetime) -> str:
        hoy = datetime.now().date()
        if fecha.date() == hoy:
            return "Hoy"
        elif fecha.date() == hoy + timedelta(days=1):
            return "Mañana"
        else:
            dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            return f"{dias[fecha.weekday()]} {fecha.day}/{fecha.month}"


class ActionReservarCita(Action):
    """Crea la reserva final en el sistema"""

    def name(self) -> Text:
        return "action_reservar_cita"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Obtener datos de los slots
        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        servicio = tracker.get_slot("servicio")
        fecha_texto = tracker.get_slot("fecha")
        horarios_disponibles = tracker.get_slot("horarios_disponibles")

        if not all([cliente_id, negocio_id, servicio_id]):
            dispatcher.utter_message(text="Falta información para completar la reserva.")
            return []

        try:
            # Interpretar la fecha que dijo el usuario
            fecha_reserva = self._interpretar_fecha(fecha_texto, horarios_disponibles)

            if not fecha_reserva:
                dispatcher.utter_message(
                    text="No pude entender la fecha. Por favor, dime 'hoy', 'mañana' o un día específico."
                )
                return []

            # Crear la cita en el backend
            response = requests.post(
                f"{API_URL}/citas",
                json={
                    "cliente_id": cliente_id,
                    "negocio_id": negocio_id,
                    "servicio_id": servicio_id,
                    "fecha_hora_cita": fecha_reserva
                },
                timeout=5
            )

            if response.status_code == 201:
                # Formatear fecha para mostrar
                fecha_obj = datetime.strptime(fecha_reserva, '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                dispatcher.utter_message(
                    text=f"✅ ¡Reserva confirmada!\n\n"
                         f"**Servicio:** {servicio}\n"
                         f"**Fecha:** {fecha_legible}\n\n"
                         f"Te esperamos. ¡Gracias por confiar en nosotros!"
                )
                return [
                    SlotSet("servicio", None),
                    SlotSet("servicio_id", None),
                    SlotSet("fecha", None),
                    SlotSet("horarios_disponibles", None)
                ]
            else:
                error_msg = response.json().get('error', 'Error desconocido')
                dispatcher.utter_message(
                    text=f"❌ No se pudo crear la reserva: {error_msg}"
                )
                return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al reservar: {str(e)}")
            return []

    def _interpretar_fecha(self, texto_fecha: str, horarios_disponibles: dict) -> str:
        """Convierte 'mañana', 'hoy', etc. en una fecha-hora específica"""
        if not texto_fecha or not horarios_disponibles:
            return None

        texto_lower = texto_fecha.lower()
        hoy = datetime.now().date()

        # Mapear texto a fecha
        if "hoy" in texto_lower:
            fecha_objetivo = hoy
        elif "mañana" in texto_lower or "manana" in texto_lower:
            fecha_objetivo = hoy + timedelta(days=1)
        elif "pasado" in texto_lower:
            fecha_objetivo = hoy + timedelta(days=2)
        else:
            # Intentar interpretar día de la semana
            dias_semana = {
                'lunes': 0, 'martes': 1, 'miercoles': 2, 'miércoles': 2,
                'jueves': 3, 'viernes': 4, 'sabado': 5, 'sábado': 5, 'domingo': 6
            }
            dia_encontrado = None
            for dia_nombre, dia_num in dias_semana.items():
                if dia_nombre in texto_lower:
                    dia_encontrado = dia_num
                    break
            
            if dia_encontrado is not None:
                dias_hasta = (dia_encontrado - hoy.weekday()) % 7
                if dias_hasta == 0:
                    dias_hasta = 7  # Si es el mismo día, ir a la próxima semana
                fecha_objetivo = hoy + timedelta(days=dias_hasta)
            else:
                # Si no se entiende, usar mañana por defecto
                fecha_objetivo = hoy + timedelta(days=1)

        fecha_str = fecha_objetivo.strftime('%Y-%m-%d')

        # Buscar el primer horario disponible de ese día
        if fecha_str in horarios_disponibles:
            horarios = horarios_disponibles[fecha_str]
            if horarios:
                return horarios[0]  # Devolver el primer slot disponible

        return None