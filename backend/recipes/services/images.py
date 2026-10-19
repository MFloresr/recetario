"""Foto orientativa de un plato desde Wikipedia (libre, gratuita y sin clave).

Solo se devuelve una foto si el artículo encontrado se llama casi igual que el plato: es mejor no mostrar
ninguna que mostrar una equivocada. Cada foto enlaza a su artículo (autoría y licencia en Wikipedia).
"""

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor

import requests
from django.core.cache import cache

from ..normalization import normalize_name

logger = logging.getLogger(__name__)

API = "https://es.wikipedia.org/w/api.php"
TIMEOUT = 6
CACHE_TTL = 60 * 60 * 24 * 7
HEADERS = {"User-Agent": "Recetario/1.0 (proyecto personal; https://es.wikipedia.org/wiki/Wikipedia:Bot)"}
RELLENO = {"de", "del", "la", "el", "los", "las", "con", "y", "al", "a", "en", "un", "una"}


def _tokens(texto: str) -> set[str]:
    return {t for t in normalize_name(texto).split() if t not in RELLENO}


def _match(plato: str, articulo: str) -> float:
    """Parecido entre el plato y el artículo (0 = no es el mismo plato).

    - Mismo nombre: vale.
    - Un artículo más concreto que el plato («Tarta de queso» → «Tarta de queso japonesa») NO vale: es otro plato.
    - Un artículo más genérico («Pollo al curry» → «Pollo») tampoco, salvo que cubra más de la mitad del nombre
      («Arroz con pollo y verduras» → «Arroz con pollo»); así nunca sale la foto de un ingrediente suelto.
    """
    a, b = _tokens(plato), _tokens(articulo)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if b < a and len(b) / len(a) > 0.5:
        return len(b) / len(a)
    return 0.0


def _is_same_dish(plato: str, articulo: str) -> bool:
    return _match(plato, articulo) > 0


def find_dish_image(title: str, session: requests.Session | None = None) -> dict | None:
    """{url, credit, page} de la foto principal del artículo de Wikipedia sobre el plato, o None."""
    clave = "dishimg:" + hashlib.sha1(normalize_name(title).encode("utf-8")).hexdigest()
    en_cache = cache.get(clave)
    if en_cache is not None:
        return en_cache or None
    try:
        respuesta = (session or requests.Session()).get(
            API,
            params={
                "action": "query", "format": "json", "generator": "search", "gsrsearch": title, "gsrlimit": 5,
                "prop": "pageimages|info", "piprop": "thumbnail", "pithumbsize": 640, "inprop": "url", "redirects": 1,
            },
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        paginas = (respuesta.json().get("query") or {}).get("pages") or {}
    except (requests.RequestException, ValueError, AttributeError):
        logger.warning("No se pudo buscar la foto de «%s»", title)
        return None  # fallo temporal: no se guarda en caché
    resultado = None
    candidatas = [(p, _match(title, p.get("title", ""))) for p in paginas.values() if (p.get("thumbnail") or {}).get("source")]
    candidatas = [(p, m) for p, m in candidatas if m > 0]
    if candidatas:  # la más parecida; a igualdad, la mejor posicionada en la búsqueda
        pagina, _ = max(candidatas, key=lambda c: (c[1], -c[0].get("index", 99)))
        resultado = {"url": pagina["thumbnail"]["source"], "credit": "Wikipedia", "page": pagina.get("fullurl", "")}
    cache.set(clave, resultado or False, CACHE_TTL)
    return resultado


def attach_images(suggestions: list[dict]) -> list[dict]:
    """Añade `image` a cada sugerencia (en paralelo). Si no hay foto fiable, `image` es None."""
    if not suggestions:
        return suggestions
    with ThreadPoolExecutor(max_workers=5) as pool:
        fotos = list(pool.map(lambda s: find_dish_image(s["title"]), suggestions))
    return [{**s, "image": foto} for s, foto in zip(suggestions, fotos)]
