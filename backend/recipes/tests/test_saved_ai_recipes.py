import json

import pytest
import requests

from recipes.models import FavoriteRecipe, RecipeCache
from recipes.tests.conftest import FakeResponse

RECETA = {
    "title": "Tortilla de patatas",
    "description": "Clásico de la cocina española",
    "meal_type": "Comida",
    "servings": 4,
    "estimated_minutes": 45,
    "difficulty": "Fácil",
    "ingredients": [{"name": "huevos", "quantity": "6"}, {"name": "patatas", "quantity": "600 g"}, {"name": "cebolla", "quantity": "1"}],
    "steps": ["Pela las patatas", "Fríelas", "Cuaja la tortilla"],
    "image": {"url": "https://upload.wikimedia.org/t.jpg", "credit": "Wikipedia", "page": "https://es.wikipedia.org/wiki/Tortilla_de_patatas"},
}


def guardar(client, receta=RECETA, **extra):
    return client.post("/api/favorites/?lang=es", {"recipe": receta, **extra}, format="json")


def test_guardar_una_receta_de_la_ia_en_el_recetario(client, user):
    r = guardar(client, notes="Para el domingo")
    assert r.status_code == 201
    receta = r.json()["recipe"]
    assert receta["source"] == "ai" and receta["external_id"].startswith(f"ai-{user.id}-")
    assert receta["title"] == "Tortilla de patatas"
    assert receta["meal_type"] == "almuerzo" and receta["difficulty"] == "fácil"  # se normalizan
    assert receta["estimated_minutes"] == 45 and receta["servings"] == 4
    assert receta["ingredients"][1] == {"ingredient": "patatas", "measure": "600 g"}
    assert receta["instructions"] == "Pela las patatas\nFríelas\nCuaja la tortilla"
    assert receta["image"] == RECETA["image"]["url"] and receta["image_credit"] == "Wikipedia"
    assert r.json()["notes"] == "Para el domingo"


def test_la_receta_guardada_no_se_traduce_ni_se_toca(client, wikipedia):
    guardar(client)
    lista = client.get("/api/favorites/", {"lang": "es"}).json()
    assert lista[0]["recipe"]["title"] == "Tortilla de patatas"
    assert "translation" not in lista[0]["recipe"]  # ya está en español


def test_no_se_guarda_dos_veces_la_misma_receta(client):
    assert guardar(client).status_code == 201
    assert guardar(client).status_code == 400
    assert FavoriteRecipe.objects.count() == 1


def test_dos_usuarios_guardan_la_misma_receta_sin_pisarse(client, other_client):
    guardar(client)
    propia = {**RECETA, "steps": ["Otros pasos distintos"]}
    assert guardar(other_client, propia).status_code == 201
    pasos = lambda c: c.get("/api/favorites/").json()[0]["recipe"]["instructions"]  # noqa: E731
    assert pasos(client) == "Pela las patatas\nFríelas\nCuaja la tortilla"
    assert pasos(other_client) == "Otros pasos distintos"


def test_el_detalle_de_una_receta_de_la_ia_solo_lo_ve_su_dueno(client, other_client):
    receta_id = guardar(client).json()["recipe"]["external_id"]
    assert client.get(f"/api/recipes/{receta_id}/").status_code == 200
    assert other_client.get(f"/api/recipes/{receta_id}/").status_code == 404
    assert client.get("/api/recipes/ai-999-inventada/").status_code == 404


def test_detalle_con_coincidencia_en_espanol(client):
    receta_id = guardar(client).json()["recipe"]["external_id"]
    d = client.get(f"/api/recipes/{receta_id}/", {"ingredients": "huevo,patata", "lang": "es"}).json()
    assert d["match"]["match_score"] == 67  # huevos y patatas de tres ingredientes
    assert d["match"]["missing_ingredients"] == ["cebolla"]
    assert d["match"]["missing"] == [{"ingredient": "cebolla", "measure": "1", "name_es": "cebolla"}]
    assert d["description"] == "Clásico de la cocina española"


