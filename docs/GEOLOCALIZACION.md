# 📍 Geolocalización de Negocios

## 🎨 Flujo de Usuario

```
┌─────────────────────────────────────────────────────────────────┐
│  PROPIETARIO CREA/EDITA NEGOCIO                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Formulario de Negocio               │
        │   ┌─────────────────────────────┐     │
        │   │ Dirección: [____________]  📍│     │
        │   └─────────────────────────────┘     │
        │                                       │
        │   3 Opciones:                         │
        │   1️⃣ Escribir manualmente             │
        │   2️⃣ Click en 📍 (GPS)                 │
        │   3️⃣ Botón "Actualizar coords"        │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Geocodificación (Nominatim)         │
        │   Dirección → Coordenadas             │
        │   "Calle X, Madrid" → 40.41, -3.70    │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Base de Datos PostgreSQL            │
        │   negocios {                          │
        │     direccion: "Calle X, Madrid"      │
        │     latitud: 40.41685                 │
        │     longitud: -3.70379                │
        │   }                                   │
        └───────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  CLIENTE BUSCA NEGOCIOS                                         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Obtener ubicación del usuario       │
        │   navigator.geolocation               │
        │   → lat: 40.40, lon: -3.68            │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Query PostgreSQL con Haversine      │
        │   SELECT *, distancia_km              │
        │   ORDER BY distancia_km               │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Resultados Ordenados por Distancia  │
        │   • Negocio A - 2.3 km 📍             │
        │   • Negocio B - 5.7 km 📍             │
        │   • Negocio C - 12.1 km 📍            │
        └───────────────────────────────────────┘
```

## Descripción

Los negocios ahora incluyen coordenadas geográficas (latitud/longitud) para permitir:
- Ordenamiento por distancia al usuario
- Búsqueda por proximidad
- Visualización en mapas

## 🎯 Experiencia de Usuario

### Al Crear un Negocio

Los propietarios tienen **3 formas** de ingresar la ubicación:

#### 1. **Input Manual + Geocodificación Automática**
- El propietario escribe la dirección (ej: "Calle Gran Vía 123, Madrid")
- Al enviar el formulario, se geocodifica automáticamente usando Nominatim
- Se muestra un mensaje indicando si se obtuvieron las coordenadas

#### 2. **Botón "Usar mi ubicación actual"** 📍
- Icono de pin en el campo de dirección
- 1 clic obtiene la ubicación GPS del dispositivo
- Reverse geocoding convierte coordenadas → dirección legible
- Ideal para negocios locales que el propietario gestiona desde el mismo lugar

#### 3. **Actualización Manual** (solo edición)
- Botón "Actualizar coordenadas desde dirección"
- Permite re-geocodificar después de editar la dirección
- Útil si la dirección cambió pero no se recargó el formulario

### Feedback Visual

- ✅ **Éxito**: Icono verde + coordenadas mostradas (ej: "40.41685, -3.70379")
- ⚠️ **Error**: Alerta naranja indicando que el negocio se creará sin coordenadas
- 📍 **Cargando**: Modal de "Obteniendo ubicación..." al usar GPS

## 🔧 Tecnología

### Servicio de Geocodificación: **Nominatim (OpenStreetMap)**

#### ✅ Ventajas
- **100% gratuito** sin límites estrictos
- No requiere API key
- Datos de OpenStreetMap (comunidad global)
- Soporte para español (`accept-language=es`)
- Reverse geocoding incluido

#### ⚠️ Límites
- Política de uso justo: ~1 petición/segundo
- Debe incluir User-Agent identificable
- Para uso masivo, considerar servidor Nominatim propio

#### 🔄 Alternativa: Google Maps Geocoding API
Si en el futuro necesitas más precisión:
```javascript
const geocodeUrl = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(direccion)}&key=TU_API_KEY`;
```
⚠️ Requiere cuenta de Google Cloud y facturación (200 USD gratis/mes)

## 📊 Modelo de Datos

### Tabla `negocios`

```sql
CREATE TABLE negocios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    tipo_negocio VARCHAR(50) DEFAULT 'general',
    direccion TEXT,
    descripcion TEXT,
    propietario_id INTEGER NOT NULL REFERENCES usuarios(id),
    foto_base64 TEXT,
    latitud DECIMAL(10, 8),  -- Rango: -90 a +90
    longitud DECIMAL(11, 8), -- Rango: -180 a +180
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_negocios_ubicacion ON negocios(latitud, longitud);
```

### Precisión
- **DECIMAL(10, 8)**: ~1.1 mm de precisión (suficiente para direcciones)
- Ej: Madrid = `40.41685, -3.70379`

## 🧮 Cálculo de Distancias

### Fórmula Haversine (implementada en PostgreSQL)

```sql
SELECT 
    n.*,
    6371 * acos(
        cos(radians(user_lat)) * cos(radians(n.latitud)) * 
        cos(radians(n.longitud) - radians(user_lon)) + 
        sin(radians(user_lat)) * sin(radians(n.latitud))
    ) as distancia_km
