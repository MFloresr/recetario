"""Errores controlados de servicios externos y manejador global de excepciones de la API."""

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class ExternalServiceError(Exception):
    """Un servicio externo (TheMealDB, IA) falló. Se traduce a una respuesta HTTP clara, nunca a un traceback."""

    status_code = 502
    code = "external_service_error"

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class TheMealDBError(ExternalServiceError):
    code = "themealdb_error"


class AIServiceError(ExternalServiceError):
    code = "ai_error"


class TranslationError(ExternalServiceError):
    code = "translation_error"


def api_exception_handler(exc, context):
    if isinstance(exc, ExternalServiceError):
        return Response({"detail": exc.message, "code": exc.code}, status=exc.status_code)
    return drf_exception_handler(exc, context)
