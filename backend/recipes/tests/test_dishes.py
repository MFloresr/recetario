import pytest
from django.core.management import call_command

from recipes.models import Dish
from recipes.services import catalog_import as ci


def plato(**kw):
    datos = {"source": "wikidata", "source_id": "Q1", "name_es": "Paella", "country": "ES"}
    return Dish.objects.create(**{**datos, **kw})


@pytest.mark.django_db
def test_lista_requiere_login():
    from rest_framework.test import APIClient

    assert APIClient().get("/api/dishes/").status_code == 401


def test_filtra_por_pais_dieta_y_comida(client):
    plato()
    plato(source_id="Q2", name_es="Gazpacho", diets=["vegano"], meal_type="entrante")
    plato(source_id="Q3", name_es="Pizza", country="IT")
    assert client.get("/api/dishes/").json()["count"] == 3
    assert [d["name_es"] for d in client.get("/api/dishes/?country=es&diet=vegano").json()["results"]] == ["Gazpacho"]
    assert client.get("/api/dishes/?meal=entrante").json()["count"] == 1
    assert client.get("/api/dishes/?q=pizz").json()["count"] == 1


def test_paginacion_y_limite_invalido(client):
    for n in range(3):
        plato(source_id=f"Q{n}", name_es=f"Plato {n}")
    assert len(client.get("/api/dishes/?limit=2").json()["results"]) == 2
    assert client.get("/api/dishes/?limit=abc").status_code == 400


def test_paises_con_total(client):
    plato()
    plato(source_id="Q2", name_es="Tortilla")
    plato(source_id="Q3", name_es="Pizza", country="IT")
    assert client.get("/api/dishes/countries/").json() == [{"country": "ES", "total": 2}, {"country": "IT", "total": 1}]


def test_solo_lectura(client):
    assert client.post("/api/dishes/", {"name_es": "x"}).status_code == 405


class FakeSparql:
    def __init__(self, filas):
        self.filas = filas

    def get(self, url, **kw):
        filas = self.filas

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"results": {"bindings": filas}}

        return R()


def fila(qid, nombre, img="http://commons.wikimedia.org/wiki/Special:FilePath/Paella%20valenciana.jpg"):
    return {"d": {"value": f"http://www.wikidata.org/entity/{qid}"}, "label": {"value": nombre}, "img": {"value": img}}


def test_wikidata_quita_repetidos_y_ids_sin_etiqueta():
    sesion = FakeSparql([fila("Q1", "Paella"), fila("Q1", "Paella"), fila("Q2", "Q2")])
    platos = ci.platos_wikidata("ES", session=sesion)
    assert [p["source_id"] for p in platos] == ["Q1"]
    assert platos[0]["image"] == "https://commons.wikimedia.org/wiki/Special:FilePath/Paella%20valenciana.jpg?width=640"
    assert platos[0]["image_credit"] == "Commons: Paella valenciana.jpg"


@pytest.mark.django_db
def test_cargar_catalogo_es_repetible_y_no_pisa_lo_revisado(monkeypatch):
    base = {"source": "wikidata", "source_id": "Q1", "name_es": "Paella", "country": "ES", "image": "https://x/a.jpg"}
    monkeypatch.setattr(ci, "platos_wikidata", lambda iso: [dict(base)])
    call_command("cargar_catalogo", fuente="wikidata", paises="ES")
    Dish.objects.filter(source_id="Q1").update(name_es="Paella valenciana", reviewed=True)
    call_command("cargar_catalogo", fuente="wikidata", paises="ES")
    assert Dish.objects.count() == 1
    assert Dish.objects.get().name_es == "Paella valenciana"


@pytest.mark.django_db
def test_dry_run_no_guarda(monkeypatch):
    monkeypatch.setattr(ci, "platos_wikidata", lambda iso: [{"source": "wikidata", "source_id": "Q1", "name_es": "Paella"}])
    call_command("cargar_catalogo", "--dry-run", fuente="wikidata", paises="ES")
    assert Dish.objects.count() == 0


