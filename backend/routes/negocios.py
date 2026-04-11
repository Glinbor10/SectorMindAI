from flask import Blueprint, jsonify, request
from ..db import get_db_connection 
from ..perf import medir_tiempo

negocios_bp = Blueprint('negocios', __name__, url_prefix='/negocios')



# 1. LISTAR NEGOCIOS
@negocios_bp.route('/', methods=['GET'])
@medir_tiempo('GET /negocios/')
def listar_negocios():
    propietario_id = request.args.get('propietario_id')
    user_lat = request.args.get('lat')  # Latitud del usuario
    user_lon = request.args.get('lon')  # Longitud del usuario
    
    conn = get_db_connection()
    
    # Construir query con cálculo de distancia si se proporcionan coordenadas del usuario
    if user_lat and user_lon:
        try:
            user_lat = float(user_lat)
            user_lon = float(user_lon)
            
            query = """
                SELECT n.id, n.nombre, n.tipo_negocio, n.direccion, n.descripcion, n.foto_base64,
                       n.propietario_id, n.latitud, n.longitud, n.created_at,
                CASE 
                    WHEN n.latitud IS NOT NULL AND n.longitud IS NOT NULL
                    THEN 6371 * acos(
                        cos(radians(%s)) * cos(radians(n.latitud)) * 
                        cos(radians(n.longitud) - radians(%s)) + 
                        sin(radians(%s)) * sin(radians(n.latitud))
                    )
                    ELSE NULL
                END as distancia_km
                FROM negocios n
            """
            params = [user_lat, user_lon, user_lat]
        except (ValueError, TypeError):
            return jsonify({'error': 'Coordenadas inválidas'}), 400
    else:
        query = """
            SELECT n.id, n.nombre, n.tipo_negocio, n.direccion, n.descripcion, n.foto_base64,
                   n.propietario_id, n.latitud, n.longitud, n.created_at
            FROM negocios n
        """
        params = []
    
    if propietario_id:
        try:
            propietario_id = int(propietario_id)
        except ValueError:
            return jsonify({'error': 'propietario_id inválido'}), 400
        query += " WHERE n.propietario_id = %s"
        params.append(propietario_id)
    
    # Ordenar por distancia si está disponible
    if user_lat and user_lon:
        query += " ORDER BY distancia_km NULLS LAST"
    
    negocios = conn.execute(query, params).fetchall()
    conn.close()
    negocios_list = []
    for row in negocios:
        row_dict = dict(row)
        # Solo exponer foto_base64
        negocios_list.append(row_dict)
    return jsonify(negocios_list)

# 2. OBTENER UN SOLO NEGOCIO
@negocios_bp.route('/<int:negocio_id>', methods=['GET'])
def obtener_negocio(negocio_id):
    conn = get_db_connection()
    query = """
        SELECT n.id, n.nombre, n.tipo_negocio, n.direccion, n.descripcion, n.foto_base64,
               n.propietario_id, n.latitud, n.longitud, n.created_at
        FROM negocios n
        WHERE n.id = %s
    """
    negocio = conn.execute(query, (negocio_id,)).fetchone()
    
    if negocio is None:
        conn.close()
        return jsonify({'error': 'Negocio no encontrado'}), 404
        
    row_dict = dict(negocio)
    
    # Obtener horarios de la tabla horarios_negocio
    horarios_query = """
        SELECT dia_semana, hora_apertura, hora_cierre
        FROM horarios_negocio
        WHERE negocio_id = %s
        ORDER BY dia_semana, hora_apertura
    """
    horarios_rows = conn.execute(horarios_query, (negocio_id,)).fetchall()
    conn.close()
    
    # Formatear horarios en texto legible
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    horarios_texto = ""
    if horarios_rows:
        dia_actual = None
        for row in horarios_rows:
            dia_semana = row['dia_semana']  # Access by column name
            hora_apertura = row['hora_apertura']
            hora_cierre = row['hora_cierre']
            if dia_semana != dia_actual:
                if dia_actual is not None:
                    horarios_texto += "\n"
                horarios_texto += f"{dias[dia_semana]}: {hora_apertura.strftime('%H:%M')} - {hora_cierre.strftime('%H:%M')}"
                dia_actual = dia_semana
            else:
                horarios_texto += f" y {hora_apertura.strftime('%H:%M')} - {hora_cierre.strftime('%H:%M')}"
    else:
        horarios_texto = "No disponible"
    
    row_dict['horarios'] = horarios_texto
    
    # Solo exponer foto_base64
    return jsonify(row_dict)

