# Geolocalizacion de Negocios - SectorMindAI v1.0.0

## Objetivo
Permitir que el cliente encuentre negocios cercanos con distancia estimada y ordenada por proximidad.

## Flujo funcional

1. El usuario comparte su ubicación desde el frontend a través de la Web Geolocation API (método primario).
2. Opcionalmente, el usuario puede ajustar manualmente su ubicación en un mapa interactivo (OpenStreetMap) para mayor precisión.
3. Se consulta al backend con las coordenadas `lat` y `lon` finales.
4. PostgreSQL calcula la distancia con la fórmula de Haversine.
5. Se retornan los negocios ordenados por distancia.

## Stack tecnico

- Frontend: geolocation API del navegador
- Geocodificación y mapas: OpenStreetMap (a través de Leaflet y Nominatim para el ajuste manual)
- Backend: Flask
- DB: PostgreSQL

## Datos de negocio

Tabla `negocios` con campos geograficos:
- `latitud`
- `longitud`

Indice de ubicacion para optimizar consultas por proximidad.

## Notas operativas

- Ubicacion del usuario se usa para ranking, no como dato persistente del usuario.
- Coordenadas de negocio forman parte de los datos del negocio.
- Precision suficiente para escenarios urbanos y de reserva local.

## Estado de evolutivo

Version 1.0.0 estable.
No hay roadmap de nuevas funcionalidades geoespaciales en esta linea.
Solo mantenimiento correctivo si aparece incidencia.

## Fecha de actualizacion

2026-03-21