class FakeIA:
    def enrich_dishes(self, dishes):
        return [
            {"name_es": "Pollo asado", "description": "Clásico", "meal_type": "almuerzo", "diets": ["sin gluten"],
             "calories": 450, "ingredients": [{"name": "pollo", "quantity": "1"}], "steps": ["Asar"]}
            for _ in dishes
        ]


@pytest.mark.django_db
def test_enriquecer_completa_y_deja_sin_revisar(monkeypatch):
    from recipes.management.commands import enriquecer_catalogo as cmd

    monkeypatch.setattr(cmd, "get_ai_service", lambda: FakeIA())
    plato(source="themealdb", source_id="1", name_es="Roast chicken", name_en="Roast chicken", country="GB")
    call_command("enriquecer_catalogo")
    d = Dish.objects.get()
    assert (d.name_es, d.diets, d.calories, d.enriched, d.reviewed) == ("Pollo asado", ["sin gluten"], 450, True, False)
    assert d.steps == "Asar"


def test_enrich_valida_dietas_y_tipo():
    from recipes.services.ai import EnrichOutput

    v = EnrichOutput(data={"dishes": [{"name_es": "X", "diets": ["Vegano", "keto", "vegano"], "meal_type": "marciano", "calories": 100}]})
    assert v.is_valid(), v.errors
    d = v.data["dishes"][0]
    assert d["diets"] == ["vegano"] and d["meal_type"] == ""


def plato_completo(**kw):
    datos = {
        "source_id": "Q9", "name_es": "Arroz con pollo", "enriched": True, "meal_type": "almuerzo",
        "ingredients": [{"ingredient": "arroz", "measure": "200 g"}, {"ingredient": "pollo", "measure": "1"}],
    }
    return plato(**{**datos, **kw})


def test_sugerencias_salen_del_catalogo(client, monkeypatch):
    from recipes.services import suggestions as sg

    monkeypatch.setattr(sg, "TheMealDBClient", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe llamar a TheMealDB")))
    for n in range(5):
        plato_completo(source_id=f"Q{n}", name_es=f"Arroz {n}")
    r = client.get("/api/recipes/suggestions/?ingredients=arroz&lang=es").json()
    assert r["count"] == 5
    assert r["results"][0]["source"] == "catalog" and r["results"][0]["external_id"].startswith("dish-")
    assert r["results"][0]["match_score"] == 50 and r["results"][0]["area"] == "España"


def test_sugerencias_ignoran_platos_sin_completar(client, monkeypatch):
    from recipes.views import build_suggestions  # noqa: F401
    from recipes import views

    plato(source_id="Q1", name_es="Sin receta")
    monkeypatch.setattr(views, "build_suggestions", lambda *a, **k: {"results": []})
    assert client.get("/api/recipes/suggestions/?ingredients=arroz&lang=es").json()["count"] == 0


def test_detalle_de_un_plato_del_catalogo(client):
    d = plato_completo()
    r = client.get(f"/api/recipes/dish-{d.id}/?lang=es&ingredients=arroz").json()
    assert r["title"] == "Arroz con pollo" and r["source"] == "catalog"
    assert r["match"]["matched_ingredients"] == ["arroz"]
    assert client.get("/api/recipes/dish-99999/").status_code == 404


def test_plato_sin_completar_no_tiene_detalle(client):
    d = plato()
    assert client.get(f"/api/recipes/dish-{d.id}/").status_code == 404


def test_favorito_de_un_plato_del_catalogo(client):
    d = plato_completo()
    r = client.post("/api/favorites/", {"external_id": f"dish-{d.id}"}, format="json")
    assert r.status_code == 201, r.content
    lista = client.get("/api/favorites/").json()
    assert lista[0]["recipe"]["title"] == "Arroz con pollo"
