"""Sugerencias de recetas a partir de los ingredientes del usuario (lógica de negocio de /recipes/suggestions/)."""

from concurrent.futures import ThreadPoolExecutor

from ..catalog import to_english
from ..exceptions import ExternalServiceError
from ..normalization import normalize_name
from .matching import calculate_match
from ..models import Dish
from .recipes import CATALOG_SOURCE, dish_to_recipe, fetch_many, remember_recipes
from .themealdb import SOURCE, TheMealDBClient

MAX_RESULTS = 20
MAX_CANDIDATES = 30  # recetas que se descargan completas para calcular la coincidencia
MAX_WORKERS = 8


def parse_ingredients(raw: str) -> list[str]:
    """«Pollo, arroz, , ajo» → ['pollo', 'arroz', 'ajo'] (normalizados y sin repetidos)."""
    vistos: list[str] = []
    for parte in (raw or "").split(","):
        nombre = normalize_name(parte)
        if nombre and nombre not in vistos:
            vistos.append(nombre)
    return vistos


def _collect_candidates(client: TheMealDBClient, terms: list[str]) -> tuple[dict[str, dict], list[ExternalServiceError]]:
    """Recetas que usan cada ingrediente, con el número de ingredientes del usuario en que aparecen."""
    candidatos: dict[str, dict] = {}
    errores: list[ExternalServiceError] = []

    def buscar(term: str):
        try:
            return client.filter_by_ingredient(term)
        except ExternalServiceError as exc:
            errores.append(exc)
            return []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for resumen_lista in pool.map(buscar, terms):
            for resumen in resumen_lista:
                actual = candidatos.setdefault(resumen["external_id"], {**resumen, "hits": 0})
                actual["hits"] += 1
    return candidatos, errores


def build_suggestions(
    pantry: list[str],
    *,
    category: str = "",
    max_missing: int | None = None,
    search: str = "",
    client: TheMealDBClient | None = None,
    limit: int = MAX_RESULTS,
) -> dict:
    client = client or TheMealDBClient()
    terms = list(dict.fromkeys(to_english(nombre) for nombre in pantry))

    candidatos, errores = _collect_candidates(client, terms)

    # Búsqueda por nombre: añade esas recetas (ya vienen completas)
    if search:
        try:
            for receta in client.search_by_name(search):
                remember_recipes([receta])
                candidatos.setdefault(receta["external_id"], {"external_id": receta["external_id"], "title": receta["title"], "hits": 0})
        except ExternalServiceError as exc:
            errores.append(exc)

    if not candidatos and errores:
        raise errores[0]  # TheMealDB no respondió: error controlado en lugar de «0 resultados»

    elegidos = sorted(candidatos.values(), key=lambda c: (-c["hits"], c["title"].lower()))[:MAX_CANDIDATES]

    recetas, errores_descarga = fetch_many([c["external_id"] for c in elegidos], client)
    errores.extend(errores_descarga)

    if not recetas and errores:
        raise errores[0]

    clave_busqueda = normalize_name(search)
    clave_categoria = normalize_name(category)
    resultados = []
    for receta in recetas:
        if clave_categoria and normalize_name(receta["category"]) != clave_categoria:
            continue
        if clave_busqueda and clave_busqueda not in normalize_name(receta["title"]):
            continue
        coincidencia = calculate_match(pantry, receta["ingredients"])
        if max_missing is not None and len(coincidencia["missing_ingredients"]) > max_missing:
            continue
        resultados.append(
            {
                "external_id": receta["external_id"],
                "title": receta["title"],
                "image": receta["image"],
                "category": receta["category"],
                "area": receta["area"],
                **coincidencia,
                "source": SOURCE,
            }
        )

    resultados.sort(key=lambda r: (-r["match_score"], len(r["missing_ingredients"]), r["title"].lower()))
    resultados = resultados[:limit]
    return {"count": len(resultados), "results": resultados}


def catalog_suggestions(pantry: list[str], *, category: str = "", max_missing: int | None = None, search: str = "", limit: int = MAX_RESULTS) -> list[dict]:
    """Sugerencias del catálogo propio: platos ya completados (en español) que se pueden preparar con la despensa."""
    platos = Dish.objects.filter(enriched=True).exclude(ingredients=[])
    clave_busqueda = normalize_name(search)
    clave_categoria = normalize_name(category)
    resultados = []
    for plato in platos:
        receta = dish_to_recipe(plato)
        if clave_categoria and clave_categoria not in (normalize_name(plato.meal_type), normalize_name(plato.country)):
            continue
        if clave_busqueda and clave_busqueda not in normalize_name(plato.name_es):
            continue
        coincidencia = calculate_match(pantry, receta["ingredients"], translate=False)
        if pantry and not coincidencia["matched_ingredients"] and not clave_busqueda:
            continue
        if max_missing is not None and len(coincidencia["missing_ingredients"]) > max_missing:
            continue
        resultados.append({
            "external_id": receta["external_id"],
            "title": receta["title"],
            "image": receta["image"],
            "category": receta["category"],
            "area": receta["area"],
            **coincidencia,
            "source": CATALOG_SOURCE,
        })
    resultados.sort(key=lambda r: (-r["match_score"], len(r["missing_ingredients"]), r["title"].lower()))
    return resultados[:limit]
