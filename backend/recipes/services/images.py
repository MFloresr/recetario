"""Foto de muestra de un plato.

Se prueban varias fuentes, de la más precisa a la más amplia, y se devuelve la primera que da una foto fiable:

1. **Wikipedia** (libre, sin clave): la foto principal del artículo del plato.
2. **Pexels** (gratuita, con clave opcional `PEXELS_API_KEY`): fotos de comida de calidad, con crédito al autor.
3. **Openverse** (fotos con licencia libre, sin clave): solo se acepta una foto si su título nombra todo el plato.
4. **Wikimedia Commons** (libre, sin clave): fotos cuyo nombre de archivo coincide con el plato.

Es mejor no mostrar ninguna foto que mostrar la de otro plato: Wikipedia y Commons solo se aceptan si el nombre
coincide. Siempre es una foto de muestra, y cada una enlaza a su origen (autoría y licencia).
"""

import hashlib
import logging
import re
from concurrent.futures import ThreadPoolExecutor

import requests
from django.conf import settings
from django.core.cache import cache

from ..normalization import normalize_name

logger = logging.getLogger(__name__)

WIKIPEDIA_API = "https://es.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
PEXELS_API = "https://api.pexels.com/v1/search"
OPENVERSE_API = "https://api.openverse.org/v1/images/"
TIMEOUT = 6
CACHE_TTL = 60 * 60 * 24 * 7
HEADERS = {"User-Agent": "Recetario/1.0 (proyecto personal; https://es.wikipedia.org/wiki/Wikipedia:Bot)"}
RELLENO = {"de", "del", "la", "el", "los", "las", "con", "y", "al", "a", "en", "un", "una", "para", "su", "sus"}


def _tokens(texto: str) -> set[str]:
    return {t for t in normalize_name(texto).split() if t not in RELLENO}


