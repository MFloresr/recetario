import json

import pytest

from recipes.models import RecipeCache, TranslationCache
from recipes.services.translation import _pieces, translate_strings
from recipes.spanish import area_es, category_es, ingredient_known_es, measure_es


# --- Tablas y reglas (sin traductor) ---


def test_categorias_y_paises():
    assert category_es("Chicken") == "Pollo"
    assert category_es("Algo nuevo") == "Algo nuevo"  # lo desconocido se deja igual
    assert area_es("Spanish") == "Española"


@pytest.mark.parametrize(
    "ingles, espanol",
    [("Chicken", "pollo"), ("olive oil", "aceite de oliva"), ("Garlic Cloves", "dientes de ajo"), ("sriracha", None)],
)
def test_ingredientes_conocidos(ingles, espanol):
    assert ingredient_known_es(ingles) == espanol


@pytest.mark.parametrize(
    "ingles, espanol",
    [
        ("1 tblsp", "1 cda."),
        ("2 Tablespoons", "2 cda."),
        ("1/2 teaspoon", "1/2 cdta."),
        ("1 cup", "1 taza"),
        ("1 Large Chopped", "1 grande picado"),
        ("500g", "500g"),
        ("Pinch", "pizca"),
        ("To taste", "al gusto"),
        ("", ""),
    ],
)
def test_medidas(ingles, espanol):
    assert measure_es(ingles) == espanol


def test_textos_largos_se_parten_por_frases():
    largo = " ".join(f"Esto es la frase número {n} de la receta." for n in range(30))
    trozos = _pieces(largo, limite=100)
    assert all(len(t) <= 100 for t in trozos) and len(trozos) > 1
    assert " ".join(trozos) == largo


# --- Servicio de traducción con caché ---


def test_traduce_y_guarda_en_cache(db, fake_mealdb):
    r = translate_strings(["Chicken Handi", "Cook it."])
    assert r == {"Chicken Handi": "ES(Chicken Handi)", "Cook it.": "ES(Cook it.)"}
    assert TranslationCache.objects.count() == 2
    llamadas = len(fake_mealdb.translation_calls)
    translate_strings(["Chicken Handi", "Cook it."])  # la segunda vez sale de la caché
    assert len(fake_mealdb.translation_calls) == llamadas


def test_ignora_vacios_y_repetidos(db, fake_mealdb):
    r = translate_strings(["", "  ", "Rice", "Rice"])
    assert r == {"Rice": "ES(Rice)"}
    assert len(fake_mealdb.translation_calls) == 1


def test_el_cupo_agotado_no_rompe_nada_ni_se_cachea(db, fake_mealdb):
    fake_mealdb.translator_mode = "quota"
    assert translate_strings(["Rice"]) == {}
    assert TranslationCache.objects.count() == 0


def test_si_el_traductor_no_responde_devuelve_vacio(db, fake_mealdb):
    fake_mealdb.translator_mode = "down"
    assert translate_strings(["Rice"]) == {}


def test_traduccion_con_ia_si_hay_clave(db, fake_ai):
    fake_ai.queue = [json.dumps({"translations": ["Arroz", "Cocínalo."]})]
    assert translate_strings(["Rice", "Cook it."]) == {"Rice": "Arroz", "Cook it.": "Cocínalo."}
    assert fake_ai.calls == 1


def test_ia_con_lista_de_distinta_longitud_no_se_acepta(db, fake_ai):
    fake_ai.queue = [json.dumps({"translations": ["solo una"]})] * 2
    assert translate_strings(["Rice", "Cook it."]) == {}
    assert TranslationCache.objects.count() == 0


def test_proveedor_none_no_traduce(db, settings, fake_mealdb):
    settings.TRANSLATION_PROVIDER = "none"
    assert translate_strings(["Rice"]) == {}
    assert fake_mealdb.translation_calls == []


# --- Endpoints con ?lang=es ---


def test_sugerencias_en_espanol(client, fake_mealdb):
    r = client.get("/api/recipes/suggestions/", {"ingredients": "pollo,arroz,ajo,cebolla", "lang": "es"})
    assert r.status_code == 200
    handi = next(x for x in r.json()["results"] if x["external_id"] == "1")
    assert handi["title"] == "ES(Chicken Handi)" and handi["original_title"] == "Chicken Handi"
    assert handi["category"] == "Pollo" and handi["area"] == "India"
    assert handi["matched_ingredients"] == ["pollo", "arroz", "cebolla", "ajo"]
    assert handi["missing_ingredients"] == ["yogur"]
    assert handi["match_score"] == 80  # el cálculo no cambia con el idioma