# 3. CREAR NEGOCIO
@negocios_bp.route('/', methods=['POST'])
def crear_negocio():
    print(f"DEBUG: Content-Type recibido: {request.content_type}")
    print(f"DEBUG: Method: {request.method}")
    print(f"DEBUG: Form keys: {list(request.form.keys()) if request.form else 'None'}")
    print(f"DEBUG: Files keys: {list(request.files.keys()) if request.files else 'None'}")


    # Permitir tanto JSON como FormData
    foto_base64 = None
    horarios = None
    latitud = None
    longitud = None
    
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        nombre = request.form.get('nombre')
        tipo_negocio = request.form.get('tipo_negocio', 'general')
        direccion = request.form.get('direccion')
        descripcion = request.form.get('descripcion')
        propietario_id = request.form.get('propietario_id')
        horarios = request.form.get('horarios')
        dias_apertura = request.form.get('dias_apertura')
        latitud = request.form.get('latitud')
        longitud = request.form.get('longitud')
        # Procesar archivo de foto si existe
        if 'foto' in request.files:
            foto_file = request.files['foto']
            if foto_file:
                import base64
                foto_base64 = 'data:' + foto_file.mimetype + ';base64,' + base64.b64encode(foto_file.read()).decode('utf-8')
    else:
        data = request.get_json() or {}
        nombre = data.get('nombre')
        tipo_negocio = data.get('tipo_negocio', 'general')
        direccion = data.get('direccion')
        descripcion = data.get('descripcion')
        propietario_id = data.get('propietario_id')
        horarios = data.get('horarios')
        dias_apertura = data.get('dias_apertura')
        latitud = data.get('latitud')
        longitud = data.get('longitud')

    if not (nombre and direccion and propietario_id):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    try:
        propietario_id = int(propietario_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'propietario_id inválido'}), 400
    
    # Validar y convertir coordenadas si están presentes
    if latitud is not None:
        try:
            latitud = float(latitud)
            if latitud < -90 or latitud > 90:
                return jsonify({'error': 'Latitud debe estar entre -90 y 90'}), 400
        except (ValueError, TypeError):
            latitud = None
    
    if longitud is not None:
        try:
            longitud = float(longitud)
            if longitud < -180 or longitud > 180:
                return jsonify({'error': 'Longitud debe estar entre -180 y 180'}), 400
        except (ValueError, TypeError):
            longitud = None
    
    # Parsear días de apertura y horarios si vienen como JSON string
    import json
    if dias_apertura is not None and isinstance(dias_apertura, str):
        try:
            dias_apertura = json.loads(dias_apertura)
        except json.JSONDecodeError:
            return jsonify({'error': 'dias_apertura debe ser un array JSON válido'}), 400
    
    if horarios is not None and isinstance(horarios, str):
        try:
            horarios = json.loads(horarios)
        except json.JSONDecodeError:
            return jsonify({'error': 'horarios debe ser un array JSON válido'}), 400
    
    # Permitir crear negocio sin horarios; normalizar a listas vacías cuando no se envían
    if dias_apertura is None:
        dias_apertura = []
    if horarios is None:
        horarios = []
    
    if dias_apertura and not isinstance(dias_apertura, list):
        return jsonify({'error': 'dias_apertura debe ser una lista'}), 400
    
    if horarios and not isinstance(horarios, list):
        return jsonify({'error': 'horarios debe ser una lista'}), 400

    conn = get_db_connection()
    try:
        # Crear el negocio con coordenadas
        if foto_base64 and (latitud is not None and longitud is not None):
            cursor = conn.execute(
                'INSERT INTO negocios (nombre, tipo_negocio, direccion, descripcion, propietario_id, foto_base64, latitud, longitud) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id',
                (nombre, tipo_negocio, direccion, descripcion, propietario_id, foto_base64, latitud, longitud)
            )
        elif foto_base64:
            cursor = conn.execute(
                'INSERT INTO negocios (nombre, tipo_negocio, direccion, descripcion, propietario_id, foto_base64) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id',
                (nombre, tipo_negocio, direccion, descripcion, propietario_id, foto_base64)
            )
        elif latitud is not None and longitud is not None:
            cursor = conn.execute(
                'INSERT INTO negocios (nombre, tipo_negocio, direccion, descripcion, propietario_id, latitud, longitud) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id',
                (nombre, tipo_negocio, direccion, descripcion, propietario_id, latitud, longitud)
            )
        else:
            cursor = conn.execute(
                'INSERT INTO negocios (nombre, tipo_negocio, direccion, descripcion, propietario_id) VALUES (%s, %s, %s, %s, %s) RETURNING id',
                (nombre, tipo_negocio, direccion, descripcion, propietario_id)
            )
        new_id = cursor.fetchone()['id']
        
        # Insertar horarios si se enviaron; permite negocio sin horarios
        if dias_apertura and horarios:
            for dia in dias_apertura:
                for horario in horarios:
                    conn.execute(
                        'INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (%s, %s, %s, %s)',
                        (new_id, dia, horario['apertura'], horario['cierre'])
                    )
            message = 'Negocio creado exitosamente con horarios'
        else:
            message = 'Negocio creado exitosamente'
        
        conn.commit()
        return jsonify({'id': new_id, 'message': message}), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 4. ACTUALIZAR NEGOCIO
