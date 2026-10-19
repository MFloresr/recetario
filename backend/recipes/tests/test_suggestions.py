import requests

URL = "/api/recipes/suggestions/"


def test_sugerencias_ordenadas_por_coincidencia(client, fake_mealdb):
    r = client.get(URL, {"ingredients": "pollo,arroz,ajo,cebolla"})
    assert r.status_code == 200
    datos = r.json()
    assert datos["count"] == len(datos["results"]) == 3
    # Garlic Rice (2 de 2 = 100 %) gana a Chicken Handi (4 de 5 = 80 %) y a Beef Stew (1 de 4 = 25 %)
    assert [x["title"] for x in datos["results"]] == ["Garlic Rice", "Chicken Handi", "Beef Stew"]
    handi = datos["results"][1]
    assert handi["match_score"] == 80
    assert handi["matched_ingredients"] == ["chicken", "rice", "onion", "garlic"]
    assert handi["missing_ingredients"] == ["yogurt"]
    assert handi["source"] == "themealdb" and handi["category"] == "Chicken" and handi["area"] == "Indian"
    puntuaciones = [x["match_score"] for x in datos["results"]]
    assert puntuaciones == sorted(puntuaciones, reverse=True)


def test_sin_duplicados_aunque_varios_ingredientes_devuelvan_la_misma_receta(client, fake_mealdb):
    ids = [x["external_id"] for x in client.get(URL, {"ingredients": "pollo,arroz,ajo,cebolla"}).json()["results"]]
    assert len(ids) == len(set(ids))


def test_entiende_nombres_en_ingles_y_con_tildes_o_mayusculas(client, fake_mealdb):
    r = client.get(URL, {"ingredients": " Chicken , ARROZ "})
    assert {x["title"] for x in r.json()["results"]} >= {"Chicken Handi"}


def test_filtro_max_missing(client, fake_mealdb):
    r = client.get(URL, {"ingredients": "pollo,arroz,ajo,cebolla", "max_missing": 0})
    assert [x["title"] for x in r.json()["results"]] == ["Garlic Rice"]


def test_filtro_por_categoria(client, fake_mealdb):
    r = client.get(URL, {"ingredients": "pollo,arroz,ajo,cebolla", "category": "chicken"})
    assert [x["title"] for x in r.json()["results"]] == ["Chicken Handi"]


def test_filtro_por_nombre(client, fake_mealdb):
    r = client.get(URL, {"ingredients": "pollo,arroz,ajo,cebolla", "search": "garlic"})
    assert [x["title"] for x in r.json()["results"]] == ["Garlic Rice"]


def test_solo_busqueda_por_nombre(client, fake_mealdb):
    r = client.get(URL, {"search": "beef"})
    assert r.status_code == 200
    assert [x["title"] for x in r.json()["results"]] == ["Beef Stew"]


def test_exige_ingredientes_o_busqueda(client, fake_mealdb):
    assert client.get(URL).status_code == 400
    assert client.get(URL, {"ingredients": " , ,"}).status_code == 400


def test_sin_coincidencias_devuelve_lista_vacia(client, fake_mealdb):
    r = client.get(URL, {"ingredients": "unicornio"})
    assert r.status_code == 200 and r.json() == {"count": 0, "results": []}


def test_ingredientes_validos_con_max_missing_negativo_dan_400(client, fake_mealdb):
    assert client.get(URL, {"ingredients": "pollo", "max_missing": -1}).status_code == 400


def test_maximo_20_resultados(client, monkeypatch):
    import recipes.tests.conftest as c

    for n in range(10, 40):
        c.MEALS[str(n)] = {"idMeal": str(n), "strMeal": f"Plato {n:02d}", "strCategory": "Misc", "strArea": "X", "strMealThumb": "u",
                           "strInstructions": "", "ingredients": [("rice", "1")]}
    falso = c.FakeMealDB()
    monkeypatch.setattr(requests.Session, "get", lambda self, url, **kw: falso.get(url, **kw))
    try:
        assert len(client.get(URL, {"ingredients": "arroz"}).json()["results"]) == 20
    finally:
        for n in range(10, 40):
            c.MEALS.pop(str(n), None)


def test_si_themealdb_falla_el_error_es_controlado(client, monkeypatch):
    monkeypatch.setattr(requests.Session, "get", lambda self, url, **kw: (_ for _ in ()).throw(requests.Timeout()))
    r = client.get(URL, {"ingredients": "pollo"})
    assert r.status_code == 504
    assert r.json() == {"detail": "TheMealDB tardó demasiado en responder. Inténtalo de nuevo en unos segundos.", "code": "themealdb_timeout"}


def test_si_themealdb_responde_basura_el_error_es_controlado(client, monkeypatch):
    from recipes.tests.conftest import FakeResponse

    monkeypatch.setattr(requests.Session, "get", lambda self, url, **kw: FakeResponse(text="no es json"))
    r = client.get(URL, {"ingredients": "pollo"})
    assert r.status_code == 502 and r.json()["code"] == "themealdb_invalid_json"


def test_los_hilos_no_abren_conexiones_a_la_base_de_datos(client, fake_mealdb, monkeypatch, wikipedia):
    """Cada hilo con su conexión agotaría el pooler de Supabase (15 clientes en modo sesión): solo el principal."""
    import threading

    from django.db.backends.base.base import BaseDatabaseWrapper

    original = BaseDatabaseWrapper.ensure_connection

    def solo_principal(self):
        assert threading.current_thread() is threading.main_thread(), "un hilo secundario abrió una conexión a la base de datos"
        return original(self)

    monkeypatch.setattr(BaseDatabaseWrapper, "ensure_connection", solo_principal)
    r = client.get(URL, {"ingredients": "pollo,arroz,ajo,cebolla", "lang": "es"})
    assert r.status_code == 200 and r.json()["count"] == 3
    # la búsqueda con IA también usa hilos (fotos): tampoco pueden tocar la base de datos
    client.get("/api/recipes/1/", {"lang": "es"})