def test_sin_lang_todo_sigue_en_ingles(client, fake_mealdb):
    r = client.get("/api/recipes/suggestions/", {"ingredients": "pollo"})
    assert r.json()["results"][0]["title"] in {"Chicken Handi", "Garlic Rice", "Beef Stew"}
    assert fake_mealdb.translation_calls == []


def test_idioma_no_soportado_da_400(client, fake_mealdb):
    assert client.get("/api/recipes/suggestions/", {"ingredients": "pollo", "lang": "fr"}).status_code == 400


def test_la_busqueda_por_nombre_en_espanol_se_traduce_al_ingles(client, fake_mealdb):
    r = client.get("/api/recipes/suggestions/", {"search": "pollo", "lang": "es"})
    assert ("search.php", {"s": "chicken"}) in fake_mealdb.calls
    assert [x["original_title"] for x in r.json()["results"]] == ["Chicken Handi"]


def test_detalle_en_espanol(client, fake_mealdb):
    d = client.get("/api/recipes/1/", {"ingredients": "pollo,arroz", "lang": "es"}).json()
    assert d["title"] == "ES(Chicken Handi)"
    assert d["category"] == "Pollo" and d["area"] == "India"
    assert d["ingredients"][0] == {"ingredient": "pollo", "measure": "500g"}
    assert d["ingredients"][3] == {"ingredient": "ajo", "measure": "2 diente(s)"}
    assert d["instructions"] == "ES(Cook it.)"
    assert d["translation"] == {"lang": "es", "provider": "mymemory", "complete": True}
    assert d["match"]["missing"][0]["name_es"] == "cebolla"
    assert "yogur" in d["match"]["missing_ingredients"]


def test_el_detalle_traducido_no_altera_la_receta_guardada(client, fake_mealdb):
    client.get("/api/recipes/1/", {"lang": "es"})
    guardada = RecipeCache.objects.get(external_id="1")
    assert guardada.title == "Chicken Handi" and guardada.instructions == "Cook it."


def test_los_rotulos_step_no_se_traducen(client, fake_mealdb, monkeypatch):
    import recipes.tests.conftest as c

    monkeypatch.setitem(c.MEALS["2"], "strInstructions", "STEP 1\nFry the rice.\nSTEP 2\nServe.")
    d = client.get("/api/recipes/2/", {"lang": "es"}).json()
    assert d["instructions"] == "ES(Fry the rice.)\nES(Serve.)"


def test_si_el_traductor_falla_el_detalle_sale_en_ingles_con_las_tablas(client, fake_mealdb):
    fake_mealdb.translator_mode = "quota"
    r = client.get("/api/recipes/1/", {"lang": "es"})
    assert r.status_code == 200
    d = r.json()
    assert d["title"] == "Chicken Handi"  # sin traductor se queda el título original
    assert d["category"] == "Pollo"  # pero las tablas siguen funcionando
    assert d["ingredients"][0]["ingredient"] == "pollo"
    assert d["translation"]["complete"] is False


def test_favoritos_en_espanol(client, fake_mealdb):
    client.post("/api/favorites/", {"external_id": "1"}, format="json")
    en = client.get("/api/favorites/").json()[0]["recipe"]
    es = client.get("/api/favorites/", {"lang": "es"}).json()[0]["recipe"]
    assert en["title"] == "Chicken Handi" and es["title"] == "ES(Chicken Handi)"
    assert es["category"] == "Pollo"


def test_crear_favorito_con_lang_devuelve_la_receta_traducida(client, fake_mealdb):
    r = client.post("/api/favorites/?lang=es", {"external_id": "2"}, format="json")
    assert r.status_code == 201 and r.json()["recipe"]["title"] == "ES(Garlic Rice)"


def test_las_recetas_de_themealdb_llevan_tipo_de_comida(client, fake_mealdb):
    r = client.get("/api/recipes/suggestions/", {"ingredients": "pollo,arroz,ajo", "lang": "es"})
    tipos = {x["original_title"]: x["meal_type"] for x in r.json()["results"]}
    assert tipos["Chicken Handi"] == "plato principal"
    assert tipos["Garlic Rice"] == "guarnición"  # categoría «Side»
    assert client.get("/api/recipes/1/", {"lang": "es"}).json()["meal_type"] == "plato principal"
