# Acción submit del form de reserva
class ActionSubmitReservaForm(Action):
    def name(self) -> Text:
        return "action_submit_reserva_form"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        servicio = tracker.get_slot("servicio")
        fecha = tracker.get_slot("fecha")

        if not (cliente_id and negocio_id and servicio_id and fecha):
            dispatcher.utter_message(text="Faltan datos para completar la reserva. Por favor, indícame el servicio y la fecha/hora que deseas.")
            return []

        try:
            # Llamada a la API para reservar la cita
            response = requests.post(f"{API_URL}/citas", json={
                "cliente_id": cliente_id,
                "negocio_id": negocio_id,
                "servicio_id": servicio_id,
                "fecha_hora_cita": fecha,
                "estado": "confirmada"
            }, timeout=10)
            if response.status_code == 200:
                dispatcher.utter_message(text=f"✅ ¡Perfecto! Tu cita para '{servicio}' ha sido reservada para {fecha}.")
            else:
                dispatcher.utter_message(text="No se pudo completar la reserva. Intenta de nuevo o revisa los datos.")
        except Exception as e:
            dispatcher.utter_message(text=f"Error al reservar la cita: {str(e)}")
        return []
from typing import Any, Text, Dict, List
import os
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACIÓN API ---
# Usar hostname Docker por defecto
API_URL = os.getenv("API_URL", "http://backend:5000")


