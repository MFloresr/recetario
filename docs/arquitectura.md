# Arquitectura

## Principios

- **Monorepo con dos proyectos independientes:** `backend/` y `frontend/`.
- **El frontend solo habla con Django.** TheMealDB y la IA se consumen desde el backend, que actúa como proxy y capa de lógica. Así las claves no salen del servidor y los errores externos se controlan en un solo sitio.
- **Sin lógica de negocio en las vistas.** Las vistas de DRF reciben la petición, validan con serializadores y delegan en `services/`.
- **Errores controlados.** Un fallo de TheMealDB o de la IA se convierte en una respuesta JSON `{"detail", "code"}` con el estado HTTP adecuado (502, 503 o 504); nunca un traceback. Si la IA falla, la búsqueda normal sigue funcionando.

## Backend

```
Petición HTTP
   │
   ▼
views.py            valida entrada con serializers, devuelve la respuesta HTTP
   │
   ▼
services/
   ├── themealdb.py    cliente de TheMealDB (timeout 10 s, errores controlados)
   ├── recipes.py      caché en base de datos (detalle y favoritos) y en memoria (búsquedas)
   ├── matching.py     cálculo de coincidencia entre despensa y receta
   ├── suggestions.py  orquesta la búsqueda por ingredientes
   ├── translation.py  traducción con caché en base de datos (MyMemory o IA)
   ├── localization.py pasa resultados y recetas al español (?lang=es)
   ├── images.py       foto orientativa de un plato desde Wikipedia (solo si el artículo coincide)
   └── ai.py           AIRecipeService (interfaz) + proveedor compatible con OpenAI
   │
   ▼
models.py           Ingredient, RecipeCache, FavoriteRecipe, ShoppingListItem
```

Módulos auxiliares: `spanish.py` (categorías, países, ingredientes y medidas en español), `normalization.py` (nombres sin tildes ni mayúsculas), `catalog.py` (tabla es↔en de ingredientes, categorías) y `exceptions.py` (errores externos y manejador global de DRF).

### Cómo se calculan las sugerencias

1. Los ingredientes del usuario se normalizan y se traducen al inglés.
2. Se consulta TheMealDB (`filter.php?i=`) por cada ingrediente, en paralelo.
3. Se eliminan duplicados y se descargan completas (también en paralelo) hasta 30 recetas, priorizando las que aparecen en más ingredientes del usuario.
4. Para cada una se calcula `matched_ingredients`, `missing_ingredients` y `match_score` (porcentaje de ingredientes cubiertos).
5. Se aplican los filtros, se ordena por mayor coincidencia, menos faltantes y título, y se devuelven 20 como máximo.

Un ingrediente de la despensa cubre uno de la receta si uno contiene todas las palabras del otro («chicken» cubre «chicken breast»).

### IA

`AIRecipeService` define `suggest_recipes`, `adapt_recipe` y `generate_shopping_list`. `OpenAICompatibleService` pide JSON (`response_format`), valida la respuesta con serializadores DRF y reintenta una vez si no es válida. `get_ai_service()` elige el proveedor según `AI_PROVIDER` y falla con un error controlado si la IA no está configurada.

## Frontend

- Vue 3 con Composition API y `<script setup>`, TypeScript estricto.
- Vuetify 4 (Material Design 3) con tema claro y oscuro; el tema elegido se guarda en el navegador.
- **Pinia:** `auth`, `pantry`, `recipe` (búsqueda, favoritos e IA), `shoppingList` y `ui` (tema, avisos y contador de peticiones).
- **API:** `api/client.ts` (Axios con JWT, refresco automático con una sola renovación simultánea y conversión de errores a mensajes legibles) y `api/endpoints.ts` (funciones tipadas por recurso).
- **Navegación:** barra inferior en móvil y menú lateral en escritorio; rutas privadas protegidas por un guard.

## Recetas de la IA guardadas

Una receta de la IA que el usuario guarda se almacena en `RecipeCache` con `source="ai"` y un identificador propio, `ai-<usuario>-<huella>`: así nadie puede pisar ni ver la receta de otro (el detalle devuelve 404 a los demás). Se borra al quitarla de favoritos y al borrar la cuenta. Ya está en español, así que no pasa por el traductor, y su coincidencia con la despensa se calcula en español.

## Pruebas

- **Backend (pytest):** 189 tests con TheMealDB y la IA simulados. Cubren autenticación, aislamiento entre usuarios, normalización, cálculo de coincidencia, sugerencias, detalle, favoritos, lista de la compra, errores de TheMealDB y de la IA.
- **Frontend (Vitest):** 54 tests de componentes (formulario de login, chip de ingrediente, tarjeta de receta, añadir ingredientes, lista de la compra), conversión de errores y utilidades.
