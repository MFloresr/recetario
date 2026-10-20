# Recetario

Recetario inteligente: añades los ingredientes que tienes en casa y la app te muestra qué recetas puedes preparar, ordenadas por el porcentaje de ingredientes que ya tienes. También puedes pedir ideas a una IA, adaptar una receta a tu despensa, guardar favoritas con notas y generar la lista de la compra con lo que falta. Pensada para usarse desde el móvil mientras se cocina.

## Qué incluye

- **Autenticación** con JWT (registro, login con correo o usuario, refresco automático del token).
- **Despensa** agrupada por categorías, con autocompletado de ingredientes frecuentes.
- **Búsqueda de recetas** en TheMealDB por ingredientes, ordenadas por coincidencia, con filtros (categoría, máximo de ingredientes que faltan, nombre). **Todo se muestra en español**: el backend traduce las recetas (ver «Traducción»).
- **Detalle de receta** con indicador de coincidencia con tu despensa y los ingredientes que te faltan.
- **Lista de la compra** agrupada por categoría; desde una receta se añaden de golpe los ingredientes que faltan.
- **Favoritos** con notas personales.
- **IA opcional.** «Sugiéreme algo con IA» propone recetas completas: tipo de comida (desayuno, almuerzo, merienda, cena, postre, batido, snack…), tiempo, dificultad, raciones, ingredientes con cantidades, pasos y una foto orientativa cuando existe. También adapta una receta a tu despensa. Si no está configurada o falla, la app sigue funcionando con la búsqueda normal.
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

Tests (167):

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

Otros comandos: `npm run test` (Vitest, 47 tests), `npm run lint`, `npm run format`, `npm run build`.

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

### Recetas de la IA: qué son y qué no son

- **Las genera la IA a partir de lo que sabe; no navega por internet.** Una IA conectada por API (Gemini, OpenAI…) no busca en la web: escribe la receta desde su conocimiento. Por eso la pantalla lo avisa y conviene revisar cantidades y tiempos. Se le pide que proponga platos reales y conocidos, con su nombre habitual.
- **Fotos:** vienen de Wikipedia (libre y sin clave) y solo se muestran si existe un artículo con el mismo nombre que el plato; si no, la receta sale sin foto en lugar de con una equivocada. Cada foto enlaza a su artículo (autoría y licencia). Los platos clásicos (tortilla de patatas, paella, gazpacho…) suelen tener foto; los poco conocidos, no.
- **Tipo de comida:** puedes pedirlo («quiero un postre»). Las recetas de TheMealDB llevan también un tipo deducido de su categoría (Breakfast → desayuno, Dessert → postre…). TheMealDB no ofrece tiempo ni dificultad, así que esas recetas no los muestran.

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
| GET · DELETE | `/api/auth/me/` | Usuario actual · borrar la cuenta (pide la contraseña) |
| GET POST PATCH DELETE | `/api/ingredients/` | Despensa |
| GET POST PATCH DELETE | `/api/shopping-list/` | Lista de la compra |
| POST | `/api/shopping-list/clear-bought/` | Eliminar los comprados |
| GET | `/api/recipes/suggestions/?ingredients=pollo,arroz` | Sugerencias por ingredientes |
| GET | `/api/recipes/{external_id}/` | Detalle (con `?ingredients=` añade la coincidencia) |
| GET POST PATCH DELETE | `/api/favorites/` | Favoritos |
| POST | `/api/ai/suggestions/` (acepta `meal_type`) · `/api/ai/adapt-recipe/` · `/api/ai/shopping-list/` | IA |
| GET | `/api/health/` | Comprobación de que la API responde |

Todas las rutas salvo `health`, `register` y `login` exigen `Authorization: Bearer <token>`, y cada usuario solo ve y modifica sus propios datos.

## Despliegue

Está publicado en tres servicios, todos con plan gratuito:

| Pieza | Servicio | Dirección |
|---|---|---|
| Frontend | Vercel (proyecto `recetario-web`, carpeta `frontend`) | https://recetario-web-mu.vercel.app |
| Backend (API) | Vercel (proyecto `recetario-api`, carpeta `backend`) | https://recetario-api-alpha.vercel.app/api/health/ |
| Base de datos | Supabase (PostgreSQL), esquema propio `recetario` | — |