class ActionSetContexto(Action):
    def name(self) -> Text:
        return "action_set_contexto"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        metadata = tracker.latest_message.get('metadata', {})

        # Prioridad: metadata SIEMPRE que venga, incluso si cambia de negocio
        cliente_id = metadata.get('cliente_id') if 'cliente_id' in metadata else tracker.get_slot("cliente_id")
        negocio_id = metadata.get('negocio_id') if 'negocio_id' in metadata else tracker.get_slot("negocio_id")
        tipo_negocio = metadata.get('tipo_negocio') if 'tipo_negocio' in metadata else tracker.get_slot("tipo_negocio")
        negocio_nombre = metadata.get('negocio_nombre') if 'negocio_nombre' in metadata else tracker.get_slot("negocio")

        if negocio_id:
            try:
                response = requests.get(f"{API_URL}/negocios/{negocio_id}", timeout=5)
                if response.status_code == 200:
                    negocio_info = response.json()
                    tipo_negocio = negocio_info.get('tipo_negocio')
                    negocio_nombre = negocio_info.get('nombre')
            except Exception:
                pass


        # Enviar los slots actuales al frontend como mensaje JSON
        slots_actuales = {
            "cliente_id": cliente_id,
            "negocio_id": negocio_id,
            "tipo_negocio": tipo_negocio,
            "negocio_nombre": negocio_nombre
        }
        dispatcher.utter_message(text=f"[SLOTS] {slots_actuales}")
        return [
            SlotSet("cliente_id", cliente_id),
            SlotSet("negocio_id", negocio_id),
            SlotSet("tipo_negocio", tipo_negocio),
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
        tipo_negocio = tracker.get_slot("tipo_negocio")
        intent = tracker.latest_message.get('intent', {}).get('name', '')

        print(f"🔍 ActionNormalizarServicio - Mensaje: '{mensaje_usuario}'")
        print(f"   Negocio ID: {negocio_id}, Tipo: {tipo_negocio}, Intent: {intent}")

        if not negocio_id:
            dispatcher.utter_message(text="No sé en qué negocio estás. Por favor, selecciona uno desde la web.")
            return []

        # Filtro de servicios cruzados
        if tipo_negocio == "dentista" and any(word in mensaje_usuario for word in ["corte", "tinte", "masaje", "fisioterapia"]):
            dispatcher.utter_message(text="Este es un negocio dental. Ofrecemos servicios como limpieza, empaste, revisiones. ¿Qué necesitas?")
            return []
        elif tipo_negocio == "peluqueria" and any(word in mensaje_usuario for word in ["empaste", "diente", "masaje", "fisioterapia"]):
            dispatcher.utter_message(text="Esta es una peluquería. Ofrecemos cortes, tintes, peinados. ¿Qué necesitas?")
            return []
        elif tipo_negocio == "fisioterapia" and any(word in mensaje_usuario for word in ["empaste", "diente", "corte", "tinte"]):
            dispatcher.utter_message(text="Este es un centro de fisioterapia. Ofrecemos masajes, tratamientos musculares. ¿Qué necesitas?")
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

            # Buscar coincidencia fuzzy SIEMPRE, aunque el intent no sea de reserva
            servicio_detectado = None
            servicio_id = None
            print(f"   Buscando en {len(servicios_disponibles)} servicios...")
            for servicio in servicios_disponibles:
                nombre_servicio = servicio['nombre'].lower()
                palabras = nombre_servicio.split()
                palabras_filtradas = [p for p in palabras if len(p) > 3]
                print(f"     Servicio '{servicio['nombre']}' -> palabras clave: {palabras_filtradas}")
                if any(palabra in mensaje_usuario for palabra in palabras_filtradas):
                    servicio_detectado = servicio['nombre']
                    servicio_id = servicio['id']
                    print(f"     ✅ COINCIDENCIA ENCONTRADA: {servicio_detectado}")
                    break

            if servicio_detectado:
                print(f"   Resultado final: Servicio detectado = {servicio_detectado}")
                # Preguntar por fecha/hora, no reservar automáticamente
                dispatcher.utter_message(text=f"He detectado que quieres reservar el servicio '{servicio_detectado}'. ¿Para qué día y hora te gustaría reservar? Puedes decirme una fecha y hora concreta, o pedir ver los horarios disponibles.")
                return [
                    SlotSet("servicio", servicio_detectado),
                    SlotSet("servicio_id", servicio_id)
                ]
            else:
                print("   Resultado final: No se detectó ningún servicio")
                opciones = ", ".join([s['nombre'] for s in servicios_disponibles])
                dispatcher.utter_message(
                    text=f"No entendí qué servicio quieres. Tenemos: {opciones}"
                )
                from rasa_sdk.events import UserUtteranceReverted
                return [SlotSet("servicio", None), SlotSet("servicio_id", None), UserUtteranceReverted()]

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
            dispatcher.utter_message(text="Necesito saber qué servicio quieres primero. Por favor, dime qué servicio te interesa.")
            return []

        try:
            # Detectar si el usuario pide más opciones
            ultimo_intent = tracker.latest_message.get('intent', {}).get('name', '')
            dias_a_buscar = 14 if ultimo_intent == 'pedir_mas_opciones' else 7
            
            # Consultar disponibilidad para los próximos días
            horarios_por_dia = {}
            hoy = datetime.now().date()

            for i in range(dias_a_buscar):  # 7 o 14 días según el contexto
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
            if ultimo_intent == 'pedir_mas_opciones':
                mensaje = f"📅 **Aquí tienes más días disponibles para {servicio}:**\n\n"
                dias_mostrados = 0
                # Mostrar desde el día 6 en adelante si pide más opciones
                for fecha_str, horarios in list(horarios_por_dia.items())[5:10]:
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                    dia_texto = self._formatear_dia(fecha_obj)
                    horas = [h.split()[1][:5] for h in horarios[:3]]
                    mensaje += f"**{dia_texto}**: {', '.join(horas)}\n"
                    dias_mostrados += 1
            else:
                mensaje = f"📅 Horarios disponibles para **{servicio}**:\n\n"
                dias_mostrados = 0
                for fecha_str, horarios in list(horarios_por_dia.items())[:5]:
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                    dia_texto = self._formatear_dia(fecha_obj)
                    horas = [h.split()[1][:5] for h in horarios[:3]]
                    mensaje += f"**{dia_texto}**: {', '.join(horas)}\n"
                    dias_mostrados += 1

            if len(horarios_por_dia) > dias_mostrados:
                mensaje += f"\n💡 _Tenemos disponibilidad hasta {len(horarios_por_dia)} días adelante. Pregunta por 'más días' si quieres ver más opciones._\n"

            mensaje += "\n¿Para qué día quieres reservar? (Ej: 'mañana', 'hoy', 'el lunes')"

            dispatcher.utter_message(text=mensaje)
            
            # Guardar disponibilidad en slot para uso posterior
            # NO limpiar servicio_id y servicio para mantener contexto
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
                # Obtener tipo de negocio para emoji contextual
                tipo_negocio = tracker.get_slot("tipo_negocio")
                
                # Emojis específicos según tipo de negocio
                emoji_dict = {
                    "dentista": "🦷",
                    "fisioterapia": "🧘",
                    "peluqueria": "💇"
                }
                emoji = emoji_dict.get(tipo_negocio, "✅")
                
                # Formatear fecha para mostrar
                fecha_obj = datetime.strptime(fecha_reserva, '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                dispatcher.utter_message(
                    text=f"{emoji} ¡Reserva confirmada!\n\n"
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
        """Convierte 'mañana', 'hoy', etc. en una fecha-hora específica y busca coincidencia exacta de hora si se especifica."""
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

        # Buscar coincidencia exacta de hora si se especifica
        import re
        hora_match = re.search(r'(\d{1,2}):(\d{2})', texto_lower)
        hora_usuario = None
        if hora_match:
            hora_usuario = f"{int(hora_match.group(1)):02d}:{hora_match.group(2)}"

        if fecha_str in horarios_disponibles:
            horarios = horarios_disponibles[fecha_str]
            if hora_usuario:
                # Buscar coincidencia exacta de hora
                for slot in horarios:
                    if hora_usuario in slot:
                        return slot
            if horarios:
                return horarios[0]  # Si no se especificó hora, devolver el primer slot disponible

        return None


class ActionInfoNegocio(Action):
    """Proporciona información general sobre el negocio"""

    def name(self) -> Text:
        return "action_info_negocio"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        negocio_id = tracker.get_slot("negocio_id")
        negocio_nombre = tracker.get_slot("negocio")

        if not negocio_id:
            dispatcher.utter_message(text="No tengo información del negocio en este momento.")
            return []

        try:
            response = requests.get(f"{API_URL}/negocios/{negocio_id}", timeout=5)
            
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude obtener la información del negocio.")
                return []

            negocio = response.json()
            
            mensaje = f"📍 **{negocio['nombre']}**\n\n"
            
            if negocio.get('descripcion'):
                mensaje += f"{negocio['descripcion']}\n\n"
            
            if negocio.get('direccion'):
                mensaje += f"📌 **Dirección:** {negocio['direccion']}\n"
            
            mensaje += f"🏢 **Tipo:** {negocio.get('tipo_negocio', 'Negocio').capitalize()}\n\n"
            mensaje += "Pregúntame por horarios, servicios o reserva tu cita. 😊"

            dispatcher.utter_message(text=mensaje)
            return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al consultar información: {str(e)}")
            return []


class ActionMostrarHorarios(Action):
    """Muestra los horarios de apertura del negocio"""

    def name(self) -> Text:
        return "action_mostrar_horarios"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        negocio_id = tracker.get_slot("negocio_id")

        if not negocio_id:
            dispatcher.utter_message(text="No tengo información del negocio.")
            return []

        try:
            # Consultar horarios desde la base de datos
            response = requests.get(f"{API_URL}/negocios/{negocio_id}/horarios", timeout=5)
            
            if response.status_code == 404:
                dispatcher.utter_message(text="Este endpoint aún no está implementado. Déjame crear el endpoint primero.")
                return []
            
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude consultar los horarios.")
                return []

            horarios = response.json()
            
            if not horarios:
                dispatcher.utter_message(text="No tengo horarios configurados para este negocio.")
                return []

            # Organizar horarios por día
            dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            horarios_por_dia = {}
            
            for horario in horarios:
                dia = dias_semana[horario['dia_semana']]
                if dia not in horarios_por_dia:
                    horarios_por_dia[dia] = []
                horarios_por_dia[dia].append({
                    'apertura': horario['hora_apertura'][:5],
                    'cierre': horario['hora_cierre'][:5]
                })

            mensaje = "🕒 **Horarios de apertura:**\n\n"
            
            for dia in dias_semana:
                if dia in horarios_por_dia:
                    turnos = horarios_por_dia[dia]
                    if len(turnos) == 1:
                        mensaje += f"**{dia}:** {turnos[0]['apertura']} - {turnos[0]['cierre']}\n"
                    else:
                        horarios_texto = " y ".join([f"{t['apertura']}-{t['cierre']}" for t in turnos])
                        mensaje += f"**{dia}:** {horarios_texto}\n"

            dispatcher.utter_message(text=mensaje)
            return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al consultar horarios: {str(e)}")
            return []


class ActionListarServicios(Action):
    """Lista todos los servicios con precios y duración"""

    def name(self) -> Text:
        return "action_listar_servicios"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        negocio_id = tracker.get_slot("negocio_id")

        if not negocio_id:
            dispatcher.utter_message(text="No tengo información del negocio.")
            return []

        try:
            response = requests.get(f"{API_URL}/negocios/{negocio_id}/servicios", timeout=5)
            
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude cargar los servicios.")
                return []

            servicios = response.json()
            
            if not servicios:
                dispatcher.utter_message(text="Este negocio no tiene servicios configurados.")
                return []

            mensaje = "💇 **Servicios disponibles:**\n\n"
            
            for servicio in servicios:
                mensaje += f"**{servicio['nombre']}**\n"
                mensaje += f"   💰 {servicio['precio']}€ | ⏱️ {servicio['duracion_minutos']} min\n\n"

            mensaje += "¿Quieres reservar alguno? Dime cuál te interesa. 😊"

            dispatcher.utter_message(text=mensaje)
            return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al listar servicios: {str(e)}")
            return []


class ActionMostrarUbicacion(Action):
    """Muestra la ubicación del negocio"""

    def name(self) -> Text:
        return "action_mostrar_ubicacion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        negocio_id = tracker.get_slot("negocio_id")

        if not negocio_id:
            dispatcher.utter_message(text="No tengo información del negocio.")
            return []

        try:
            response = requests.get(f"{API_URL}/negocios/{negocio_id}", timeout=5)
            
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude obtener la ubicación.")
                return []

            negocio = response.json()
            direccion = negocio.get('direccion', 'No disponible')

            mensaje = f"📍 **Ubicación:**\n\n{direccion}\n\n"
            mensaje += "Puedes encontrarnos fácilmente en esta dirección. ¡Te esperamos!"

            dispatcher.utter_message(text=mensaje)
            return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al consultar ubicación: {str(e)}")
            return []


class ActionConsultarCitasUsuario(Action):
    """Muestra las citas del usuario"""

    def name(self) -> Text:
        return "action_consultar_citas_usuario"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")
        tipo_negocio = tracker.get_slot("tipo_negocio")
        intent_name = tracker.latest_message.get('intent', {}).get('name', '')

        print(f"🔍 ActionConsultarCitasUsuario - cliente_id: {cliente_id}, negocio_id: {negocio_id}, tipo_negocio: {tipo_negocio}")

        if not cliente_id:
            dispatcher.utter_message(text="Debes iniciar sesión para ver tus citas.")
            return []

        try:
            # Consultar citas del usuario en este negocio
            response = requests.get(
                f"{API_URL}/citas",
                params={
                    "cliente_id": cliente_id
                },
                timeout=5
            )
            
            print(f"   Respuesta API: status={response.status_code}, content={response.text[:500]}")
            
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude consultar tus citas.")
                return []

            citas = response.json()
            print(f"   Citas obtenidas: {len(citas)} citas totales")
            for c in citas[:3]:  # Mostrar primeras 3
                print(f"     Cita: {c.get('servicio_nombre')} - {c.get('fecha_hora_cita')} - estado: {c.get('estado')} - tipo: {c.get('tipo_negocio')}")
            
            # Filtrar por negocio si está especificado
            if negocio_id:
                citas_filtradas = [c for c in citas if c.get('negocio_id') == negocio_id]
                print(f"   Después de filtrar por negocio_id '{negocio_id}': {len(citas_filtradas)} citas")
                citas = citas_filtradas
            
            # Filtrar solo citas futuras y confirmadas
            hoy = datetime.now()
            print(f"   Fecha actual: {hoy}")
            citas_futuras = [
                c for c in citas 
                if datetime.strptime(c['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S') > hoy
                and c['estado'] == 'confirmada'
            ]
            print(f"   Citas futuras confirmadas: {len(citas_futuras)}")
            for c in citas_futuras[:3]:
                print(f"     Cita futura: {c.get('servicio_nombre')} - {c.get('fecha_hora_cita')}")
            
            if not citas_futuras:
                dispatcher.utter_message(
                    text="No tienes citas pendientes en este negocio. ¿Quieres reservar una? 😊"
                )
                return []

            mensaje = "📅 **Tus próximas citas:**\n\n"
            
            for cita in citas_futuras[:5]:  # Mostrar máximo 5
                fecha_obj = datetime.strptime(cita['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                mensaje += f"🔹 **{cita['servicio_nombre']}**\n"
                mensaje += f"   📆 {fecha_legible}\n"
                mensaje += f"   ⏱️ {cita['duracion_minutos']} minutos\n\n"

            mensaje += "Si quieres cancelar alguna, dime el **número de la cita**."

            dispatcher.utter_message(text=mensaje)
            return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al consultar citas: {str(e)}")
            return []


class ActionCancelarCita(Action):
    """Muestra las citas del usuario y solicita confirmación para cancelar"""

    def name(self) -> Text:
        return "action_cancelar_cita"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")
        cita_a_cancelar_id = tracker.get_slot("cita_a_cancelar_id")

        if not cliente_id:
            dispatcher.utter_message(text="Debes iniciar sesión para cancelar citas.")
            return []

        try:
            # Si ya tenemos ID de cita confirmada, proceder a cancelar
            if cita_a_cancelar_id:
                response = requests.delete(
                    f"{API_URL}/citas/{cita_a_cancelar_id}",
                    timeout=5
                )
                
                if response.status_code == 200 or response.status_code == 204:
                    dispatcher.utter_message(
                        text=f"✅ **Cita cancelada correctamente**\n\n"
                             f"Si cambias de opinión, puedes reservar otra cita cuando quieras."
                    )
                    return [SlotSet("cita_a_cancelar_id", None)]
                else:
                    dispatcher.utter_message(text="No pude cancelar la cita. Intenta más tarde.")
                    return [SlotSet("cita_a_cancelar_id", None)]

            # Si no hay ID, mostrar citas disponibles para cancelar
            response = requests.get(
                f"{API_URL}/citas",
                params={
                    "cliente_id": cliente_id,
                    "negocio_id": negocio_id
                },
                timeout=5
            )
            
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude consultar tus citas.")
                return []

            citas = response.json()
            
            # Filtrar citas futuras confirmadas
            hoy = datetime.now()
            citas_futuras = [
                c for c in citas 
                if datetime.strptime(c['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S') > hoy
                and c['estado'] == 'confirmada'
            ]

            if not citas_futuras:
                dispatcher.utter_message(text="No tienes citas pendientes para cancelar.")
                return []

            # Mostrar citas disponibles
            if len(citas_futuras) == 1:
                cita = citas_futuras[0]
                fecha_obj = datetime.strptime(cita['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                mensaje = f"📅 **Tienes esta cita pendiente:**\n\n"
                mensaje += f"🔹 **{cita['servicio_nombre']}**\n"
                mensaje += f"📆 {fecha_legible}\n"
                mensaje += f"⏱️ {cita['duracion_minutos']} minutos\n\n"
                mensaje += "¿Quieres cancelarla? Responde **'sí'** para confirmar o **'no'** para mantenerla."
                
                dispatcher.utter_message(text=mensaje)
                # Guardar el ID temporalmente para confirmar
                return [SlotSet("cita_a_cancelar_id", cita['id'])]
            else:
                mensaje = f"📅 **Tienes {len(citas_futuras)} citas pendientes:**\n\n"
                
                for i, cita in enumerate(citas_futuras, 1):
                    fecha_obj = datetime.strptime(cita['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
                    fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                    mensaje += f"**{i}.** {cita['servicio_nombre']} - {fecha_legible}\n"
                
                mensaje += "\n❌ **Para cancelar múltiples citas, cancélalas una a una.**\n"
                mensaje += "Responde con el **número de la cita** que quieres cancelar."
                
                dispatcher.utter_message(text=mensaje)
                # Guardar las citas en slot para selección
                return [SlotSet("citas_disponibles", citas_futuras)]

        except Exception as e:
            dispatcher.utter_message(text=f"Error al procesar cancelación: {str(e)}")
            return []


class ActionConfirmarCancelacion(Action):
    """Confirma la cancelación cuando el usuario selecciona número de cita"""

    def name(self) -> Text:
        return "action_confirmar_cancelacion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        mensaje_usuario = tracker.latest_message.get('text', '').strip()
        citas_disponibles = tracker.get_slot("citas_disponibles")

        if not citas_disponibles:
            dispatcher.utter_message(text="No hay citas para seleccionar. Intenta de nuevo.")
            return []

        try:
            # Intentar extraer número del mensaje
            numero = None
            for palabra in mensaje_usuario.split():
                if palabra.isdigit():
                    numero = int(palabra)
                    break
            
            if numero and 1 <= numero <= len(citas_disponibles):
                cita_seleccionada = citas_disponibles[numero - 1]
                fecha_obj = datetime.strptime(cita_seleccionada['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                mensaje = f"🔹 **{cita_seleccionada['servicio_nombre']}**\n"
                mensaje += f"📆 {fecha_legible}\n\n"
                mensaje += "¿Confirmas la cancelación? Responde **'sí'** o **'no'**."
                
                dispatcher.utter_message(text=mensaje)
                return [
                    SlotSet("cita_a_cancelar_id", cita_seleccionada['id']),
                    SlotSet("citas_disponibles", None)
                ]
            else:
                dispatcher.utter_message(text="Número inválido. Por favor, elige un número de la lista.")
                return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error: {str(e)}")
            return []


class ActionDenegarCancelacion(Action):
    """Cancela la cancelación cuando el usuario dice no"""

    def name(self) -> Text:
        return "action_denegar_cancelacion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Cancelación cancelada. Tu cita sigue activa.")
        return [SlotSet("cita_a_cancelar_id", None), SlotSet("citas_disponibles", None)]
    """Responde cuando el usuario pregunta qué es el bot"""

    def name(self) -> Text:
        return "action_responder_bot_challenge"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        negocio_id = tracker.get_slot("negocio_id")
        negocio_nombre = tracker.get_slot("negocio")

        if not negocio_id or not negocio_nombre:
            dispatcher.utter_message(
                text="Soy un asistente virtual de **Sector Mind AI**, tu plataforma inteligente de reservas."
            )
            return []

        try:
            # Obtener información del negocio para conocer al propietario
            response = requests.get(f"{API_URL}/negocios/{negocio_id}", timeout=5)
            
            if response.status_code != 200:
                dispatcher.utter_message(
                    text=f"Soy el asistente virtual de **{negocio_nombre}**, potenciado por **Sector Mind AI**."
                )
                return []

            negocio = response.json()
            propietario_nombre = negocio.get('propietario_nombre', 'nuestro equipo')

            mensaje = f"🤖 Soy el asistente virtual de **{negocio_nombre}**, gestionado por **{propietario_nombre}**.\n\n"
            mensaje += "Estoy aquí para ayudarte a:\n"
            mensaje += "✅ Consultar servicios y precios\n"
            mensaje += "✅ Ver horarios de apertura\n"
            mensaje += "✅ Reservar citas\n"
            mensaje += "✅ Gestionar tus reservas\n\n"
            mensaje += "¿En qué puedo ayudarte? 😊"

            dispatcher.utter_message(text=mensaje)
            return []

        except Exception as e:
            dispatcher.utter_message(
                text=f"Soy el asistente virtual de **{negocio_nombre}**, potenciado por **Sector Mind AI**."
            )
            return []


class ActionCancelarCitaConfirmada(Action):
    """Cancela la cita seleccionada y limpia slots relevantes"""

    def name(self) -> Text:
        return "action_cancelar_cita_confirmada"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        cliente_id = tracker.get_slot("cliente_id")
        cita_id = tracker.get_slot("cita_a_cancelar_id")
        tipo_negocio = tracker.get_slot("tipo_negocio")

        if not cliente_id:
            dispatcher.utter_message(text="Debes iniciar sesión para cancelar citas.")
            return []

        if not cita_id:
            dispatcher.utter_message(text="No tengo identificada la cita a cancelar.")
            return []

        try:
            response = requests.delete(f"{API_URL}/citas/{cita_id}", timeout=5)

            if response.status_code in (200, 204):
                # Emoji por tipo de negocio (coherencia visual)
                emoji_dict = {
                    "dentista": "🦷",
                    "fisioterapia": "🧘",
                    "peluqueria": "💇",
                }
                emoji = emoji_dict.get(tipo_negocio, "✅")

                # Usar utter para confirmación de eliminación
                dispatcher.utter_message(text=f"{emoji} Cita cancelada correctamente.")
                # Alternativa: dispatcher.utter_message(response="utter_confirmacion_eliminada")

                return [
                    SlotSet("cita_a_cancelar_id", None),
                    SlotSet("fecha", None),
                    SlotSet("servicio", None),
                ]
            else:
                dispatcher.utter_message(text="No pude cancelar la cita. Intenta más tarde.")
                return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al cancelar la cita: {str(e)}")
            return []