# Recetario

Recetario inteligente: añades los ingredientes que tienes en casa y la app te muestra qué recetas puedes preparar, ordenadas por el porcentaje de ingredientes que ya tienes. También puedes pedir ideas a una IA, adaptar una receta a tu despensa, guardar favoritas con notas y generar la lista de la compra con lo que falta. Pensada para usarse desde el móvil mientras se cocina.

## Qué incluye

- **Autenticación** con JWT (registro, login con correo o usuario, refresco automático del token).
- **Despensa** agrupada por categorías, con autocompletado de ingredientes frecuentes.
- **Búsqueda de recetas** en TheMealDB por ingredientes, ordenadas por coincidencia, con filtros (categoría, máximo de ingredientes que faltan, nombre). **Todo se muestra en español**: el backend traduce las recetas (ver «Traducción»).
- **Detalle de receta** con indicador de coincidencia con tu despensa y los ingredientes que te faltan.
- **Lista de la compra** agrupada por categoría; desde una receta se añaden de golpe los ingredientes que faltan.
- **Favoritos** con notas personales.
- **IA opcional** (sugerencias, adaptar receta, lista de la compra). Si no está configurada o falla, la app sigue funcionando con la búsqueda normal.
- Interfaz **Material Design 3** (Vuetify), responsive, con tema claro y oscuro.

## Estructura

```
recetario/
├── backend/     Django 6 + Django REST Framework (API)
├── frontend/    Vue 3 + TypeScript + Vite + Vuetify 4 (Material Design 3)
├── docs/        Notas de arquitectura
└── README.md
```

Backend y frontend son proyectos independientes. **El frontend solo habla con la API de Django**: nunca llama directamente a TheMealDB ni a la IA, y ninguna clave sale del backend.

## Requisitos

- Python 3.12 o superior
- Node.js 22 o superior
- PostgreSQL (opcional en desarrollo: sin `DATABASE_URL` se usa SQLite)

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # y rellena los valores (SECRET_KEY al menos)
python manage.py migrate
python manage.py runserver
```

La API queda en <http://localhost:8000/api/>. Comprobación rápida: <http://localhost:8000/api/health/> responde `{"status":"ok"}`.

Tests (134):

```bash
cd backend
pytest -v
```

Los tests usan siempre SQLite en memoria (aunque `.env` apunte a PostgreSQL) y **nunca hacen llamadas externas**: TheMealDB y la IA se simulan.

## Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

La app queda en <http://localhost:5173>. Crea una cuenta en «Crear cuenta» y empieza por añadir ingredientes.

Otros comandos: `npm run test` (Vitest, 32 tests), `npm run lint`, `npm run format`, `npm run build`.

## Variables de entorno

**`backend/.env`** (ver `backend/.env.example`):

| Variable | Descripción |
|---|---|
| `DEBUG` | `True` solo en desarrollo. |
| `SECRET_KEY` | Clave secreta de Django. Genera una propia y no la compartas. |
| `DATABASE_URL` | Cadena de conexión de PostgreSQL. Si falta, se usa SQLite local. |
| `CORS_ALLOWED_ORIGINS` | Orígenes del frontend permitidos, separados por comas. |
| `THEMEALDB_BASE_URL` | URL base de TheMealDB. |
| `AI_PROVIDER` | Proveedor de IA. Hoy: `openai` (cualquier API compatible con OpenAI). |
| `AI_API_KEY` | Clave del proveedor de IA. Solo en el backend. Vacía = la IA queda desactivada. |
| `AI_MODEL` | Modelo a usar. |
| `AI_BASE_URL` | Opcional: URL base de otra API compatible con OpenAI. Vacío = api.openai.com. |
| `TRANSLATION_PROVIDER` | `auto` (IA si hay clave, si no MyMemory), `mymemory`, `ai` o `none`. |
| `MYMEMORY_EMAIL` | Opcional: tu correo sube el cupo diario gratuito de MyMemory de 5.000 a 50.000 caracteres. |

**`frontend/.env`**:

| Variable | Descripción |
|---|---|
| `VITE_API_URL` | URL de la API de Django (por defecto `http://localhost:8000/api`). |

Los archivos `.env` no se suben a Git.

### Traducción

TheMealDB solo existe en inglés, así que el frontend pide siempre `?lang=es` y el backend devuelve las recetas en español:

