import pytest
import requests

from recipes.exceptions import TheMealDBError
from recipes.services.themealdb import TheMealDBClient, normalize_meal
from recipes.tests.conftest import MEALS, FakeResponse, _full


def test_normalize_meal_al_formato_interno():
    receta = normalize_meal(_full(MEALS["1"]))
    assert receta["external_id"] == "1"
    assert receta["title"] == "Chicken Handi"
    assert receta["ingredients"][0] == {"ingredient": "chicken", "measure": "500g"}
    assert len(receta["ingredients"]) == 5  # los huecos vacíos de TheMealDB se descartan
    assert receta["source"] == "themealdb"


def test_cliente_busca_y_obtiene_por_id(fake_mealdb):
    cliente = TheMealDBClient(base_url="https://x")
    assert [r["title"] for r in cliente.search_by_name("rice")] == ["Garlic Rice"]
    assert cliente.get_by_id("3")["title"] == "Beef Stew"
    assert cliente.get_by_id("999") is None
    assert [r["external_id"] for r in cliente.filter_by_ingredient("garlic")] == ["1", "2"]
    assert cliente.list_categories() == ["Beef", "Chicken"]


def test_sin_resultados_devuelve_lista_vacia(fake_mealdb):
    assert TheMealDBClient(base_url="https://x").search_by_name("zzz") == []


def test_timeout_se_convierte_en_error_controlado(monkeypatch):
    def agotado(self, url, **kw):
        raise requests.Timeout()

    monkeypatch.setattr(requests.Session, "get", agotado)
    with pytest.raises(TheMealDBError) as info:
        TheMealDBClient(base_url="https://x").search_by_name("pollo")
    assert info.value.status_code == 504 and info.value.code == "themealdb_timeout"


def test_error_de_red_http_y_json_invalido(monkeypatch):
    cliente = TheMealDBClient(base_url="https://x")
    monkeypatch.setattr(requests.Session, "get", lambda self, url, **kw: (_ for _ in ()).throw(requests.ConnectionError()))
    with pytest.raises(TheMealDBError, match="conectar"):
        cliente.random()
    monkeypatch.setattr(requests.Session, "get", lambda self, url, **kw: FakeResponse({}, status_code=500))
    with pytest.raises(TheMealDBError, match="500"):
        cliente.random()
    monkeypatch.setattr(requests.Session, "get", lambda self, url, **kw: FakeResponse(text="<html>no es json"))
    with pytest.raises(TheMealDBError, match="no se pudo leer"):
        cliente.random()
