"""Acceso a recetas: caché en base de datos (solo al abrir en detalle o marcar favorita) y caché en memoria."""

from concurrent.futures import ThreadPoolExecutor

from django.core.cache import cache

from ..exceptions import ExternalServiceError

from ..models import RecipeCache
from .themealdb import SOURCE, TheMealDBClient

MEMORY_TTL = 60 * 60  # 1 hora


def recipe_to_dict(recipe: RecipeCache) -> dict:
    return {
        "external_id": recipe.external_id,
        "title": recipe.title,
        "image": recipe.image,
        "category": recipe.category,
        "area": recipe.area,
        "instructions": recipe.instructions,
        "ingredients": recipe.ingredients,
        "source": recipe.source,
    }


def fetch_recipe(external_id: str, client: TheMealDBClient | None = None) -> dict | None:
    """Receta normalizada desde la base de datos, la memoria o TheMealDB. No guarda nada en la base de datos."""
    en_bd = RecipeCache.objects.filter(external_id=external_id, source=SOURCE).first()
    if en_bd:
        return recipe_to_dict(en_bd)
    clave = f"meal:{external_id}"
    receta = cache.get(clave)
    if receta is None:
        receta = (client or TheMealDBClient()).get_by_id(external_id)
        if receta is not None:
            cache.set(clave, receta, MEMORY_TTL)
    return receta


def fetch_many(ids: list[str], client: TheMealDBClient | None = None) -> tuple[list[dict], list[ExternalServiceError]]:
    """Recetas por id, en el orden pedido, más los errores de TheMealDB que hubo por el camino.

    La base de datos se consulta UNA vez y desde el hilo principal; los hilos solo hacen peticiones HTTP.
    Un hilo que tocara la base de datos abriría su propia conexión y, con el pooler de Supabase (15 clientes
    en modo sesión), unas pocas peticiones simultáneas lo agotarían (EMAXCONNSESSION).
    """
    recetas = {r.external_id: recipe_to_dict(r) for r in RecipeCache.objects.filter(external_id__in=ids, source=SOURCE)}
    pendientes = [i for i in ids if i not in recetas]
    en_memoria = cache.get_many([f"meal:{i}" for i in pendientes])
    for i in pendientes:
        if f"meal:{i}" in en_memoria:
            recetas[i] = en_memoria[f"meal:{i}"]
    faltan = [i for i in pendientes if i not in recetas]
    errores: list[ExternalServiceError] = []
    if faltan:
        cliente = client or TheMealDBClient()

        def descargar(i: str):
            try:
                return i, cliente.get_by_id(i)
            except ExternalServiceError as exc:
                errores.append(exc)
                return i, None

        with ThreadPoolExecutor(max_workers=8) as pool:
            for i, receta in pool.map(descargar, faltan):
                if receta is not None:
                    recetas[i] = receta
                    cache.set(f"meal:{i}", receta, MEMORY_TTL)
    return [recetas[i] for i in ids if i in recetas], errores


def remember_recipes(recipes: list[dict]) -> None:
    """Guarda en memoria recetas ya descargadas (p. ej. de una búsqueda por nombre) para no pedirlas otra vez."""
    for receta in recipes:
        cache.set(f"meal:{receta['external_id']}", receta, MEMORY_TTL)


def save_recipe(receta: dict) -> RecipeCache:
    """Guarda (o actualiza) la receta en RecipeCache."""
    objeto, _ = RecipeCache.objects.update_or_create(
        external_id=receta["external_id"],
        defaults={
            "source": receta.get("source", SOURCE),
            "title": receta["title"],
            "image": receta.get("image", ""),
            "category": receta.get("category", ""),
            "area": receta.get("area", ""),
            "instructions": receta.get("instructions", ""),
            "ingredients": receta.get("ingredients", []),
            "raw_data": receta,
        },
    )
    return objeto


def get_recipe(external_id: str, client: TheMealDBClient | None = None, save: bool = True) -> dict | None:
    """Receta normalizada. Con `save=True` queda guardada en RecipeCache (detalle y favoritos)."""
    receta = fetch_recipe(external_id, client)
    if receta is not None and save:
        save_recipe(receta)
    return receta
