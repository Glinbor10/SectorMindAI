"""
Módulo de extracción de fechas y horas
"""
import re
from datetime import datetime, timedelta
from typing import Optional


class ExtractorFechaHora:
    """Clase para extraer fechas y horas del texto del usuario"""
    
    @staticmethod
    def extraer_solo_fecha(texto_fecha: str, horarios_disponibles: dict) -> Optional[str]:
        """
        Extrae SOLO la fecha, ignora horas - PRIORIZA número sobre día de semana
        
        Args:
            texto_fecha: Texto del usuario
            horarios_disponibles: Dict con {fecha: [slots]}
        
        Returns:
            String con fecha en formato YYYY-MM-DD o None
        """
        if not texto_fecha or not horarios_disponibles:
            return None

        texto_lower = texto_fecha.lower().strip()
        hoy = datetime.now().date()

        # Precalcular fechas disponibles para resolver expresiones ambiguas
        fechas_disponibles = []
        for fecha_str in sorted(horarios_disponibles.keys()):
            try:
                fechas_disponibles.append(datetime.strptime(fecha_str, '%Y-%m-%d').date())
            except ValueError:
                # Ignorar entradas mal formateadas para no romper el flujo
                continue

        print(f"[DEBUG extraer_solo_fecha] Entrada: '{texto_fecha}', Hoy: {hoy}")

        fecha_objetivo = None
        dia_numero_mencionado = None

        dias_semana = {
            'lunes': 0, 'martes': 1, 'miercoles': 2, 'miércoles': 2,
            'jueves': 3, 'viernes': 4, 'sabado': 5, 'sábado': 5, 'domingo': 6
        }
        dia_semana_mencionado = None
        for dia_nombre, dia_num in dias_semana.items():
            if dia_nombre in texto_lower:
                dia_semana_mencionado = dia_num
                break
        
        # Casos simples
        if "hoy" in texto_lower:
            fecha_objetivo = hoy
        elif "mañana" in texto_lower or "manana" in texto_lower:
            fecha_objetivo = hoy + timedelta(days=1)
        elif "pasado" in texto_lower:
            fecha_objetivo = hoy + timedelta(days=2)
        else:
            # PRIMERO: Buscar si hay un número de día específico (1-31)
            dia_match = re.search(r'\b([1-9]|[12]\d|3[01])(?:/(\d{1,2}))?\b', texto_lower)
            
            if dia_match:
                dia = int(dia_match.group(1))
                dia_numero_mencionado = dia
                mes = int(dia_match.group(2)) if dia_match.group(2) else hoy.month

                # Si se menciona solo un número de día (ej: "30" o "viernes 30"),
                # intentar primero casar con días disponibles reales para evitar
                # devolver fechas no disponibles del mes actual.
                if fechas_disponibles and dia_match.group(2) is None:
                    candidatas_por_dia = [f for f in fechas_disponibles if f.day == dia]
                    if candidatas_por_dia:
                        futuras = [f for f in candidatas_por_dia if f >= hoy]
                        fecha_objetivo = min(futuras) if futuras else min(candidatas_por_dia)
                        print(f"[DEBUG extraer_solo_fecha] Número día resuelto por disponibilidad: {fecha_objetivo}")

                # Si el usuario combina día de semana + número (ej: "viernes 30"),
                # priorizar una fecha que exista realmente en horarios_disponibles.
                if dia_semana_mencionado is not None and fechas_disponibles:
                    candidatas = [
                        f for f in fechas_disponibles
                        if f.day == dia and f.weekday() == dia_semana_mencionado
                    ]
                    if candidatas:
                        # Tomar la más próxima en el futuro; si no hay futuras, la primera disponible.
                        futuras = [f for f in candidatas if f >= hoy]
                        fecha_objetivo = min(futuras) if futuras else min(candidatas)
                        print(f"[DEBUG extraer_solo_fecha] Día+semana resuelto por disponibilidad: {fecha_objetivo}")

                try:
                    if fecha_objetivo is None:
                        fecha_objetivo = datetime(hoy.year, mes, dia).date()
                        print(f"[DEBUG extraer_solo_fecha] Número día encontrado: {dia}/{mes} → {fecha_objetivo}")
                except ValueError:
                    # Try previous month
                    mes_prev = hoy.month - 1 if hoy.month > 1 else 12
                    year = hoy.year if hoy.month > 1 else hoy.year - 1
                    try:
                        if fecha_objetivo is None:
                            fecha_objetivo = datetime(year, mes_prev, dia).date()
                            print(f"[DEBUG extraer_solo_fecha] Número día encontrado (mes prev): {dia}/{mes_prev} → {fecha_objetivo}")
                    except ValueError:
                        fecha_objetivo = None
            
            # Ajustar a futuro si la fecha es pasada
            if fecha_objetivo and fecha_objetivo < hoy:
                try:
                    fecha_objetivo = datetime(hoy.year + 1, fecha_objetivo.month, fecha_objetivo.day).date()
                    print(f"[DEBUG extraer_solo_fecha] Fecha ajustada a futuro: {fecha_objetivo}")
                except ValueError:
                    fecha_objetivo = None
            
            # SEGUNDO: Si no hay número, buscar día de la semana
            if not fecha_objetivo and dia_semana_mencionado is not None:
                # Si también hay número de día, intentar casar con fechas disponibles primero.
                if dia_numero_mencionado is not None and fechas_disponibles:
                    candidatas = [
                        f for f in fechas_disponibles
                        if f.day == dia_numero_mencionado and f.weekday() == dia_semana_mencionado
                    ]
                    if candidatas:
                        futuras = [f for f in candidatas if f >= hoy]
                        fecha_objetivo = min(futuras) if futuras else min(candidatas)
                        print(f"[DEBUG extraer_solo_fecha] Día+semana por fallback disponibilidad: {fecha_objetivo}")

                # Si solo hay día de semana, mantener comportamiento original (próxima ocurrencia)
                if not fecha_objetivo:
                    dias_hasta = (dia_semana_mencionado - hoy.weekday()) % 7
                    if dias_hasta == 0:
                        dias_hasta = 7
                    fecha_objetivo = hoy + timedelta(days=dias_hasta)
                    print(f"[DEBUG extraer_solo_fecha] Día semana: {dia_semana_mencionado} → {fecha_objetivo}")

        if not fecha_objetivo:
            if fechas_disponibles:
                fecha_objetivo = fechas_disponibles[0]
                print(f"[DEBUG extraer_solo_fecha] Primera disponible: {fecha_objetivo}")

        if not fecha_objetivo:
            return None

        fecha_str = fecha_objetivo.strftime('%Y-%m-%d')
        
        # NO saltar automáticamente a otra fecha - dejar que el usuario sepa que no hay horarios
        if fecha_str not in horarios_disponibles:
            print(f"[DEBUG extraer_solo_fecha] Fecha {fecha_str} no disponible")
            return None

        print(f"[DEBUG extraer_solo_fecha] Resultado: {fecha_str}")
        return fecha_str

    @staticmethod
    def extraer_solo_hora(texto_hora: str, horarios_disponibles: list) -> Optional[str]:
        """
        Extrae SOLO la hora de los horarios disponibles
        
        Args:
            texto_hora: Texto del usuario
            horarios_disponibles: Lista de slots disponibles
        
        Returns:
            String con slot completo "YYYY-MM-DD HH:MM:SS" o None
        """
        if not texto_hora or not horarios_disponibles:
            return None

        texto_lower = texto_hora.lower().strip()
        print(f"[DEBUG extraer_solo_hora] Entrada: '{texto_hora}'")
        print(f"[DEBUG extraer_solo_hora] Horarios disponibles: {horarios_disponibles}")

        # Palabras textuales para horas
        horas_texto = {
            'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
            'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10,
            'once': 11, 'doce': 12, 'trece': 13, 'catorce': 14, 'quince': 15,
            'dieciséis': 16, 'diecisiete': 17, 'dieciocho': 18, 'diecinueve': 19,
            'veinte': 20, 'veintiuno': 21, 'veintidós': 22, 'veintitrés': 23
        }
        
        minutos_texto = {
            'media': 30, 'cuarto': 15, 'y media': 30, 'y cuarto': 15
        }

        hora = None
        minuto = 0

        # Buscar hora en texto
        for palabra, valor in horas_texto.items():
            if palabra in texto_lower:
                hora = valor
                print(f"[DEBUG extraer_solo_hora] Hora texto: {palabra} = {hora}")
                break
        
        # Buscar minutos en texto
        for frase, valor in minutos_texto.items():
            if frase in texto_lower:
                minuto = valor
                print(f"[DEBUG extraer_solo_hora] Minuto texto: {frase} = {minuto}")
                break

        # Si no encontró en texto, buscar números
        if hora is None:
            # Buscar hora:minuto o hora minuto (con : o espacio como separador)
            # Acepta formatos con cero inicial como 09:45.
            hora_match = re.search(r'\b((?:[01]?\d|2[0-3]))(?:[:\s](\d{2}))?\b', texto_lower)
            if hora_match:
                hora = int(hora_match.group(1))
                if hora_match.group(2):
                    minuto = int(hora_match.group(2))
                print(f"[DEBUG extraer_solo_hora] Hora número: {hora}:{minuto:02d}")

        if hora is not None:
            # Detectar modificadores de horario (tarde/noche/pm)
            es_tarde_noche = False
            if any(palabra in texto_lower for palabra in ['tarde', 'noche', 'pm', 'p.m.', 'p.m']):
                es_tarde_noche = True
                # Si la hora es menor a 12 y se especifica tarde/noche/pm, añadir 12 horas
                if hora < 12:
                    hora += 12
                    print(f"[DEBUG extraer_solo_hora] Ajustada a formato 24h: {hora}:00 (tarde/noche/pm)")
            
            # Detectar mañana/am para asegurar que no se ajuste
            if any(palabra in texto_lower for palabra in ['mañana', 'madrugada', 'am', 'a.m.', 'a.m']):
                # Asegurar que está en formato mañana (no hacer nada si ya es < 12)
                if hora >= 12 and hora < 24:
                    hora -= 12
                    print(f"[DEBUG extraer_solo_hora] Ajustada a formato mañana: {hora}:00 (am)")
            
            hora_buscada = f"{hora:02d}:{minuto:02d}"
            
            # Buscar coincidencia exacta
            for slot in horarios_disponibles:
                slot_hora = slot.split()[1][:5]
                if hora_buscada == slot_hora:
                    print(f"[DEBUG extraer_solo_hora] Match exacto: {slot}")
                    return slot
            
            # Si no hay exacta, buscar la más cercana DESPUÉS de la hora buscada
            hora_usuario_minutos = hora * 60 + minuto
            mejor_slot = None
            menor_diferencia = float('inf')
            
            for slot in horarios_disponibles:
                slot_hora_str = slot.split()[1][:5]
                slot_h, slot_m = map(int, slot_hora_str.split(':'))
                slot_minutos = slot_h * 60 + slot_m
                
                # Solo considerar slots >= hora buscada
                if slot_minutos >= hora_usuario_minutos:
                    diferencia = slot_minutos - hora_usuario_minutos
                    if diferencia < menor_diferencia:
                        menor_diferencia = diferencia
                        mejor_slot = slot
            
            if mejor_slot:
                print(f"[DEBUG extraer_solo_hora] Más cercano después de {hora_buscada}: {mejor_slot}")
                return mejor_slot
        
        # NO hacer fallback automático - si no se entiende la hora, retornar None
        print(f"[DEBUG extraer_solo_hora] No se pudo extraer hora válida")
        return None