def test_quitar_de_favoritos_borra_la_receta_de_la_ia(client):
    fav = guardar(client).json()
    assert client.delete(f"/api/favorites/{fav['id']}/").status_code == 204
    assert not RecipeCache.objects.filter(source="ai").exists()


def test_quitar_una_receta_de_themealdb_no_borra_la_cache_compartida(client, fake_mealdb):
    fav = client.post("/api/favorites/", {"external_id": "1"}, format="json").json()
    client.delete(f"/api/favorites/{fav['id']}/")
    assert RecipeCache.objects.filter(external_id="1").exists()


def test_borrar_la_cuenta_borra_sus_recetas_de_la_ia(client, user, other_client):
    guardar(client)
    guardar(other_client)
    assert client.delete("/api/auth/me/", {"password": "Contrasena-Segura-91"}, format="json").status_code == 204
    assert RecipeCache.objects.filter(source="ai").count() == 1  # solo queda la del otro usuario


@pytest.mark.parametrize(
    "cambio",
    [
        {"title": ""},
        {"ingredients": []},
        {"steps": []},
        {"image": {"url": "http://inseguro.example/a.jpg"}},
        {"servings": 0},
    ],
)
def test_receta_de_la_ia_invalida_da_400(client, cambio):
    assert guardar(client, {**RECETA, **cambio}).status_code == 400
    assert not RecipeCache.objects.exists()


def test_hay_que_indicar_external_id_o_recipe_pero_no_los_dos(client, fake_mealdb):
    assert client.post("/api/favorites/", {}, format="json").status_code == 400
    assert client.post("/api/favorites/", {"external_id": "1", "recipe": RECETA}, format="json").status_code == 400


def test_se_puede_guardar_sin_imagen(client):
    r = guardar(client, {**RECETA, "image": None})
    assert r.status_code == 201 and r.json()["recipe"]["image"] == ""


# --- Buscar con la IA una receta concreta ---


def test_buscar_con_la_ia_una_receta_concreta_sin_ingredientes(client, fake_ai, monkeypatch):
    capturado = {}

    def post(self, url, json=None, **kw):
        capturado["prompt"] = json["messages"][1]["content"]
        return FakeResponse({"choices": [{"message": {"content": "{\"suggestions\": [{\"title\": \"Lasaña boloñesa\"}]}"}}]})

    monkeypatch.setattr(requests.Session, "post", post)
    r = client.post("/api/ai/suggestions/", {"query": "lasaña"}, format="json")
    assert r.status_code == 200 and r.json()["suggestions"][0]["title"] == "Lasaña boloñesa"
    assert "«lasaña»" in capturado["prompt"] and "Ingredientes disponibles" not in capturado["prompt"]


def test_buscar_una_receta_con_ingredientes_como_ayuda(client, fake_ai, monkeypatch):
    capturado = {}

    def post(self, url, json=None, **kw):
        capturado["prompt"] = json["messages"][1]["content"]
        return FakeResponse({"choices": [{"message": {"content": "{\"suggestions\": []}"}}]})

    monkeypatch.setattr(requests.Session, "post", post)
    client.post("/api/ai/suggestions/", {"query": "tarta de queso", "ingredients": ["queso", "huevo"]}, format="json")
    assert "«tarta de queso»" in capturado["prompt"] and "queso, huevo" in capturado["prompt"]


@pytest.mark.parametrize("cuerpo", [{}, {"query": "   "}, {"ingredients": []}])
def test_sin_ingredientes_ni_busqueda_da_400(client, fake_ai, cuerpo):
    assert client.post("/api/ai/suggestions/", cuerpo, format="json").status_code == 400
    assert fake_ai.calls == 0


