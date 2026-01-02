"""
Acciones principales de Rasa - Fallback inteligente y respuesta bot challenge
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction
from datetime import datetime, timedelta
import requests
import re
from fuzzywuzzy import fuzz

from .utils import limpiar_flujo, obtener_horarios_disponibles, formatear_horarios_display, API_URL
from .extractores import ExtractorFechaHora


# ============================================================
# RESPUESTA BOT CHALLENGE
# ============================================================

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
        
        elif flujo_activo == "reserva_hora":
            print("   → Redirigiendo a ActionConfirmarHoraReserva")
            return self._ejecutar_confirmar_hora_reserva(dispatcher, tracker)
        
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
            print("   → Redirigiendo a ActionConfirmarFechaCambio")
            return self._ejecutar_confirmar_fecha_cambio(dispatcher, tracker)
        
        elif flujo_activo == "cambiar_hora":
            print("   → Redirigiendo a ActionConfirmarHoraCambio")
            return self._ejecutar_confirmar_hora_cambio(dispatcher, tracker)

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

            servicios_disponibles = response.json()  # Backend returns list directly
            
            # Buscar coincidencia con servicios (con tolerancia a errores)
            servicio_encontrado = None
            mejor_similitud = 0
            
            mensaje_lower = mensaje_usuario.lower()
            
            for servicio in servicios_disponibles:
                nombre_servicio = servicio['nombre'].lower()
                
                # Búsqueda exacta primero (palabra completa)
                if nombre_servicio in mensaje_lower or any(nombre_servicio.startswith(palabra) for palabra in mensaje_lower.split()):
                    print(f"   → Servicio detectado (exacto): {servicio['nombre']}")
                    return [SlotSet("servicio_id", servicio['id']), SlotSet("servicio_nombre", servicio['nombre'])]
                
                # Fuzzy matching: comparar cada palabra del usuario contra el nombre del servicio
                palabras_usuario = mensaje_lower.split()
                palabras_servicio = nombre_servicio.split()
                
                for palabra_usuario in palabras_usuario:
                    if len(palabra_usuario) >= 3:  # Palabras de al menos 3 caracteres
                        # Comparar contra el nombre completo del servicio
                        similitud = fuzz.ratio(palabra_usuario, nombre_servicio) / 100.0
                        print(f"   [DEBUG] Comparando '{palabra_usuario}' vs '{nombre_servicio}': {similitud:.2f}")
                        if similitud > mejor_similitud and similitud > 0.60:  # Umbral de 60%
                            mejor_similitud = similitud
                            servicio_encontrado = servicio
                            print(f"   [DEBUG] Nuevo mejor: {servicio_encontrado['nombre']} con {similitud:.2f}")
                        
                        # Comparar contra cada palabra individual del servicio
                        for palabra_servicio in palabras_servicio:
                            if len(palabra_servicio) >= 3:
                                similitud_palabra = fuzz.ratio(palabra_usuario, palabra_servicio) / 100.0
                                print(f"   [DEBUG] Palabra a palabra: '{palabra_usuario}' vs '{palabra_servicio}': {similitud_palabra:.2f}")
                                if similitud_palabra > mejor_similitud and similitud_palabra > 0.70:  # Umbral más alto para palabras individuales
                                    mejor_similitud = similitud_palabra
                                    servicio_encontrado = servicio
                                    print(f"   [DEBUG] Nuevo mejor (palabra): {servicio_encontrado['nombre']} con {similitud_palabra:.2f}")
            
            if servicio_encontrado:
                print(f"   → Servicio detectado (fuzzy {mejor_similitud:.2f}): {servicio_encontrado['nombre']}")
                return [SlotSet("servicio_id", servicio_encontrado['id']), SlotSet("servicio_nombre", servicio_encontrado['nombre'])]

            # No se detectó servicio - mostrar opciones
            opciones = "\n".join([f"{i+1}. {s['nombre']}" for i, s in enumerate(servicios_disponibles)])
            dispatcher.utter_message(
                text=f"No estoy seguro de qué servicio te interesa. Tenemos:\n{opciones}\n\n¿Cuál te interesa?"
            )
            return []

        except Exception:
            dispatcher.utter_message(text="No he entendido bien. ¿Puedes repetirlo?")
            return []

    # ============================================
    # MÉTODOS AUXILIARES - Ejecutan la lógica de cada flujo
    # ============================================

    def _ejecutar_reservar_cita(self, dispatcher, tracker):
        """Ejecuta la lógica de reservar cita - SOLO PROCESA FECHA"""
        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        servicio = tracker.get_slot("servicio_nombre")
        horarios_disponibles = tracker.get_slot("horarios_disponibles")
        fecha_texto = tracker.latest_message.get('text', '')

        # Detectar si el usuario quiere cambiar de intención
        texto_lower = fecha_texto.lower()
        palabras_salir = ['anular', 'cancelar', 'no quiero', 'cambiar', 'salir', 'nada', 'olvidar']
        if any(palabra in texto_lower for palabra in palabras_salir):
            dispatcher.utter_message(text="Entendido, cancelamos. ¿En qué puedo ayudarte?")
            return limpiar_flujo()

        if not all([cliente_id, negocio_id, servicio_id]):
            dispatcher.utter_message(text="Falta información.")
            return limpiar_flujo()

        try:
            # SOLO EXTRAER FECHA
            fecha_seleccionada = ExtractorFechaHora.extraer_solo_fecha(fecha_texto, horarios_disponibles)

            if not fecha_seleccionada:
                # Verificar si se entendió la fecha pero no hay horarios
                texto_lower = fecha_texto.lower()
                mensaje_fecha = None
                
                if "hoy" in texto_lower or "mañana" in texto_lower or "manana" in texto_lower or "pasado" in texto_lower:
                    mensaje_fecha = "⚠️ Ese día no abrimos o no hay horarios disponibles."
                elif re.search(r'\b([1-9]|[12]\d|3[01])\b', texto_lower):
                    mensaje_fecha = "⚠️ Ese día no tenemos horarios disponibles."
                elif any(dia in texto_lower for dia in ['lunes', 'martes', 'miercoles', 'miércoles', 'jueves', 'viernes', 'sabado', 'sábado', 'domingo']):
                    mensaje_fecha = "⚠️ Ese día no abrimos o no hay horarios disponibles."
                else:
                    mensaje_fecha = "No entendí la fecha."
                
                dispatcher.utter_message(text=f"{mensaje_fecha} Dime otro día disponible.")
                return []  # Mantener flujo_activo="reserva_fecha" para que siga esperando

            # Obtener horarios para esa fecha
            horarios_dia = horarios_disponibles.get(fecha_seleccionada, [])
            if not horarios_dia:
                dispatcher.utter_message(text="No hay horarios para ese día. Elige otro.")
                return []

            # Mostrar horarios disponibles
            fecha_obj = datetime.strptime(fecha_seleccionada, '%Y-%m-%d')
            dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            dia_texto = f"{dias_es[fecha_obj.weekday()]} {fecha_obj.day:02d}/{fecha_obj.month:02d}"
            horas = [h.split()[1][:5] for h in horarios_dia]
            
            mensaje = f"📅 <b>Fecha seleccionada: {dia_texto}</b>\n\n"
            mensaje += f"⏰ <b>Horarios disponibles:</b> {', '.join(horas)}\n\n"
            mensaje += "¿A qué hora prefieres?"
            dispatcher.utter_message(text=mensaje)

            # Transicionar a siguiente paso: pedir hora
            return [
                SlotSet("flujo_activo", "reserva_hora"),
                SlotSet("fecha_reserva", fecha_seleccionada),
                SlotSet("horarios_dia", horarios_dia)
            ]

        except Exception as e:
            dispatcher.utter_message(text=f"Error: {str(e)}")
            return limpiar_flujo()

    def _ejecutar_confirmar_hora_reserva(self, dispatcher, tracker):
        """Ejecuta la lógica de confirmar hora de reserva"""
        cliente_id = tracker.get_slot("cliente_id")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        servicio = tracker.get_slot("servicio_nombre")
        fecha_reserva = tracker.get_slot("fecha_reserva")
        horarios_dia = tracker.get_slot("horarios_dia")
        hora_texto = tracker.latest_message.get('text', '')

        print(f"🔄 Fallback ConfirmarHora - cliente_id: {cliente_id}, negocio_id: {negocio_id}, servicio_id: {servicio_id}")

        if not all([cliente_id, negocio_id, servicio_id, fecha_reserva, horarios_dia]):
            dispatcher.utter_message(text="Falta información para completar la reserva.")
            return limpiar_flujo()

        try:
            # Extraer SOLO hora (retorna timestamp completo YYYY-MM-DD HH:MM:SS)
            slot_completo = ExtractorFechaHora.extraer_solo_hora(hora_texto, horarios_dia)

            if not slot_completo:
                dispatcher.utter_message(text="⏰ Esa hora no está disponible. Elige otra de las opciones.")
                return []  # Mantener flujo_activo="reserva_hora" para que siga esperando

            # Crear cita
            payload = {
                "cliente_id": cliente_id,
                "negocio_id": negocio_id,
                "servicio_id": servicio_id,
                "fecha_hora_cita": slot_completo
            }
            print(f"📤 Fallback POST /citas payload: {payload}")
            
            response = requests.post(
                f"{API_URL}/citas",
                json=payload,
                timeout=5
            )
            
            print(f"📥 Fallback Response: {response.status_code}, {response.text}")

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
        fecha_obj = datetime.fromisoformat(cita_seleccionada['fecha_hora_cita'])
        fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')

        mensaje = f"📅 <b>Has seleccionado:</b>\n\n"
        mensaje += f"🔹 <b>{cita_seleccionada.get('servicio_nombre', 'Servicio')}</b>\n"
        mensaje += f"📆 {fecha_legible}\n\n"
        mensaje += "¿Quieres cancelarla? Responde <b>'sí'</b> o <b>'no'</b>."

        dispatcher.utter_message(text=mensaje)

        return [
            SlotSet("flujo_activo", "cancelar_confirmacion"),
            SlotSet("cita_id_cancelar", cita_seleccionada['id']),
            SlotSet("citas_disponibles", None)
        ]

    def _ejecutar_procesar_confirmacion_cancelar(self, dispatcher, tracker):
        """Ejecuta la lógica de confirmar cancelación"""
        ultimo_mensaje = tracker.latest_message.get('text', '').lower().strip()
        cita_id = tracker.get_slot("cita_id_cancelar")

        if not cita_id:
            dispatcher.utter_message(text="No he entendido. ¿En qué puedo ayudarte?")
            return limpiar_flujo()

        afirmaciones = ['sí', 'si', 'yes', 'vale', 'ok', 'claro', 'confirmo', 'afirmativo']
        negaciones = ['no', 'nada', 'negativo', 'mejor no']

        es_afirmativo = any(palabra in ultimo_mensaje for palabra in afirmaciones)
        es_negativo = any(palabra in ultimo_mensaje for palabra in negaciones)

        if es_afirmativo and not es_negativo:
            try:
                print(f"🗑️ DELETE /citas/{cita_id}")
                response = requests.delete(
                    f"{API_URL}/citas/{cita_id}",
                    timeout=5
                )
                print(f"📥 DELETE Response: {response.status_code}")
                
                if response.status_code in (200, 204):
                    dispatcher.utter_message(
                        text="✅ <b>Cita cancelada correctamente</b>\n\n"
                             "Si cambias de opinión, puedes reservar otra cita cuando quieras."
                    )
                else:
                    dispatcher.utter_message(text="No pude cancelar la cita. Intenta más tarde.")
                
            except Exception as e:
                print(f"❌ Error DELETE: {e}")
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
        fecha_obj = datetime.fromisoformat(cita_seleccionada['fecha_hora_cita'])
        fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')

        # Obtener horarios disponibles
        horarios = obtener_horarios_disponibles(negocio_id, cita_seleccionada.get('servicio_id'))

        mensaje = f"📅 <b>Cita a cambiar:</b>\n\n"
        mensaje += f"🔹 <b>{cita_seleccionada.get('servicio_nombre', 'Servicio')}</b>\n"
        mensaje += f"📆 {fecha_legible}\n\n"
        
        if horarios:
            mensaje += formatear_horarios_display(horarios)
        
        mensaje += "\n¿Para qué día quieres cambiarla?"

        dispatcher.utter_message(text=mensaje)

        return [
            SlotSet("flujo_activo", "cambiar_fecha"),
            SlotSet("cita_id_cambio", cita_seleccionada['id']),
            SlotSet("servicio_id", cita_seleccionada.get('servicio_id')),
            SlotSet("servicio_nombre", cita_seleccionada.get('servicio_nombre')),
            SlotSet("horarios_disponibles", horarios),
            SlotSet("citas_disponibles", None)
        ]

    def _ejecutar_confirmar_fecha_cambio(self, dispatcher, tracker):
        """Ejecuta la lógica de confirmar FECHA de cambio - PIDE LA HORA"""
        cita_id = tracker.get_slot("cita_id_cambio")
        servicio = tracker.get_slot("servicio_nombre")
        horarios_disponibles = tracker.get_slot("horarios_disponibles")
        fecha_texto = tracker.latest_message.get('text', '')

        if not cita_id or not horarios_disponibles:
            dispatcher.utter_message(text="No tengo identificada la cita a cambiar.")
            return limpiar_flujo()

        try:
            # Extraer SOLO fecha (sin hora)
            fecha_str = ExtractorFechaHora.extraer_solo_fecha(fecha_texto, horarios_disponibles)

            if not fecha_str:
                # Verificar si se entendió la fecha pero no hay horarios
                texto_lower = fecha_texto.lower()
                mensaje_fecha = None
                
                if "hoy" in texto_lower or "mañana" in texto_lower or "manana" in texto_lower or "pasado" in texto_lower:
                    mensaje_fecha = "⚠️ Ese día no abrimos o no hay horarios disponibles."
                elif re.search(r'\b([1-9]|[12]\d|3[01])\b', texto_lower):
                    mensaje_fecha = "⚠️ Ese día no tenemos horarios disponibles."
                elif any(dia in texto_lower for dia in ['lunes', 'martes', 'miercoles', 'miércoles', 'jueves', 'viernes', 'sabado', 'sábado', 'domingo']):
                    mensaje_fecha = "⚠️ Ese día no abrimos o no hay horarios disponibles."
                else:
                    mensaje_fecha = "No entendí la fecha."
                
                dispatcher.utter_message(text=f"{mensaje_fecha} Dime otro día disponible.")
                return []  # Mantener flujo_activo="cambiar_fecha" para que siga esperando

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
                SlotSet("flujo_activo", "cambiar_hora"),
                SlotSet("fecha_reserva", fecha_str),
                SlotSet("horarios_dia", horarios_dia)
            ]

        except Exception as e:
            dispatcher.utter_message(text=f"Error al procesar fecha: {str(e)}")
            return limpiar_flujo()

    def _ejecutar_confirmar_hora_cambio(self, dispatcher, tracker):
        """Ejecuta la lógica de confirmar HORA de cambio - CAMBIA LA CITA"""
        cita_id = tracker.get_slot("cita_id_cambio")
        negocio_id = tracker.get_slot("negocio_id")
        servicio_id = tracker.get_slot("servicio_id")
        servicio = tracker.get_slot("servicio_nombre")
        fecha_str = tracker.get_slot("fecha_reserva")
        horarios_dia = tracker.get_slot("horarios_dia")
        hora_texto = tracker.latest_message.get('text', '')

        if not cita_id or not fecha_str or not horarios_dia:
            dispatcher.utter_message(text="Falta información para cambiar la cita.")
            return limpiar_flujo()

        try:
            # Extraer SOLO hora
            hora_seleccionada = ExtractorFechaHora.extraer_solo_hora(hora_texto, horarios_dia)

            if not hora_seleccionada:
                dispatcher.utter_message(text="⏰ Esa hora no está disponible. Elige otra de las opciones.")
                return []  # Mantener flujo_activo="cambiar_hora" para que siga esperando

            # hora_seleccionada es un timestamp completo "YYYY-MM-DD HH:MM:SS"
            # Extraer solo la parte de hora "HH:MM:SS"
            hora_str = hora_seleccionada.split()[1] if ' ' in hora_seleccionada else hora_seleccionada
            fecha_hora_nueva = f"{fecha_str} {hora_str}"
            
            print(f"📝 Fallback cambio - cita_id: {cita_id}, nueva fecha_hora: {fecha_hora_nueva}")

            # Actualizar cita
            response = requests.put(
                f"{API_URL}/citas/{cita_id}",
                json={"fecha_hora_cita": fecha_hora_nueva, "servicio_id": servicio_id},
                timeout=5
            )
            
            print(f"📥 PUT Response: {response.status_code}")

            if response.status_code == 200:
                fecha_obj = datetime.strptime(fecha_hora_nueva, '%Y-%m-%d %H:%M:%S')
                fecha_legible = fecha_obj.strftime('%d/%m/%Y a las %H:%M')
                
                dispatcher.utter_message(
                    text=f"✅ <b>¡Cita cambiada exitosamente!</b>\n\n"
                         f"<b>Servicio:</b> {servicio}\n"
                         f"<b>Nueva fecha:</b> {fecha_legible}\n\n"
                         f"¡Gracias!"
                )
                return limpiar_flujo()
            else:
                dispatcher.utter_message(text="No pude cambiar la cita. Contacta con el negocio.")
                return limpiar_flujo()

        except Exception as e:
            dispatcher.utter_message(text=f"Error al cambiar horario: {str(e)}")
            return limpiar_flujo()

