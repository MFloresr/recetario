import json

import pytest
import requests
from rest_framework.test import APIClient

from recipes.models import Ingredient, MealPlan
from recipes.tests.conftest import FakeResponse

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def plan_ia(dias=7, **extra):
    return json.dumps(
        {
            "title": "Semana ligera",
            "days": [
                {
                    "day": f"Día {i + 1}",
                    "meals": [
                        {"type": "Desayuno", "title": "Tostadas con tomate", "description": "Con aceite de oliva", "calories": 320, "ingredients": ["pan", "tomate"]},
                        {"type": "comida", "title": f"Lentejas {i}", "calories": 550, "ingredients": ["lentejas", "zanahoria"]},
                        {"type": "cena", "title": "Tortilla francesa", "calories": 400},
                    ],
                }
                for i in range(dias)
            ],
            "notes": "Bebe agua entre comidas",
            **extra,
        }
    )


def test_genera_y_guarda_la_dieta_de_la_semana(client, fake_ai, user):
    fake_ai.queue = [plan_ia()]
    r = client.post("/api/ai/meal-plan/", {"goal": "bajar de peso", "meals": ["desayuno", "almuerzo", "cena"]}, format="json")
    assert r.status_code == 201
    plan = r.json()
    assert plan["title"] == "Semana ligera" and plan["notes"] == "Bebe agua entre comidas"
    assert [d["day"] for d in plan["days"]] == DIAS  # los días se ordenan de lunes a domingo
    comidas = plan["days"][0]["meals"]
    assert [m["type"] for m in comidas] == ["desayuno", "almuerzo", "cena"]  # «comida» pasa a almuerzo
    assert comidas[0]["calories"] == 320 and comidas[2]["ingredients"] == []
    assert plan["options"]["goal"] == "bajar de peso"
    assert MealPlan.objects.filter(user=user).count() == 1


def test_el_plan_se_puede_consultar_otro_dia(client, fake_ai):
    fake_ai.queue = [plan_ia()]
    creado = client.post("/api/ai/meal-plan/", {}, format="json").json()
    lista = client.get("/api/meal-plans/").json()
    assert [p["id"] for p in lista] == [creado["id"]]
    assert client.get(f"/api/meal-plans/{creado['id']}/").json()["days"][0]["day"] == "Lunes"


def test_los_planes_son_privados(client, other_client, fake_ai):
    fake_ai.queue = [plan_ia()]
    creado = client.post("/api/ai/meal-plan/", {}, format="json").json()
    assert other_client.get("/api/meal-plans/").json() == []
    assert other_client.get(f"/api/meal-plans/{creado['id']}/").status_code == 404
    assert other_client.delete(f"/api/meal-plans/{creado['id']}/").status_code == 404


def test_borrar_un_plan(client, fake_ai):
    fake_ai.queue = [plan_ia()]
    creado = client.post("/api/ai/meal-plan/", {}, format="json").json()
    assert client.delete(f"/api/meal-plans/{creado['id']}/").status_code == 204
    assert client.get("/api/meal-plans/").json() == []


def test_solo_se_conservan_los_ultimos_planes(client, fake_ai):
    fake_ai.queue = [plan_ia() for _ in range(7)]
    ids = [client.post("/api/ai/meal-plan/", {}, format="json").json()["id"] for _ in range(7)]
    guardados = [p["id"] for p in client.get("/api/meal-plans/").json()]
    assert guardados == ids[:1:-1]  # los 5 más recientes, el último primero


@pytest.mark.parametrize("dias", [6, 8])
def test_un_plan_sin_siete_dias_se_reintenta_y_luego_da_error_controlado(client, fake_ai, dias):
    fake_ai.queue = [plan_ia(dias), plan_ia(dias)]
    r = client.post("/api/ai/meal-plan/", {}, format="json")
    assert r.status_code == 502 and r.json()["code"] == "ai_invalid_json"
    assert MealPlan.objects.count() == 0


def test_si_el_primer_intento_no_tiene_siete_dias_el_segundo_sirve(client, fake_ai):
    fake_ai.queue = [plan_ia(5), plan_ia()]
    assert client.post("/api/ai/meal-plan/", {}, format="json").status_code == 201
    assert fake_ai.calls == 2


def test_las_preferencias_viajan_a_la_ia_y_la_despensa_solo_si_se_pide(client, fake_ai, user, monkeypatch):
    Ingredient.objects.create(user=user, name="garbanzos")
    prompts = []

    def post(self, url, json=None, **kw):
        prompts.append(json["messages"][1]["content"])
        return FakeResponse({"choices": [{"message": {"content": plan_ia()}}]})

    monkeypatch.setattr(requests.Session, "post", post)
    client.post("/api/ai/meal-plan/", {"goal": "ganar músculo", "calories": 2600, "diet": "vegetariana", "avoid": ["frutos secos"], "use_pantry": True}, format="json")
    client.post("/api/ai/meal-plan/", {}, format="json")
    con, sin = prompts
    assert "ganar músculo" in con and "2600 kcal" in con and "vegetariana" in con and "frutos secos" in con and "garbanzos" in con
    assert "garbanzos" not in sin


@pytest.mark.parametrize("cuerpo", [{"goal": "dieta milagro"}, {"meals": ["desayuno"]}, {"meals": ["brunch", "cena"]}, {"calories": 200}, {"calories": 9000}])
def test_entradas_invalidas_dan_400_sin_llamar_a_la_ia(client, fake_ai, cuerpo):
    assert client.post("/api/ai/meal-plan/", cuerpo, format="json").status_code == 400
    assert fake_ai.calls == 0


def test_hace_falta_iniciar_sesion(db):
    anonimo = APIClient()
    assert anonimo.post("/api/ai/meal-plan/", {}, format="json").status_code == 401
    assert anonimo.get("/api/meal-plans/").status_code == 401