def test_una_receta_buscada_se_guarda_sola_en_el_recetario(client, fake_ai):
    fake_ai.queue = [json.dumps({"suggestions": [{"title": "Lasaña", "meal_type": "almuerzo", "ingredients": [{"name": "pasta", "quantity": "250 g"}], "steps": ["Cuece la pasta"], "difficulty": "media", "estimated_minutes": 60}]})]
    sugerida = client.post("/api/ai/suggestions/", {"query": "lasaña"}, format="json").json()["suggestions"][0]
    assert sugerida["saved"] is True and sugerida["external_id"].startswith("ai-")
    assert guardar(client, sugerida).status_code == 400  # ya estaba guardada: no se duplica


def test_las_recetas_generadas_quedan_guardadas_para_verlas_otro_dia(client, other_client, fake_ai):
    fake_ai.queue = [json.dumps({"suggestions": [
        {"title": "Tortilla", "ingredients": [{"name": "huevos", "quantity": "4"}], "steps": [{"text": "Bate los huevos", "minutes": 2}]},
        {"title": "Sopa", "ingredients_used": ["caldo"], "steps": ["Calienta el caldo"]},
    ]})]
    r = client.post("/api/ai/suggestions/", {"query": "algo rápido"}, format="json").json()["suggestions"]
    assert [s["saved"] for s in r] == [True, True]
    guardadas = client.get("/api/favorites/").json()
    assert {g["recipe"]["title"] for g in guardadas} == {"Tortilla", "Sopa"}
    # otro día: se abre el detalle de la receta guardada; es solo de su dueño
    assert client.get(f"/api/recipes/{r[0]['external_id']}/").status_code == 200
    assert other_client.get(f"/api/recipes/{r[0]['external_id']}/").status_code == 404
    assert other_client.get("/api/favorites/").json() == []


def test_pedir_dos_veces_la_misma_receta_no_la_duplica(client, fake_ai):
    cuerpo = json.dumps({"suggestions": [{"title": "Tortilla", "ingredients": [{"name": "huevos", "quantity": "4"}], "steps": ["Bate"]}]})
    fake_ai.queue = [cuerpo, cuerpo]
    client.post("/api/ai/suggestions/", {"query": "tortilla"}, format="json")
    client.post("/api/ai/suggestions/", {"query": "tortilla"}, format="json")
    assert FavoriteRecipe.objects.count() == 1


def test_una_receta_sin_pasos_ni_ingredientes_no_se_guarda_pero_se_muestra(client, fake_ai):
    fake_ai.queue = [json.dumps({"suggestions": [{"title": "Idea vaga", "description": "algo"}]})]
    s = client.post("/api/ai/suggestions/", {"query": "idea"}, format="json").json()["suggestions"][0]
    assert s["saved"] is False and s["external_id"] is None
    assert FavoriteRecipe.objects.count() == 0


def test_una_foto_con_url_muy_larga_se_guarda_sin_romper(client, fake_ai):
    url = "https://thumb.wikimedia.org/wikipedia/commons/thumb/" + "a" * 330 + ".jpg"
    receta = {**RECETA, "image": {"url": url, "credit": "Wikimedia Commons", "page": "https://commons.wikimedia.org/x"}}
    r = guardar(client, receta)
    assert r.status_code == 201 and r.json()["recipe"]["image"] == url


def test_si_guardar_falla_la_receta_se_muestra_igual(client, fake_ai, monkeypatch):
    from django.db import DataError

    def falla(*a, **kw):
        raise DataError("value too long")

    monkeypatch.setattr("recipes.services.recipes.save_ai_recipe", falla)
    fake_ai.queue = [json.dumps({"suggestions": [{"title": "Tortilla", "ingredients": [{"name": "huevos", "quantity": "4"}], "steps": ["Bate"]}]})]
    r = client.post("/api/ai/suggestions/", {"query": "tortilla"}, format="json")
    assert r.status_code == 200
    s = r.json()["suggestions"][0]
    assert s["title"] == "Tortilla" and s["saved"] is False and s["external_id"] is None
