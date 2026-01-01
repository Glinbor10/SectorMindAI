from typing import Any, Text, Dict, List
import os, requests, re
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from datetime import datetime, timedelta
from dotenv import load_dotenv
from difflib import get_close_matches

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

        # Si estamos esperando fecha para reserva, redirigir a action_reservar_cita
        esperando_fecha = tracker.get_slot("esperando_fecha")
        if esperando_fecha:
            print("🔀 ActionNormalizarServicio: Detectado esperando_fecha=True, redirigiendo a action_reservar_cita")
            from rasa_sdk.events import FollowupAction
            return [FollowupAction("action_reservar_cita")]

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
                # Mensaje visual de transición
                dispatcher.utter_message(text=f"✅ Servicio detectado: <b>{servicio_detectado}</b>\n\nAhora te pediré la fecha y hora para tu cita ⏰.")

                # Mostrar horarios disponibles antes de activar el form
                try:
                    response = requests.post(
                        f"{API_URL}/disponibilidad",
                        json={
                            "negocio_id": negocio_id,
                            "servicio_id": servicio_id,
                            "fecha": None
                        },
                        timeout=5
                    )
                    horarios_por_dia = {}
                    hoy = datetime.now().date()
                    if response.status_code == 200:
                        data = response.json()
                        horarios = data.get('disponibles', {})
                        # Si la API devuelve todos los días juntos
                        if isinstance(horarios, dict):
                            horarios_por_dia = horarios
                        # Si la API devuelve solo un día
                        elif isinstance(horarios, list):
                            fecha_str = hoy.strftime('%Y-%m-%d')
                            horarios_por_dia[fecha_str] = horarios
                    # Si no hay datos, intentar los próximos 7 días
                    if not horarios_por_dia:
                        for i in range(7):
                            fecha = hoy + timedelta(days=i)
                            fecha_str = fecha.strftime('%Y-%m-%d')
                            resp = requests.post(
                                f"{API_URL}/disponibilidad",
                                json={
                                    "negocio_id": negocio_id,
                                    "servicio_id": servicio_id,
                                    "fecha": fecha_str
                                },
                                timeout=5
                            )
                            if resp.status_code == 200:
                                data = resp.json()
                                horarios = data.get('disponibles', [])
                                if horarios:
                                    horarios_por_dia[fecha_str] = horarios[:5]
                    if horarios_por_dia:
                        dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                        mensaje = f"📅 Horarios disponibles para <b>{servicio_detectado}</b> en los próximos días:\n\n"
                        dias_mostrados = 0
                        for fecha_str, horarios in list(horarios_por_dia.items())[:5]:
                            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                            dia_texto = f"{dias_es[fecha_obj.weekday()]} {fecha_obj.day:02d}/{fecha_obj.month:02d}"
                            horas = [h.split()[1][:5] for h in horarios[:3]]
                            mensaje += f"<b>{dia_texto}</b>: {', '.join(horas)}\n"
                            dias_mostrados += 1
                        dispatcher.utter_message(text=mensaje)
                    else:
                        dispatcher.utter_message(text="No hay horarios disponibles para este servicio en los próximos días.")
                        return []
                except Exception as e:
                    print(f"   Error al consultar horarios: {str(e)}")
                    dispatcher.utter_message(text=f"Error al consultar horarios: {str(e)}")
                    return []

                # NO activar formulario, solo guardar slots y horarios
                print(f"   💾 Guardando slots: servicio={servicio_detectado}, servicio_id={servicio_id}")
                print(f"   💾 Horarios guardados: {horarios_por_dia}")
                
                # Preguntar la fecha directamente
                dispatcher.utter_message(text="¿Para qué día y hora quieres la cita?")
                
                # Activar contexto de espera de fecha
                return [
                    SlotSet("servicio", servicio_detectado),
                    SlotSet("servicio_id", servicio_id),
                    SlotSet("horarios_disponibles", horarios_por_dia),
                    SlotSet("esperando_fecha", True)
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
                return [
                    SlotSet("horarios_disponibles", horarios_por_dia),
                    SlotSet("requested_slot", "fecha")
                ]

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
        horarios_disponibles = tracker.get_slot("horarios_disponibles")
        esperando_fecha = tracker.get_slot("esperando_fecha")
        cita_a_cancelar_id = tracker.get_slot("cita_a_cancelar_id")
        fecha_texto = None

        # Si hay cita_a_cancelar_id, redirigir a confirmar cambio de horario
        if cita_a_cancelar_id and esperando_fecha:
            print("🔀 ActionReservarCita: Detectado cita_a_cancelar_id, redirigiendo a action_confirmar_cambio_horario")
            from rasa_sdk.events import FollowupAction
            return [FollowupAction("action_confirmar_cambio_horario")]

        # Si estamos esperando fecha y no hay fecha en el slot, usar el último mensaje
        if esperando_fecha and not fecha_texto:
            fecha_texto = tracker.latest_message.get('text', '')
            print(f"📝 Capturando texto como fecha: '{fecha_texto}'")

        if not all([cliente_id, negocio_id, servicio_id]):
            dispatcher.utter_message(text="Falta información para completar la reserva.")
            return [SlotSet("esperando_fecha", False)]

        try:
            # Interpretar la fecha que dijo el usuario
            fecha_reserva = self._interpretar_fecha(fecha_texto, horarios_disponibles)

            if not fecha_reserva:
                dispatcher.utter_message(
                    text="No pude entender la fecha. Por favor, dime 'hoy', 'mañana' o un día específico."
                )
                return [SlotSet("esperando_fecha", True)]

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
                    SlotSet("horarios_disponibles", None),
                    SlotSet("esperando_fecha", False)
                ]
            else:
                error_msg = response.json().get('error', 'Error desconocido')
                dispatcher.utter_message(
                    text=f"❌ No se pudo crear la reserva: {error_msg}"
                )
                return [SlotSet("esperando_fecha", False)]

        except Exception as e:
            dispatcher.utter_message(text=f"Error al reservar: {str(e)}")
            return [SlotSet("esperando_fecha", False)]

    def _interpretar_fecha(self, texto_fecha: str, horarios_disponibles: dict) -> str:
        """Convierte 'mañana', 'hoy', 'viernes a las 10', etc. en una fecha-hora específica."""
        if not texto_fecha:
            return None

        texto_lower = texto_fecha.lower().strip()
        hoy = datetime.now().date()
        
        print(f"🕒 Interpretando fecha: '{texto_fecha}'")
        print(f"   Horarios disponibles: {horarios_disponibles}")

        # Extraer hora si se especifica
        import re
        hora_match = re.search(r'(\d{1,2})(?::(\d{2}))?', texto_lower)
        hora_especificada = None
        if hora_match:
            hora = int(hora_match.group(1))
            minuto = int(hora_match.group(2)) if hora_match.group(2) else 0
            hora_especificada = f"{hora:02d}:{minuto:02d}"
            print(f"   Hora especificada: {hora_especificada}")

        # Determinar el día objetivo
        fecha_objetivo = None
        
        # Palabras clave para fechas relativas
        if "hoy" in texto_lower:
            fecha_objetivo = hoy
            print(f"   Detectado 'hoy': {fecha_objetivo}")
        elif "mañana" in texto_lower or "manana" in texto_lower:
            fecha_objetivo = hoy + timedelta(days=1)
            print(f"   Detectado 'mañana': {fecha_objetivo}")
        elif "pasado" in texto_lower:
            fecha_objetivo = hoy + timedelta(days=2)
            print(f"   Detectado 'pasado mañana': {fecha_objetivo}")
        else:
            # Días de la semana
            dias_semana = {
                'lunes': 0, 'martes': 1, 'miercoles': 2, 'miércoles': 2,
                'jueves': 3, 'viernes': 4, 'sabado': 5, 'sábado': 5, 'domingo': 6
            }
            for dia_nombre, dia_num in dias_semana.items():
                if dia_nombre in texto_lower:
                    dias_hasta = (dia_num - hoy.weekday()) % 7
                    if dias_hasta == 0:
                        dias_hasta = 7
                    fecha_objetivo = hoy + timedelta(days=dias_hasta)
                    print(f"   Detectado '{dia_nombre}': {fecha_objetivo}")
                    break
        
        # Si no se encontró fecha específica, usar el primer día disponible
        if not fecha_objetivo:
            if horarios_disponibles:
                fechas_disponibles = sorted(horarios_disponibles.keys())
                if fechas_disponibles:
                    fecha_str = fechas_disponibles[0]
                    fecha_objetivo = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    print(f"   Sin fecha específica, usando primer día disponible: {fecha_str}")

        if not fecha_objetivo:
            print("   ❌ No se pudo determinar fecha objetivo")
            return None

        fecha_str = fecha_objetivo.strftime('%Y-%m-%d')
        print(f"   Fecha objetivo determinada: {fecha_str}")

        # Buscar horario en ese día específico
        if not horarios_disponibles or fecha_str not in horarios_disponibles:
            print(f"   ❌ No hay horarios disponibles para {fecha_str}")
            # Buscar el siguiente día disponible
            fechas_disponibles = sorted(horarios_disponibles.keys())
            for fecha_disponible in fechas_disponibles:
                if fecha_disponible >= fecha_str:
                    fecha_str = fecha_disponible
                    print(f"   ⚠️ Usando siguiente día disponible: {fecha_str}")
                    break
            else:
                return None

        horarios = horarios_disponibles.get(fecha_str, [])
        print(f"   Horarios disponibles ese día: {horarios}")
        
        if not horarios:
            print("   ❌ No hay slots disponibles")
            return None
            
        if hora_especificada:
            # Buscar coincidencia exacta de hora (formato completo o solo hora:minuto)
            for slot in horarios:
                # Extraer hora del slot (formato: '2026-01-07 09:30:00')
                slot_hora = slot.split()[1][:5]  # Extrae '09:30'
                if hora_especificada == slot_hora or hora_especificada in slot:
                    print(f"   ✅ Encontrado slot exacto: {slot}")
                    return slot
            # Si no hay coincidencia exacta, buscar la hora más cercana
            print(f"   ⚠️ No hay slot exacto para {hora_especificada}, usando primero disponible")
        
        # Usar el primer slot disponible del día correcto
        primer_slot = horarios[0]
        print(f"   ✅ Usando primer slot: {primer_slot}")
        return primer_slot