Cada `git push` a `main` redespliega los dos proyectos de Vercel.

**Variables del backend en Vercel** (Settings → Environment Variables): `SECRET_KEY` y `DATABASE_URL` (sensibles), `DEBUG=False` y `CORS_ALLOWED_ORIGINS` con la dirección del frontend. Para la IA, `AI_API_KEY` (y `AI_BASE_URL` / `AI_MODEL` si no es OpenAI). **Variable del frontend:** `VITE_API_URL` con la dirección de la API acabada en `/api`. Las variables nuevas solo se aplican en el siguiente despliegue.

**Base de datos.** La app usa un rol propio (`recetario_app`) y un esquema propio (`recetario`) en lugar del esquema `public`, que es el que expone la API REST de Supabase; el esquema no está expuesto y las tablas tienen RLS activado. La conexión va por el pooler en modo sesión (la conexión directa de Supabase solo funciona por IPv6 y Vercel no la puede usar). Las migraciones **no** se ejecutan en el despliegue: se lanzan desde un equipo con `DATABASE_URL` apuntando a producción:

```bash
cd backend
DATABASE_URL="postgres://recetario_app.<ref>:<clave>@aws-0-eu-west-2.pooler.supabase.com:5432/postgres?sslmode=require" python manage.py migrate
```

**Conexiones.** El pooler en modo sesión admite 15 clientes a la vez. Por eso cada petición abre y cierra su conexión (`CONN_MAX_AGE=0`) y los hilos que usa la búsqueda para llamar a TheMealDB **no tocan la base de datos** (un test lo comprueba): una conexión por hilo agotaba el pooler con unas pocas búsquedas simultáneas.

El registro de cuentas es público y tiene un límite de 20 por hora y dirección.

**Privacidad y datos.** La web incluye un aviso de privacidad (`/privacy`) que hay que aceptar al registrarse, y cada usuario puede **borrar su cuenta y todos sus datos** desde el menú de su cuenta (`DELETE /api/auth/me/`, pide la contraseña). No usa cookies ni analítica: solo guarda en el navegador la sesión y el tema. El texto del aviso es el de un proyecto personal; si el uso crece o se monetiza, conviene revisarlo con un profesional.

**Seguridad de la web.** `frontend/vercel.json` añade las cabeceras `Content-Security-Policy` (solo se permiten scripts propios, imágenes de TheMealDB y Wikipedia y peticiones a la API), `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` y `Permissions-Policy`. Si cambia la dirección de la API o se añade otro origen de imágenes, hay que actualizar la política.

**Pruebas y vigilancia automáticas** (GitHub Actions, carpeta `.github/workflows`):
- `ci.yml`: en cada `push` y pull request pasa los tests del backend, comprueba que no faltan migraciones y pasa lint, tests y build del frontend.
- `vigilancia.yml`: cada hora comprueba que la web y la API responden; si falla, GitHub te avisa por correo. Se puede lanzar a mano desde la pestaña Actions.

## Decisiones y límites conocidos

- **Idioma.** Lo que escribe el usuario se traduce al inglés con una tabla de ~120 ingredientes comunes (`backend/recipes/catalog.py`); lo que no esté en la tabla se envía tal cual (si escribes «chicken» funciona). Ampliar esa tabla es lo que más mejora los resultados. Las traducciones automáticas son de calidad razonable pero no perfecta (por ejemplo, el imperativo formal en los pasos).
- **El agua cuenta siempre como disponible** y no entra en el porcentaje.
- **Caché.** Las recetas solo se guardan en la base de datos (`RecipeCache`) al abrirlas en detalle o marcarlas como favoritas. Las búsquedas usan una caché en memoria de 1 hora.
- **Tiempo estimado.** TheMealDB no lo ofrece, así que las tarjetas de receta no lo muestran; sí lo devuelve la IA en sus sugerencias.
- **Extras sobre lo especificado:** `GET /api/health/`, `PATCH /api/favorites/{id}/` (editar notas), el parámetro opcional `?ingredients=` del detalle, el parámetro `?lang=es`, la tabla `TranslationCache` y las variables `AI_BASE_URL`, `TRANSLATION_PROVIDER` y `MYMEMORY_EMAIL`.
- **Sin Docker, PWA, notificaciones, pagos ni OCR** en esta primera versión.
