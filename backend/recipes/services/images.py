"""Foto de muestra de un plato.

Se prueban varias fuentes, de la más precisa a la más amplia, y se devuelve la primera que da una foto fiable:

1. **Wikipedia** (libre, sin clave): la foto principal del artículo del plato.
2. **Pexels** (gratuita, con clave opcional `PEXELS_API_KEY`): fotos de comida de calidad, con crédito al autor.
3. **Unsplash** (gratuita, con clave opcional `UNSPLASH_ACCESS_KEY`): reserva si Pexels no está disponible.
4. **Openverse** (fotos con licencia libre, sin clave): solo se acepta una foto si su título nombra todo el plato.
5. **Wikimedia Commons** (libre, sin clave): fotos cuyo nombre de archivo coincide con el plato.

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
UNSPLASH_API = "https://api.unsplash.com/search/photos"
OPENVERSE_API = "https://api.openverse.org/v1/images/"
TIMEOUT = 6
CACHE_TTL = 60 * 60 * 24 * 7
HEADERS = {"User-Agent": "Recetario/1.0 (proyecto personal; https://es.wikipedia.org/wiki/Wikipedia:Bot)"}
RELLENO = {"de", "del", "la", "el", "los", "las", "con", "y", "al", "a", "en", "un", "una", "para", "su", "sus"}

# Foto de respaldo por tipo de comida: se usa solo cuando ninguna fuente encuentra una foto del plato, para que toda receta tenga foto.
# Son fotos de Unsplash (enlazadas, con su autoría). Siempre es una foto de muestra de ese tipo de comida, no del plato.
FOTOS_RESPALDO = {
    "desayuno": {"url": "https://images.unsplash.com/photo-1504754524776-8f4f37790ca0?auto=format&fit=crop&w=1080&q=80", "credit": "Rachel Park (Unsplash)", "page": "https://unsplash.com/photos/breakfast-spread-with-waffles-eggs-and-juice-hrlvr2ZlUNk"},
    "almuerzo": {"url": "https://images.unsplash.com/photo-1599118732532-f1cdb1ae7389?auto=format&fit=crop&w=1080&q=80", "credit": "Michal Balog (Unsplash)", "page": "https://unsplash.com/photos/cooked-food-on-white-ceramic-plate-ihdvOzjH4zs"},
    "merienda": {"url": "https://images.unsplash.com/photo-1766185387804-e5da118064f7?auto=format&fit=crop&w=1080&q=80", "credit": "Stacy (Unsplash)", "page": "https://unsplash.com/photos/stack-of-cookies-next-to-a-white-mug-F3hRk3PL1Mc"},
    "cena": {"url": "https://images.unsplash.com/photo-1673646960449-45c61e27ef47?auto=format&fit=crop&w=1080&q=80", "credit": "Natalia Gusakova (Unsplash)", "page": "https://unsplash.com/photos/a-white-plate-topped-with-meat-and-vegetables-qIUkWt00Uoc"},
    "postre": {"url": "https://images.unsplash.com/photo-1708175313856-8573b2bf8a3a?auto=format&fit=crop&w=1080&q=80", "credit": "Med Wael Laraiedh (Unsplash)", "page": "https://unsplash.com/photos/a-piece-of-cheesecake-on-a-white-plate-hszGPnZGB3A"},
    "batido": {"url": "https://images.unsplash.com/photo-1622597468620-656aa1f981ea?auto=format&fit=crop&w=1080&q=80", "credit": "Jugoslocos (Unsplash)", "page": "https://unsplash.com/photos/strawberry-shake-on-clear-drinking-glass-zpv8D8DOShs"},
    "snack": {"url": "https://images.unsplash.com/photo-1490818387583-1baba5e638af?auto=format&fit=crop&w=1080&q=80", "credit": "Brooke Lark (Unsplash)", "page": "https://unsplash.com/photos/variety-of-sliced-fruits-08bOYnH_r_E"},
    "entrante": {"url": "https://images.unsplash.com/photo-1577906096429-f73c2c312435?auto=format&fit=crop&w=1080&q=80", "credit": "Sebastian Coman Photography (Unsplash)", "page": "https://unsplash.com/photos/small-appetizers-are-arranged-on-a-silver-plate-ZGgIYaL9lYk"},
    "bebida": {"url": "https://images.unsplash.com/photo-1586734565008-fbdbc166fd6c?auto=format&fit=crop&w=1080&q=80", "credit": "Vinicius Amano (Unsplash)", "page": "https://unsplash.com/photos/clear-drinking-glass-with-ice-cubes-V1zGiNVPumM"},
    "otro": {"url": "https://images.unsplash.com/photo-1515003197210-e0cd71810b5f?auto=format&fit=crop&w=1080&q=80", "credit": "Brooke Lark (Unsplash)", "page": "https://unsplash.com/photos/pasta-dish-on-brown-plate-4J059aGa5s4"},
}
FOTOS_RESPALDO["plato principal"] = FOTOS_RESPALDO["cena"]


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


def _from_unsplash(consulta: str, session) -> dict | None:
    clave = getattr(settings, "UNSPLASH_ACCESS_KEY", "")
    if not clave or not consulta:
        return None
    respuesta = _get(
        session, UNSPLASH_API, params={"query": f"{consulta} food dish", "per_page": 1, "orientation": "landscape"},
        headers={"Authorization": f"Client-ID {clave}"},
    )
    fotos = respuesta.json().get("results") or []
    if not fotos:
        return None
    foto = fotos[0]
    url = (foto.get("urls") or {}).get("regular") or (foto.get("urls") or {}).get("small")
    if not url:
        return None
    autor = (foto.get("user") or {}).get("name") or "Unsplash"
    return {"url": url, "credit": f"{autor} (Unsplash)", "page": (foto.get("links") or {}).get("html", "")}


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
        lambda: _from_unsplash(photo_query_en or consulta, session),
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


def find_dish_image_or_fallback(title: str, photo_query: str = "", photo_query_en: str = "", meal_type: str = "") -> dict:
    """Foto de muestra del plato; si ninguna fuente da una fiable, la de respaldo de su tipo de comida (nunca None)."""
    foto = find_dish_image(title, photo_query, photo_query_en)
    return foto or FOTOS_RESPALDO.get(normalize_name(meal_type), FOTOS_RESPALDO["otro"])


def attach_images(suggestions: list[dict]) -> list[dict]:
    """Añade `image` a cada sugerencia (en paralelo). Siempre hay foto: si ninguna fuente da una fiable, la de respaldo de su tipo de comida."""
    if not suggestions:
        return suggestions
    with ThreadPoolExecutor(max_workers=5) as pool:
        fotos = list(
            pool.map(
                lambda s: find_dish_image_or_fallback(s["title"], s.get("photo_query", ""), s.get("photo_query_en", ""), s.get("meal_type", "")),
                suggestions,
            )
        )
    return [{**s, "image": foto} for s, foto in zip(suggestions, fotos)]
