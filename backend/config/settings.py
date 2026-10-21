"""Configuración de Django para Recetario. Todo lo sensible se lee del entorno (ver .env.example)."""

import os
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# Vercel define VERCEL=1 tanto en el build como en ejecución
ON_VERCEL = bool(os.environ.get("VERCEL"))

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173"]),
)
environ.Env.read_env(BASE_DIR / ".env")

# --- Seguridad / entorno ---

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

if ON_VERCEL:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, ".vercel.app"]
    # Vercel termina el HTTPS y reenvía la petición a la función
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Aplicaciones ---

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "recipes",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Base de datos ---
# PostgreSQL mediante DATABASE_URL. Sin ella se usa SQLite local para no bloquear el desarrollo.

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
# Cada petición abre y cierra su conexión (valor por defecto): el pooler de Supabase en modo sesión solo admite
# 15 clientes y las instancias de Vercel aparecen y desaparecen, así que las conexiones persistentes lo agotarían.
DATABASES["default"]["CONN_MAX_AGE"] = 0
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- CORS: el frontend es el único origen autorizado ---

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# --- API REST: todo requiere sesión salvo que una vista diga lo contrario ---

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "recipes.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {"ai": "40/hour", "register": "20/hour"},  # la IA cuesta dinero; el registro está abierto al público
    "NUM_PROXIES": 1 if ON_VERCEL else None,  # la IP real viene en X-Forwarded-For
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# --- Servicios externos (se usan a partir de las fases 4 y 6) ---

THEMEALDB_BASE_URL = env("THEMEALDB_BASE_URL", default="https://www.themealdb.com/api/json/v1/1")
AI_PROVIDER = env("AI_PROVIDER", default="openai")
AI_API_KEY = env("AI_API_KEY", default="")
AI_MODEL = env("AI_MODEL", default="gpt-4o-mini")
# Opcional: otra API compatible con OpenAI (Gemini, Groq, Ollama...). Vacío = api.openai.com
AI_BASE_URL = env("AI_BASE_URL", default="")
# Opcional: modelos de reserva (separados por comas) si el principal está saturado (429/5xx)
AI_FALLBACK_MODELS = env.list("AI_FALLBACK_MODELS", default=[])

# Opcional: clave gratuita de https://www.pexels.com/api/ para fotos de muestra de más platos
PEXELS_API_KEY = env("PEXELS_API_KEY", default="")
# Opcional: clave gratuita de https://unsplash.com/developers (reserva si Pexels no responde)
UNSPLASH_ACCESS_KEY = env("UNSPLASH_ACCESS_KEY", default="")

# Traducción de las recetas al español (TheMealDB solo existe en inglés).
# auto = IA si hay clave configurada, si no MyMemory (gratuito, sin clave); también: mymemory, ai, none
TRANSLATION_PROVIDER = env("TRANSLATION_PROVIDER", default="auto")
# Opcional: un correo sube el cupo diario gratuito de MyMemory (de 5.000 a 50.000 caracteres)
MYMEMORY_EMAIL = env("MYMEMORY_EMAIL", default="")
