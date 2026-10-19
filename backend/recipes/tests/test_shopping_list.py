from recipes.models import ShoppingListItem


def test_crear_y_listar(client):
    r = client.post("/api/shopping-list/", {"name": "Leche", "quantity": "2 l"}, format="json")
    assert r.status_code == 201
    assert r.json()["category"] == "lacteo"
    assert [i["name"] for i in client.get("/api/shopping-list/").json()] == ["Leche"]


def test_no_duplica_un_producto_pendiente_y_actualiza_la_cantidad(client):
    client.post("/api/shopping-list/", {"name": "Leche", "quantity": "1 l"}, format="json")
    r = client.post("/api/shopping-list/", {"name": "leche", "quantity": "3 l"}, format="json")
    assert r.status_code == 200
    items = client.get("/api/shopping-list/").json()
    assert len(items) == 1 and items[0]["quantity"] == "3 l"


def test_un_producto_ya_comprado_se_puede_volver_a_añadir(client):
    creado = client.post("/api/shopping-list/", {"name": "Pan"}, format="json").json()
    client.patch(f"/api/shopping-list/{creado['id']}/", {"bought": True}, format="json")
    assert client.post("/api/shopping-list/", {"name": "Pan"}, format="json").status_code == 201


def test_marcar_comprado_y_limpiar_comprados(client):
    a = client.post("/api/shopping-list/", {"name": "Pan"}, format="json").json()
    client.post("/api/shopping-list/", {"name": "Sal"}, format="json")
    client.patch(f"/api/shopping-list/{a['id']}/", {"bought": True}, format="json")
    r = client.post("/api/shopping-list/clear-bought/")
    assert r.status_code == 200 and r.json() == {"deleted": 1}
    assert [i["name"] for i in client.get("/api/shopping-list/").json()] == ["Sal"]


def test_aislamiento_entre_usuarios(client, other_client, other_user):
    ajeno = ShoppingListItem.objects.create(user=other_user, name="Ajeno", bought=True)
    assert client.get("/api/shopping-list/").json() == []
    assert client.patch(f"/api/shopping-list/{ajeno.id}/", {"bought": False}, format="json").status_code == 404
    assert client.delete(f"/api/shopping-list/{ajeno.id}/").status_code == 404
    client.post("/api/shopping-list/clear-bought/")
    assert ShoppingListItem.objects.filter(id=ajeno.id).exists()  # limpiar comprados no toca lo de otros


def test_borrar_un_producto(client):
    creado = client.post("/api/shopping-list/", {"name": "Sal"}, format="json").json()
    assert client.delete(f"/api/shopping-list/{creado['id']}/").status_code == 204