class ActionInfoNegocio(Action):
    """Proporciona información general sobre el negocio"""

    def name(self) -> Text:
        return "action_info_negocio"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Si estamos esperando fecha para reserva, redirigir a action_reservar_cita
        esperando_fecha = tracker.get_slot("esperando_fecha")
        if esperando_fecha:
            print("🔀 ActionInfoNegocio: Detectado esperando_fecha=True, redirigiendo a action_reservar_cita")
            from rasa_sdk.events import FollowupAction
            return [FollowupAction("action_reservar_cita")]

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

        # Si estamos esperando fecha para reserva, redirigir a action_reservar_cita
        esperando_fecha = tracker.get_slot("esperando_fecha")
        if esperando_fecha:
            print("🔀 ActionMostrarHorarios: Detectado esperando_fecha=True, redirigiendo a action_reservar_cita")
            from rasa_sdk.events import FollowupAction
            return [FollowupAction("action_reservar_cita")]

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

        # Si estamos esperando fecha para reserva, redirigir a action_reservar_cita
        esperando_fecha = tracker.get_slot("esperando_fecha")
        if esperando_fecha:
            print("🔀 ActionListarServicios: Detectado esperando_fecha=True, redirigiendo a action_reservar_cita")
            from rasa_sdk.events import FollowupAction
            return [FollowupAction("action_reservar_cita")]

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

        # Si estamos esperando fecha para reserva, redirigir a action_reservar_cita
        esperando_fecha = tracker.get_slot("esperando_fecha")
        if esperando_fecha:
            print("🔀 ActionMostrarUbicacion: Detectado esperando_fecha=True, redirigiendo a action_reservar_cita")
            from rasa_sdk.events import FollowupAction
            return [FollowupAction("action_reservar_cita")]

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

        # Si estamos esperando fecha para reserva, redirigir a action_reservar_cita
        esperando_fecha = tracker.get_slot("esperando_fecha")
        if esperando_fecha:
            print("🔀 ActionConsultarCitasUsuario: Detectado esperando_fecha=True, redirigiendo a action_reservar_cita")
            from rasa_sdk.events import FollowupAction
            return [FollowupAction("action_reservar_cita")]

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

        # Si estamos esperando fecha para reserva, redirigir a action_reservar_cita
        esperando_fecha = tracker.get_slot("esperando_fecha")
        if esperando_fecha:
            print("🔀 ActionCancelarCita: Detectado esperando_fecha=True, redirigiendo a action_reservar_cita")
            from rasa_sdk.events import FollowupAction
            return [FollowupAction("action_reservar_cita")]

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


