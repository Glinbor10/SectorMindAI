from typing import Any, Text, Dict, List, Tuple
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

class ActionUrgenciaBase:
    """
    Clase de apoyo con lógica común. 
    NO hereda de 'Action' para que Rasa no intente registrarla como acción independiente.
    """

    def validar_tipo_negocio(self, tipo_esperado: str, tracker: Tracker, dispatcher: CollectingDispatcher) -> bool:
        """Valida que el negocio sea del tipo correcto"""
        tipo_negocio = tracker.get_slot("tipo_negocio")
        negocio_actual = tracker.get_slot("negocio") or "este negocio"
        if tipo_negocio != tipo_esperado:
            dispatcher.utter_message(text=f"Este servicio no está disponible en {negocio_actual}.")
            return False
        return True

    def obtener_slots_basicos(self, tracker: Tracker) -> Tuple:
        """Obtiene slots básicos comunes"""
        negocio_id = tracker.get_slot("negocio_id")
        cliente_id = tracker.get_slot("cliente_id")
        return negocio_id, cliente_id

    def validar_slots_basicos(self, negocio_id, cliente_id, dispatcher: CollectingDispatcher) -> bool:
        """Valida slots básicos"""
        if not negocio_id or not cliente_id:
            dispatcher.utter_message(text="No tengo suficiente información. Por favor, inicia desde la web.")
            return False
        return True