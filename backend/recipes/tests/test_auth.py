import pytest
from rest_framework.test import APIClient

REGISTRO = {"email": "nuevo@example.com", "username": "nuevo", "password": "Contrasena-Segura-77"}


@pytest.fixture
def anon():
    return APIClient()


def test_registro_crea_el_usuario_sin_devolver_la_contrasena(anon, db):
    r = anon.post("/api/auth/register/", REGISTRO, format="json")
    assert r.status_code == 201
    assert r.json()["email"] == "nuevo@example.com"
    assert "password" not in r.json()


def test_registro_rechaza_correo_repetido_sin_distinguir_mayusculas(anon, user):
    r = anon.post("/api/auth/register/", {**REGISTRO, "email": "ANA@example.com"}, format="json")
    assert r.status_code == 400
    assert "email" in r.json()


def test_registro_rechaza_usuario_repetido(anon, user):
    r = anon.post("/api/auth/register/", {**REGISTRO, "username": "Ana"}, format="json")
    assert r.status_code == 400
    assert "username" in r.json()


@pytest.mark.parametrize("password", ["corta1", "12345678", "password"])
def test_registro_valida_la_contrasena(anon, db, password):
    r = anon.post("/api/auth/register/", {**REGISTRO, "password": password}, format="json")
    assert r.status_code == 400


def test_login_con_usuario_y_con_correo(anon, user):
    por_usuario = anon.post("/api/auth/login/", {"username": "ana", "password": "Contrasena-Segura-91"}, format="json")
    por_correo = anon.post("/api/auth/login/", {"email": "ANA@example.com", "password": "Contrasena-Segura-91"}, format="json")
    for r in (por_usuario, por_correo):
        assert r.status_code == 200
        assert {"access", "refresh"} <= set(r.json())


def test_login_con_contrasena_incorrecta_da_401(anon, user):
    r = anon.post("/api/auth/login/", {"username": "ana", "password": "mala"}, format="json")
    assert r.status_code == 401


def test_login_sin_identificador_da_400(anon, user):
    r = anon.post("/api/auth/login/", {"password": "Contrasena-Segura-91"}, format="json")
    assert r.status_code == 400


def test_me_devuelve_el_usuario_actual(anon, user):
    tokens = anon.post("/api/auth/login/", {"username": "ana", "password": "Contrasena-Segura-91"}, format="json").json()
    anon.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    r = anon.get("/api/auth/me/")
    assert r.status_code == 200
    assert r.json()["username"] == "ana"


def test_refresh_devuelve_un_acceso_nuevo(anon, user):
    tokens = anon.post("/api/auth/login/", {"username": "ana", "password": "Contrasena-Segura-91"}, format="json").json()
    r = anon.post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert r.status_code == 200
    assert "access" in r.json()


@pytest.mark.parametrize(
    "ruta",
    ["/api/auth/me/", "/api/ingredients/", "/api/shopping-list/", "/api/favorites/", "/api/recipes/suggestions/?ingredients=pollo", "/api/recipes/1/"],
)
def test_las_rutas_privadas_exigen_token(anon, db, ruta):
    assert anon.get(ruta).status_code == 401


@pytest.mark.parametrize("ruta", ["/api/ai/suggestions/", "/api/ai/adapt-recipe/", "/api/ai/shopping-list/"])
def test_las_rutas_de_ia_exigen_token(anon, db, ruta):
    assert anon.post(ruta, {}, format="json").status_code == 401


def test_el_registro_tiene_limite_por_hora(anon, db):
    for n in range(20):
        r = anon.post("/api/auth/register/", {"email": f"u{n}@example.com", "username": f"u{n}", "password": "Contrasena-Segura-77"}, format="json")
        assert r.status_code == 201
    r = anon.post("/api/auth/register/", {"email": "otro@example.com", "username": "otro", "password": "Contrasena-Segura-77"}, format="json")
    assert r.status_code == 429


# --- Borrar la cuenta ---


def test_borrar_cuenta_elimina_al_usuario_y_todos_sus_datos(client, user, other_user, fake_mealdb):
    from django.contrib.auth import get_user_model

    from recipes.models import FavoriteRecipe, Ingredient, RecipeCache, ShoppingListItem

    client.post("/api/ingredients/", {"name": "Arroz"}, format="json")
    client.post("/api/shopping-list/", {"name": "Leche"}, format="json")
    client.post("/api/favorites/", {"external_id": "1"}, format="json")
    Ingredient.objects.create(user=other_user, name="Ajeno")

    r = client.delete("/api/auth/me/", {"password": "Contrasena-Segura-91"}, format="json")
    assert r.status_code == 204
    assert not get_user_model().objects.filter(pk=user.pk).exists()
    assert not Ingredient.objects.filter(user_id=user.pk).exists()
    assert not ShoppingListItem.objects.filter(user_id=user.pk).exists()
    assert not FavoriteRecipe.objects.filter(user_id=user.pk).exists()
    # lo de otras personas y la caché compartida de recetas no se tocan
    assert Ingredient.objects.filter(user=other_user, name="Ajeno").exists()
    assert RecipeCache.objects.filter(external_id="1").exists()


def test_borrar_cuenta_exige_la_contrasena_correcta(client, user):
    r = client.delete("/api/auth/me/", {"password": "otra-cosa"}, format="json")
    assert r.status_code == 400 and "password" in r.json()
    assert client.delete("/api/auth/me/", {}, format="json").status_code == 400
    assert client.get("/api/auth/me/").status_code == 200  # sigue existiendo


def test_borrar_cuenta_exige_sesion(anon, user):
    assert anon.delete("/api/auth/me/", {"password": "Contrasena-Segura-91"}, format="json").status_code == 401


def test_tras_borrar_la_cuenta_el_token_deja_de_valer(anon, user):
    tokens = anon.post("/api/auth/login/", {"username": "ana", "password": "Contrasena-Segura-91"}, format="json").json()
    anon.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert anon.delete("/api/auth/me/", {"password": "Contrasena-Segura-91"}, format="json").status_code == 204
    assert anon.get("/api/auth/me/").status_code == 401
    anon.credentials()
    assert anon.post("/api/auth/login/", {"username": "ana", "password": "Contrasena-Segura-91"}, format="json").status_code == 401
