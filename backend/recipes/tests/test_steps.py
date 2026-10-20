import json

import pytest
import requests
from rest_framework import serializers

from recipes.services.ai import StepField, _to_minutes
from recipes.tests.conftest import FakeResponse


@pytest.mark.parametrize(
    "valor, esperado",
    [(15, 15), (15.9, 15), ("20", 20), ("15-20 min", 15), (None, None), ("", None), ("mucho", None), (-5, 0), (True, None)],
)
def test_minutos(valor, esperado):
    assert _to_minutes(valor) == esperado


def test_un_paso_puede_ser_texto_suelto_u_objeto():
    campo = StepField()
    assert campo.to_internal_value("  Corta la cebolla  ") == {"text": "Corta la cebolla", "minutes": None}
    assert campo.to_internal_value({"text": "Hornea", "minutes": "45 min"}) == {"text": "Hornea", "minutes": 45}
    assert campo.to_internal_value({"texto": "Reposa", "minutes": None}) == {"text": "Reposa", "minutes": None}


@pytest.mark.parametrize("malo", ["", "   ", {"text": ""}, {"minutes": 5}, 42, ["x"], "x" * 1501])
def test_pasos_invalidos(malo):
    with pytest.raises(serializers.ValidationError):
        StepField().to_internal_value(malo)


def test_la_ia_devuelve_pasos_con_tiempos_consejos_y_tiempos_de_preparacion_y_cocina(client, fake_ai, wikipedia):
    fake_ai.queue = [
        json.dumps(
            {
                "suggestions": [
                    {
                        "title": "Arroz con leche",
                        "steps": [
                            {"text": "Calienta la leche con la canela a fuego medio.", "minutes": 10},
                            "Añade el arroz",
                            {"text": "Deja reposar", "minutes": "15 min"},
                        ],
                        "tips": ["Remueve a menudo", "Se conserva 3 días en la nevera"],
                        "prep_minutes": 10,
                        "cook_minutes": 40,
                        "estimated_minutes": 50,
                        "photo_query": "arroz con leche",
                        "photo_query_en": "rice pudding",
                    }
                ]
            }
        )
    ]
    s = client.post("/api/ai/suggestions/", {"ingredients": ["arroz"]}, format="json").json()["suggestions"][0]
    assert s["steps"] == [
        {"text": "Calienta la leche con la canela a fuego medio.", "minutes": 10},
        {"text": "Añade el arroz", "minutes": None},
        {"text": "Deja reposar", "minutes": 15},
    ]
    assert s["tips"] == ["Remueve a menudo", "Se conserva 3 días en la nevera"]
    assert (s["prep_minutes"], s["cook_minutes"], s["estimated_minutes"]) == (10, 40, 50)
    assert s["photo_query"] == "arroz con leche"


def test_el_prompt_pide_pasos_detallados_con_minutos_y_nombre_para_la_foto(client, fake_ai, monkeypatch):
    capturado = {}

    def post(self, url, json=None, **kw):
        capturado["prompt"] = json["messages"][1]["content"]
        return FakeResponse({"choices": [{"message": {"content": '{"suggestions": []}'}}]})

    monkeypatch.setattr(requests.Session, "post", post)
    client.post("/api/ai/suggestions/", {"ingredients": ["arroz"]}, format="json")
    for pista in ["MUY detallados", "minutes", "prep_minutes", "cook_minutes", "tips", "photo_query_en", "cómo saber que está listo"]:
        assert pista in capturado["prompt"], pista


def test_se_guardan_y_se_recuperan_los_pasos_con_tiempos_los_consejos_y_los_tiempos(client):
    receta = {
        "title": "Arroz con leche",
        "ingredients": [{"name": "arroz", "quantity": "100 g"}],
        "steps": [{"text": "Hierve la leche", "minutes": 10}, "Añade el arroz", {"text": "Cuece", "minutes": 35}],
        "tips": ["Remueve a menudo"],
        "prep_minutes": 10,
        "cook_minutes": 45,
        "estimated_minutes": 55,
    }
    r = client.post("/api/favorites/?lang=es", {"recipe": receta}, format="json")
    assert r.status_code == 201
    guardada = r.json()["recipe"]
    assert guardada["steps"] == [
        {"text": "Hierve la leche", "minutes": 10},
        {"text": "Añade el arroz", "minutes": None},
        {"text": "Cuece", "minutes": 35},
    ]
    assert guardada["tips"] == ["Remueve a menudo"]
    assert (guardada["prep_minutes"], guardada["cook_minutes"]) == (10, 45)
    assert guardada["instructions"] == "Hierve la leche\nAñade el arroz\nCuece"
    detalle = client.get(f"/api/recipes/{guardada['external_id']}/", {"lang": "es"}).json()
    assert detalle["steps"] == guardada["steps"] and detalle["tips"] == ["Remueve a menudo"]
