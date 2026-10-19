"""Traducción de textos con caché en base de datos.

Dos proveedores intercambiables:
- MyMemory: gratuito y sin clave (cupo diario limitado; un correo en MYMEMORY_EMAIL lo amplía).
- La IA configurada (si hay `AI_API_KEY`): mejor calidad y traduce por lotes.

Cada texto se traduce una sola vez: el resultado queda en `TranslationCache`. Si el proveedor falla o
se agota el cupo, la función devuelve lo que sí pudo traducir y el resto queda en el idioma original;
la app nunca se rompe por esto.
"""

import hashlib
import logging
import re
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

import requests
from django.conf import settings

from ..exceptions import ExternalServiceError, TranslationError
from ..models import TranslationCache
from . import ai as ai_service

logger = logging.getLogger(__name__)

MYMEMORY_URL = "https://api.mymemory.translated.net/get"
MYMEMORY_MAX_CHARS = 450  # el límite de MyMemory es de 500 bytes por consulta
AI_BATCH = 40
MAX_WORKERS = 8


def _hash(texto: str) -> str:
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()


def _pieces(texto: str, limite: int = MYMEMORY_MAX_CHARS) -> list[str]:
    """Parte un texto largo por frases para que cada trozo quepa en una consulta."""
    if len(texto) <= limite:
        return [texto]
    trozos, actual = [], ""
    for frase in re.split(r"(?<=[.!?;])\s+", texto):
        while len(frase) > limite:  # una «frase» enorme sin puntuación: se corta por palabras
            corte = frase.rfind(" ", 0, limite)
            corte = corte if corte > 0 else limite
            trozos.append(frase[:corte])
            frase = frase[corte:].strip()
        if actual and len(actual) + 1 + len(frase) > limite:
            trozos.append(actual)
            actual = frase
        else:
            actual = f"{actual} {frase}".strip()
    if actual:
        trozos.append(actual)
    return trozos


class Translator(ABC):
    name: str

    @abstractmethod
    def translate(self, texts: list[str], source: str, target: str) -> dict[str, str]:
        """Devuelve {original: traducido} solo de lo que pudo traducir."""


class MyMemoryTranslator(Translator):
    name = "mymemory"

    def __init__(self, session: requests.Session | None = None, email: str = "", timeout: int = 10):
        self.session = session or requests.Session()
        self.email = email
        self.timeout = timeout

    def _one(self, texto: str, source: str, target: str) -> str:
        params = {"q": texto, "langpair": f"{source}|{target}"}
        if self.email:
            params["de"] = self.email
        try:
            respuesta = self.session.get(MYMEMORY_URL, params=params, timeout=self.timeout)
            datos = respuesta.json()
        except (requests.RequestException, ValueError) as exc:
            raise TranslationError("No se pudo contactar con el traductor.", code="translation_unreachable") from exc
        traducido = (datos.get("responseData") or {}).get("translatedText") or ""
        if respuesta.status_code != 200 or str(datos.get("responseStatus")) != "200" or datos.get("quotaFinished") or "MYMEMORY WARNING" in traducido.upper():
            raise TranslationError("El traductor gratuito ha agotado su cupo diario.", status_code=429, code="translation_quota")
        return traducido

    def _text(self, texto: str, source: str, target: str) -> str:
        return " ".join(self._one(trozo, source, target) for trozo in _pieces(texto))

    def translate(self, texts: list[str], source: str, target: str) -> dict[str, str]:
        resultado: dict[str, str] = {}
        error: TranslationError | None = None

        def trabajo(texto: str):
            try:
                return texto, self._text(texto, source, target)
            except TranslationError as exc:
                return texto, exc

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            for texto, valor in pool.map(trabajo, texts):
                if isinstance(valor, TranslationError):
                    error = valor
                elif valor.strip():
                    resultado[texto] = valor
        if error and not resultado:
            raise error
        if error:
            logger.warning("Traducción parcial: %s", error.message)
        return resultado


class AITranslator(Translator):
    name = "ai"

    def __init__(self, servicio: ai_service.AIRecipeService):
        self.servicio = servicio

    def translate(self, texts: list[str], source: str, target: str) -> dict[str, str]:
        resultado: dict[str, str] = {}
        for i in range(0, len(texts), AI_BATCH):
            lote = texts[i : i + AI_BATCH]
            try:
                traducidos = self.servicio.translate(lote, source, target)
            except ExternalServiceError as exc:
                if not resultado and i + AI_BATCH >= len(texts):
                    raise TranslationError(exc.message, status_code=exc.status_code, code=exc.code) from exc
                logger.warning("Traducción parcial con IA: %s", exc.message)
                continue
            resultado.update(dict(zip(lote, traducidos)))
        return resultado


def get_translator() -> Translator | None:
    """Proveedor según TRANSLATION_PROVIDER (auto: IA si hay clave, si no MyMemory)."""
    proveedor = (settings.TRANSLATION_PROVIDER or "auto").lower()
    if proveedor == "none":
        return None
    if proveedor == "auto":
        proveedor = "ai" if settings.AI_API_KEY else "mymemory"
    if proveedor == "ai":
        try:
            return AITranslator(ai_service.get_ai_service())
        except ExternalServiceError:
            return None
    return MyMemoryTranslator(email=settings.MYMEMORY_EMAIL)


def translate_strings(texts: list[str], source: str = "en", target: str = "es", translator: Translator | None = None) -> dict[str, str]:
    """{original: traducido} para los textos que se pudieron traducir (de la caché o del proveedor)."""
    unicos = list(dict.fromkeys(t for t in texts if t and t.strip()))
    if not unicos:
        return {}
    direccion = f"{source}-{target}"
    por_hash = {_hash(t): t for t in unicos}
    resultado = {
        por_hash[fila.source_hash]: fila.translated
        for fila in TranslationCache.objects.filter(direction=direccion, source_hash__in=list(por_hash))
    }
    pendientes = [t for t in unicos if t not in resultado]
    if pendientes:
        traductor = translator or get_translator()
        if traductor is not None:
            try:
                nuevos = traductor.translate(pendientes, source, target)
            except ExternalServiceError as exc:
                logger.warning("No se pudo traducir: %s", exc.message)
                nuevos = {}
            if nuevos:
                TranslationCache.objects.bulk_create(
                    [TranslationCache(direction=direccion, source_hash=_hash(o), source=o, translated=t) for o, t in nuevos.items()],
                    ignore_conflicts=True,
                )
                resultado.update(nuevos)
    return resultado
