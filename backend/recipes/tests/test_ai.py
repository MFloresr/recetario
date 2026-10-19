import json

import pytest
import requests

from recipes.tests.conftest import FakeResponse

SUGERENCIAS = {
    "suggestions": [
        {
            "title": "Arroz con pollo y verduras",
            "description": "Plato sencillo de una sola olla",
            "ingredients_used": ["pollo", "arroz"],
            "missing_ingredients": ["caldo de pollo"],
            "steps": ["Sofríe", "Añade el arroz"],
            "estimated_minutes": 35,
            "difficulty": "fácil",
        }
    ]
}
ENTRADA = {"ingredients": ["pollo", "arroz", "ajo"], "max_results": 3, "diet": "", "avoid": ["lactosa"]}
RECETA = {"title": "Chicken Handi", "ingredients": [{"ingredient": "chicken", "measure": "500g"}, {"ingredient": "yogurt", "measure": "200g"}]}


def test_sin_clave_de_ia_el_error_es_controlado(client, settings):
    settings.AI_API_KEY = ""
    r = client.post("/api/ai/suggestions/", ENTRADA, format="json")
    assert r.status_code == 503 and r.json()["code"] == "ai_not_configured"


def test_proveedor_no_soportado(client, settings):
    settings.AI_API_KEY = "x"
    settings.AI_PROVIDER = "inventado"
    r = client.post("/api/ai/suggestions/", ENTRADA, format="json")
    assert r.status_code == 503 and r.json()["code"] == "ai_unsupported_provider"


def test_sugerencias_validas(client, fake_ai):
    fake_ai.queue = [json.dumps(SUGERENCIAS)]
    r = client.post("/api/ai/suggestions/", ENTRADA, format="json")
    assert r.status_code == 200
    s = r.json()["suggestions"][0]
    assert s["title"] == "Arroz con pollo y verduras" and s["estimated_minutes"] == 35 and s["difficulty"] == "fácil"
    assert fake_ai.calls == 1


def test_json_invalido_se_reintenta_una_vez(client, fake_ai):
    fake_ai.queue = ["esto no es json", json.dumps(SUGERENCIAS)]
    r = client.post("/api/ai/suggestions/", ENTRADA, format="json")
    assert r.status_code == 200
    assert fake_ai.calls == 2


def test_json_con_estructura_incorrecta_tambien_se_reintenta(client, fake_ai):
    fake_ai.queue = [json.dumps({"otra_cosa": 1}), json.dumps(SUGERENCIAS)]
    assert client.post("/api/ai/suggestions/", ENTRADA, format="json").status_code == 200
    assert fake_ai.calls == 2


def test_si_vuelve_a_fallar_el_error_es_controlado(client, fake_ai):
    fake_ai.queue = ["no json", "tampoco {"]
    r = client.post("/api/ai/suggestions/", ENTRADA, format="json")
    assert r.status_code == 502
    assert r.json()["code"] == "ai_invalid_json"
    assert "búsqueda normal" in r.json()["detail"]
    assert fake_ai.calls == 2


@pytest.mark.parametrize(
    "fallo, estado, codigo",
    [
        (requests.Timeout(), 504, "ai_timeout"),
        (requests.ConnectionError(), 502, "ai_unreachable"),
        (FakeResponse({}, status_code=429), 502, "ai_http_error"),
        (FakeResponse({"sin": "choices"}), 502, "ai_invalid_response"),
    ],
)
def test_fallos_del_proveedor_son_controlados(client, fake_ai, fallo, estado, codigo):
    fake_ai.queue = [fallo]
    r = client.post("/api/ai/suggestions/", ENTRADA, format="json")
    assert r.status_code == estado and r.json()["code"] == codigo


def test_adaptar_receta(client, fake_ai):
    fake_ai.queue = [json.dumps({
        "substitutions": [{"original": "yogurt", "substitute": "nata agria", "note": "Más densa"}],
        "adapted_steps": ["Mezcla el pollo"],
        "warnings": ["Sin yogur queda menos cremoso"],
    })]
    r = client.post("/api/ai/adapt-recipe/", {"recipe": RECETA, "available_ingredients": ["pollo"]}, format="json")
    assert r.status_code == 200
    assert r.json()["substitutions"][0]["substitute"] == "nata agria"
    assert r.json()["warnings"] == ["Sin yogur queda menos cremoso"]


def test_lista_de_la_compra_con_ia(client, fake_ai):
    fake_ai.queue = [json.dumps({"missing": [{"name": "yogur", "quantity": "200 g"}]})]
    r = client.post("/api/ai/shopping-list/", {"recipe": RECETA, "available_ingredients": ["pollo"]}, format="json")
    assert r.status_code == 200
    assert r.json() == {"missing": [{"name": "yogur", "quantity": "200 g"}]}


@pytest.mark.parametrize(
    "ruta, cuerpo",
    [
        ("/api/ai/suggestions/", {"ingredients": []}),
        ("/api/ai/suggestions/", {"ingredients": ["pollo"], "max_results": 99}),
        ("/api/ai/adapt-recipe/", {"recipe": {"ingredients": []}, "available_ingredients": []}),
        ("/api/ai/shopping-list/", {"recipe": {"title": "x"}, "available_ingredients": []}),
    ],
)
def test_entradas_invalidas_dan_400_sin_llamar_a_la_ia(client, fake_ai, ruta, cuerpo):
    assert client.post(ruta, cuerpo, format="json").status_code == 400
    assert fake_ai.calls == 0


def test_la_peticion_a_la_ia_lleva_formato_json_y_la_clave_solo_en_cabecera(client, fake_ai, monkeypatch):
    capturado = {}

    def post(self, url, json=None, headers=None, **kw):
        capturado.update(url=url, json=json, headers=headers)
        return FakeResponse({"choices": [{"message": {"content": "{\"suggestions\": []}"}}]})

    monkeypatch.setattr(requests.Session, "post", post)
    client.post("/api/ai/suggestions/", ENTRADA, format="json")
    assert capturado["url"] == "https://api.openai.com/v1/chat/completions"
    assert capturado["json"]["response_format"] == {"type": "json_object"}
    assert capturado["headers"]["Authorization"] == "Bearer clave-de-prueba"
    assert "clave-de-prueba" not in str(capturado["json"])
