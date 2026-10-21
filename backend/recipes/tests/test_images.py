import pytest

from recipes.services.images import FOTOS_RESPALDO, _is_same_dish, attach_images, find_dish_image


def pagina(titulo, miniatura="https://upload.wikimedia.org/x.jpg", index=1):
    return {"title": titulo, "thumbnail": {"source": miniatura}, "fullurl": f"https://es.wikipedia.org/wiki/{titulo}", "index": index}


@pytest.mark.parametrize(
    "plato, articulo, coincide",
    [
        ("Tortilla de patatas", "Tortilla de patatas", True),
        ("Arroz con pollo y verduras", "Arroz con pollo", True),  # el artículo es parte del nombre del plato
        ("Paella", "Paella valenciana", False),  # artículo más concreto = otro plato
        ("Tarta de queso", "Tarta de queso japonesa", False),
        ("Pollo al curry", "Arroz", False),
        ("Ensalada fresca de la casa", "Ensalada", False),  # artículo demasiado genérico
        ("Pollo al curry", "Pollo", False),
        ("Gazpacho", "Gazpacho", True),
        ("Ensalada César", "Ensalada César", True),
        ("", "Paella", False),
    ],
)
def test_mismo_plato(plato, articulo, coincide):
    assert _is_same_dish(plato, articulo) is coincide


def test_devuelve_la_foto_del_articulo_que_coincide(wikipedia):
    wikipedia.pages = [pagina("Tortilla de patatas")]
    foto = find_dish_image("Tortilla de patatas")
    assert foto == {"url": "https://upload.wikimedia.org/x.jpg", "credit": "Wikipedia", "page": "https://es.wikipedia.org/wiki/Tortilla de patatas"}


def test_no_pone_foto_si_el_articulo_es_otro_plato(wikipedia):
    wikipedia.pages = [pagina("Arroz")]
    assert find_dish_image("Pollo al curry") is None


def test_prefiere_el_resultado_mejor_posicionado_que_coincide(wikipedia):
    wikipedia.pages = [pagina("Sopa", "https://img/sopa.jpg", index=1), pagina("Sopa de ajo", "https://img/ajo.jpg", index=2)]
    assert find_dish_image("Sopa de ajo")["url"] == "https://img/ajo.jpg"


def test_articulo_sin_miniatura_no_vale(wikipedia):
    wikipedia.pages = [{"title": "Paella", "fullurl": "x", "index": 1}]
    assert find_dish_image("Paella") is None


def test_un_fallo_de_red_devuelve_none_y_no_se_cachea(wikipedia):
    wikipedia.fail = True
    assert find_dish_image("Paella") is None
    wikipedia.fail = False
    wikipedia.pages = [pagina("Paella")]
    assert find_dish_image("Paella") is not None  # se reintenta: el fallo no quedó guardado


def test_la_busqueda_se_cachea(wikipedia):
    wikipedia.pages = [pagina("Paella")]
    find_dish_image("Paella")
    find_dish_image("paella")
    assert len(wikipedia.calls) == 1


def test_adjuntar_fotos_a_las_sugerencias(wikipedia):
    wikipedia.pages = [pagina("Paella")]
    r = attach_images([{"title": "Paella"}, {"title": "Plato inventado sin artículo"}])
    assert r[0]["image"]["credit"] == "Wikipedia"
    assert r[1]["image"] == FOTOS_RESPALDO["otro"]  # sin foto fiable, la de respaldo: toda receta tiene foto
    assert attach_images([]) == []


def test_la_foto_de_respaldo_es_la_del_tipo_de_comida(wikipedia):
    r = attach_images([{"title": "Plato inventado", "meal_type": "postre"}, {"title": "Otro inventado", "meal_type": "Plato principal"}])
    assert r[0]["image"] == FOTOS_RESPALDO["postre"]
    assert r[1]["image"] == FOTOS_RESPALDO["plato principal"]
