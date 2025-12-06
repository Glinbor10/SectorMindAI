from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests
from datetime import datetime, timedelta

# --- CONFIGURACIÓN API ---
API_URL = "http://localhost:5000"

# Importar actions específicas de contexto (urgencias solamente)
from .dentista_actions import (
    ActionUrgenciaDental,
    ActionBuscarUrgenciaProxima
)
from .peluqueria_actions import (
    ActionUrgenciaPeluqueria
)
from .fisioterapia_actions import (
    ActionUrgenciaFisioterapia
)


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

        # Consultar tipo de negocio desde la API
        tipo_negocio = None
        if negocio_id:
            try:
                response = requests.get(f"{API_URL}/negocios/{negocio_id}", timeout=5)
                if response.status_code == 200:
                    negocio_info = response.json()
                    tipo_negocio = negocio_info.get('tipo_negocio')
            except Exception as e:
                print(f"Error consultando tipo de negocio: {e}")

        # Guardar en slots para usar en las siguientes actions
        return [
            SlotSet("cliente_id", cliente_id),
            SlotSet("negocio_id", negocio_id),
            SlotSet("negocio", negocio_nombre),
            SlotSet("tipo_negocio", tipo_negocio)
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

        if not cliente_id:
            dispatcher.utter_message(text="Debes iniciar sesión para ver tus citas.")
            return []

        try:
            # Consultar citas del usuario en este negocio
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
            
            # Filtrar solo citas futuras y confirmadas
            hoy = datetime.now()
            citas_futuras = [
                c for c in citas 
                if datetime.strptime(c['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S') > hoy
                and c['estado'] == 'confirmado'
            ]

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

            mensaje += "Si necesitas cancelar alguna, dime '**cancela mi cita del [día]**'"

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
                and c['estado'] == 'confirmado'
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


class ActionResponderBotChallenge(Action):
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