FROM negocios n
WHERE n.latitud IS NOT NULL AND n.longitud IS NOT NULL
ORDER BY distancia_km;
```

- **6371** = Radio de la Tierra en kilómetros
- Precisión: ~10 metros para distancias < 1000 km
- Performance: Índice en `(latitud, longitud)` acelera las consultas

### Uso desde el Frontend

```javascript
// Obtener ubicación del usuario
navigator.geolocation.getCurrentPosition((pos) => {
    const userLat = pos.coords.latitude;
    const userLon = pos.coords.longitude;
    
    // Llamar al endpoint con parámetros de ubicación
    fetch(`${API_URL}/negocios/?lat=${userLat}&lon=${userLon}`)
        .then(res => res.json())
        .then(negocios => {
            // Los negocios vienen ordenados por distancia
            negocios.forEach(neg => {
                console.log(`${neg.nombre}: ${neg.distancia_km.toFixed(1)} km`);
            });
        });
});
```

## 🔒 Privacidad

- **Ubicación del usuario**: Solo se usa para ordenar resultados (no se almacena)
- **Ubicación del negocio**: Pública (necesaria para que clientes encuentren el negocio)
- **Permiso del navegador**: Requerido solo al usar "Usar mi ubicación"

## 🚀 Mejoras Futuras

### Corto plazo
- [ ] Filtro por radio (ej: "Mostrar negocios a menos de 5 km")
- [ ] Búsqueda por ciudad/código postal
- [ ] Cache de geocodificaciones para direcciones repetidas

### Medio plazo
- [ ] Mapa interactivo con marcadores (Leaflet.js)
- [ ] Selector visual de ubicación (arrastrar pin en mapa)
- [ ] Integración con Google Places Autocomplete

### Largo plazo
- [ ] Rutas/indicaciones desde ubicación del usuario
- [ ] Búsqueda por área geográfica (polígonos)
- [ ] Heat map de densidad de negocios

## 📝 Notas de Implementación

### Migración de Datos Existentes
```sql
-- Los negocios existentes tendrán latitud/longitud NULL
-- Se pueden geocodificar en batch:
UPDATE negocios 
SET latitud = 40.4168, longitud = -3.7038 
WHERE direccion LIKE '%Madrid%' AND latitud IS NULL;
```

### Testing
```python
def test_crear_negocio_con_coordenadas():
    response = client.post('/negocios/', json={
        'nombre': 'Test Business',
        'direccion': 'Calle Test 123',
        'latitud': 40.4168,
        'longitud': -3.7038,
        'propietario_id': 1
    })
    assert response.status_code == 201
    assert 'latitud' in response.json()
```

## 🆘 Troubleshooting

### "No se pudo geocodificar"
- Verificar que la dirección sea válida y completa
- Incluir ciudad/país para mejor precisión
- Revisar consola del navegador para errores de CORS

### Distancias incorrectas
- Verificar que latitud/longitud no estén invertidas
- Confirmar que las coordenadas usan formato decimal (no grados/minutos/segundos)
- PostgreSQL debe usar `radians()` correctamente

### Rate limiting de Nominatim
- Agregar delay entre peticiones (1 segundo)
- Considerar servidor Nominatim propio
- Implementar cache de resultados

---

## 🎨 Interfaz Visual por Tipo de Negocio (v0.6.1)

### Estilos Personalizados

Cada tipo de negocio tiene una identidad visual clara mediante backgrounds y emoji:

| Tipo | Emoji | Color Background | CSS Class | Hex Color |
|------|-------|------------------|-----------|-----------|
| **Dentista** | 🦷 | Azul claro | `bg-blue-100` | `#dbeafe` |
| **Peluquería** | ✂️ | Rosa claro | `bg-pink-100` | `#fce7f3` |
| **Fisioterapia** | 🦴 | Verde claro | `bg-green-100` | `#dcfce7` |

### Ubicaciones en la UI

1. **Grid de Negocios (Cliente)**: `renderBusinessGrid()` en `index.html`
   - Emoji a escala `text-6xl` (36px)
   - Background aplicado al div contenedor
   - Solo cuando no hay `foto_base64`

2. **Lista de Propietario**: `loadMyBusinesses()` en `index.html`
   - Emoji a escala `text-5xl` (32px)
   - Mismo comportamiento de fallback

3. **Página de Gestión**: `loadBusinessData()` en `gestion_negocio.html`
   - Emoji a escala `2rem` (32px)
   - Thumbnail (16x16) en cabecera
   - Flex display para centrado

### Implementación

La función `getBusinessStyle()` mapea tipos a estilos:

```javascript
function getBusinessStyle(tipoNegocio) {
    const styles = {
        'dentista': { bgColor: 'bg-blue-100', emoji: '🦷', color: '#dbeafe' },
        'peluqueria': { bgColor: 'bg-pink-100', emoji: '✂️', color: '#fce7f3' },
        'fisioterapia': { bgColor: 'bg-green-100', emoji: '🦴', color: '#dcfce7' }
    };
    return styles[tipoNegocio.toLowerCase()] || styles['dentista'];
}
```

**Fallback**: Si el tipo no coincide, usa "dentista" como default.

### Ventajas

✅ Diferenciación visual clara por tipo de negocio
✅ Experiencia UX consistente en todas las vistas
✅ Escalable: solo agregar nuevas entradas al objeto `styles`
✅ Prioriza fotos reales cuando están disponibles
