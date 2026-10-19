"""Ajustes para pytest: siempre SQLite en memoria, aunque .env apunte a PostgreSQL, y sin llamadas externas."""

from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # solo tests: más rápido
