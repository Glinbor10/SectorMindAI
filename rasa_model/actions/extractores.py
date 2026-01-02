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

        print(f"[DEBUG extraer_solo_fecha] Entrada: '{texto_fecha}', Hoy: {hoy}")

        fecha_objetivo = None
        
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
                mes = int(dia_match.group(2)) if dia_match.group(2) else hoy.month
                try:
                    fecha_objetivo = datetime(hoy.year, mes, dia).date()
                    if fecha_objetivo < hoy:
                        fecha_objetivo = datetime(hoy.year + 1, mes, dia).date()
                    print(f"[DEBUG extraer_solo_fecha] Número día encontrado: {dia}/{mes} → {fecha_objetivo}")
                except ValueError:
                    fecha_objetivo = None
            
            # SEGUNDO: Si no hay número, buscar día de la semana
            if not fecha_objetivo:
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
                        print(f"[DEBUG extraer_solo_fecha] Día semana: {dia_nombre} → {fecha_objetivo}")
                        break

        if not fecha_objetivo:
            fechas_disponibles = sorted(horarios_disponibles.keys())
            if fechas_disponibles:
                fecha_objetivo = datetime.strptime(fechas_disponibles[0], '%Y-%m-%d').date()
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
            hora_match = re.search(r'\b([0-9]|1[0-9]|2[0-3])(?:[:|\s](\d{2}))?\b', texto_lower)
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