def _match(plato: str, articulo: str) -> float:
    """Parecido entre el plato y el nombre de un artículo o archivo (0 = no es el mismo plato).

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


def _get(session, url: str, headers: dict | None = None, **kwargs):
    return (session or requests.Session()).get(url, headers={**HEADERS, **(headers or {})}, timeout=TIMEOUT, **kwargs)


def _from_wikipedia(titulo: str, session) -> dict | None:
    respuesta = _get(
        session,
        WIKIPEDIA_API,
        params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": titulo, "gsrlimit": 5,
            "prop": "pageimages|info", "piprop": "thumbnail", "pithumbsize": 640, "inprop": "url", "redirects": 1,
        },
    )
    paginas = (respuesta.json().get("query") or {}).get("pages") or {}
    candidatas = [(p, _match(titulo, p.get("title", ""))) for p in paginas.values() if (p.get("thumbnail") or {}).get("source")]
    candidatas = [(p, m) for p, m in candidatas if m > 0]
    if not candidatas:
        return None
    pagina, _ = max(candidatas, key=lambda c: (c[1], -c[0].get("index", 99)))  # la más parecida; a igualdad, la mejor posicionada
    return {"url": pagina["thumbnail"]["source"], "credit": "Wikipedia", "page": pagina.get("fullurl", "")}


def _from_pexels(consulta: str, session) -> dict | None:
    clave = getattr(settings, "PEXELS_API_KEY", "")
    if not clave or not consulta:
        return None
    respuesta = _get(
        session, PEXELS_API, params={"query": f"{consulta} food dish", "per_page": 1, "orientation": "landscape"}, headers={"Authorization": clave}
    )
    fotos = respuesta.json().get("photos") or []
    if not fotos:
        return None
    foto = fotos[0]
    url = (foto.get("src") or {}).get("large") or (foto.get("src") or {}).get("medium")
    if not url:
        return None
    return {"url": url, "credit": f"{foto.get('photographer', 'Pexels')} (Pexels)", "page": foto.get("url", "")}


def _from_openverse(consulta: str, session) -> dict | None:
    """Foto con licencia libre (casi siempre de Flickr). Se acepta solo si el título contiene todas las palabras del plato."""
    def palabras_de(texto: str) -> set[str]:  # sin signos de puntuación: «pudding:» cuenta como «pudding»
        return {t for t in re.findall(r"[a-z0-9]+", normalize_name(texto)) if t not in RELLENO}

    palabras = palabras_de(consulta)
    if not palabras:
        return None
    respuesta = _get(session, OPENVERSE_API, params={"q": consulta, "page_size": 8, "mature": "false"})
    for foto in respuesta.json().get("results") or []:
        if palabras <= palabras_de(foto.get("title", "")) and foto.get("thumbnail"):
            licencia = (foto.get("license") or "").upper()
            autor = foto.get("creator") or foto.get("source") or "Openverse"
            return {
                "url": foto["thumbnail"],
                "credit": f"{autor} (CC {licencia})" if licencia else f"{autor} (Openverse)",
                "page": foto.get("foreign_landing_url") or foto.get("url", ""),
            }
    return None


def _from_commons(consulta: str, session) -> dict | None:
    if not consulta:
        return None
    respuesta = _get(
        session,
        COMMONS_API,
        params={
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrsearch": f"{consulta} filetype:bitmap",
            "gsrlimit": 8, "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 640,
        },
    )
    paginas = (respuesta.json().get("query") or {}).get("pages") or {}
    candidatas = []
    for pagina in paginas.values():
        nombre = re.sub(r"^Archivo:|^File:|\.\w+$", "", pagina.get("title", ""))
        info = (pagina.get("imageinfo") or [{}])[0]
        miniatura = info.get("thumburl")
        if miniatura and _match(consulta, re.sub(r"[_\d()-]+", " ", nombre)) > 0:
            candidatas.append((pagina, info, miniatura))
    if not candidatas:
        return None
    pagina, info, miniatura = min(candidatas, key=lambda c: c[0].get("index", 99))
    autor = re.sub(r"<[^>]+>", "", ((info.get("extmetadata") or {}).get("Artist") or {}).get("value", "")).strip()
    return {"url": miniatura, "credit": f"{autor or 'Wikimedia Commons'} (Wikimedia Commons)", "page": info.get("descriptionurl", "")}


def find_dish_image(title: str, photo_query: str = "", photo_query_en: str = "", session: requests.Session | None = None) -> dict | None:
    """{url, credit, page} de una foto de muestra del plato, o None si ninguna fuente da una fiable."""
    consulta = photo_query.strip() or title
    huella = "|".join(normalize_name(x) for x in (title, photo_query, photo_query_en))
    clave = "dishimg:" + hashlib.sha1(huella.encode("utf-8")).hexdigest()
    en_cache = cache.get(clave)
    if en_cache is not None:
        return en_cache or None
    fuentes = [
        lambda: _from_wikipedia(consulta, session),
        lambda: _from_wikipedia(title, session) if normalize_name(title) != normalize_name(consulta) else None,
        lambda: _from_pexels(photo_query_en or consulta, session),
        lambda: _from_openverse(photo_query_en or "", session),
        lambda: _from_commons(consulta, session),
    ]
    fallo = False
    for fuente in fuentes:
        try:
            resultado = fuente()
        except (requests.RequestException, ValueError, AttributeError):
            logger.warning("No se pudo buscar la foto de «%s» en una fuente", title)
            fallo = True
            continue
        if resultado:
            cache.set(clave, resultado, CACHE_TTL)
            return resultado
    if not fallo:  # sin foto de verdad (no por un fallo temporal): se recuerda para no repetir las búsquedas
        cache.set(clave, False, CACHE_TTL)
    return None


def attach_images(suggestions: list[dict]) -> list[dict]:
    """Añade `image` a cada sugerencia (en paralelo). Si no hay foto fiable, `image` es None."""
    if not suggestions:
        return suggestions
    with ThreadPoolExecutor(max_workers=5) as pool:
        fotos = list(
            pool.map(lambda s: find_dish_image(s["title"], s.get("photo_query", ""), s.get("photo_query_en", "")), suggestions)
        )
    return [{**s, "image": foto} for s, foto in zip(suggestions, fotos)]
