"""
Utilidades comunes para las acciones de Rasa
"""
import os
import requests
from datetime import datetime
from typing import Dict, Any, List
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

API_URL = os.getenv("API_URL", "http://backend:5000")


def limpiar_flujo():
    """Limpia todos los slots de flujo activo"""
    return [
        SlotSet("flujo_activo", None),
        SlotSet("servicio_id", None),
        SlotSet("servicio", None),
        SlotSet("horarios_disponibles", None),
        SlotSet("cita_id_cancelar", None),
        SlotSet("cita_id_cambio", None),
        SlotSet("citas_disponibles", None),
        SlotSet("fecha_reserva", None),
        SlotSet("horarios_dia", None)
    ]


def obtener_horarios_disponibles(negocio_id: int, servicio_id: int, dias: int = 30) -> dict:
    """
    Obtiene horarios disponibles del backend para los próximos N días.
    Retorna: dict con formato {fecha: [slots]}
    """
    from datetime import timedelta
    
    horarios_por_dia = {}
    fecha_actual = datetime.now().date()
    
    try:
        for i in range(dias):
            fecha = fecha_actual + timedelta(days=i)
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
                disponibles = data.get('disponibles', [])
                
                if disponibles:
                    horarios_por_dia[fecha_str] = disponibles
        
        return horarios_por_dia
    except Exception as e:
        print(f"Error obteniendo horarios: {e}")
        return {}


def formatear_horarios_display(horarios_por_dia: dict, negocio_id: int = None, 
                               servicio_id: int = None, dias_mostrar: int = 3) -> str:
    """
    Formatea horarios para mostrar al usuario (compacto).
    
    Args:
        horarios_por_dia: Dict con {fecha: [slots]}
        negocio_id: ID del negocio (no usado actualmente)
        servicio_id: ID del servicio (no usado actualmente)
        dias_mostrar: Número de días a mostrar (default: 3 para mantenerlo corto)
    
    Returns:
        String formateado con horarios de forma compacta
    """
    if not horarios_por_dia:
        return "No hay horarios disponibles."
    
    dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    dias_cortos = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sab', 'Dom']
    
    mensaje = "📅 <b>Próximas disponibilidades:</b>\n"
    
    fechas_ordenadas = sorted(horarios_por_dia.keys())[:dias_mostrar]
    
    for fecha_str in fechas_ordenadas:
        horarios = horarios_por_dia[fecha_str]
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
        dia_corto = dias_cortos[fecha_obj.weekday()]
        
        # Solo mostrar primeras 3 horas por día
        horas = [h.split()[1][:5] for h in horarios[:3]]
        horas_texto = ', '.join(horas)
        
        if len(horarios) > 3:
            horas_texto += f"... (+{len(horarios)-3} más)"
        
        mensaje += f"<b>{dia_corto} {fecha_obj.day}</b>: {horas_texto}\n"
    
    return mensaje


def build_availability_dates_payload(horarios_por_dia: dict, dias_mostrar: int = 5) -> Dict[str, Any]:
    if not horarios_por_dia:
        return {"dates": [], "meta": {"total": 0, "last_label": ""}}
    dias_cortos = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']
    fechas_ordenadas = sorted(horarios_por_dia.keys())
    fechas = []
    for fecha_str in fechas_ordenadas[:dias_mostrar]:
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
        dia_corto = dias_cortos[fecha_obj.weekday()]
        label = f"{dia_corto} {fecha_obj.day:02d}/{fecha_obj.month:02d}"
        value = f"{fecha_obj.day:02d}/{fecha_obj.month:02d}"
        fechas.append({"label": label, "value": value})
    last_label = ""
    if fechas_ordenadas:
        last_fecha = datetime.strptime(fechas_ordenadas[-1], '%Y-%m-%d')
        last_label = f"{dias_cortos[last_fecha.weekday()]} {last_fecha.day:02d}/{last_fecha.month:02d}"
    return {
        "dates": fechas,
        "meta": {"total": len(fechas_ordenadas), "last_label": last_label}
    }


def build_availability_hours_payload(horarios_dia: List[str], max_items: int = 8) -> Dict[str, Any]:
    if not horarios_dia:
        return {"hours": [], "meta": {"total": 0, "morning": 0, "afternoon": 0}}
    horas = [h.split()[1][:5] for h in horarios_dia]
    morning = 0
    afternoon = 0
    for h in horas:
        try:
            hour = int(h.split(':')[0])
            if hour < 14:
                morning += 1
            else:
                afternoon += 1
        except Exception:
            continue
    return {
        "hours": horas[:max_items],
        "meta": {"total": len(horas), "morning": morning, "afternoon": afternoon}
    }


def calcular_similitud(palabra1: str, palabra2: str) -> float:
    """
    Calcula similitud entre dos palabras (Levenshtein normalizado)
    """
    if palabra1 == palabra2:
        return 1.0
    
    len1, len2 = len(palabra1), len(palabra2)
    if len1 == 0 or len2 == 0:
        return 0.0
    
    # Matriz de distancia de Levenshtein
    matriz = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    for i in range(len1 + 1):
        matriz[i][0] = i
    for j in range(len2 + 1):
        matriz[0][j] = j
    
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            costo = 0 if palabra1[i-1] == palabra2[j-1] else 1
            matriz[i][j] = min(
                matriz[i-1][j] + 1,      # eliminación
                matriz[i][j-1] + 1,      # inserción
                matriz[i-1][j-1] + costo # sustitución
            )
    
    distancia = matriz[len1][len2]
    max_len = max(len1, len2)
    similitud = 1 - (distancia / max_len)
    
    return similitud
