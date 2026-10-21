import json

import pytest
import requests

from recipes.services.images import FOTOS_RESPALDO
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
        (FakeResponse({}, status_code=429), 502, "ai_overloaded"),
        (FakeResponse({}, status_code=401), 502, "ai_http_error"),
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


# --- Recetas completas: foto, tipo de comida, dificultad, tiempo ---

COMPLETA = {
    "suggestions": [
        {
            "title": "Tortilla de patatas",
            "description": "Clásico de la cocina española",
            "meal_type": "Comida",
            "servings": 4,
            "ingredients": [{"name": "huevos", "quantity": "6"}, {"name": "patatas", "quantity": "600 g"}],
            "ingredients_used": ["huevos"],
            "missing_ingredients": ["patatas"],
            "steps": ["Pela las patatas", "Fríelas", "Mézclalas con el huevo batido"],
            "estimated_minutes": 40,
            "difficulty": "Fácil",
        },
        {"title": "Batido de plátano", "meal_type": "Smoothie", "steps": ["Tritura todo"], "difficulty": "media"},
    ]
}


def test_receta_completa_con_foto_tipo_y_dificultad(client, fake_ai, wikipedia):
    wikipedia.pages = [{"title": "Tortilla de patatas", "thumbnail": {"source": "https://upload.wikimedia.org/tortilla.jpg"}, "fullurl": "https://es.wikipedia.org/wiki/Tortilla_de_patatas", "index": 1}]
    fake_ai.queue = [json.dumps(COMPLETA)]
    r = client.post("/api/ai/suggestions/", {**ENTRADA, "meal_type": "almuerzo"}, format="json")
    assert r.status_code == 200
    tortilla, batido = r.json()["suggestions"]
    assert tortilla["meal_type"] == "almuerzo"  # «Comida» se normaliza
    assert tortilla["difficulty"] == "fácil" and tortilla["estimated_minutes"] == 40 and tortilla["servings"] == 4
    assert tortilla["ingredients"] == [{"name": "huevos", "quantity": "6"}, {"name": "patatas", "quantity": "600 g"}]
    assert tortilla["image"] == {"url": "https://upload.wikimedia.org/tortilla.jpg", "credit": "Wikipedia", "page": "https://es.wikipedia.org/wiki/Tortilla_de_patatas"}
    assert batido["meal_type"] == "batido" and batido["image"] == FOTOS_RESPALDO["batido"]  # sin foto fiable del plato, la de respaldo de su tipo
    assert batido["ingredients"] == []


def test_tipo_de_comida_desconocido_pasa_a_otro(client, fake_ai):
    fake_ai.queue = [json.dumps({"suggestions": [{"title": "Cosa", "meal_type": "algo raro"}]})]
    r = client.post("/api/ai/suggestions/", ENTRADA, format="json")
    assert r.json()["suggestions"][0]["meal_type"] == "otro"


def test_el_tipo_de_comida_pedido_viaja_en_la_peticion_a_la_ia(client, fake_ai, monkeypatch):
    capturado = {}

    def post(self, url, json=None, **kw):
        capturado["prompt"] = json["messages"][1]["content"]
        return FakeResponse({"choices": [{"message": {"content": "{\"suggestions\": []}"}}]})

    monkeypatch.setattr(requests.Session, "post", post)
    assert client.post("/api/ai/suggestions/", {**ENTRADA, "meal_type": "postre"}, format="json").status_code == 200
    assert "de tipo «postre»" in capturado["prompt"]
    assert "ingredients" in capturado["prompt"] and "estimated_minutes" in capturado["prompt"]


def test_tipo_de_comida_invalido_en_la_entrada_da_400(client, fake_ai):
    assert client.post("/api/ai/suggestions/", {**ENTRADA, "meal_type": "banquete"}, format="json").status_code == 400
    assert fake_ai.calls == 0


def test_si_las_fuentes_fallan_las_recetas_salen_con_la_foto_de_respaldo(client, fake_ai, wikipedia):
    wikipedia.fail = True
    fake_ai.queue = [json.dumps(COMPLETA)]
    r = client.post("/api/ai/suggestions/", ENTRADA, format="json")
    assert r.status_code == 200
    assert all(s["image"]["credit"].endswith("(Unsplash)") for s in r.json()["suggestions"])


# --- Modelos de reserva cuando el principal está saturado ---


def test_si_el_modelo_principal_esta_saturado_se_usa_el_de_reserva(client, fake_ai, settings, monkeypatch):
    settings.AI_MODEL = "principal"
    settings.AI_FALLBACK_MODELS = ["reserva-1", "reserva-2"]
    usados = []

    def post(self, url, json=None, **kw):
        usados.append(json["model"])
        if json["model"] != "reserva-2":
            return FakeResponse({}, status_code=503)
        return FakeResponse({"choices": [{"message": {"content": "{\"suggestions\": []}"}}]})

    monkeypatch.setattr(requests.Session, "post", post)
    r = client.post("/api/ai/suggestions/", ENTRADA, format="json")
    assert r.status_code == 200
    assert usados == ["principal", "reserva-1", "reserva-2"]


def test_un_error_que_no_es_de_saturacion_no_prueba_las_reservas(client, fake_ai, settings, monkeypatch):
    settings.AI_FALLBACK_MODELS = ["reserva"]
    usados = []

    def post(self, url, json=None, **kw):
        usados.append(json["model"])
        return FakeResponse({}, status_code=401)

    monkeypatch.setattr(requests.Session, "post", post)
    r = client.post("/api/ai/suggestions/", ENTRADA, format="json")
    assert r.status_code == 502 and r.json()["code"] == "ai_http_error"
    assert len(usados) == 1


def test_si_todos_los_modelos_estan_saturados_el_error_es_controlado(client, fake_ai, settings, monkeypatch):
    settings.AI_FALLBACK_MODELS = ["reserva"]
    monkeypatch.setattr(requests.Session, "post", lambda self, url, **kw: FakeResponse({}, status_code=503))
    r = client.post("/api/ai/suggestions/", ENTRADA, format="json")
    assert r.status_code == 502 and r.json()["code"] == "ai_overloaded"
    assert "saturada" in r.json()["detail"]
