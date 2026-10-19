from recipes.models import RecipeCache


def test_detalle_normalizado_y_guardado_en_cache(client, fake_mealdb):
    r = client.get("/api/recipes/1/")
    assert r.status_code == 200
    datos = r.json()
    assert datos["title"] == "Chicken Handi" and datos["area"] == "Indian"
    assert datos["ingredients"][0] == {"ingredient": "chicken", "measure": "500g"}
    assert "match" not in datos
    assert RecipeCache.objects.get(external_id="1").title == "Chicken Handi"


def test_la_segunda_peticion_sale_de_la_cache(client, fake_mealdb):
    client.get("/api/recipes/1/")
    antes = len(fake_mealdb.calls)
    client.get("/api/recipes/1/")
    assert len(fake_mealdb.calls) == antes


def test_con_ingredientes_incluye_la_coincidencia_y_los_faltantes_en_espanol(client, fake_mealdb):
    datos = client.get("/api/recipes/1/", {"ingredients": "pollo,arroz,ajo,cebolla"}).json()
    assert datos["match"]["match_score"] == 80
    assert datos["match"]["missing"] == [{"ingredient": "yogurt", "measure": "100g", "name_es": "yogur"}]


def test_receta_inexistente_da_404(client, fake_mealdb):
    r = client.get("/api/recipes/999/")
    assert r.status_code == 404
    assert not RecipeCache.objects.exists()


def test_buscar_no_guarda_recetas_en_la_base_de_datos(client, fake_mealdb):
    client.get("/api/recipes/suggestions/", {"ingredients": "pollo"})
    assert not RecipeCache.objects.exists()  # solo se guardan al abrir el detalle o marcar favorita
