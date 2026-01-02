# backend/logic.py
from datetime import datetime, timedelta


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

def verificar_solapamiento(negocio_id, servicio_id, fecha_hora_cita_str, conn, cita_id_excluir=None):
    """Verifica si el tramo horario solicitado es válido (dentro de horario y sin citas).
    
    Args:
        cita_id_excluir: ID de la cita a excluir de la verificación (usado al editar una cita)
    """
    
    print(f"🔍 verificar_solapamiento: negocio={negocio_id}, servicio={servicio_id}, fecha_hora={fecha_hora_cita_str}, excluir_cita={cita_id_excluir}")
    
    # 1. Obtener duración
    servicio_info = conn.execute(
        'SELECT duracion_minutos FROM servicios WHERE id = %s', (servicio_id,)
    ).fetchone()
    if not servicio_info:
        return False, "Servicio no válido."

    duracion_servicio = servicio_info['duracion_minutos']
    
    # Parsear la fecha con soporte para múltiples formatos
    try:
        # Intentar formato ISO 8601 (YYYY-MM-DDTHH:MM)
        if 'T' in fecha_hora_cita_str:
            inicio_solicitado = datetime.strptime(fecha_hora_cita_str, '%Y-%m-%dT%H:%M')
        else:
            # Formato estándar (YYYY-MM-DD HH:MM:SS)
            inicio_solicitado = datetime.strptime(fecha_hora_cita_str, '%Y-%m-%d %H:%M:%S')
        fin_solicitado = inicio_solicitado + timedelta(minutes=duracion_servicio)
    except ValueError:
        # Intentar sin segundos
        try:
            inicio_solicitado = datetime.strptime(fecha_hora_cita_str, '%Y-%m-%d %H:%M')
            fin_solicitado = inicio_solicitado + timedelta(minutes=duracion_servicio)
        except ValueError:
            return False, "Formato de fecha u hora incorrecto."

    fecha_dia = inicio_solicitado.strftime('%Y-%m-%d')
    dia_semana = inicio_solicitado.weekday()
    
    print(f"📅 Fecha: {fecha_dia}, Día semana: {dia_semana}, Inicio: {inicio_solicitado}, Fin: {fin_solicitado}")

    # 2. Verificar horarios de apertura (Múltiples tramos: mañana/tarde)
    horarios = conn.execute(
        'SELECT hora_apertura, hora_cierre FROM horarios_negocio WHERE negocio_id = %s AND dia_semana = %s',
        (negocio_id, dia_semana)
    ).fetchall()
    
    print(f"⏰ Horarios encontrados: {len(horarios)}")
    for h in horarios:
        print(f"   Apertura: {h['hora_apertura']} (tipo: {type(h['hora_apertura'])}), Cierre: {h['hora_cierre']} (tipo: {type(h['hora_cierre'])})")
    
    if not horarios:
        return False, "Negocio cerrado este día."

    dentro_de_horario = False
    
    # Verificamos si la cita encaja TOTALMENTE en alguno de los tramos
    for horario in horarios:
        # Convertir time objects a strings si es necesario (PostgreSQL)
        hora_apertura_str = str(horario['hora_apertura']) if not isinstance(horario['hora_apertura'], str) else horario['hora_apertura']
        hora_cierre_str = str(horario['hora_cierre']) if not isinstance(horario['hora_cierre'], str) else horario['hora_cierre']
        
        # Intentar parsear con múltiples formatos
        apertura = None
        cierre = None
        
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M']:
            try:
                apertura = datetime.strptime(f"{fecha_dia} {hora_apertura_str}", fmt)
                cierre = datetime.strptime(f"{fecha_dia} {hora_cierre_str}", fmt)
                break
            except ValueError:
                continue
        
        if not apertura or not cierre:
            print(f"   ❌ No se pudo parsear horario: apertura={hora_apertura_str}, cierre={hora_cierre_str}")
            continue
        
        print(f"   ✅ Horario parseado: {apertura} - {cierre}")
        print(f"   Verificando: {inicio_solicitado} >= {apertura} and {fin_solicitado} <= {cierre}")
        print(f"   Resultado: {inicio_solicitado >= apertura} and {fin_solicitado <= cierre}")
        
        if inicio_solicitado >= apertura and fin_solicitado <= cierre:
            dentro_de_horario = True
            break
    
    if not dentro_de_horario:
        print(f"❌ Fuera de horario")
        return False, "La hora solicitada está fuera del horario de apertura."
    
    print(f"✅ Dentro de horario")

    # 3. Verificar solapamiento con otras citas
    if cita_id_excluir:
        citas_existentes = conn.execute(
            'SELECT c.fecha_hora_cita, s.duracion_minutos FROM citas c JOIN servicios s ON c.servicio_id = s.id WHERE c.negocio_id = %s AND date(c.fecha_hora_cita) = %s AND c.estado IN (%s, %s) AND c.id != %s',
            (negocio_id, fecha_dia, 'confirmada', 'confirmado', cita_id_excluir)
        ).fetchall()
    else:
        citas_existentes = conn.execute(
            'SELECT c.fecha_hora_cita, s.duracion_minutos FROM citas c JOIN servicios s ON c.servicio_id = s.id WHERE c.negocio_id = %s AND date(c.fecha_hora_cita) = %s AND c.estado IN (%s, %s)',
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


def obtener_tramos_disponibles(negocio_id, servicio_id, fecha_solicitada, conn, cita_id_excluir=None):
    """
    Calcula tramos libres usando una ventana deslizante (Step).
    Ej: Si paso=15min, prueba 9:00, 9:15, 9:30 para ver si cabe el servicio.
    
    Args:
        cita_id_excluir: ID de la cita a excluir (usado al editar una cita)
    """
    
    servicio_info = conn.execute('SELECT duracion_minutos FROM servicios WHERE id = %s', (servicio_id,)).fetchone()
    if not servicio_info: return {'error': 'Servicio no encontrado'}
    duracion_servicio = servicio_info['duracion_minutos']

    try:
        dt_solicitada = datetime.strptime(fecha_solicitada, '%Y-%m-%d')
    except ValueError: return {'error': 'Formato fecha incorrecto'}
    
    dia_semana = dt_solicitada.weekday()

    # 1. Obtener Horarios (Mañana y Tarde)
    horarios = conn.execute(
        'SELECT hora_apertura, hora_cierre FROM horarios_negocio WHERE negocio_id = %s AND dia_semana = %s ORDER BY hora_apertura',
        (negocio_id, dia_semana)
    ).fetchall()

    if not horarios:
        return {'disponibles': [], 'mensaje': 'Negocio cerrado este día.'}

    # 2. Obtener citas existentes (excluir la cita actual si se está editando)
    if cita_id_excluir:
        citas_existentes = conn.execute(
            'SELECT c.fecha_hora_cita, s.duracion_minutos FROM citas c JOIN servicios s ON c.servicio_id = s.id WHERE c.negocio_id = %s AND date(c.fecha_hora_cita) = %s AND c.estado IN (%s, %s) AND c.id != %s',
            (negocio_id, fecha_solicitada, 'confirmada', 'confirmado', cita_id_excluir)
        ).fetchall()
    else:
        citas_existentes = conn.execute(
            'SELECT c.fecha_hora_cita, s.duracion_minutos FROM citas c JOIN servicios s ON c.servicio_id = s.id WHERE c.negocio_id = %s AND date(c.fecha_hora_cita) = %s AND c.estado IN (%s, %s)',
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
    
    # Obtener hora actual para filtrar horarios pasados
    ahora = datetime.now()
    es_hoy = dt_solicitada.date() == ahora.date()

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
        
        # Si es hoy y la apertura ya pasó, empezar desde la hora actual (redondeada al siguiente paso)
        if es_hoy and ahora > hora_inicio_turno:
            # Redondear hora actual al siguiente múltiplo de PASO_BUSQUEDA
            minutos_desde_medianoche = ahora.hour * 60 + ahora.minute
            minutos_redondeados = ((minutos_desde_medianoche // PASO_BUSQUEDA) + 1) * PASO_BUSQUEDA
            hora_candidata_calculada = ahora.replace(hour=minutos_redondeados // 60, 
                                          minute=minutos_redondeados % 60, 
                                          second=0, 
                                          microsecond=0)
            
            # Usar la hora calculada solo si está dentro del turno actual
            if hora_candidata_calculada >= hora_inicio_turno and hora_candidata_calculada < hora_fin_turno:
                hora_candidata = hora_candidata_calculada
            elif hora_candidata_calculada >= hora_fin_turno:
                # Si la hora redondeada está después del cierre del turno, saltar este turno
                continue

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