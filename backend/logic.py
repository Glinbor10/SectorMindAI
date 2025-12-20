# backend/logic.py
from datetime import datetime, timedelta
from .db_utils import adapt_query

# ======================================================================
# 📅 CONFIGURACIÓN
# ======================================================================
# Cada cuántos minutos probamos si hay hueco. 
# 15 minutos es el estándar para dentistas/fisios/peluquerías.
# Esto permite ofrecer citas a las 9:00, 9:15, 9:30, etc.
PASO_BUSQUEDA = 15 

# ======================================================================
# 📅 FUNCIONES DE LÓGICA DE NEGOCIO
# ======================================================================

def verificar_solapamiento(negocio_id, servicio_id, fecha_hora_cita_str, conn):
    """Verifica si el tramo horario solicitado es válido (dentro de horario y sin citas)."""
    
    # 1. Obtener duración
    servicio_info = conn.execute(
        adapt_query('SELECT duracion_minutos FROM servicios WHERE id = %s'), (servicio_id,)
    ).fetchone()
    if not servicio_info:
        return False, "Servicio no válido."

    duracion_servicio = servicio_info['duracion_minutos']
    
    try:
        inicio_solicitado = datetime.strptime(fecha_hora_cita_str, '%Y-%m-%d %H:%M:%S')
        fin_solicitado = inicio_solicitado + timedelta(minutes=duracion_servicio)
    except ValueError:
        return False, "Formato de fecha u hora incorrecto."

    fecha_dia = inicio_solicitado.strftime('%Y-%m-%d')
    dia_semana = inicio_solicitado.weekday()

    # 2. Verificar horarios de apertura (Múltiples tramos: mañana/tarde)
    horarios = conn.execute(
        adapt_query('SELECT hora_apertura, hora_cierre FROM horarios_negocio WHERE negocio_id = %s AND dia_semana = %s'),
        (negocio_id, dia_semana)
    ).fetchall()
    
    if not horarios:
        return False, "Negocio cerrado este día."

    dentro_de_horario = False
    
    # Verificamos si la cita encaja TOTALMENTE en alguno de los tramos
    for horario in horarios:
        # Convertir time objects a strings si es necesario (PostgreSQL)
        hora_apertura_str = str(horario['hora_apertura']) if not isinstance(horario['hora_apertura'], str) else horario['hora_apertura']
        hora_cierre_str = str(horario['hora_cierre']) if not isinstance(horario['hora_cierre'], str) else horario['hora_cierre']
        
        try:
            apertura = datetime.strptime(f"{fecha_dia} {hora_apertura_str}", '%Y-%m-%d %H:%M:%S')
            cierre = datetime.strptime(f"{fecha_dia} {hora_cierre_str}", '%Y-%m-%d %H:%M:%S')
        except ValueError:
            apertura = datetime.strptime(f"{fecha_dia} {hora_apertura_str}", '%Y-%m-%d %H:%M')
            cierre = datetime.strptime(f"{fecha_dia} {hora_cierre_str}", '%Y-%m-%d %H:%M')

        if inicio_solicitado >= apertura and fin_solicitado <= cierre:
            dentro_de_horario = True
            break
    
    if not dentro_de_horario:
        return False, "La hora solicitada está fuera del horario de apertura."

    # 3. Verificar solapamiento con otras citas
    citas_existentes = conn.execute(
        adapt_query('SELECT c.fecha_hora_cita, s.duracion_minutos FROM citas c JOIN servicios s ON c.servicio_id = s.id WHERE c.negocio_id = %s AND date(c.fecha_hora_cita) = %s AND c.estado IN (%s, %s)'),
        (negocio_id, fecha_dia, 'confirmada', 'confirmado')
    ).fetchall()

    for cita in citas_existentes:
        # PostgreSQL puede devolver datetime directo, SQLite devuelve string
        if isinstance(cita['fecha_hora_cita'], str):
            inicio_cita = datetime.strptime(cita['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
        else:
            inicio_cita = cita['fecha_hora_cita']
        
        fin_cita = inicio_cita + timedelta(minutes=cita['duracion_minutos'])
        
        # Lógica de colisión estricta: (StartA < EndB) and (EndA > StartB)
        if (inicio_solicitado < fin_cita) and (fin_solicitado > inicio_cita):
            return False, "La hora seleccionada se solapa con una cita ya existente."

    return True, "Cita válida."


def obtener_tramos_disponibles(negocio_id, servicio_id, fecha_solicitada, conn):
    """
    Calcula tramos libres usando una ventana deslizante (Step).
    Ej: Si paso=15min, prueba 9:00, 9:15, 9:30 para ver si cabe el servicio.
    """
    
    servicio_info = conn.execute(adapt_query('SELECT duracion_minutos FROM servicios WHERE id = %s'), (servicio_id,)).fetchone()
    if not servicio_info: return {'error': 'Servicio no encontrado'}
    duracion_servicio = servicio_info['duracion_minutos']

    try:
        dt_solicitada = datetime.strptime(fecha_solicitada, '%Y-%m-%d')
    except ValueError: return {'error': 'Formato fecha incorrecto'}
    
    dia_semana = dt_solicitada.weekday()

    # 1. Obtener Horarios (Mañana y Tarde)
    horarios = conn.execute(
        adapt_query('SELECT hora_apertura, hora_cierre FROM horarios_negocio WHERE negocio_id = %s AND dia_semana = %s ORDER BY hora_apertura'),
        (negocio_id, dia_semana)
    ).fetchall()

    if not horarios:
        return {'disponibles': [], 'mensaje': 'Negocio cerrado este día.'}

    # 2. Obtener citas existentes
    citas_existentes = conn.execute(
        adapt_query('SELECT c.fecha_hora_cita, s.duracion_minutos FROM citas c JOIN servicios s ON c.servicio_id = s.id WHERE c.negocio_id = %s AND date(c.fecha_hora_cita) = %s AND c.estado IN (%s, %s)'),
        (negocio_id, fecha_solicitada, 'confirmada', 'confirmado')
    ).fetchall()

    tramos_ocupados = []
    for cita in citas_existentes:
        # PostgreSQL puede devolver datetime directo, SQLite devuelve string
        if isinstance(cita['fecha_hora_cita'], str):
            inicio = datetime.strptime(cita['fecha_hora_cita'], '%Y-%m-%d %H:%M:%S')
        else:
            inicio = cita['fecha_hora_cita']
        fin = inicio + timedelta(minutes=cita['duracion_minutos'])
        tramos_ocupados.append((inicio, fin))

    tramos_disponibles = []
    
    # Duración que necesitamos reservar
    duracion_delta = timedelta(minutes=duracion_servicio)
    # Paso de búsqueda (cada cuánto ofrecemos una cita: 15 mins)
    paso_delta = timedelta(minutes=PASO_BUSQUEDA)

    # 3. Iterar sobre cada turno (Mañana / Tarde)
    for turno in horarios:
        # Convertir time objects a strings si es necesario (PostgreSQL)
        hora_apertura_str = str(turno['hora_apertura']) if not isinstance(turno['hora_apertura'], str) else turno['hora_apertura']
        hora_cierre_str = str(turno['hora_cierre']) if not isinstance(turno['hora_cierre'], str) else turno['hora_cierre']
        
        try:
            hora_inicio_turno = datetime.strptime(f"{fecha_solicitada} {hora_apertura_str}", '%Y-%m-%d %H:%M:%S')
            hora_fin_turno = datetime.strptime(f"{fecha_solicitada} {hora_cierre_str}", '%Y-%m-%d %H:%M:%S')
        except:
            hora_inicio_turno = datetime.strptime(f"{fecha_solicitada} {hora_apertura_str}", '%Y-%m-%d %H:%M')
            hora_fin_turno = datetime.strptime(f"{fecha_solicitada} {hora_cierre_str}", '%Y-%m-%d %H:%M')

        # Empezamos a buscar desde que abre el turno
        hora_candidata = hora_inicio_turno

        # Mientras el servicio quepa antes de cerrar el turno...
        while hora_candidata + duracion_delta <= hora_fin_turno:
            
            fin_candidato = hora_candidata + duracion_delta
            esta_libre = True

            # Verificar colisión con citas existentes
            for inicio_ocupado, fin_ocupado in tramos_ocupados:
                # Si hay solapamiento: (StartA < EndB) y (EndA > StartB)
                if (hora_candidata < fin_ocupado) and (fin_candidato > inicio_ocupado):
                    esta_libre = False
                    break 
            
            if esta_libre:
                tramos_disponibles.append(hora_candidata.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Avanzamos siempre 15 minutos (PASO_BUSQUEDA), independientemente de lo que dure el servicio.
            # Así encontramos huecos a las 9:00, 9:15, 9:30...
            hora_candidata += paso_delta

    return {'disponibles': tramos_disponibles}