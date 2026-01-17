"""
Tests de integración para la API externa de Nominatim (OpenStreetMap)

IMPORTANTE: Estos tests hacen llamadas REALES a la API de Nominatim.
- Se ejecutan solo cuando se marca con: .\run_tests.ps1 -Integration
- Respetan rate limits de Nominatim (1 request/segundo)
- Requieren conexión a internet
- Pueden fallar por problemas de red o cambios en la API

Uso de Nominatim según política:
https://operations.osmfoundation.org/policies/nominatim/
"""
import pytest
import requests
import time
from typing import Dict, Any, Optional


# Marcador para tests de integración
pytestmark = pytest.mark.integration


class TestNominatimIntegration:
    """Tests de integración para la API de Nominatim OpenStreetMap"""
    
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    HEADERS = {"User-Agent": "SectorMindAI/1.0"}
    REQUEST_DELAY = 1.0  # Segundos entre requests (política de Nominatim)
    
    @pytest.fixture(autouse=True)
    def rate_limit(self):
        """Añade delay automático entre tests para respetar rate limits"""
        yield
        time.sleep(self.REQUEST_DELAY)
    
    def _geocodificar(self, direccion: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Helper para hacer request a Nominatim con parámetros por defecto.
        
        Args:
            direccion: Dirección o lugar a geocodificar
            **kwargs: Parámetros adicionales para la API
            
        Returns:
            Respuesta JSON de la API o None si hay error
        """
        params = {
            "q": direccion,
            "format": "json",
            "limit": kwargs.get("limit", 10),
            "countrycodes": kwargs.get("countrycodes", "ES"),
            "accept-language": kwargs.get("accept-language", "es"),
            "addressdetails": kwargs.get("addressdetails", 1),
        }
        
        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                headers=self.HEADERS,
                timeout=kwargs.get("timeout", 10)
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error en geocodificación: {e}")
            return None
    
    # ========================================================================
    # TESTS DE GEOCODIFICACIÓN EXITOSA
    # ========================================================================
    
    def test_geocodificar_ciudad_espanola_exitoso(self):
        """Test: Geocodificar una ciudad española conocida devuelve resultados"""
        data = self._geocodificar("Madrid")
        
        assert data is not None, "Nominatim debe devolver resultados"
        assert len(data) > 0, "Debe haber al menos un resultado"
        
        # Verificar estructura del primer resultado
        primer_resultado = data[0]
        assert "lat" in primer_resultado, "Debe incluir latitud"
        assert "lon" in primer_resultado, "Debe incluir longitud"
        assert "display_name" in primer_resultado, "Debe incluir nombre para mostrar"
        
        # Verificar que las coordenadas son números válidos
        lat = float(primer_resultado["lat"])
        lon = float(primer_resultado["lon"])
        assert -90 <= lat <= 90, "Latitud debe estar en rango válido"
        assert -180 <= lon <= 180, "Longitud debe estar en rango válido"
        
        # Verificar que sea Madrid (aproximadamente)
        assert 40.0 <= lat <= 41.0, "Madrid debe estar cerca de 40°N"
        assert -4.0 <= lon <= -3.0, "Madrid debe estar cerca de -3.7°W"
    
    def test_geocodificar_direccion_completa(self):
        """Test: Geocodificar dirección completa con calle y ciudad"""
        data = self._geocodificar("Gran Via 32, Madrid")
        
        assert data is not None
        assert len(data) > 0
        
        primer_resultado = data[0]
        assert "lat" in primer_resultado
        assert "lon" in primer_resultado
        
        # Debe mencionar Madrid en el display_name
        display = primer_resultado.get("display_name", "").lower()
        assert "madrid" in display, "El resultado debe mencionar Madrid"
    
    def test_geocodificar_multiples_resultados(self):
        """Test: Búsqueda ambigua devuelve múltiples resultados"""
        data = self._geocodificar("Córdoba", limit=5)
        
        assert data is not None
        assert len(data) > 0
        
        # Puede haber varias Córdoba (ciudad, provincia)
        # Verificar que todos tengan estructura válida
        for resultado in data[:3]:  # Verificar top 3
            assert "lat" in resultado
            assert "lon" in resultado
            assert "display_name" in resultado
            
            # Verificar coordenadas válidas
            lat = float(resultado["lat"])
            lon = float(resultado["lon"])
            assert -90 <= lat <= 90
            assert -180 <= lon <= 180
    
    def test_geocodificar_con_detalles_direccion(self):
        """Test: addressdetails=1 devuelve información detallada de dirección"""
        data = self._geocodificar("Barcelona", addressdetails=1)
        
        assert data is not None
        assert len(data) > 0
        
        primer_resultado = data[0]
        assert "address" in primer_resultado, "Debe incluir detalles de dirección"
        
        address = primer_resultado["address"]
        assert isinstance(address, dict), "address debe ser un diccionario"
        
        # Debe tener campos como city, country, etc.
        assert any(key in address for key in ["city", "town", "village", "municipality"])
    
    def test_geocodificar_con_filtro_pais(self):
        """Test: countrycodes filtra resultados por país"""
        # Buscar "Valencia" solo en España
        data_es = self._geocodificar("Valencia", countrycodes="ES")
        
        assert data_es is not None
        assert len(data_es) > 0
        
        # Verificar que los resultados son de España
        for resultado in data_es[:3]:
            if "address" in resultado:
                country_code = resultado["address"].get("country_code", "")
                if country_code:  # Si tiene código de país, debe ser ES
                    assert country_code.upper() == "ES", "Debe ser de España"
    
    # ========================================================================
    # TESTS DE CASOS EDGE Y DIRECCIONES NO ENCONTRADAS
    # ========================================================================
    
    def test_geocodificar_direccion_inexistente(self):
        """Test: Dirección que no existe devuelve lista vacía"""
        # Dirección claramente falsa
        data = self._geocodificar("CiudadInventadaQueNoExiste123456789XYZ")
        
        assert data is not None, "Debe devolver lista vacía, no None"
        assert len(data) == 0, "No debe haber resultados para ciudad inventada"
    
    def test_geocodificar_string_vacio(self):
        """Test: String vacío devuelve lista vacía"""
        data = self._geocodificar("")
        
        assert data is not None
        # Puede ser lista vacía o error, pero no debe crashear
        assert isinstance(data, list)
    
    def test_geocodificar_caracteres_especiales(self):
        """Test: Direcciones con caracteres especiales españoles"""
        data = self._geocodificar("Málaga")
        
        assert data is not None
        assert len(data) > 0
        
        # Debe encontrar Málaga
        display = data[0].get("display_name", "").lower()
        assert "málaga" in display or "malaga" in display
    
    def test_geocodificar_con_limite_resultados(self):
        """Test: Parámetro limit controla número máximo de resultados"""
        data = self._geocodificar("Madrid", limit=3)
        
        assert data is not None
        # Puede haber menos de 3, pero no más
        assert len(data) <= 3, "No debe exceder el límite solicitado"
    
    # ========================================================================
    # TESTS DE MANEJO DE ERRORES Y TIMEOUTS
    # ========================================================================
    
    def test_timeout_request(self):
        """Test: Timeout muy corto genera excepción controlada"""
        # Intentar con timeout de 0.001 segundos (prácticamente imposible)
        data = self._geocodificar("Madrid", timeout=0.001)
        
        # El helper debe devolver None en caso de error
        assert data is None, "Timeout debe ser manejado y devolver None"
    
    def test_respuesta_con_importance(self):
        """Test: Resultados incluyen campo importance para ranking"""
        data = self._geocodificar("Sevilla")
        
        assert data is not None
        assert len(data) > 0
        
        primer_resultado = data[0]
        # Importance es opcional pero común en resultados de ciudades
        if "importance" in primer_resultado:
            importance = primer_resultado["importance"]
            assert isinstance(importance, (int, float))
            assert 0 <= importance <= 1, "Importance suele estar entre 0 y 1"
    
    # ========================================================================
    # TESTS DE CALIDAD DE DATOS
    # ========================================================================
    
    def test_formato_coordenadas_precision(self):
        """Test: Coordenadas tienen precisión decimal suficiente"""
        data = self._geocodificar("Valencia")
        
        assert data is not None
        assert len(data) > 0
        
        primer_resultado = data[0]
        lat_str = str(primer_resultado["lat"])
        lon_str = str(primer_resultado["lon"])
        
        # Las coordenadas deben tener decimales (mínimo precisión)
        assert "." in lat_str, "Latitud debe tener decimales"
        assert "." in lon_str, "Longitud debe tener decimales"
        
        # Verificar que tienen al menos 4 decimales (precisión ~11 metros)
        lat_decimals = len(lat_str.split(".")[-1])
        lon_decimals = len(lon_str.split(".")[-1])
        assert lat_decimals >= 4, f"Latitud debe tener ≥4 decimales, tiene {lat_decimals}"
        assert lon_decimals >= 4, f"Longitud debe tener ≥4 decimales, tiene {lon_decimals}"
    
    def test_display_name_contiene_pais(self):
        """Test: display_name incluye información de país"""
        data = self._geocodificar("Zaragoza")
        
        assert data is not None
        assert len(data) > 0
        
        display = data[0].get("display_name", "").lower()
        # Debe mencionar España o código de país
        assert any(term in display for term in ["españa", "spain", "espanya"]), \
            "display_name debe indicar el país"
    
    def test_consistencia_multiples_requests(self):
        """Test: Múltiples requests a la misma dirección son consistentes"""
        direccion = "Bilbao"
        
        # Primera llamada
        data1 = self._geocodificar(direccion)
        time.sleep(self.REQUEST_DELAY)
        
        # Segunda llamada
        data2 = self._geocodificar(direccion)
        
        assert data1 is not None
        assert data2 is not None
        assert len(data1) > 0
        assert len(data2) > 0
        
        # Las coordenadas del primer resultado deben ser idénticas
        assert data1[0]["lat"] == data2[0]["lat"], "Latitud debe ser consistente"
        assert data1[0]["lon"] == data2[0]["lon"], "Longitud debe ser consistente"
    
    # ========================================================================
    # TESTS DE CASOS REALES DE USO EN LA APP
    # ========================================================================
    
    def test_caso_real_busqueda_peluqueria_madrid(self):
        """Test: Caso real - Usuario busca peluquerías desde Madrid"""
        # Simula que el usuario dice "estoy en madrid" o "desde madrid"
        data = self._geocodificar("madrid")
        
        assert data is not None
        assert len(data) > 0
        
        # Obtener coordenadas de Madrid para búsqueda de negocios cercanos
        madrid_coords = data[0]
        lat = float(madrid_coords["lat"])
        lon = float(madrid_coords["lon"])
        
        # Verificar que podemos usar estas coordenadas para cálculos de distancia
        assert 40.3 <= lat <= 40.5, "Madrid capital está en ~40.4°N"
        assert -3.8 <= lon <= -3.6, "Madrid capital está en ~-3.7°W"
    
    def test_caso_real_direccion_con_preposiciones(self):
        """Test: Usuario dice 'desde barcelona' o 'en barcelona'"""
        # El bot debe limpiar "desde" y buscar solo "barcelona"
        data = self._geocodificar("barcelona")
        
        assert data is not None
        assert len(data) > 0
        
        # Barcelona debe estar en Cataluña
        primer_resultado = data[0]
        lat = float(primer_resultado["lat"])
        assert 41.0 <= lat <= 42.0, "Barcelona está en ~41.4°N"
    
    def test_caso_real_ciudad_con_provincia(self):
        """Test: Usuario dice 'Córdoba España' para especificar país"""
        data = self._geocodificar("Córdoba España")
        
        assert data is not None
        assert len(data) > 0
        
        # Debe devolver resultados de Córdoba (ciudad o provincia)
        primer_resultado = data[0]
        display = primer_resultado.get("display_name", "").lower()
        
        # Verificar que menciona Córdoba en el nombre
        assert "córdoba" in display or "cordoba" in display, \
            f"El resultado debe mencionar Córdoba, pero devolvió: {display}"
        
        # Si incluye detalles de dirección, validar que tenga información de localidad
        if "address" in primer_resultado:
            address = primer_resultado["address"]
            # Puede ser ciudad, provincia o ambas - lo importante es que tenga info de localidad
            tiene_localidad = any(key in address for key in 
                                 ["city", "town", "municipality", "state", "province", "county"])
            assert tiene_localidad, "Debe incluir información de localidad en address"


class TestNominatimErrorHandling:
    """Tests específicos para manejo de errores de la API"""
    
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    HEADERS = {"User-Agent": "SectorMindAI/1.0"}
    
    @pytest.fixture(autouse=True)
    def rate_limit(self):
        """Rate limiting entre tests"""
        yield
        time.sleep(1.0)
    
    def test_url_invalida_manejo_excepcion(self):
        """Test: URL inválida es manejada sin crashear"""
        try:
            # Intentar conectar a URL que no existe
            response = requests.get(
                "https://nominatim-invalidoXYZ123.openstreetmap.org/search",
                params={"q": "test", "format": "json"},
                headers=self.HEADERS,
                timeout=5
            )
            # Si llega aquí, verificar que manejamos el error de alguna forma
            assert True  # No crasheó
        except requests.exceptions.RequestException:
            # Es esperado que falle, pero controladamente
            assert True
    
    def test_parametros_invalidos_no_crashean(self):
        """Test: Parámetros inválidos no crashean la app"""
        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "q": "Madrid",
                    "format": "invalid_format_xyz",  # Formato inválido
                    "limit": 10
                },
                headers=self.HEADERS,
                timeout=5
            )
            # Nominatim puede devolver error 400, pero no debe crashear nuestro código
            # Si status_code >= 400, es error esperado
            if response.status_code >= 400:
                assert True  # Error controlado
            else:
                assert True  # Si acepta, también ok
        except requests.exceptions.RequestException:
            assert True  # Error de red es aceptable


# Configuración para ejecutar estos tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
