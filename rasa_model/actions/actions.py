from typing import Any, Text, Dict, List
import requests
import os
import re
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction
from datetime import datetime, timedelta
from dotenv import load_dotenv
from difflib import SequenceMatcher

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACIÓN API ---
API_URL = os.getenv("API_URL", "http://backend:5000")


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def limpiar_flujo():
    """Devuelve los SlotSet necesarios para limpiar el flujo actual"""
    return [
        SlotSet("flujo_activo", None),
        SlotSet("servicio", None),
        SlotSet("servicio_id", None),
        SlotSet("horarios_disponibles", None),
        SlotSet("citas_disponibles", None),
        SlotSet("cita_a_cancelar_id", None)
    ]

def calcular_similitud(texto1: str, texto2: str) -> float:
    """Calcula similitud entre dos textos (0.0 a 1.0)"""
    return SequenceMatcher(None, texto1.lower(), texto2.lower()).ratio()


# ============================================================
# ACTION: SET CONTEXTO (Saludo inicial)
# ============================================================
class ActionSetContexto(Action):
    def name(self) -> Text:
        return "action_set_contexto"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        metadata = tracker.latest_message.get('metadata', {})

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

        # IMPORTANTE: Limpiar TODOS los contextos cuando el usuario saluda
        return [
            SlotSet("cliente_id", cliente_id),
            SlotSet("negocio_id", negocio_id),
            SlotSet("tipo_negocio", tipo_negocio),
            SlotSet("negocio", negocio_nombre),
            # Limpiar flujo completamente
            SlotSet("flujo_activo", None),
            SlotSet("servicio", None),
            SlotSet("servicio_id", None),
            SlotSet("horarios_disponibles", None),
            SlotSet("citas_disponibles", None),
            SlotSet("cita_a_cancelar_id", None)
        ]


# ============================================================
# FLUJO 1: RESERVA DE CITA
# ============================================================

