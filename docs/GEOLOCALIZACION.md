# Geolocalizacion de Negocios - SectorMindAI v1.0.0

## Objetivo
Permitir que el cliente encuentre negocios cercanos con distancia estimada y ordenada por proximidad.

## Flujo funcional

1. El usuario comparte ubicacion desde frontend.
2. Se consulta backend con `lat` y `lon`.
3. PostgreSQL calcula distancia con formula Haversine.
4. Se retornan negocios ordenados por distancia.

## Stack tecnico

- Frontend: geolocation API del navegador
- Geocodificacion: Nominatim (OpenStreetMap)
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
