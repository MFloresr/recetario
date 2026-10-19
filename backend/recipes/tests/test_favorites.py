from recipes.models import FavoriteRecipe, RecipeCache


def test_guardar_favorito_guarda_tambien_la_receta(client, fake_mealdb):
    r = client.post("/api/favorites/", {"external_id": "1", "notes": "Para el domingo"}, format="json")
    assert r.status_code == 201
    assert r.json()["recipe"]["title"] == "Chicken Handi"
    assert r.json()["notes"] == "Para el domingo"
    assert RecipeCache.objects.filter(external_id="1").exists()


def test_no_se_puede_guardar_dos_veces_la_misma_receta(client, fake_mealdb):
    client.post("/api/favorites/", {"external_id": "1"}, format="json")
    r = client.post("/api/favorites/", {"external_id": "1"}, format="json")
    assert r.status_code == 400
    assert FavoriteRecipe.objects.count() == 1


def test_dos_usuarios_pueden_guardar_la_misma_receta(client, other_client, fake_mealdb):
    assert client.post("/api/favorites/", {"external_id": "1"}, format="json").status_code == 201
    assert other_client.post("/api/favorites/", {"external_id": "1"}, format="json").status_code == 201
    assert RecipeCache.objects.count() == 1


def test_receta_inexistente_da_404(client, fake_mealdb):
    assert client.post("/api/favorites/", {"external_id": "999"}, format="json").status_code == 404


def test_falta_external_id_da_400(client, fake_mealdb):
    assert client.post("/api/favorites/", {}, format="json").status_code == 400


def test_listar_solo_los_propios(client, other_client, fake_mealdb):
    client.post("/api/favorites/", {"external_id": "1"}, format="json")
    other_client.post("/api/favorites/", {"external_id": "2"}, format="json")
    titulos = [f["recipe"]["title"] for f in client.get("/api/favorites/").json()]
    assert titulos == ["Chicken Handi"]


def test_editar_notas_y_borrar(client, fake_mealdb):
    fav = client.post("/api/favorites/", {"external_id": "1"}, format="json").json()
    r = client.patch(f"/api/favorites/{fav['id']}/", {"notes": "Menos picante"}, format="json")
    assert r.status_code == 200 and r.json()["notes"] == "Menos picante"
    assert client.delete(f"/api/favorites/{fav['id']}/").status_code == 204
    assert client.get("/api/favorites/").json() == []


def test_no_se_toca_el_favorito_de_otro(client, other_client, fake_mealdb):
    fav = other_client.post("/api/favorites/", {"external_id": "1"}, format="json").json()
    assert client.patch(f"/api/favorites/{fav['id']}/", {"notes": "x"}, format="json").status_code == 404
    assert client.delete(f"/api/favorites/{fav['id']}/").status_code == 404


def test_error_de_themealdb_al_guardar_es_controlado(client, monkeypatch):
    import requests

    monkeypatch.setattr(requests.Session, "get", lambda self, url, **kw: (_ for _ in ()).throw(requests.ConnectionError()))
    r = client.post("/api/favorites/", {"external_id": "1"}, format="json")
    assert r.status_code == 502 and r.json()["code"] == "themealdb_unreachable"
