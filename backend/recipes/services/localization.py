"""Pasa recetas y resultados de búsqueda del inglés de TheMealDB al español."""

import re

from ..spanish import area_es, category_es, ingredient_known_es, meal_type_of, measure_es
from .translation import get_translator, translate_strings

SUPPORTED = {"es"}


def _lines(instrucciones: str) -> list[str]:
    """Pasos sueltos; se descartan los rótulos «STEP 1» que añade TheMealDB entre pasos."""
    lineas = [linea.strip() for linea in (instrucciones or "").splitlines() if linea.strip()]
    return [linea for linea in lineas if not re.fullmatch(r"step\s*\d+", linea, flags=re.IGNORECASE)]


def _first_lower(texto: str) -> str:
    return texto[:1].lower() + texto[1:] if texto else texto


def _ingredient_names(nombres: list[str]) -> tuple[dict[str, str], list[str]]:
    """Nombres conocidos por tabla y lista de los que faltan por traducir."""
    conocidos = {n: ingredient_known_es(n) for n in nombres}
    return {n: v for n, v in conocidos.items() if v}, [n for n, v in conocidos.items() if not v]


def _translation_info(lang: str, completo: bool) -> dict:
    traductor = get_translator()
    return {"lang": lang, "provider": traductor.name if traductor else None, "complete": completo}


def localize_summaries(results: list[dict], lang: str) -> list[dict]:
    """Resultados de /recipes/suggestions/ en español (título, categoría, país y listas de ingredientes)."""
    if lang not in SUPPORTED or not results:
        return results
    nombres = [n for r in results for n in r["matched_ingredients"] + r["missing_ingredients"]]
    conocidos, desconocidos = _ingredient_names(list(dict.fromkeys(nombres)))
    traducidos = translate_strings([r["title"] for r in results] + desconocidos)

    def ingrediente(n: str) -> str:
        return conocidos.get(n) or _first_lower(traducidos.get(n, n))

    return [
        {
            **r,
            "title": traducidos.get(r["title"], r["title"]),
            "original_title": r["title"],
            "category": category_es(r["category"]),
            "meal_type": meal_type_of(r["category"]),
            "area": area_es(r["area"]),
            "matched_ingredients": [ingrediente(n) for n in r["matched_ingredients"]],
            "missing_ingredients": [ingrediente(n) for n in r["missing_ingredients"]],
        }
        for r in results
    ]


def localize_recipe(receta: dict, lang: str, match: dict | None = None) -> dict:
    """Receta completa en español: título, categoría, país, ingredientes, medidas e instrucciones."""
    if lang not in SUPPORTED:
        return receta
    if receta.get("source") == "ai":  # ya está en español: no hay nada que traducir
        salida = dict(receta)
        if match is not None:
            salida["match"] = match
        return salida
    nombres = list(dict.fromkeys(i["ingredient"] for i in receta["ingredients"]))
    conocidos, desconocidos = _ingredient_names(nombres)
    pasos = _lines(receta.get("instructions", ""))
    traducidos = translate_strings([receta["title"], *desconocidos, *pasos])

    def ingrediente(n: str) -> str:
        return conocidos.get(n) or _first_lower(traducidos.get(n, n))

    completo = all(t in traducidos for t in [receta["title"], *desconocidos, *pasos])
    salida = {
        **receta,
        "title": traducidos.get(receta["title"], receta["title"]),
        "original_title": receta["title"],
        "category": category_es(receta.get("category", "")),
        "meal_type": meal_type_of(receta.get("category", "")),
        "area": area_es(receta.get("area", "")),
        "ingredients": [{"ingredient": ingrediente(i["ingredient"]), "measure": measure_es(i.get("measure", ""))} for i in receta["ingredients"]],
        "instructions": "\n".join(traducidos.get(p, p) for p in pasos),
        "translation": _translation_info(lang, completo),
    }
    if match is not None:
        salida["match"] = {
            **match,
            "matched_ingredients": [ingrediente(n) for n in match["matched_ingredients"]],
            "missing_ingredients": [ingrediente(n) for n in match["missing_ingredients"]],
            "missing": [
                {"ingredient": ingrediente(m["ingredient"]), "measure": measure_es(m.get("measure", "")), "name_es": ingrediente(m["ingredient"])}
                for m in match["missing"]
            ],
        }
    return salida
