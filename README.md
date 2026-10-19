# Recetario

Recetario inteligente: añades los ingredientes que tienes en casa y la app te muestra qué recetas puedes preparar, ordenadas por el porcentaje de ingredientes que ya tienes. También permite pedir sugerencias a una IA, guardar favoritas y generar la lista de la compra con lo que falta. Pensada para usarse desde el móvil mientras se cocina.

> **Estado:** fase 1 (estructura y configuración). Las demás fases —autenticación, despensa, TheMealDB, sugerencias, IA y pantallas— se construyen una a una.

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
cp .env.example .env             # y rellena los valores
python manage.py migrate
python manage.py runserver
```

La API queda en <http://localhost:8000/api/>. Comprobación rápida: <http://localhost:8000/api/health/> responde `{"status":"ok"}`.

Tests:

```bash
cd backend
pytest -v
```

Los tests usan siempre SQLite en memoria (aunque `.env` apunte a PostgreSQL) y nunca hacen llamadas externas.

## Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

La app queda en <http://localhost:5173>. Si el backend está en marcha, la barra superior muestra «API conectada».

Otros comandos: `npm run test` (Vitest), `npm run lint`, `npm run format`, `npm run build`.

## Variables de entorno

**`backend/.env`** (ver `backend/.env.example`):

| Variable | Descripción |
|---|---|
| `DEBUG` | `True` solo en desarrollo. |
| `SECRET_KEY` | Clave secreta de Django. Genera una propia y no la compartas. |
| `DATABASE_URL` | Cadena de conexión de PostgreSQL. Si falta, se usa SQLite local. |
| `CORS_ALLOWED_ORIGINS` | Orígenes del frontend permitidos, separados por comas. |
| `THEMEALDB_BASE_URL` | URL base de TheMealDB. |
| `AI_PROVIDER` | Proveedor de IA (`openai` por ahora; preparado para otros). |
| `AI_API_KEY` | Clave del proveedor de IA. Solo en el backend. |
| `AI_MODEL` | Modelo a usar. |

**`frontend/.env`** (ver `frontend/.env.example`):

| Variable | Descripción |
|---|---|
| `VITE_API_URL` | URL de la API de Django (por defecto `http://localhost:8000/api`). |

Los archivos `.env` no se suben a Git.