class ActionNormalizarServicio(Action):
    """PASO 1 RESERVA: Detecta el servicio y activa flujo_activo=reserva_fecha"""

    def name(self) -> Text:
        return "action_normalizar_servicio"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        flujo_activo = tracker.get_slot("flujo_activo")
        
        # Si hay un flujo activo, NO interferir
        if flujo_activo:
            print(f"🚫 ActionNormalizarServicio: flujo_activo={flujo_activo}, no interferir")
            return []

        mensaje_usuario = tracker.latest_message.get('text', '').lower()
        negocio_id = tracker.get_slot("negocio_id")

        print(f"🔍 ActionNormalizarServicio - Mensaje: '{mensaje_usuario}'")

        if not negocio_id:
            dispatcher.utter_message(text="No sé en qué negocio estás. Por favor, selecciona uno desde la web.")
            return []

        try:
            response = requests.get(f"{API_URL}/negocios/{negocio_id}/servicios", timeout=5)
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude cargar los servicios. Intenta de nuevo.")
                return []

            servicios_disponibles = response.json()
            if not servicios_disponibles:
                dispatcher.utter_message(text="Este negocio no tiene servicios configurados.")
                return []

            # Buscar coincidencia con servicios (con tolerancia a errores)
            servicio_detectado = None
            servicio_id = None
            mejor_similitud = 0
            
            for servicio in servicios_disponibles:
                nombre_servicio = servicio['nombre'].lower()
                
                # Búsqueda exacta primero
                palabras = [p for p in nombre_servicio.split() if len(p) > 3]
                if any(palabra in mensaje_usuario for palabra in palabras):
                    servicio_detectado = servicio['nombre']
                    servicio_id = servicio['id']
                    break
                
                # Fuzzy matching: comparar cada palabra del usuario con el nombre del servicio
                palabras_usuario = mensaje_usuario.split()
                for palabra in palabras_usuario:
                    if len(palabra) >= 4:  # Ignorar palabras muy cortas
                        similitud = calcular_similitud(palabra, nombre_servicio)
                        if similitud > mejor_similitud and similitud > 0.65:  # 65% de similitud
                            mejor_similitud = similitud
                            servicio_detectado = servicio['nombre']
                            servicio_id = servicio['id']

            if servicio_detectado:
                dispatcher.utter_message(text=f"✅ Servicio detectado: <b>{servicio_detectado}</b>")

                # Mostrar horarios disponibles
                horarios_por_dia = self._obtener_horarios(negocio_id, servicio_id)
                
                if horarios_por_dia:
                    mensaje = self._formatear_horarios(servicio_detectado, horarios_por_dia)
                    dispatcher.utter_message(text=mensaje)
                else:
                    dispatcher.utter_message(text="No hay horarios disponibles para este servicio en los próximos días.")
                    return []

                dispatcher.utter_message(text="¿Para qué día y hora quieres la cita?")
                
                # ACTIVAR FLUJO DE RESERVA
                return [
                    SlotSet("flujo_activo", "reserva_fecha"),
                    SlotSet("servicio", servicio_detectado),
                    SlotSet("servicio_id", servicio_id),
                    SlotSet("horarios_disponibles", horarios_por_dia)
                ]
            else:
                opciones = ", ".join([s['nombre'] for s in servicios_disponibles])
                dispatcher.utter_message(text=f"No entendí qué servicio quieres. Tenemos: {opciones}")
                return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al conectar con el servidor: {str(e)}")
            return []

    def _obtener_horarios(self, negocio_id, servicio_id):
        horarios_por_dia = {}
        hoy = datetime.now().date()
        for i in range(7):
            fecha = hoy + timedelta(days=i)
            fecha_str = fecha.strftime('%Y-%m-%d')
            try:
                response = requests.post(
                    f"{API_URL}/disponibilidad",
                    json={"negocio_id": negocio_id, "servicio_id": servicio_id, "fecha": fecha_str},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    horarios = data.get('disponibles', [])
                    if horarios:
                        horarios_por_dia[fecha_str] = horarios[:5]
            except:
                pass
        return horarios_por_dia

    def _formatear_horarios(self, servicio, horarios_por_dia):
        dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        mensaje = f"📅 Horarios disponibles para <b>{servicio}</b>:\n\n"
        for fecha_str, horarios in list(horarios_por_dia.items())[:5]:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
            dia_texto = f"{dias_es[fecha_obj.weekday()]} {fecha_obj.day:02d}/{fecha_obj.month:02d}"
            horas = [h.split()[1][:5] for h in horarios[:3]]
            mensaje += f"<b>{dia_texto}</b>: {', '.join(horas)}\n"
        return mensaje


class ActionReservarCita(Action):
    """PASO 2 RESERVA: Procesa la fecha y crea la cita"""

    def name(self) -> Text:
        return "action_reservar_cita"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        flujo_activo = tracker.get_slot("flujo_activo")
        
        # VALIDACIÓN: Solo ejecutar si estamos en flujo de reserva
        if flujo_activo != "reserva_fecha":
            print(f"⚠️ ActionReservarCita: flujo_activo={flujo_activo}, ignorando")
            return []

        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        servicio = tracker.get_slot("servicio")
        horarios_disponibles = tracker.get_slot("horarios_disponibles")
        fecha_texto = tracker.latest_message.get('text', '')

        print(f"📝 ActionReservarCita - Fecha texto: '{fecha_texto}'")

        # Detectar si el usuario quiere cambiar de intención
        if self._detectar_cambio_intencion(fecha_texto):
            dispatcher.utter_message(text="Entendido, cancelamos la reserva. ¿En qué puedo ayudarte?")
            return limpiar_flujo()

        if not all([cliente_id, negocio_id, servicio_id]):
            dispatcher.utter_message(text="Falta información para completar la reserva.")
            return limpiar_flujo()

        try:
            fecha_reserva = self._interpretar_fecha(fecha_texto, horarios_disponibles)

            if not fecha_reserva:
                dispatcher.utter_message(text="No pude entender la fecha. Dime 'hoy', 'mañana' o un día específico.")
                return []  # Mantener flujo activo para reintentar

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
                fecha_obj = datetime.strptime(fecha_reserva, '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                dispatcher.utter_message(
                    text=f"✅ ¡Reserva confirmada!\n\n"
                         f"<b>Servicio:</b> {servicio}\n"
                         f"<b>Fecha:</b> {fecha_legible}\n\n"
                         f"¡Gracias por confiar en nosotros!"
                )
                return limpiar_flujo()
            else:
                error_msg = response.json().get('error', 'Error desconocido')
                dispatcher.utter_message(text=f"❌ No se pudo crear la reserva: {error_msg}")
                return limpiar_flujo()

        except Exception as e:
            dispatcher.utter_message(text=f"Error al reservar: {str(e)}")
            return limpiar_flujo()

    def _detectar_cambio_intencion(self, texto):
        texto_lower = texto.lower()
        palabras_salir = ['anular', 'cancelar', 'no quiero', 'cambiar', 'salir', 'nada', 'olvidar']
        return any(palabra in texto_lower for palabra in palabras_salir)

    def _interpretar_fecha(self, texto_fecha: str, horarios_disponibles: dict) -> str:
        if not texto_fecha:
            return None

        texto_lower = texto_fecha.lower().strip()
        hoy = datetime.now().date()

        # Extraer hora si se especifica - tolera "a las", "las"
        hora_match = re.search(r'(?:a las |las )?(\d{1,2})(?::(\d{2}))?', texto_lower)
        hora_especificada = None
        if hora_match:
            hora = int(hora_match.group(1))
            minuto = int(hora_match.group(2)) if hora_match.group(2) else 0
            hora_especificada = f"{hora:02d}:{minuto:02d}"

        # Determinar el día objetivo
        fecha_objetivo = None
        
        if "hoy" in texto_lower:
            fecha_objetivo = hoy
        elif "mañana" in texto_lower or "manana" in texto_lower:
            fecha_objetivo = hoy + timedelta(days=1)
        elif "pasado" in texto_lower:
            fecha_objetivo = hoy + timedelta(days=2)
        else:
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
                    break
        
        if not fecha_objetivo and horarios_disponibles:
            fechas_disponibles = sorted(horarios_disponibles.keys())
            if fechas_disponibles:
                fecha_objetivo = datetime.strptime(fechas_disponibles[0], '%Y-%m-%d').date()

        if not fecha_objetivo:
            return None

        fecha_str = fecha_objetivo.strftime('%Y-%m-%d')

        if not horarios_disponibles or fecha_str not in horarios_disponibles:
            fechas_disponibles = sorted(horarios_disponibles.keys()) if horarios_disponibles else []
            for fecha_disponible in fechas_disponibles:
                if fecha_disponible >= fecha_str:
                    fecha_str = fecha_disponible
                    break
            else:
                return None

        horarios = horarios_disponibles.get(fecha_str, [])
        if not horarios:
            return None
            
        if hora_especificada:
            for slot in horarios:
                slot_hora = slot.split()[1][:5]
                if hora_especificada == slot_hora:
                    return slot
        
        return horarios[0]


# ============================================================
# FLUJO 2: CANCELAR CITA
# ============================================================

class ActionCancelarCita(Action):
    """PASO 1 CANCELAR: Muestra citas y activa flujo_activo=cancelar_seleccion"""

    def name(self) -> Text:
        return "action_cancelar_cita"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        flujo_activo = tracker.get_slot("flujo_activo")
        
        # Si hay un flujo activo diferente, limpiarlo primero
        if flujo_activo and flujo_activo != "cancelar_seleccion":
            print(f"🔄 ActionCancelarCita: Limpiando flujo anterior {flujo_activo}")

        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")

        if not cliente_id:
            dispatcher.utter_message(text="Debes iniciar sesión para cancelar citas.")
            return limpiar_flujo()

        try:
            response = requests.get(
                f"{API_URL}/citas",
                params={"cliente_id": cliente_id, "negocio_id": negocio_id},
                timeout=5
            )
            
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude consultar tus citas.")
                return limpiar_flujo()

            citas = response.json()
            
            hoy = datetime.now()
            citas_futuras = [
                c for c in citas 
                if datetime.strptime(c['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S') > hoy
                and c['estado'] == 'confirmada'
            ]

            if not citas_futuras:
                dispatcher.utter_message(text="No tienes citas pendientes para cancelar.")
                return limpiar_flujo()

            if len(citas_futuras) == 1:
                cita = citas_futuras[0]
                fecha_obj = datetime.strptime(cita['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                mensaje = f"📅 <b>Tienes esta cita pendiente:</b>\n\n"
                mensaje += f"🔹 <b>{cita['servicio_nombre']}</b>\n"
                mensaje += f"📆 {fecha_legible}\n\n"
                mensaje += "¿Quieres cancelarla? Responde <b>'sí'</b> o <b>'no'</b>."
                
                dispatcher.utter_message(text=mensaje)
                return [
                    SlotSet("flujo_activo", "cancelar_confirmacion"),
                    SlotSet("cita_a_cancelar_id", cita['id'])
                ]
            else:
                mensaje = f"📅 Tienes {len(citas_futuras)} citas pendientes:\n\n"
                
                for i, cita in enumerate(citas_futuras, 1):
                    fecha_obj = datetime.strptime(cita['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
                    fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                    mensaje += f"<b>{i}.</b> {cita['servicio_nombre']} - {fecha_legible}\n"
                
                mensaje += "\n¿Cuál quieres cancelar? Escribe el número."
                
                dispatcher.utter_message(text=mensaje)
                return [
                    SlotSet("flujo_activo", "cancelar_seleccion"),
                    SlotSet("citas_disponibles", citas_futuras)
                ]

        except Exception as e:
            dispatcher.utter_message(text=f"Error al procesar cancelación: {str(e)}")
            return limpiar_flujo()


class ActionSeleccionarCitaCancelar(Action):
    """PASO 2 CANCELAR: Selecciona la cita y pide confirmación"""

    def name(self) -> Text:
        return "action_seleccionar_cita_cancelar"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        flujo_activo = tracker.get_slot("flujo_activo")
        
        if flujo_activo != "cancelar_seleccion":
            print(f"⚠️ ActionSeleccionarCitaCancelar: flujo_activo={flujo_activo}, ignorando")
            return []

        citas_disponibles = tracker.get_slot("citas_disponibles")
        ultimo_mensaje = tracker.latest_message.get('text', '')

        print(f"🔍 ActionSeleccionarCitaCancelar - Mensaje: '{ultimo_mensaje}'")

        if not citas_disponibles:
            dispatcher.utter_message(text="No encuentro las citas. Di 'cancelar cita' para empezar de nuevo.")
            return limpiar_flujo()

        # Extraer número del mensaje
        match = re.search(r'\b(\d+)\b', ultimo_mensaje)
        if not match:
            dispatcher.utter_message(text="No entendí el número. ¿Cuál cita quieres cancelar?")
            return []  # Mantener flujo para reintentar

        numero = int(match.group(1))

        if numero < 1 or numero > len(citas_disponibles):
            dispatcher.utter_message(text=f"Elige un número entre 1 y {len(citas_disponibles)}.")
            return []  # Mantener flujo para reintentar

        cita_seleccionada = citas_disponibles[numero - 1]
        fecha_obj = datetime.strptime(cita_seleccionada['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
        fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')

        mensaje = f"📅 <b>Has seleccionado:</b>\n\n"
        mensaje += f"🔹 <b>{cita_seleccionada['servicio_nombre']}</b>\n"
        mensaje += f"📆 {fecha_legible}\n\n"
        mensaje += "¿Quieres cancelarla? Responde <b>'sí'</b> o <b>'no'</b>."

        dispatcher.utter_message(text=mensaje)

        return [
            SlotSet("flujo_activo", "cancelar_confirmacion"),
            SlotSet("cita_a_cancelar_id", cita_seleccionada['id']),
            SlotSet("citas_disponibles", None)
        ]


class ActionProcesarConfirmacionCancelar(Action):
    """PASO 3 CANCELAR: Procesa sí/no y ejecuta la cancelación"""

    def name(self) -> Text:
        return "action_procesar_confirmacion_cancelar"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        flujo_activo = tracker.get_slot("flujo_activo")
        
        if flujo_activo != "cancelar_confirmacion":
            print(f"⚠️ ActionProcesarConfirmacionCancelar: flujo_activo={flujo_activo}, ignorando")
            return []

        ultimo_mensaje = tracker.latest_message.get('text', '').lower().strip()
        cita_id = tracker.get_slot("cita_a_cancelar_id")
        cliente_id = tracker.get_slot("cliente_id")

        print(f"🔍 ActionProcesarConfirmacionCancelar - Mensaje: '{ultimo_mensaje}'")

        if not cita_id:
            dispatcher.utter_message(text="No he entendido. ¿En qué puedo ayudarte?")
            return limpiar_flujo()

        afirmaciones = ['sí', 'si', 'yes', 'vale', 'ok', 'claro', 'confirmo', 'afirmativo']
        negaciones = ['no', 'nada', 'negativo', 'mejor no', 'cancelar']

        es_afirmativo = any(palabra in ultimo_mensaje for palabra in afirmaciones)
        es_negativo = any(palabra in ultimo_mensaje for palabra in negaciones)

        if es_afirmativo and not es_negativo:
            try:
                response = requests.delete(
                    f"{API_URL}/citas/{cita_id}",
                    params={"cliente_id": cliente_id},
                    timeout=5
                )
                
                if response.status_code in (200, 204):
                    dispatcher.utter_message(
                        text="✅ <b>Cita cancelada correctamente</b>\n\n"
                             "Si cambias de opinión, puedes reservar otra cita cuando quieras."
                    )
                else:
                    dispatcher.utter_message(text="No pude cancelar la cita. Intenta más tarde.")
                
            except Exception as e:
                dispatcher.utter_message(text="Hubo un error al cancelar. Intenta más tarde.")
            
            return limpiar_flujo()

        elif es_negativo:
            dispatcher.utter_message(text="Perfecto, tu cita se mantiene. ¿Puedo ayudarte con algo más?")
            return limpiar_flujo()

        else:
            dispatcher.utter_message(text="No entendí. Responde 'sí' para cancelar o 'no' para mantenerla.")
            return []  # Mantener flujo para reintentar


# ============================================================
# FLUJO 3: CAMBIAR HORARIO DE CITA
# ============================================================

class ActionCambiarHorario(Action):
    """PASO 1 CAMBIAR: Muestra citas y activa flujo_activo=cambiar_seleccion"""

    def name(self) -> Text:
        return "action_cambiar_horario"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        flujo_activo = tracker.get_slot("flujo_activo")
        
        if flujo_activo and flujo_activo != "cambiar_seleccion":
            print(f"🔄 ActionCambiarHorario: Limpiando flujo anterior {flujo_activo}")

        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")

        if not cliente_id:
            dispatcher.utter_message(text="Debes iniciar sesión para cambiar citas.")
            return limpiar_flujo()

        try:
            response = requests.get(
                f"{API_URL}/citas",
                params={"cliente_id": cliente_id, "negocio_id": negocio_id},
                timeout=5
            )
            
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude consultar tus citas.")
                return limpiar_flujo()

            citas = response.json()
            
            hoy = datetime.now()
            citas_futuras = [
                c for c in citas 
                if datetime.strptime(c['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S') > hoy
                and c['estado'] == 'confirmada'
            ]

            if not citas_futuras:
                dispatcher.utter_message(text="No tienes citas pendientes para cambiar.")
                return limpiar_flujo()

            if len(citas_futuras) == 1:
                cita = citas_futuras[0]
                fecha_obj = datetime.strptime(cita['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                # Obtener horarios disponibles
                horarios = self._obtener_horarios(negocio_id, cita['servicio_id'])
                
                mensaje = f"📅 <b>Cita a cambiar:</b>\n\n"
                mensaje += f"🔹 <b>{cita['servicio_nombre']}</b>\n"
                mensaje += f"📆 {fecha_legible}\n\n"
                
                if horarios:
                    mensaje += self._formatear_horarios(horarios)
                
                mensaje += "\n¿A qué día y hora quieres cambiarla?"
                
                dispatcher.utter_message(text=mensaje)
                return [
                    SlotSet("flujo_activo", "cambiar_fecha"),
                    SlotSet("cita_a_cancelar_id", cita['id']),
                    SlotSet("servicio_id", cita['servicio_id']),
                    SlotSet("servicio", cita['servicio_nombre']),
                    SlotSet("horarios_disponibles", horarios)
                ]
            else:
                mensaje = f"📅 Tienes {len(citas_futuras)} citas pendientes:\n\n"
                
                for i, cita in enumerate(citas_futuras, 1):
                    fecha_obj = datetime.strptime(cita['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
                    fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                    mensaje += f"<b>{i}.</b> {cita['servicio_nombre']} - {fecha_legible}\n"
                
                mensaje += "\n¿Cuál quieres cambiar? Escribe el número."
                
                dispatcher.utter_message(text=mensaje)
                return [
                    SlotSet("flujo_activo", "cambiar_seleccion"),
                    SlotSet("citas_disponibles", citas_futuras)
                ]

        except Exception as e:
            dispatcher.utter_message(text=f"Error al procesar cambio: {str(e)}")
            return limpiar_flujo()

    def _obtener_horarios(self, negocio_id, servicio_id):
        horarios_por_dia = {}
        hoy = datetime.now().date()
        for i in range(7):
            fecha = hoy + timedelta(days=i)
            fecha_str = fecha.strftime('%Y-%m-%d')
            try:
                response = requests.post(
                    f"{API_URL}/disponibilidad",
                    json={"negocio_id": negocio_id, "servicio_id": servicio_id, "fecha": fecha_str},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    horarios = data.get('disponibles', [])
                    if horarios:
                        horarios_por_dia[fecha_str] = horarios[:5]
            except:
                pass
        return horarios_por_dia

    def _formatear_horarios(self, horarios_por_dia):
        dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        mensaje = "<b>📅 Horarios disponibles:</b>\n"
        for fecha_str, horarios in list(horarios_por_dia.items())[:5]:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
            dia_texto = f"{dias_es[fecha_obj.weekday()]} {fecha_obj.day:02d}/{fecha_obj.month:02d}"
            horas = [h.split()[1][:5] for h in horarios[:3]]
            mensaje += f"<b>{dia_texto}</b>: {', '.join(horas)}\n"
        return mensaje


class ActionSeleccionarCitaCambio(Action):
    """PASO 2 CAMBIAR: Selecciona la cita y pide nueva fecha"""

    def name(self) -> Text:
        return "action_seleccionar_cita_cambio"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        flujo_activo = tracker.get_slot("flujo_activo")
        
        if flujo_activo != "cambiar_seleccion":
            print(f"⚠️ ActionSeleccionarCitaCambio: flujo_activo={flujo_activo}, ignorando")
            return []

        citas_disponibles = tracker.get_slot("citas_disponibles")
        negocio_id = tracker.get_slot("negocio_id")
        mensaje_usuario = tracker.latest_message.get('text', '')

        print(f"🔍 ActionSeleccionarCitaCambio - Mensaje: '{mensaje_usuario}'")

        if not citas_disponibles:
            dispatcher.utter_message(text="No encuentro las citas. Di 'cambiar cita' para empezar de nuevo.")
            return limpiar_flujo()

        match = re.search(r'\b(\d+)\b', mensaje_usuario)
        if not match:
            dispatcher.utter_message(text="No entendí el número. ¿Cuál cita quieres cambiar?")
            return []

        numero = int(match.group(1))

        if numero < 1 or numero > len(citas_disponibles):
            dispatcher.utter_message(text=f"Elige un número entre 1 y {len(citas_disponibles)}.")
            return []

        cita_seleccionada = citas_disponibles[numero - 1]
        fecha_obj = datetime.strptime(cita_seleccionada['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
        fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')

        # Obtener horarios disponibles
        horarios = self._obtener_horarios(negocio_id, cita_seleccionada['servicio_id'])

        mensaje = f"📅 <b>Cita a cambiar:</b>\n\n"
        mensaje += f"🔹 <b>{cita_seleccionada['servicio_nombre']}</b>\n"
        mensaje += f"📆 {fecha_legible}\n\n"
        
        if horarios:
            mensaje += self._formatear_horarios(horarios)
        
        mensaje += "\n¿A qué día y hora quieres cambiarla?"

        dispatcher.utter_message(text=mensaje)

        return [
            SlotSet("flujo_activo", "cambiar_fecha"),
            SlotSet("cita_a_cancelar_id", cita_seleccionada['id']),
            SlotSet("servicio_id", cita_seleccionada['servicio_id']),
            SlotSet("servicio", cita_seleccionada['servicio_nombre']),
            SlotSet("horarios_disponibles", horarios),
            SlotSet("citas_disponibles", None)
        ]

    def _obtener_horarios(self, negocio_id, servicio_id):
        horarios_por_dia = {}
        hoy = datetime.now().date()
        for i in range(7):
            fecha = hoy + timedelta(days=i)
            fecha_str = fecha.strftime('%Y-%m-%d')
            try:
                response = requests.post(
                    f"{API_URL}/disponibilidad",
                    json={"negocio_id": negocio_id, "servicio_id": servicio_id, "fecha": fecha_str},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    horarios = data.get('disponibles', [])
                    if horarios:
                        horarios_por_dia[fecha_str] = horarios[:5]
            except:
                pass
        return horarios_por_dia

    def _formatear_horarios(self, horarios_por_dia):
        dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        mensaje = "<b>📅 Horarios disponibles:</b>\n"
        for fecha_str, horarios in list(horarios_por_dia.items())[:5]:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
            dia_texto = f"{dias_es[fecha_obj.weekday()]} {fecha_obj.day:02d}/{fecha_obj.month:02d}"
            horas = [h.split()[1][:5] for h in horarios[:3]]
            mensaje += f"<b>{dia_texto}</b>: {', '.join(horas)}\n"
        return mensaje


class ActionConfirmarCambioHorario(Action):
    """PASO 3 CAMBIAR: Procesa la nueva fecha y ejecuta el cambio"""

    def name(self) -> Text:
        return "action_confirmar_cambio_horario"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        flujo_activo = tracker.get_slot("flujo_activo")
        
        if flujo_activo != "cambiar_fecha":
            print(f"⚠️ ActionConfirmarCambioHorario: flujo_activo={flujo_activo}, ignorando")
            return []

        cita_id = tracker.get_slot("cita_a_cancelar_id")
        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        servicio = tracker.get_slot("servicio")
        horarios_disponibles = tracker.get_slot("horarios_disponibles")
        fecha_texto = tracker.latest_message.get('text', '')

        print(f"🔄 ActionConfirmarCambioHorario - Fecha texto: '{fecha_texto}'")

        if not cita_id:
            dispatcher.utter_message(text="No tengo identificada la cita a cambiar.")
            return limpiar_flujo()

        try:
            nueva_fecha = self._interpretar_fecha(fecha_texto, horarios_disponibles)

            if not nueva_fecha:
                dispatcher.utter_message(text="No pude entender la fecha. Dime 'hoy', 'mañana' o un día específico.")
                return []  # Mantener flujo para reintentar

            # Eliminar cita antigua
            response_delete = requests.delete(f"{API_URL}/citas/{cita_id}", timeout=5)
            
            if response_delete.status_code not in (200, 204):
                dispatcher.utter_message(text="No pude cancelar la cita anterior. Intenta más tarde.")
                return limpiar_flujo()

            # Crear nueva cita
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

            if response_create.status_code in (200, 201):
                fecha_obj = datetime.strptime(nueva_fecha, '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                dispatcher.utter_message(
                    text=f"✅ <b>¡Cita modificada correctamente!</b>\n\n"
                         f"<b>Servicio:</b> {servicio}\n"
                         f"<b>Nueva fecha:</b> {fecha_legible}\n\n"
                         f"¡Gracias!"
                )
                return limpiar_flujo()
            else:
                dispatcher.utter_message(text="No pude crear la nueva cita. Contacta con el negocio.")
                return limpiar_flujo()

        except Exception as e:
            dispatcher.utter_message(text=f"Error al cambiar horario: {str(e)}")
            return limpiar_flujo()

    def _interpretar_fecha(self, texto_fecha: str, horarios_disponibles: dict) -> str:
        if not texto_fecha or not horarios_disponibles:
            return None

        texto_lower = texto_fecha.lower()
        hoy = datetime.now().date()

        if "hoy" in texto_lower:
            fecha_objetivo = hoy
        elif "mañana" in texto_lower or "manana" in texto_lower:
            fecha_objetivo = hoy + timedelta(days=1)
        elif "pasado" in texto_lower:
            fecha_objetivo = hoy + timedelta(days=2)
        else:
            dias_semana = {
                'lunes': 0, 'martes': 1, 'miercoles': 2, 'miércoles': 2,
                'jueves': 3, 'viernes': 4, 'sabado': 5, 'sábado': 5, 'domingo': 6
            }
            fecha_objetivo = None
            for dia_nombre, dia_num in dias_semana.items():
                if dia_nombre in texto_lower:
                    dias_hasta = (dia_num - hoy.weekday()) % 7
                    if dias_hasta == 0:
                        dias_hasta = 7
                    fecha_objetivo = hoy + timedelta(days=dias_hasta)
                    break
            if not fecha_objetivo:
                fecha_objetivo = hoy + timedelta(days=1)

        fecha_str = fecha_objetivo.strftime('%Y-%m-%d')

        # Extraer hora - tolera "a las", "las"
        hora_match = re.search(r'(?:a las |las )?(\d{1,2})(?::(\d{2}))?', texto_lower)
        hora_usuario = None
        if hora_match:
            hora = int(hora_match.group(1))
            minuto = int(hora_match.group(2)) if hora_match.group(2) else 0
            hora_usuario = f"{hora:02d}:{minuto:02d}"

        if fecha_str in horarios_disponibles:
            horarios = horarios_disponibles[fecha_str]
            if hora_usuario:
                for slot in horarios:
                    slot_hora = slot.split()[1][:5]
                    if hora_usuario == slot_hora:
                        return slot
            if horarios:
                return horarios[0]

        # Buscar el siguiente día disponible
        for fecha_disp in sorted(horarios_disponibles.keys()):
            if fecha_disp >= fecha_str:
                horarios = horarios_disponibles[fecha_disp]
                if horarios:
                    return horarios[0]

        return None


# ============================================================
# ACCIONES DE CONSULTA (Sin flujo activo)
# ============================================================

class ActionConsultarCitasUsuario(Action):
    """Muestra las citas del usuario (no modifica flujo_activo)"""

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
            response = requests.get(
                f"{API_URL}/citas",
                params={"cliente_id": cliente_id},
                timeout=5
            )
            
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude consultar tus citas.")
                return []

            citas = response.json()
            
            if negocio_id:
                citas = [c for c in citas if c.get('negocio_id') == negocio_id]
            
            hoy = datetime.now()
            citas_futuras = [
                c for c in citas 
                if datetime.strptime(c['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S') > hoy
                and c['estado'] == 'confirmada'
            ]
            
            if not citas_futuras:
                dispatcher.utter_message(text="No tienes citas pendientes. ¿Quieres reservar una? 😊")
                return []

            mensaje = "📅 <b>Tus próximas citas:</b>\n\n"
            
            for cita in citas_futuras[:5]:
                fecha_obj = datetime.strptime(cita['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                mensaje += f"🔹 <b>{cita['servicio_nombre']}</b>\n"
                mensaje += f"   📆 {fecha_legible}\n\n"

            dispatcher.utter_message(text=mensaje)
            return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al consultar citas: {str(e)}")
            return []


class ActionListarServicios(Action):
    """Lista todos los servicios con precios"""

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

            mensaje = "💇 <b>Servicios disponibles:</b>\n\n"
            
            for servicio in servicios:
                mensaje += f"<b>{servicio['nombre']}</b>\n"
                mensaje += f"   💰 {servicio['precio']}€ | ⏱️ {servicio['duracion_minutos']} min\n\n"

            mensaje += "¿Quieres reservar alguno? Dime cuál te interesa. 😊"

            dispatcher.utter_message(text=mensaje)
            return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al listar servicios: {str(e)}")
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
            response = requests.get(f"{API_URL}/negocios/{negocio_id}/horarios", timeout=5)
            
            if response.status_code == 404:
                dispatcher.utter_message(text="Los horarios no están disponibles en este momento.")
                return []
            
            if response.status_code != 200:
                dispatcher.utter_message(text="No pude consultar los horarios.")
                return []

            horarios = response.json()
            
            if not horarios:
                dispatcher.utter_message(text="No tengo horarios configurados para este negocio.")
                return []

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

            mensaje = "🕒 <b>Horarios de apertura:</b>\n\n"
            
            for dia in dias_semana:
                if dia in horarios_por_dia:
                    turnos = horarios_por_dia[dia]
                    if len(turnos) == 1:
                        mensaje += f"<b>{dia}:</b> {turnos[0]['apertura']} - {turnos[0]['cierre']}\n"
                    else:
                        horarios_texto = " y ".join([f"{t['apertura']}-{t['cierre']}" for t in turnos])
                        mensaje += f"<b>{dia}:</b> {horarios_texto}\n"

            dispatcher.utter_message(text=mensaje)
            return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al consultar horarios: {str(e)}")
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

            mensaje = f"📍 <b>Ubicación:</b>\n\n{direccion}\n\n"
            mensaje += "¡Te esperamos!"

            dispatcher.utter_message(text=mensaje)
            return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al consultar ubicación: {str(e)}")
            return []


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
            
            mensaje = f"📍 <b>{negocio['nombre']}</b>\n\n"
            
            if negocio.get('descripcion'):
                mensaje += f"{negocio['descripcion']}\n\n"
            
            if negocio.get('direccion'):
                mensaje += f"📌 <b>Dirección:</b> {negocio['direccion']}\n"
            
            mensaje += f"🏢 <b>Tipo:</b> {negocio.get('tipo_negocio', 'Negocio').capitalize()}\n\n"
            mensaje += "Pregúntame por horarios, servicios o reserva tu cita. 😊"

            dispatcher.utter_message(text=mensaje)
            return []

        except Exception as e:
            dispatcher.utter_message(text=f"Error al consultar información: {str(e)}")
            return []


class ActionMostrarDisponibilidad(Action):
    """Muestra más horarios disponibles"""

    def name(self) -> Text:
        return "action_mostrar_disponibilidad"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        servicio = tracker.get_slot("servicio")

        if not negocio_id or not servicio_id:
            dispatcher.utter_message(text="Dime primero qué servicio te interesa.")
            return []

        try:
            horarios_por_dia = {}
            hoy = datetime.now().date()

            for i in range(14):
                fecha = hoy + timedelta(days=i)
                fecha_str = fecha.strftime('%Y-%m-%d')

                response = requests.post(
                    f"{API_URL}/disponibilidad",
                    json={"negocio_id": negocio_id, "servicio_id": servicio_id, "fecha": fecha_str},
                    timeout=5
                )

                if response.status_code == 200:
                    data = response.json()
                    horarios = data.get('disponibles', [])
                    if horarios:
                        horarios_por_dia[fecha_str] = horarios[:5]

            if not horarios_por_dia:
                dispatcher.utter_message(text=f"No hay horarios disponibles para {servicio}.")
                return []

            dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            mensaje = f"📅 <b>Horarios disponibles para {servicio}:</b>\n\n"
            
            for fecha_str, horarios in list(horarios_por_dia.items())[:7]:
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                dia_texto = f"{dias_es[fecha_obj.weekday()]} {fecha_obj.day:02d}/{fecha_obj.month:02d}"
                horas = [h.split()[1][:5] for h in horarios[:3]]
                mensaje += f"<b>{dia_texto}</b>: {', '.join(horas)}\n"

            mensaje += "\n¿Para qué día quieres reservar?"
            
            dispatcher.utter_message(text=mensaje)
            return [SlotSet("horarios_disponibles", horarios_por_dia)]

        except Exception as e:
            dispatcher.utter_message(text=f"Error al consultar disponibilidad: {str(e)}")
            return []


class ActionResponderBotChallenge(Action):
    """Responde cuando el usuario pregunta qué es el bot"""

    def name(self) -> Text:
        return "action_responder_bot_challenge"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        negocio_nombre = tracker.get_slot("negocio")

        if negocio_nombre:
            mensaje = f"🤖 Soy el asistente virtual de <b>{negocio_nombre}</b>.\n\n"
        else:
            mensaje = "🤖 Soy un asistente virtual de <b>Sector Mind AI</b>.\n\n"
        
        mensaje += "Puedo ayudarte a:\n"
        mensaje += "✅ Consultar servicios y precios\n"
        mensaje += "✅ Ver horarios de apertura\n"
        mensaje += "✅ Reservar citas\n"
        mensaje += "✅ Gestionar tus reservas\n\n"
        mensaje += "¿En qué puedo ayudarte? 😊"

        dispatcher.utter_message(text=mensaje)
        return []


# ============================================================
# FALLBACK INTELIGENTE - CEREBRO CENTRAL
# ============================================================

class ActionFallbackInteligente(Action):
    """Fallback que redirige según flujo_activo o detecta servicios"""

    def name(self) -> Text:
        return "action_fallback_inteligente"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        flujo_activo = tracker.get_slot("flujo_activo")
        mensaje_usuario = tracker.latest_message.get('text', '').lower()

        print(f"🔍 ActionFallbackInteligente - Mensaje: '{mensaje_usuario}', flujo_activo: {flujo_activo}")

        # ============================================
        # PRIORIDAD 1: Redirigir según flujo activo
        # ============================================
        
        if flujo_activo == "reserva_fecha":
            print("   → Redirigiendo a ActionReservarCita")
            return self._ejecutar_reservar_cita(dispatcher, tracker)
        
        elif flujo_activo == "cancelar_seleccion":
            print("   → Redirigiendo a ActionSeleccionarCitaCancelar")
            return self._ejecutar_seleccionar_cita_cancelar(dispatcher, tracker)
        
        elif flujo_activo == "cancelar_confirmacion":
            print("   → Redirigiendo a ActionProcesarConfirmacionCancelar")
            return self._ejecutar_procesar_confirmacion_cancelar(dispatcher, tracker)
        
        elif flujo_activo == "cambiar_seleccion":
            print("   → Redirigiendo a ActionSeleccionarCitaCambio")
            return self._ejecutar_seleccionar_cita_cambio(dispatcher, tracker)
        
        elif flujo_activo == "cambiar_fecha":
            print("   → Redirigiendo a ActionConfirmarCambioHorario")
            return self._ejecutar_confirmar_cambio_horario(dispatcher, tracker)

        # ============================================
        # PRIORIDAD 2: Sin flujo activo - detectar servicio
        # ============================================
        negocio_id = tracker.get_slot("negocio_id")
        
        if not negocio_id:
            dispatcher.utter_message(text="No he entendido bien. ¿Puedes repetirlo?")
            return []

        try:
            response = requests.get(f"{API_URL}/negocios/{negocio_id}/servicios", timeout=5)
            if response.status_code != 200:
                dispatcher.utter_message(text="No he entendido bien. ¿Puedes repetirlo?")
                return []

            servicios_disponibles = response.json()
            
            # Buscar coincidencia con servicios (con tolerancia a errores)
            servicio_encontrado = None
            mejor_similitud = 0
            
            for servicio in servicios_disponibles:
                nombre_servicio = servicio['nombre'].lower()
                
                # Búsqueda exacta primero
                palabras = [p for p in nombre_servicio.split() if len(p) > 3]
                if any(palabra in mensaje_usuario for palabra in palabras):
                    print(f"   → Servicio detectado (exacto): {servicio['nombre']}")
                    return [FollowupAction("action_normalizar_servicio")]
                
                # Fuzzy matching: comparar cada palabra del usuario
                palabras_usuario = mensaje_usuario.split()
                for palabra in palabras_usuario:
                    if len(palabra) >= 4:
                        similitud = calcular_similitud(palabra, nombre_servicio)
                        if similitud > mejor_similitud and similitud > 0.65:
                            mejor_similitud = similitud
                            servicio_encontrado = servicio
            
            if servicio_encontrado:
                print(f"   → Servicio detectado (fuzzy {mejor_similitud:.2f}): {servicio_encontrado['nombre']}")
                return [FollowupAction("action_normalizar_servicio")]

            # No se detectó servicio
            dispatcher.utter_message(
                text="No he entendido bien. Puedo ayudarte con:\n"
                     "📅 Reservar citas\n"
                     "💰 Consultar servicios\n"
                     "📍 Ver ubicación\n"
                     "🕒 Ver horarios\n"
                     "❌ Cancelar o cambiar citas"
            )
            return []

        except Exception:
            dispatcher.utter_message(text="No he entendido bien. ¿Puedes repetirlo?")
            return []

    # ============================================
    # MÉTODOS AUXILIARES - Ejecutan la lógica de cada flujo
    # ============================================

    def _ejecutar_reservar_cita(self, dispatcher, tracker):
        """Ejecuta la lógica de reservar cita"""
        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        servicio = tracker.get_slot("servicio")
        horarios_disponibles = tracker.get_slot("horarios_disponibles")
        fecha_texto = tracker.latest_message.get('text', '')

        # Detectar si el usuario quiere cambiar de intención
        texto_lower = fecha_texto.lower()
        palabras_salir = ['anular', 'cancelar', 'no quiero', 'cambiar', 'salir', 'nada', 'olvidar']
        if any(palabra in texto_lower for palabra in palabras_salir):
            dispatcher.utter_message(text="Entendido, cancelamos la reserva. ¿En qué puedo ayudarte?")
            return limpiar_flujo()

        if not all([cliente_id, negocio_id, servicio_id]):
            dispatcher.utter_message(text="Falta información para completar la reserva.")
            return limpiar_flujo()

        try:
            fecha_reserva = self._interpretar_fecha(fecha_texto, horarios_disponibles)

            if not fecha_reserva:
                dispatcher.utter_message(text="No pude entender la fecha. Dime 'hoy', 'mañana' o un día específico.")
                return []

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
                fecha_obj = datetime.strptime(fecha_reserva, '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                dispatcher.utter_message(
                    text=f"✅ ¡Reserva confirmada!\n\n"
                         f"<b>Servicio:</b> {servicio}\n"
                         f"<b>Fecha:</b> {fecha_legible}\n\n"
                         f"¡Gracias por confiar en nosotros!"
                )
                return limpiar_flujo()
            else:
                error_msg = response.json().get('error', 'Error desconocido')
                dispatcher.utter_message(text=f"❌ No se pudo crear la reserva: {error_msg}")
                return limpiar_flujo()

        except Exception as e:
            dispatcher.utter_message(text=f"Error al reservar: {str(e)}")
            return limpiar_flujo()

    def _ejecutar_seleccionar_cita_cancelar(self, dispatcher, tracker):
        """Ejecuta la lógica de seleccionar cita para cancelar"""
        citas_disponibles = tracker.get_slot("citas_disponibles")
        ultimo_mensaje = tracker.latest_message.get('text', '')

        if not citas_disponibles:
            dispatcher.utter_message(text="No encuentro las citas. Di 'cancelar cita' para empezar de nuevo.")
            return limpiar_flujo()

        # Extraer número del mensaje
        match = re.search(r'\b(\d+)\b', ultimo_mensaje)
        if not match:
            dispatcher.utter_message(text="No entendí el número. ¿Cuál cita quieres cancelar? (1, 2, 3...)")
            return []

        numero = int(match.group(1))

        if numero < 1 or numero > len(citas_disponibles):
            dispatcher.utter_message(text=f"Elige un número entre 1 y {len(citas_disponibles)}.")
            return []

        cita_seleccionada = citas_disponibles[numero - 1]
        fecha_obj = datetime.strptime(cita_seleccionada['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
        fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')

        mensaje = f"📅 <b>Has seleccionado:</b>\n\n"
        mensaje += f"🔹 <b>{cita_seleccionada['servicio_nombre']}</b>\n"
        mensaje += f"📆 {fecha_legible}\n\n"
        mensaje += "¿Quieres cancelarla? Responde <b>'sí'</b> o <b>'no'</b>."

        dispatcher.utter_message(text=mensaje)

        return [
            SlotSet("flujo_activo", "cancelar_confirmacion"),
            SlotSet("cita_a_cancelar_id", cita_seleccionada['id']),
            SlotSet("citas_disponibles", None)
        ]

    def _ejecutar_procesar_confirmacion_cancelar(self, dispatcher, tracker):
        """Ejecuta la lógica de confirmar cancelación"""
        ultimo_mensaje = tracker.latest_message.get('text', '').lower().strip()
        cita_id = tracker.get_slot("cita_a_cancelar_id")
        cliente_id = tracker.get_slot("cliente_id")

        if not cita_id:
            dispatcher.utter_message(text="No he entendido. ¿En qué puedo ayudarte?")
            return limpiar_flujo()

        afirmaciones = ['sí', 'si', 'yes', 'vale', 'ok', 'claro', 'confirmo', 'afirmativo']
        negaciones = ['no', 'nada', 'negativo', 'mejor no']

        es_afirmativo = any(palabra in ultimo_mensaje for palabra in afirmaciones)
        es_negativo = any(palabra in ultimo_mensaje for palabra in negaciones)

        if es_afirmativo and not es_negativo:
            try:
                response = requests.delete(
                    f"{API_URL}/citas/{cita_id}",
                    params={"cliente_id": cliente_id},
                    timeout=5
                )
                
                if response.status_code in (200, 204):
                    dispatcher.utter_message(
                        text="✅ <b>Cita cancelada correctamente</b>\n\n"
                             "Si cambias de opinión, puedes reservar otra cita cuando quieras."
                    )
                else:
                    dispatcher.utter_message(text="No pude cancelar la cita. Intenta más tarde.")
                
            except Exception:
                dispatcher.utter_message(text="Hubo un error al cancelar. Intenta más tarde.")
            
            return limpiar_flujo()

        elif es_negativo:
            dispatcher.utter_message(text="Perfecto, tu cita se mantiene. ¿Puedo ayudarte con algo más?")
            return limpiar_flujo()

        else:
            dispatcher.utter_message(text="No entendí. Responde 'sí' para cancelar o 'no' para mantenerla.")
            return []

    def _ejecutar_seleccionar_cita_cambio(self, dispatcher, tracker):
        """Ejecuta la lógica de seleccionar cita para cambiar"""
        citas_disponibles = tracker.get_slot("citas_disponibles")
        negocio_id = tracker.get_slot("negocio_id")
        mensaje_usuario = tracker.latest_message.get('text', '')

        if not citas_disponibles:
            dispatcher.utter_message(text="No encuentro las citas. Di 'cambiar cita' para empezar de nuevo.")
            return limpiar_flujo()

        match = re.search(r'\b(\d+)\b', mensaje_usuario)
        if not match:
            dispatcher.utter_message(text="No entendí el número. ¿Cuál cita quieres cambiar? (1, 2, 3...)")
            return []

        numero = int(match.group(1))

        if numero < 1 or numero > len(citas_disponibles):
            dispatcher.utter_message(text=f"Elige un número entre 1 y {len(citas_disponibles)}.")
            return []

        cita_seleccionada = citas_disponibles[numero - 1]
        fecha_obj = datetime.strptime(cita_seleccionada['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
        fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')

        # Obtener horarios disponibles
        horarios = self._obtener_horarios(negocio_id, cita_seleccionada['servicio_id'])

        mensaje = f"📅 <b>Cita a cambiar:</b>\n\n"
        mensaje += f"🔹 <b>{cita_seleccionada['servicio_nombre']}</b>\n"
        mensaje += f"📆 {fecha_legible}\n\n"
        
        if horarios:
            mensaje += self._formatear_horarios(horarios)
        
        mensaje += "\n¿A qué día y hora quieres cambiarla?"

        dispatcher.utter_message(text=mensaje)

        return [
            SlotSet("flujo_activo", "cambiar_fecha"),
            SlotSet("cita_a_cancelar_id", cita_seleccionada['id']),
            SlotSet("servicio_id", cita_seleccionada['servicio_id']),
            SlotSet("servicio", cita_seleccionada['servicio_nombre']),
            SlotSet("horarios_disponibles", horarios),
            SlotSet("citas_disponibles", None)
        ]

    def _ejecutar_confirmar_cambio_horario(self, dispatcher, tracker):
        """Ejecuta la lógica de confirmar cambio de horario"""
        cita_id = tracker.get_slot("cita_a_cancelar_id")
        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        servicio = tracker.get_slot("servicio")
        horarios_disponibles = tracker.get_slot("horarios_disponibles")
        fecha_texto = tracker.latest_message.get('text', '')

        if not cita_id:
            dispatcher.utter_message(text="No tengo identificada la cita a cambiar.")
            return limpiar_flujo()

        try:
            nueva_fecha = self._interpretar_fecha(fecha_texto, horarios_disponibles)

            if not nueva_fecha:
                dispatcher.utter_message(text="No pude entender la fecha. Dime 'hoy', 'mañana' o un día específico.")
                return []

            # Eliminar cita antigua
            response_delete = requests.delete(f"{API_URL}/citas/{cita_id}", timeout=5)
            
            if response_delete.status_code not in (200, 204):
                dispatcher.utter_message(text="No pude cancelar la cita anterior. Intenta más tarde.")
                return limpiar_flujo()

            # Crear nueva cita
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

            if response_create.status_code in (200, 201):
                fecha_obj = datetime.strptime(nueva_fecha, '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                dispatcher.utter_message(
                    text=f"✅ <b>¡Cita modificada correctamente!</b>\n\n"
                         f"<b>Servicio:</b> {servicio}\n"
                         f"<b>Nueva fecha:</b> {fecha_legible}\n\n"
                         f"¡Gracias!"
                )
                return limpiar_flujo()
            else:
                dispatcher.utter_message(text="No pude crear la nueva cita. Contacta con el negocio.")
                return limpiar_flujo()

        except Exception as e:
            dispatcher.utter_message(text=f"Error al cambiar horario: {str(e)}")
            return limpiar_flujo()

    # ============================================
    # MÉTODOS DE UTILIDAD
    # ============================================

    def _interpretar_fecha(self, texto_fecha: str, horarios_disponibles: dict) -> str:
        if not texto_fecha:
            return None

        texto_lower = texto_fecha.lower().strip()
        hoy = datetime.now().date()

        # Extraer hora - más flexible con "a las", "las", etc.
        hora_match = re.search(r'(?:a las |las )?(\d{1,2})(?::(\d{2}))?', texto_lower)
        hora_especificada = None
        if hora_match:
            hora = int(hora_match.group(1))
            minuto = int(hora_match.group(2)) if hora_match.group(2) else 0
            hora_especificada = f"{hora:02d}:{minuto:02d}"

        fecha_objetivo = None
        
        if "hoy" in texto_lower:
            fecha_objetivo = hoy
        elif "mañana" in texto_lower or "manana" in texto_lower:
            fecha_objetivo = hoy + timedelta(days=1)
        elif "pasado" in texto_lower:
            fecha_objetivo = hoy + timedelta(days=2)
        else:
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
                    break
        
        if not fecha_objetivo and horarios_disponibles:
            fechas_disponibles = sorted(horarios_disponibles.keys())
            if fechas_disponibles:
                fecha_objetivo = datetime.strptime(fechas_disponibles[0], '%Y-%m-%d').date()

        if not fecha_objetivo:
            return None

        fecha_str = fecha_objetivo.strftime('%Y-%m-%d')

        if not horarios_disponibles or fecha_str not in horarios_disponibles:
            fechas_disponibles = sorted(horarios_disponibles.keys()) if horarios_disponibles else []
            for fecha_disponible in fechas_disponibles:
                if fecha_disponible >= fecha_str:
                    fecha_str = fecha_disponible
                    break
            else:
                return None

        horarios = horarios_disponibles.get(fecha_str, [])
        if not horarios:
            return None
            
        if hora_especificada:
            # Búsqueda exacta
            for slot in horarios:
                slot_hora = slot.split()[1][:5]
                if hora_especificada == slot_hora:
                    return slot
            
            # Búsqueda aproximada - horario más cercano
            hora_target = int(hora_especificada.split(':')[0])
            mejor_slot = None
            menor_diff = float('inf')
            
            for slot in horarios:
                slot_hora = slot.split()[1][:5]
                hora_slot = int(slot_hora.split(':')[0])
                diff = abs(hora_slot - hora_target)
                
                if diff < menor_diff:
                    menor_diff = diff
                    mejor_slot = slot
            
            if mejor_slot and menor_diff <= 1:  # Máximo 1 hora de diferencia
                return mejor_slot
        
        return horarios[0]

    def _obtener_horarios(self, negocio_id, servicio_id):
        horarios_por_dia = {}
        hoy = datetime.now().date()
        for i in range(7):
            fecha = hoy + timedelta(days=i)
            fecha_str = fecha.strftime('%Y-%m-%d')
            try:
                response = requests.post(
                    f"{API_URL}/disponibilidad",
                    json={"negocio_id": negocio_id, "servicio_id": servicio_id, "fecha": fecha_str},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    horarios = data.get('disponibles', [])
                    if horarios:
                        horarios_por_dia[fecha_str] = horarios[:5]
            except:
                pass
        return horarios_por_dia

    def _formatear_horarios(self, horarios_por_dia):
        dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        mensaje = "<b>📅 Horarios disponibles:</b>\n"
        for fecha_str, horarios in list(horarios_por_dia.items())[:5]:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
            dia_texto = f"{dias_es[fecha_obj.weekday()]} {fecha_obj.day:02d}/{fecha_obj.month:02d}"
            horas = [h.split()[1][:5] for h in horarios[:3]]
            mensaje += f"<b>{dia_texto}</b>: {', '.join(horas)}\n"
        return mensaje