- **Con tablas (sin traductor):** categorías, países, nombres de ingredientes frecuentes y medidas (`1 tblsp` → `1 cda.`). Está en `backend/recipes/spanish.py`.
- **Con traductor automático:** títulos, instrucciones e ingredientes poco comunes. Por defecto usa **MyMemory**, gratuito y sin clave (cupo diario limitado; pon tu correo en `MYMEMORY_EMAIL` para ampliarlo). Si configuras una IA (`AI_API_KEY`), se usa ella, con mejor calidad.
- **Caché:** cada texto se traduce una sola vez y se guarda en la tabla `TranslationCache`; la segunda vez que alguien ve la receta es instantáneo.
- **Si el traductor falla o se agota el cupo**, la app sigue funcionando: lo que no se pudo traducir queda en inglés y la receta lo avisa.
- La búsqueda por nombre también acepta español («pollo al curry»): se traduce al inglés antes de consultar TheMealDB.
- Sin `lang`, la API devuelve los datos originales de TheMealDB en inglés.

### Usar otro proveedor de IA

El servicio de IA habla el protocolo de OpenAI (`/chat/completions` con salida JSON), que ofrecen muchos proveedores. Para usar otro basta con cambiar tres variables, sin tocar código. Por ejemplo, con la API compatible de Gemini:

```
AI_PROVIDER=openai
AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
AI_MODEL=<modelo de Gemini que quieras usar>
AI_API_KEY=<tu clave>
```

Para un proveedor con otro protocolo se escribe otra subclase de `AIRecipeService` en `backend/recipes/services/ai.py` y se registra en `PROVIDERS`. Las peticiones a la IA tienen un límite de 40 por hora y usuario.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/auth/register/` | Crear cuenta |
| POST | `/api/auth/login/` | Login (correo o usuario) → `access` y `refresh` |
| POST | `/api/auth/token/refresh/` | Renovar el token de acceso |
| GET | `/api/auth/me/` | Usuario actual |
| GET POST PATCH DELETE | `/api/ingredients/` | Despensa |
| GET POST PATCH DELETE | `/api/shopping-list/` | Lista de la compra |
| POST | `/api/shopping-list/clear-bought/` | Eliminar los comprados |
| GET | `/api/recipes/suggestions/?ingredients=pollo,arroz` | Sugerencias por ingredientes |
| GET | `/api/recipes/{external_id}/` | Detalle (con `?ingredients=` añade la coincidencia) |
| GET POST PATCH DELETE | `/api/favorites/` | Favoritos |
| POST | `/api/ai/suggestions/` · `/api/ai/adapt-recipe/` · `/api/ai/shopping-list/` | IA |
| GET | `/api/health/` | Comprobación de que la API responde |

Todas las rutas salvo `health`, `register` y `login` exigen `Authorization: Bearer <token>`, y cada usuario solo ve y modifica sus propios datos.

## Decisiones y límites conocidos

- **Idioma.** Lo que escribe el usuario se traduce al inglés con una tabla de ~120 ingredientes comunes (`backend/recipes/catalog.py`); lo que no esté en la tabla se envía tal cual (si escribes «chicken» funciona). Ampliar esa tabla es lo que más mejora los resultados. Las traducciones automáticas son de calidad razonable pero no perfecta (por ejemplo, el imperativo formal en los pasos).
- **El agua cuenta siempre como disponible** y no entra en el porcentaje.
- **Caché.** Las recetas solo se guardan en la base de datos (`RecipeCache`) al abrirlas en detalle o marcarlas como favoritas. Las búsquedas usan una caché en memoria de 1 hora.
- **Tiempo estimado.** TheMealDB no lo ofrece, así que las tarjetas de receta no lo muestran; sí lo devuelve la IA en sus sugerencias.
- **Extras sobre lo especificado:** `GET /api/health/`, `PATCH /api/favorites/{id}/` (editar notas), el parámetro opcional `?ingredients=` del detalle, el parámetro `?lang=es`, la tabla `TranslationCache` y las variables `AI_BASE_URL`, `TRANSLATION_PROVIDER` y `MYMEMORY_EMAIL`.
- **Sin Docker, PWA, notificaciones, pagos ni OCR** en esta primera versión.
