import pytest

from recipes.models import Ingredient
from recipes.normalization import normalize_name


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("Tomate Cherry", "tomate cherry"),
        ("  Jamón   Serrano ", "jamon serrano"),
        ("PIMIENTO", "pimiento"),
        ("Caña de azúcar", "caña de azucar"),  # la ñ es otra letra, no una tilde
        ("", ""),
    ],
)
def test_normalizacion(entrada, esperado):
    assert normalize_name(entrada) == esperado


def test_el_modelo_normaliza_al_guardar(user):
    ingrediente = Ingredient.objects.create(user=user, name="Tomate Cherry")
    assert ingrediente.normalized_name == "tomate cherry"


def test_crear_ingrediente_adivina_la_categoria(client):
    r = client.post("/api/ingredients/", {"name": "Pollo"}, format="json")
    assert r.status_code == 201
    assert r.json()["category"] == "carne"
    assert r.json()["in_pantry"] is True


def test_una_categoria_enviada_manda_sobre_la_adivinada(client):
    r = client.post("/api/ingredients/", {"name": "Pollo", "category": "otro"}, format="json")
    assert r.json()["category"] == "otro"


def test_no_se_repiten_ingredientes_aunque_cambien_tildes_o_mayusculas(client):
    client.post("/api/ingredients/", {"name": "Jamón"}, format="json")
    r = client.post("/api/ingredients/", {"name": " JAMON "}, format="json")
    assert r.status_code == 400
    assert "despensa" in str(r.json()["name"])


def test_dos_usuarios_pueden_tener_el_mismo_ingrediente(client, other_client):
    assert client.post("/api/ingredients/", {"name": "Arroz"}, format="json").status_code == 201
    assert other_client.post("/api/ingredients/", {"name": "Arroz"}, format="json").status_code == 201


def test_cada_usuario_solo_ve_sus_ingredientes(client, other_client, other_user):
    Ingredient.objects.create(user=other_user, name="Secreto")
    client.post("/api/ingredients/", {"name": "Mío"}, format="json")
    nombres = [i["name"] for i in client.get("/api/ingredients/").json()]
    assert nombres == ["Mío"]


def test_no_se_puede_modificar_ni_borrar_lo_de_otro_usuario(client, other_user):
    ajeno = Ingredient.objects.create(user=other_user, name="Ajeno")
    assert client.patch(f"/api/ingredients/{ajeno.id}/", {"quantity": "9"}, format="json").status_code == 404
    assert client.delete(f"/api/ingredients/{ajeno.id}/").status_code == 404
    assert Ingredient.objects.filter(id=ajeno.id).exists()


def test_editar_cantidad_y_borrar(client):
    creado = client.post("/api/ingredients/", {"name": "Harina"}, format="json").json()
    r = client.patch(f"/api/ingredients/{creado['id']}/", {"quantity": "1 kg"}, format="json")
    assert r.status_code == 200 and r.json()["quantity"] == "1 kg"
    assert client.delete(f"/api/ingredients/{creado['id']}/").status_code == 204


def test_nombre_vacio_se_rechaza(client):
    assert client.post("/api/ingredients/", {"name": "   "}, format="json").status_code == 400
