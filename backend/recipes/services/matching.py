"""Cálculo de coincidencia entre la despensa del usuario y los ingredientes de una receta."""

from ..catalog import to_english, to_spanish
from ..normalization import normalize_name

# Se da por hecho que siempre hay agua en casa: no cuenta como ingrediente ni como faltante
ALWAYS_AVAILABLE = {"water"}


def _tokens(nombre: str) -> set[str]:
    """Palabras del nombre en singular simple: «Chicken Breasts» → {chicken, breast}."""
    palabras = set()
    for palabra in normalize_name(nombre).replace("_", " ").split():
        if len(palabra) > 4 and palabra.endswith("oes"):  # tomatoes → tomato, potatoes → potato
            palabra = palabra[:-2]
        elif len(palabra) > 3 and palabra.endswith("s") and not palabra.endswith("ss"):
            palabra = palabra[:-1]
        palabras.add(palabra)
    return palabras


def ingredient_matches(pantry_item: str, recipe_ingredient: str) -> bool:
    """El ingrediente de la despensa cubre el de la receta si uno contiene todas las palabras del otro.

    «chicken» cubre «chicken breast» y «chicken breast» cubre «chicken»; «rice» no cubre «tomato».
    """
    a, b = _tokens(pantry_item), _tokens(recipe_ingredient)
    return bool(a) and bool(b) and (a <= b or b <= a)


def calculate_match(pantry: list[str], recipe_ingredients: list[dict]) -> dict:
    """Devuelve ingredientes que coinciden, los que faltan y el porcentaje (0-100) de coincidencia.

    `pantry` son nombres del usuario (en español o inglés); se traducen antes de comparar.
    """
    despensa = [to_english(nombre) for nombre in pantry if nombre and nombre.strip()]
    vistos: set[str] = set()
    matched: list[str] = []
    missing: list[str] = []
    for item in recipe_ingredients:
        nombre = (item.get("ingredient") or "").strip()
        clave = normalize_name(nombre)
        if not clave or clave in vistos or clave in ALWAYS_AVAILABLE:
            continue
        vistos.add(clave)
        if any(ingredient_matches(propio, nombre) for propio in despensa):
            matched.append(nombre)
        else:
            missing.append(nombre)
    total = len(matched) + len(missing)
    score = round(100 * len(matched) / total) if total else 0
    return {"matched_ingredients": matched, "missing_ingredients": missing, "match_score": score}


def with_spanish_names(recipe_ingredients: list[dict], names: list[str]) -> list[dict]:
    """Para mostrar en la lista de la compra: [{ingredient, measure, name_es}] con el nombre en español si se conoce."""
    por_nombre = {normalize_name(i.get("ingredient", "")): i for i in recipe_ingredients}
    salida = []
    for nombre in names:
        original = por_nombre.get(normalize_name(nombre), {"ingredient": nombre, "measure": ""})
        salida.append({**original, "name_es": to_spanish(nombre)})
    return salida
