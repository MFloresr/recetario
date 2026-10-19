# Arquitectura

## Principios

- **Monorepo con dos proyectos independientes:** `backend/` y `frontend/`.
- **El frontend solo habla con Django.** TheMealDB y la IA se consumen desde el backend, que actúa como proxy y capa de lógica. Así las claves no salen del servidor y los errores externos se controlan en un solo sitio.
- **Sin lógica de negocio en las vistas.** Las vistas de DRF reciben la petición, validan con serializadores y delegan en `services/`.

## Capas del backend

```
Petición HTTP
   │
   ▼
views (DRF)          valida entrada/salida con serializers, devuelve la respuesta HTTP
   │
   ▼
services/            lógica de negocio y clientes de servicios externos
   │   ├── themealdb.py   (fase 4)
   │   └── ai.py          (fase 6, interfaz común para varios proveedores)
   ▼
models (Django ORM)  PostgreSQL mediante DATABASE_URL
```

Los fallos de servicios externos (TheMealDB, IA) se convierten en errores controlados con el código HTTP adecuado; nunca se devuelve un traceback.

## Frontend

- Vue 3 con Composition API y `<script setup>`, TypeScript estricto.
- Vuetify 4 (Material Design 3) con tema claro y oscuro; el tema elegido se guarda en el navegador.
- Pinia para el estado global, Vue Router para la navegación y Axios para hablar con la API.

## Fases

1. Estructura y configuración (hecha).
2. Autenticación (registro, login, refresco de token, usuario actual).
3. Modelos y despensa, lista de la compra.
4. Integración con TheMealDB.
5. Sugerencias por ingredientes, detalle de receta y favoritos.
6. IA.
7. Frontend completo con Material Design 3.
