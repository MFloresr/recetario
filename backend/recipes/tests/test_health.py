from rest_framework.test import APIClient


def test_health_responde_sin_autenticacion():
    respuesta = APIClient().get("/api/health/")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}