@negocios_bp.route('/<int:negocio_id>', methods=['PUT'])
def actualizar_negocio(negocio_id):
    # Soporta tanto JSON como FormData (para actualizar foto)

    data = request.get_json()
    nombre = data.get('nombre') if data else None
    tipo_negocio = data.get('tipo_negocio') if data else None
    descripcion = data.get('descripcion') if data else None
    direccion = data.get('direccion') if data else None
    foto_base64 = data.get('foto_base64') if data else None
    latitud = data.get('latitud') if data else None
    longitud = data.get('longitud') if data else None
    
    if not any([nombre, tipo_negocio, descripcion, foto_base64, direccion, latitud, longitud]):
        return jsonify({'error': 'No hay datos para actualizar'}), 400
    
    # Validar coordenadas si están presentes
    if latitud is not None:
        try:
            latitud = float(latitud)
            if latitud < -90 or latitud > 90:
                return jsonify({'error': 'Latitud debe estar entre -90 y 90'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Latitud inválida'}), 400
    
    if longitud is not None:
        try:
            longitud = float(longitud)
            if longitud < -180 or longitud > 180:
                return jsonify({'error': 'Longitud debe estar entre -180 y 180'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Longitud inválida'}), 400

    conn = get_db_connection()
    try:
        updates = []
        params = []
        if nombre is not None:
            updates.append("nombre = %s")
            params.append(nombre)
        if tipo_negocio is not None:
            updates.append("tipo_negocio = %s")
            params.append(tipo_negocio)
        if descripcion is not None:
            updates.append("descripcion = %s")
            params.append(descripcion)
        if latitud is not None:
            updates.append("latitud = %s")
            params.append(latitud)
        if longitud is not None:
            updates.append("longitud = %s")
            params.append(longitud)
        if foto_base64 is not None:
            updates.append("foto_base64 = %s")
            params.append(foto_base64)
        if direccion is not None:
            updates.append("direccion = %s")
            params.append(direccion)
        params.append(negocio_id)
        query = f"UPDATE negocios SET {', '.join(updates)} WHERE id = %s"
        cursor = conn.execute(query, params)
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'error': 'Negocio no encontrado'}), 404
        return jsonify({'message': 'Negocio actualizado', 'foto_base64': foto_base64}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 5. OBTENER SERVICIOS DE UN NEGOCIO (ESTO ES LO NUEVO)
@negocios_bp.route('/<int:negocio_id>/servicios', methods=['GET'])
def obtener_servicios_negocio(negocio_id):
    conn = get_db_connection()
    try:
        # Obtenemos nombre e id de los servicios
        query = "SELECT id, nombre, duracion_minutos, precio FROM servicios WHERE negocio_id = %s"
        servicios = conn.execute(query, (negocio_id,)).fetchall()
        return jsonify([dict(row) for row in servicios])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 6. OBTENER HORARIOS DE UN NEGOCIO
@negocios_bp.route('/<int:negocio_id>/horarios', methods=['GET'])
def obtener_horarios_negocio(negocio_id):
    conn = get_db_connection()
    try:
        query = "SELECT dia_semana, hora_apertura, hora_cierre FROM horarios_negocio WHERE negocio_id = %s ORDER BY dia_semana, hora_apertura"
        horarios = conn.execute(query, (negocio_id,)).fetchall()
        # Convertir time objects a strings para PostgreSQL
        result = []
        for row in horarios:
            horario_dict = dict(row)
            if 'hora_apertura' in horario_dict:
                horario_dict['hora_apertura'] = str(horario_dict['hora_apertura'])
            if 'hora_cierre' in horario_dict:
                horario_dict['hora_cierre'] = str(horario_dict['hora_cierre'])
            result.append(horario_dict)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 6b. ACTUALIZAR HORARIOS DE UN NEGOCIO
@negocios_bp.route('/<int:negocio_id>/horarios', methods=['PUT'])
def actualizar_horarios_negocio(negocio_id):
    data = request.get_json()
    horarios = data.get('horarios')
    dias_apertura = data.get('dias_apertura')
    
    if not (horarios and dias_apertura):
        return jsonify({'error': 'Debes especificar horarios y dias_apertura'}), 400
    
    if not isinstance(dias_apertura, list) or len(dias_apertura) == 0:
        return jsonify({'error': 'dias_apertura debe ser una lista con al menos un día'}), 400
    
    if not isinstance(horarios, list) or len(horarios) == 0:
        return jsonify({'error': 'horarios debe ser una lista con al menos un horario'}), 400
    
    conn = get_db_connection()
    try:
        # Eliminar horarios existentes
        conn.execute('DELETE FROM horarios_negocio WHERE negocio_id = %s', (negocio_id,))
        
        # Insertar nuevos horarios para cada día y cada rango horario (mañana/tarde)
        for dia in dias_apertura:
            for horario in horarios:
                conn.execute(
                    'INSERT INTO horarios_negocio (negocio_id, dia_semana, hora_apertura, hora_cierre) VALUES (%s, %s, %s, %s)',
                    (negocio_id, dia, horario['apertura'], horario['cierre'])
                )
        
        conn.commit()
        return jsonify({'message': 'Horarios actualizados exitosamente'}), 200
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 7. CREAR SERVICIO PARA UN NEGOCIO
@negocios_bp.route('/<int:negocio_id>/servicios', methods=['POST'])
def crear_servicio(negocio_id):
    data = request.get_json()
    nombre = data.get('nombre')
    precio = data.get('precio')
    duracion_minutos = data.get('duracion_minutos')
    propietario_id = data.get('propietario_id')  # Para verificar permisos

    if not (nombre and precio is not None and duracion_minutos):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    # Validación explícita de precio y duración
    try:
        precio = float(precio)
        duracion_minutos = int(duracion_minutos)
    except (ValueError, TypeError):
        return jsonify({'error': 'Precio y duración deben ser numéricos'}), 400
    if precio <= 0:
        return jsonify({'error': 'El precio debe ser mayor que cero'}), 400
    if duracion_minutos <= 0:
        return jsonify({'error': 'La duración debe ser mayor que cero'}), 400

    try:
        propietario_id = int(propietario_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'propietario_id inválido'}), 400

    conn = get_db_connection()
    try:
        # Verificar que el negocio pertenece al propietario
        negocio = conn.execute("SELECT propietario_id FROM negocios WHERE id = %s", (negocio_id,)).fetchone()
        if not negocio or negocio['propietario_id'] != propietario_id:
            return jsonify({'error': 'No tienes permisos para este negocio'}), 403

        cursor = conn.execute(
            'INSERT INTO servicios (negocio_id, nombre, precio, duracion_minutos) VALUES (%s, %s, %s, %s) RETURNING id',
            (negocio_id, nombre, precio, duracion_minutos)
        )
        new_id = cursor.fetchone()['id']
        conn.commit()
        return jsonify({'id': new_id, 'message': 'Servicio creado exitosamente'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 8. ACTUALIZAR SERVICIO
@negocios_bp.route('/<int:negocio_id>/servicios/<int:servicio_id>', methods=['PUT'])
def actualizar_servicio(negocio_id, servicio_id):
    data = request.get_json()
    nombre = data.get('nombre')
    precio = data.get('precio')
    duracion_minutos = data.get('duracion_minutos')
    propietario_id = data.get('propietario_id')

    if not any([nombre, precio is not None, duracion_minutos]):
        return jsonify({'error': 'No hay datos para actualizar'}), 400

    # Validación explícita de precio y duración si se envían
    if precio is not None:
        try:
            precio = float(precio)
        except (ValueError, TypeError):
            return jsonify({'error': 'El precio debe ser numérico'}), 400
        if precio <= 0:
            return jsonify({'error': 'El precio debe ser mayor que cero'}), 400
    if duracion_minutos is not None:
        try:
            duracion_minutos = int(duracion_minutos)
        except (ValueError, TypeError):
            return jsonify({'error': 'La duración debe ser numérica'}), 400
        if duracion_minutos <= 0:
            return jsonify({'error': 'La duración debe ser mayor que cero'}), 400

    try:
        propietario_id = int(propietario_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'propietario_id inválido'}), 400

    conn = get_db_connection()
    try:
        # Verificar permisos
        negocio = conn.execute("SELECT propietario_id FROM negocios WHERE id = %s", (negocio_id,)).fetchone()
        if not negocio or negocio['propietario_id'] != propietario_id:
            return jsonify({'error': 'No tienes permisos para este negocio'}), 403

        # Verificar que el servicio pertenece al negocio
        servicio = conn.execute("SELECT id FROM servicios WHERE id = %s AND negocio_id = %s", (servicio_id, negocio_id)).fetchone()
        if not servicio:
            return jsonify({'error': 'Servicio no encontrado'}), 404

        updates = []
        params = []
        if nombre is not None:
            updates.append("nombre = %s")
            params.append(nombre)
        if precio is not None:
            updates.append("precio = %s")
            params.append(precio)
        if duracion_minutos is not None:
            updates.append("duracion_minutos = %s")
            params.append(duracion_minutos)

        params.append(servicio_id)
        query = f"UPDATE servicios SET {', '.join(updates)} WHERE id = %s"
        cursor = conn.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Servicio no encontrado'}), 404

        return jsonify({'message': 'Servicio actualizado'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 9. ELIMINAR SERVICIO
@negocios_bp.route('/<int:negocio_id>/servicios/<int:servicio_id>', methods=['DELETE'])
def eliminar_servicio(negocio_id, servicio_id):
    propietario_id = request.args.get('propietario_id')

    if not propietario_id:
        return jsonify({'error': 'Falta propietario_id'}), 400

    try:
        propietario_id = int(propietario_id)
    except ValueError:
        return jsonify({'error': 'propietario_id inválido'}), 400

    conn = get_db_connection()
    try:
        # Verificar permisos
        negocio = conn.execute("SELECT propietario_id FROM negocios WHERE id = %s", (negocio_id,)).fetchone()
        if not negocio or negocio['propietario_id'] != propietario_id:
            return jsonify({'error': 'No tienes permisos para este negocio'}), 403

        # Verificar que el servicio pertenece al negocio
        servicio = conn.execute("SELECT id FROM servicios WHERE id = %s AND negocio_id = %s", (servicio_id, negocio_id)).fetchone()
        if not servicio:
            return jsonify({'error': 'Servicio no encontrado'}), 404

        cursor = conn.execute("DELETE FROM servicios WHERE id = %s", (servicio_id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Servicio no encontrado'}), 404

        return jsonify({'message': 'Servicio eliminado'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 10. ELIMINAR NEGOCIO
@negocios_bp.route('/<int:negocio_id>', methods=['DELETE'])
def eliminar_negocio(negocio_id):
    propietario_id = request.args.get('propietario_id')

    if not propietario_id:
        return jsonify({'error': 'Falta propietario_id'}), 400

    try:
        propietario_id = int(propietario_id)
    except ValueError:
        return jsonify({'error': 'propietario_id inválido'}), 400

    conn = get_db_connection()
    try:
        # Verificar si el negocio existe
        negocio = conn.execute("SELECT propietario_id FROM negocios WHERE id = %s", (negocio_id,)).fetchone()
        if not negocio:
            return jsonify({'error': 'Negocio no encontrado'}), 404

        # Verificar permisos
        if negocio['propietario_id'] != propietario_id:
            return jsonify({'error': 'No tienes permisos para este negocio'}), 403

        # Eliminar el negocio (las tablas relacionadas se eliminarán automáticamente por CASCADE)
        cursor = conn.execute("DELETE FROM negocios WHERE id = %s", (negocio_id,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Negocio no encontrado'}), 404

        return jsonify({'message': 'Negocio eliminado'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()