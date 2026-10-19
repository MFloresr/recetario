import pytest

from recipes.catalog import guess_category, to_english, to_spanish
from recipes.services.matching import calculate_match, ingredient_matches

HANDI = [
    {"ingredient": "chicken", "measure": "500g"},
    {"ingredient": "rice", "measure": "200g"},
    {"ingredient": "onion", "measure": "1"},
    {"ingredient": "garlic", "measure": "2 cloves"},
    {"ingredient": "yogurt", "measure": "100g"},
]


def test_match_score_del_ejemplo_del_enunciado():
    r = calculate_match(["pollo", "arroz", "ajo", "cebolla"], HANDI)
    assert r["match_score"] == 80
    assert r["matched_ingredients"] == ["chicken", "rice", "onion", "garlic"]
    assert r["missing_ingredients"] == ["yogurt"]


def test_sin_ingredientes_la_coincidencia_es_cero():
    r = calculate_match([], HANDI)
    assert r["match_score"] == 0 and len(r["missing_ingredients"]) == 5


def test_todo_cubierto_da_cien():
    assert calculate_match(["chicken", "rice", "onion", "garlic", "yogurt"], HANDI)["match_score"] == 100


def test_receta_sin_ingredientes_no_divide_por_cero():
    assert calculate_match(["pollo"], [])["match_score"] == 0


def test_ingredientes_repetidos_en_la_receta_cuentan_una_vez():
    receta = HANDI + [{"ingredient": "Garlic", "measure": "1 clove"}]
    assert calculate_match(["ajo"], receta)["match_score"] == 20  # 1 de 5


@pytest.mark.parametrize(
    "despensa, receta, coincide",
    [
        ("chicken", "chicken breast", True),
        ("chicken breast", "chicken", True),
        ("tomatoes", "tomato", True),
        ("rice", "tomato", False),
        ("oil", "olive oil", True),
    ],
)
def test_ingredient_matches(despensa, receta, coincide):
    assert ingredient_matches(despensa, receta) is coincide


def test_traduccion_y_categoria():
    assert to_english("Pollo") == "chicken"
    assert to_english("Tomates") == "tomatoes"  # singular/plural
    assert to_english("chicken") == "chicken"  # lo desconocido se deja tal cual
    assert to_spanish("garlic") == "ajo"
    assert guess_category("Pollo") == "carne"
    assert guess_category("algo raro") == ""


def test_el_agua_no_cuenta_como_ingrediente():
    receta = [{"ingredient": "Water", "measure": "1 cup"}, {"ingredient": "rice", "measure": "1 cup"}]
    r = calculate_match(["arroz"], receta)
    assert r["match_score"] == 100 and r["missing_ingredients"] == []