class ActionFallbackInteligente(Action):
    """Fallback inteligente que redirige cuando esperando_fecha=True o busca servicios"""

    def name(self) -> Text:
        return "action_fallback_inteligente"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        mensaje_usuario = tracker.latest_message.get('text', '').lower()
        esperando_fecha = tracker.get_slot("esperando_fecha")

        print(f"🔍 Fallback inteligente - Mensaje: '{mensaje_usuario}'")
        print(f"   esperando_fecha: {esperando_fecha}")

        # PRIORIDAD 1: Si estamos esperando una fecha, redirigir INMEDIATAMENTE
        if esperando_fecha:
            print(f"   ⏩ Redirigiendo a action_reservar_cita")
            from rasa_sdk.events import FollowupAction
            return [FollowupAction("action_reservar_cita")]

        # PRIORIDAD 2: Si NO estamos esperando fecha, intentar detectar servicio
        negocio_id = tracker.get_slot("negocio_id")
        
        # Si no hay negocio, respuesta genérica
        if not negocio_id:
            dispatcher.utter_message(text="No he entendido bien. ¿Puedes repetirlo?")
            return []

        try:
            # Buscar si el mensaje coincide con algún servicio
            response = requests.get(f"{API_URL}/negocios/{negocio_id}/servicios", timeout=5)
            if response.status_code != 200:
                dispatcher.utter_message(text="No he entendido bien. ¿Puedes repetirlo?")
                return []

            servicios_disponibles = response.json()
            if not servicios_disponibles:
                dispatcher.utter_message(text="No he entendido bien. ¿Puedes repetirlo?")
                return []

            # Buscar coincidencia con servicios
            servicio_detectado = None
            servicio_id = None
            
            for servicio in servicios_disponibles:
                nombre_servicio = servicio['nombre'].lower()
                # Buscar coincidencia bidireccional:
                # 1. Palabras del servicio que están en el mensaje
                palabras_servicio = [p for p in nombre_servicio.split() if len(p) > 3]
                # 2. Palabras del mensaje que están en el servicio
                palabras_mensaje = [p for p in mensaje_usuario.split() if len(p) > 3]
                
                # Coincidencia exacta si alguna palabra del servicio está en el mensaje
                if any(palabra in mensaje_usuario for palabra in palabras_servicio):
                    servicio_detectado = servicio['nombre']
                    servicio_id = servicio['id']
                    print(f"     ✅ Servicio detectado en fallback (palabra servicio en mensaje): {servicio_detectado}")
                    break
                
                # O si alguna palabra del mensaje está en el nombre del servicio
                if any(palabra in nombre_servicio for palabra in palabras_mensaje):
                    servicio_detectado = servicio['nombre']
                    servicio_id = servicio['id']
                    print(f"     ✅ Servicio detectado en fallback (palabra mensaje en servicio): {servicio_detectado}")
                    break
                
                # Fuzzy matching: buscar palabras similares con errores tipográficos
                for palabra_usuario in palabras_mensaje:
                    # Buscar coincidencias similares en las palabras del servicio (tolerancia 70%)
                    matches = get_close_matches(palabra_usuario, palabras_servicio, n=1, cutoff=0.70)
                    if matches:
                        servicio_detectado = servicio['nombre']
                        servicio_id = servicio['id']
                        print(f"     ✅ Servicio detectado en fallback (fuzzy: '{palabra_usuario}' ~ '{matches[0]}'): {servicio_detectado}")
                        break
                
                if servicio_detectado:
                    break

            if servicio_detectado:
                # Activar el flujo de reserva
                dispatcher.utter_message(text=f"✅ Perfecto, quieres reservar: <b>{servicio_detectado}</b>\n\nAhora te pediré la fecha y hora para tu cita ⏰.")
                
                # Consultar horarios disponibles
                try:
                    horarios_por_dia = {}
                    hoy = datetime.now().date()
                    for i in range(7):
                        fecha = hoy + timedelta(days=i)
                        fecha_str = fecha.strftime('%Y-%m-%d')
                        resp = requests.post(
                            f"{API_URL}/disponibilidad",
                            json={
                                "negocio_id": negocio_id,
                                "servicio_id": servicio_id,
                                "fecha": fecha_str
                            },
                            timeout=5
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            horarios = data.get('disponibles', [])
                            if horarios:
                                horarios_por_dia[fecha_str] = horarios[:5]
                    
                    if horarios_por_dia:
                        dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                        mensaje = f"📅 Horarios disponibles para <b>{servicio_detectado}</b>:\n\n"
                        for fecha_str, horarios in list(horarios_por_dia.items())[:5]:
                            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                            dia_texto = f"{dias_es[fecha_obj.weekday()]} {fecha_obj.day:02d}/{fecha_obj.month:02d}"
                            horas = [h.split()[1][:5] for h in horarios[:3]]
                            mensaje += f"<b>{dia_texto}</b>: {', '.join(horas)}\n"
                        dispatcher.utter_message(text=mensaje)
                except Exception:
                    pass

                # Preguntar fecha y activar contexto
                dispatcher.utter_message(text="¿Para qué día y hora quieres la cita?")
                
                return [
                    SlotSet("servicio", servicio_detectado),
                    SlotSet("servicio_id", servicio_id),
                    SlotSet("horarios_disponibles", horarios_por_dia if 'horarios_por_dia' in locals() else None),
                    SlotSet("esperando_fecha", True)
                ]
            else:
                # No se detectó servicio, mostrar mensaje de ayuda
                dispatcher.utter_message(
                    text="No he entendido bien. ¿Puedes repetirlo? Puedo ayudarte con:\n" +
                         "📅 Reservar citas\n" +
                         "💰 Consultar servicios\n" +
                         "📍 Ver ubicación\n" +
                         "🕒 Ver horarios"
                )
                return []

        except Exception as e:
            dispatcher.utter_message(text="No he entendido bien. ¿Puedes repetirlo?")
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


class ActionCambiarHorario(Action):
    """Permite cambiar la fecha/hora de una cita existente"""

    def name(self) -> Text:
        return "action_cambiar_horario"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # Si estamos esperando fecha para reserva, redirigir a action_reservar_cita
        esperando_fecha = tracker.get_slot("esperando_fecha")
        if esperando_fecha:
            print("🔀 ActionCambiarHorario: Detectado esperando_fecha=True, redirigiendo a action_reservar_cita")
            from rasa_sdk.events import FollowupAction
            return [FollowupAction("action_reservar_cita")]

        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")

        if not cliente_id:
            dispatcher.utter_message(text="Debes iniciar sesión para cambiar citas.")
            return []

        try:
            # Consultar citas del usuario
            response = requests.get(
                f"{API_URL}/citas",
                params={"cliente_id": cliente_id, "negocio_id": negocio_id},
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
                dispatcher.utter_message(text="No tienes citas pendientes para modificar.")
                return []

            # Mostrar citas disponibles
            if len(citas_futuras) == 1:
                cita = citas_futuras[0]
                fecha_obj = datetime.strptime(cita['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                mensaje = f"📅 **Cita actual:**\n\n"
                mensaje += f"🔹 **{cita['servicio_nombre']}**\n"
                mensaje += f"📆 {fecha_legible}\n\n"
                mensaje += "¿A qué día y hora quieres cambiarla? (Ej: 'mañana a las 10', 'viernes a las 15:00')"
                
                dispatcher.utter_message(text=mensaje)
                # Guardar ID de cita a cambiar y servicio_id para consultar disponibilidad
                return [
                    SlotSet("cita_a_cancelar_id", cita['id']),
                    SlotSet("servicio_id", cita['servicio_id']),
                    SlotSet("servicio", cita['servicio_nombre'])
                ]
            else:
                mensaje = f"📅 **Tienes {len(citas_futuras)} citas pendientes:**\n\n"
                
                for i, cita in enumerate(citas_futuras, 1):
                    fecha_obj = datetime.strptime(cita['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
                    fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                    mensaje += f"**{i}.** {cita['servicio_nombre']} - {fecha_legible}\n"
                
                mensaje += "\n📝 **Responde con el número de la cita que quieres cambiar.**"
                
                dispatcher.utter_message(text=mensaje)
                return [
                    SlotSet("citas_disponibles", citas_futuras),
                    SlotSet("esperando_seleccion_cambio", True)
                ]

        except Exception as e:
            dispatcher.utter_message(text=f"Error al procesar cambio: {str(e)}")
            return []


class ActionSeleccionarCitaCambio(Action):
    """Selecciona la cita a cambiar cuando el usuario responde con un número"""

    def name(self) -> Text:
        return "action_seleccionar_cita_cambio"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        mensaje_usuario = tracker.latest_message.get('text', '').strip()
        citas_disponibles = tracker.get_slot("citas_disponibles")
        negocio_id = tracker.get_slot("negocio_id")

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
                
                # Consultar disponibilidad para el servicio
                try:
                    servicio_id = cita_seleccionada['servicio_id']
                    horarios_por_dia = {}
                    hoy = datetime.now().date()

                    for i in range(7):
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
                                horarios_por_dia[fecha_str] = horarios[:5]
                    
                    if horarios_por_dia:
                        dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                        mensaje = f"📅 **Cita a cambiar:**\n"
                        mensaje += f"🔹 {cita_seleccionada['servicio_nombre']} - {fecha_legible}\n\n"
                        mensaje += f"📅 **Horarios disponibles:**\n\n"
                        
                        for fecha_str, horarios in list(horarios_por_dia.items())[:5]:
                            fecha_obj_disp = datetime.strptime(fecha_str, '%Y-%m-%d')
                            dia_texto = f"{dias_es[fecha_obj_disp.weekday()]} {fecha_obj_disp.day:02d}/{fecha_obj_disp.month:02d}"
                            horas = [h.split()[1][:5] for h in horarios[:3]]
                            mensaje += f"**{dia_texto}**: {', '.join(horas)}\n"
                        
                        mensaje += "\n¿A qué día y hora quieres cambiarla? (Ej: 'mañana a las 10', 'viernes a las 15:00')"
                        dispatcher.utter_message(text=mensaje)
                    else:
                        mensaje = f"📅 **Cita a cambiar:**\n"
                        mensaje += f"🔹 {cita_seleccionada['servicio_nombre']} - {fecha_legible}\n\n"
                        mensaje += "¿A qué día y hora quieres cambiarla? (Ej: 'mañana a las 10', 'viernes a las 15:00')"
                        dispatcher.utter_message(text=mensaje)
                
                except Exception:
                    mensaje = f"📅 **Cita a cambiar:**\n"
                    mensaje += f"🔹 {cita_seleccionada['servicio_nombre']} - {fecha_legible}\n\n"
                    mensaje += "¿A qué día y hora quieres cambiarla? (Ej: 'mañana a las 10', 'viernes a las 15:00')"
                    dispatcher.utter_message(text=mensaje)
                
                return [
                    SlotSet("cita_a_cancelar_id", cita_seleccionada['id']),
                    SlotSet("servicio_id", cita_seleccionada['servicio_id']),
                    SlotSet("servicio", cita_seleccionada['servicio_nombre']),
                    SlotSet("citas_disponibles", None),
                    SlotSet("horarios_disponibles", horarios_por_dia if 'horarios_por_dia' in locals() else None),
                    SlotSet("esperando_seleccion_cambio", False),
                    SlotSet("esperando_fecha", True)
                ]
            else:
                dispatcher.utter_message(text="Número inválido. Por favor, elige un número de la lista.")
                return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error: {str(e)}")
            return []


class ActionConfirmarCambioHorario(Action):
    """Procesa el cambio de horario una vez que el usuario da la nueva fecha"""

    def name(self) -> Text:
        return "action_confirmar_cambio_horario"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        cita_id = tracker.get_slot("cita_a_cancelar_id")
        esperando_fecha = tracker.get_slot("esperando_fecha")
        
        print(f"🔄 ActionConfirmarCambioHorario - cita_id: {cita_id}, esperando_fecha: {esperando_fecha}")
        
        # Si estamos esperando fecha para reserva (no cambio), redirigir
        if esperando_fecha and not cita_id:
            print("🔀 ActionConfirmarCambioHorario: Detectado esperando_fecha=True sin cita_id, redirigiendo a action_reservar_cita")
            from rasa_sdk.events import FollowupAction
            return [FollowupAction("action_reservar_cita")]

        fecha_texto = tracker.latest_message.get('text', '')
        horarios_disponibles = tracker.get_slot("horarios_disponibles")
        servicio = tracker.get_slot("servicio")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")

        if not cita_id:
            dispatcher.utter_message(text="No tengo identificada la cita a cambiar.")
            return []

        # Si no hay horarios disponibles, consultarlos ahora
        if not horarios_disponibles:
            try:
                horarios_por_dia = {}
                hoy = datetime.now().date()

                for i in range(7):
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
                            horarios_por_dia[fecha_str] = horarios[:5]
                
                horarios_disponibles = horarios_por_dia
            except Exception as e:
                dispatcher.utter_message(text=f"Error al consultar disponibilidad: {str(e)}")
                return []

        try:
            # Interpretar la nueva fecha
            print(f"🕒 Interpretando nueva fecha: '{fecha_texto}'")
            nueva_fecha = self._interpretar_fecha(fecha_texto, horarios_disponibles)
            print(f"   Resultado: {nueva_fecha}")

            if not nueva_fecha:
                dispatcher.utter_message(
                    text="No pude entender la fecha o no hay disponibilidad. Por favor, dime 'hoy', 'mañana' o un día específico con hora."
                )
                return []

            # Actualizar la cita en el backend usando DELETE + POST
            # Primero eliminar la cita antigua
            print(f"🗑️ Eliminando cita {cita_id}...")
            response_delete = requests.delete(f"{API_URL}/citas/{cita_id}", timeout=5)
            print(f"   Respuesta DELETE: {response_delete.status_code}")
            
            if response_delete.status_code not in (200, 204):
                dispatcher.utter_message(text="No pude cancelar la cita anterior. Intenta más tarde.")
                return []

            # Luego crear la nueva cita
            cliente_id = tracker.get_slot("cliente_id")
            print(f"📝 Creando nueva cita: cliente={cliente_id}, negocio={negocio_id}, servicio={servicio_id}, fecha={nueva_fecha}")
            response_create = requests.post(
                f"{API_URL}/citas",
                json={
                    "cliente_id": cliente_id,
                    "negocio_id": negocio_id,
                    "servicio_id": servicio_id,
                    "fecha_hora_cita": nueva_fecha,
                    "estado": "confirmada"
                },
                timeout=5
            )
            print(f"   Respuesta POST: {response_create.status_code}")

            if response_create.status_code in (200, 201):
                tipo_negocio = tracker.get_slot("tipo_negocio")
                emoji_dict = {
                    "dentista": "🦷",
                    "fisioterapia": "🧘",
                    "peluqueria": "💇"
                }
                emoji = emoji_dict.get(tipo_negocio, "✅")
                
                fecha_obj = datetime.strptime(nueva_fecha, '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                dispatcher.utter_message(
                    text=f"{emoji} ¡Cita modificada correctamente!\n\n"
                         f"**Servicio:** {servicio}\n"
                         f"**Nueva fecha:** {fecha_legible}\n\n"
                         f"Te esperamos. ¡Gracias!"
                )
                return [
                    SlotSet("cita_a_cancelar_id", None),
                    SlotSet("servicio", None),
                    SlotSet("servicio_id", None),
                    SlotSet("fecha", None),
                    SlotSet("horarios_disponibles", None),
                    SlotSet("esperando_fecha", False)
                ]
            else:
                dispatcher.utter_message(text="No pude crear la nueva cita. Por favor, contacta con el negocio.")
                return [
                    SlotSet("esperando_fecha", False),
                    SlotSet("cita_a_cancelar_id", None)
                ]

        except Exception as e:
            dispatcher.utter_message(text=f"Error al cambiar horario: {str(e)}")
            return [
                SlotSet("esperando_fecha", False),
                SlotSet("cita_a_cancelar_id", None)
            ]

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
                    dias_hasta = 7
                fecha_objetivo = hoy + timedelta(days=dias_hasta)
            else:
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
                for slot in horarios:
                    # Extraer hora del slot (formato: '2026-01-07 09:30:00')
                    slot_hora = slot.split()[1][:5]  # Extrae '09:30'
                    if hora_usuario == slot_hora or hora_usuario in slot:
                        return slot
            if horarios:
                return horarios[0]

        return None