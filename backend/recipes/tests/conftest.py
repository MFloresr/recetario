"""Fixtures compartidas. Ningún test hace llamadas reales: TheMealDB y la IA se simulan."""

import json

import pytest
import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

User = get_user_model()


class FakeWikipedia:
    """Fuentes de fotos simuladas. Por defecto no hay nada en ninguna.

    `pages` (Wikipedia): [{title, thumbnail, fullurl, index}] · `commons`: [{title, imageinfo, index}] ·
    `pexels`: [{src, photographer, url}] · `fail`: todas las fuentes fallan.
    """

    def __init__(self):
        self.pages: list[dict] = []
        self.commons: list[dict] = []
        self.pexels: list[dict] = []
        self.calls: list[dict] = []
        self.pexels_calls: list[dict] = []
        self.fail = False

    def get(self, url, params=None, **kwargs):
        if self.fail:
            raise requests.ConnectionError()
        if "pexels.com" in url:
            self.pexels_calls.append({"params": params, "headers": kwargs.get("headers")})
            return FakeResponse({"photos": self.pexels})
        self.calls.append(params or {})
        lista = self.commons if "commons.wikimedia.org" in url else self.pages
        paginas = {str(i): p for i, p in enumerate(lista)}
        return FakeResponse({"query": {"pages": paginas}} if paginas else {"batchcomplete": ""})


@pytest.fixture
def wikipedia():
    return FakeWikipedia()


@pytest.fixture(autouse=True)
def bloquear_red(monkeypatch, wikipedia):
    """Ningún test sale a internet: solo responden las fotos simuladas y los fakes que cada test pida."""

    def get(self, url, **kw):
        if "wikipedia.org" in url or "commons.wikimedia.org" in url or "pexels.com" in url:
            return wikipedia.get(url, **kw)
        raise RuntimeError(f"Llamada de red real en un test: {url}")

    def post(self, url, **kw):
        raise RuntimeError(f"Llamada de red real en un test: {url}")

    monkeypatch.setattr(requests.Session, "get", get)
    monkeypatch.setattr(requests.Session, "post", post)


@pytest.fixture(autouse=True)
def limpiar_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="ana", email="ana@example.com", password="Contrasena-Segura-91")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="luis", email="luis@example.com", password="Contrasena-Segura-92")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def other_client(other_user):
    c = APIClient()
    c.force_authenticate(other_user)
    return c


# --- TheMealDB simulado ---

MEALS = {
    "1": {"idMeal": "1", "strMeal": "Chicken Handi", "strCategory": "Chicken", "strArea": "Indian", "strMealThumb": "https://img/1.jpg",
          "strInstructions": "Cook it.", "ingredients": [("chicken", "500g"), ("rice", "200g"), ("onion", "1"), ("garlic", "2 cloves"), ("yogurt", "100g")]},
    "2": {"idMeal": "2", "strMeal": "Garlic Rice", "strCategory": "Side", "strArea": "Spanish", "strMealThumb": "https://img/2.jpg",
          "strInstructions": "Fry.", "ingredients": [("rice", "1 cup"), ("garlic", "3 cloves")]},
    "3": {"idMeal": "3", "strMeal": "Beef Stew", "strCategory": "Beef", "strArea": "British", "strMealThumb": "https://img/3.jpg",
          "strInstructions": "Stew.", "ingredients": [("beef", "1kg"), ("onion", "2"), ("carrots", "3"), ("potatoes", "4")]},
}


def _full(meal: dict) -> dict:
    datos = {k: v for k, v in meal.items() if k != "ingredients"}
    for n in range(1, 21):
        nombre, medida = meal["ingredients"][n - 1] if n <= len(meal["ingredients"]) else ("", "")
        datos[f"strIngredient{n}"] = nombre
        datos[f"strMeasure{n}"] = medida
    return datos


class FakeResponse:
    def __init__(self, payload=None, status_code=200, text=None):
        self._payload = payload
        self.status_code = status_code
        self._text = text

    def json(self):
        if self._text is not None:
            return json.loads(self._text)
        return self._payload


class FakeMealDB:
    """Imita filter.php, lookup.php y search.php. Cuenta las llamadas para comprobar la caché."""

    ES_EN = {"pollo": "chicken", "pollo al curry": "chicken curry", "arroz": "rice"}

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.translation_calls: list[dict] = []
        self.translator_mode = "ok"  # ok | quota | down

    def _mymemory(self, params):
        self.translation_calls.append(params)
        if self.translator_mode == "down":
            raise requests.ConnectionError()
        if self.translator_mode == "quota":
            return FakeResponse({"responseData": {"translatedText": "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY"}, "responseStatus": 429, "quotaFinished": True}, status_code=429)
        texto = params["q"]
        traducido = self.ES_EN.get(texto.lower(), texto) if params["langpair"] == "es|en" else f"ES({texto})"
        return FakeResponse({"responseData": {"translatedText": traducido}, "responseStatus": 200})

    def get(self, url, params=None, timeout=None, **kwargs):
        path = url.rsplit("/", 1)[-1]
        params = params or {}
        if "wikipedia.org" in url or "wikimedia.org" in url:
            return FakeResponse({"batchcomplete": ""})
        if "mymemory" in url:
            return self._mymemory(params)
        self.calls.append((path, params))
        if path == "filter.php" and "i" in params:
            ingrediente = params["i"].replace("_", " ")
            hallados = [m for m in MEALS.values() if any(ingrediente == i[0] for i in m["ingredients"])]
            return FakeResponse({"meals": [{"idMeal": m["idMeal"], "strMeal": m["strMeal"], "strMealThumb": m["strMealThumb"]} for m in hallados] or None})
        if path == "lookup.php":
            meal = MEALS.get(params.get("i"))
            return FakeResponse({"meals": [_full(meal)] if meal else None})
        if path == "search.php":
            hallados = [m for m in MEALS.values() if params.get("s", "").lower() in m["strMeal"].lower()]
            return FakeResponse({"meals": [_full(m) for m in hallados] or None})
        if path == "list.php":
            return FakeResponse({"meals": [{"strCategory": "Beef"}, {"strCategory": "Chicken"}]})
        return FakeResponse({"meals": None})


@pytest.fixture
def fake_mealdb(monkeypatch):
    falso = FakeMealDB()
    monkeypatch.setattr(requests.Session, "get", lambda self, url, **kw: falso.get(url, **kw))
    return falso


# --- IA simulada ---


class FakeAI:
    """Cola de respuestas para requests.Session.post: cada elemento es contenido de texto, una excepción o una respuesta."""

    def __init__(self):
        self.queue: list = []
        self.calls = 0

    def post(self, url, json=None, headers=None, timeout=None, **kwargs):
        self.calls += 1
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, FakeResponse):
            return item
        return FakeResponse({"choices": [{"message": {"content": item}}]})


@pytest.fixture
def fake_ai(monkeypatch, settings):
    settings.AI_API_KEY = "clave-de-prueba"
    settings.AI_PROVIDER = "openai"
    settings.AI_BASE_URL = ""
    falso = FakeAI()
    monkeypatch.setattr(requests.Session, "post", lambda self, url, **kw: falso.post(url, **kw))
    return falso
