"""
Tests unitarios para las acciones de Rasa
"""
import pytest
from datetime import datetime, timedelta
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk import Tracker
from rasa_sdk.events import SlotSet

from rasa_model.actions.extractores import ExtractorFechaHora


class TestExtractorFechas:
    """Tests para extractor de fechas"""
    
    def test_extraer_fecha_mañana(self):
        """Test: Debe extraer 'mañana' como el día siguiente"""
        horarios = {
            (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'): ['2026-01-03 10:00:00']
        }
        resultado = ExtractorFechaHora.extraer_solo_fecha("mañana", horarios)
        esperado = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        assert resultado == esperado
    
    def test_extraer_fecha_lunes(self):
        """Test: Debe extraer día de la semana (lunes)"""
        hoy = datetime.now()
        dias_hasta_lunes = (0 - hoy.weekday()) % 7
        if dias_hasta_lunes == 0:
            dias_hasta_lunes = 7
        
        fecha_lunes = hoy + timedelta(days=dias_hasta_lunes)
        horarios = {fecha_lunes.strftime('%Y-%m-%d'): ['2026-01-05 10:00:00']}
        
        resultado = ExtractorFechaHora.extraer_solo_fecha("el lunes", horarios)
        esperado = fecha_lunes.strftime('%Y-%m-%d')
        assert resultado == esperado
    
    def test_extraer_fecha_numero(self):
        """Test: Debe extraer número de día específico"""
        horarios = {'2027-01-30': ['2027-01-30 10:00:00']}
        resultado = ExtractorFechaHora.extraer_solo_fecha("viernes 30", horarios)
        assert resultado == '2027-01-30'
    
    def test_extraer_fecha_no_disponible(self):
        """Test: Debe retornar None si la fecha no está disponible"""
        horarios = {'2026-01-05': ['2026-01-05 10:00:00']}
        resultado = ExtractorFechaHora.extraer_solo_fecha("mañana", horarios)
        assert resultado is None


class TestExtractorHoras:
    """Tests para extractor de horas"""
    
    def test_extraer_hora_exacta(self):
        """Test: Debe encontrar hora exacta disponible"""
        horarios = ['2026-01-05 10:00:00', '2026-01-05 11:00:00', '2026-01-05 12:00:00']
        resultado = ExtractorFechaHora.extraer_solo_hora("10:00", horarios)
        assert resultado == '2026-01-05 10:00:00'
    
    def test_extraer_hora_con_espacio(self):
        """Test: Debe aceptar hora con espacio (10 45)"""
        horarios = ['2026-01-05 10:30:00', '2026-01-05 10:45:00', '2026-01-05 11:00:00']
        resultado = ExtractorFechaHora.extraer_solo_hora("10 45", horarios)
        assert resultado == '2026-01-05 10:45:00'
    
    def test_extraer_hora_mas_cercana(self):
        """Test: Debe buscar la hora más cercana después de la solicitada"""
        horarios = ['2026-01-05 10:30:00', '2026-01-05 11:00:00', '2026-01-05 12:00:00']
        resultado = ExtractorFechaHora.extraer_solo_hora("10:40", horarios)
        assert resultado == '2026-01-05 11:00:00'
    
    def test_extraer_hora_invalida(self):
        """Test: Debe rechazar hora inválida (24)"""
        horarios = ['2026-01-05 10:00:00', '2026-01-05 11:00:00']
        resultado = ExtractorFechaHora.extraer_solo_hora("a las 24", horarios)
        assert resultado is None
    
    def test_extraer_hora_texto(self):
        """Test: Debe reconocer hora en texto (diez)"""
        horarios = ['2026-01-05 10:00:00', '2026-01-05 11:00:00']
        resultado = ExtractorFechaHora.extraer_solo_hora("diez", horarios)
        assert resultado == '2026-01-05 10:00:00'
    
    def test_extraer_hora_media(self):
        """Test: Debe reconocer 'y media' (10:30)"""
        horarios = ['2026-01-05 10:30:00', '2026-01-05 11:00:00']
        resultado = ExtractorFechaHora.extraer_solo_hora("diez y media", horarios)
        assert resultado == '2026-01-05 10:30:00'


class TestFuzzyMatching:
    """Tests para fuzzy matching de servicios (serán más complejos)"""
    
    def test_fuzzy_tinti_vs_tinte(self):
        """Test: 'tinti' debe detectarse como 'Tinte'"""
        # Este test requeriría mockear las acciones de Rasa
        # Por ahora es un placeholder
        pass
    
    def test_fuzzy_corti_di_pili_vs_corte_de_pelo(self):
        """Test: 'corti di pili' debe detectarse como 'Corte de Pelo'"""
        # Este test requeriría mockear las acciones de Rasa
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
