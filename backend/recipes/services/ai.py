"""Servicio de IA con una interfaz común. Cambiar de proveedor no obliga a tocar vistas ni serializadores.

Hoy hay un proveedor compatible con la API de OpenAI (`/chat/completions`). Muchos otros lo ofrecen
(Gemini, Groq, OpenRouter, Ollama...): basta con cambiar `AI_BASE_URL` y `AI_MODEL`. Para un proveedor con
otro protocolo se escribe otra subclase de `AIRecipeService` y se registra en `PROVIDERS`.
"""

import json
from abc import ABC, abstractmethod

import requests
from django.conf import settings
from rest_framework import serializers

from ..exceptions import AIServiceError
from ..normalization import normalize_name

TIMEOUT = 60

SYSTEM_PROMPT = (
    "Eres un asistente de cocina. Responde SIEMPRE en español y SOLO con un objeto JSON válido, "
    "sin texto antes ni después. No inventes ingredientes que el usuario no tenga: si falta alguno, "
    "indícalo como ingrediente faltante."
)


# --- Esquemas de salida: lo que devuelve la IA se valida antes de usarlo ---


MEAL_TYPES = ["desayuno", "almuerzo", "merienda", "cena", "postre", "batido", "snack", "entrante", "plato principal", "bebida", "otro"]
_MEAL_ALIASES = {
    "comida": "almuerzo", "brunch": "desayuno", "smoothie": "batido", "licuado": "batido", "tentempie": "snack",
    "aperitivo": "entrante", "tapa": "entrante", "principal": "plato principal", "segundo": "plato principal", "dulce": "postre",
}
DIFFICULTIES = ["fácil", "media", "difícil"]
_DIFFICULTY_ALIASES = {"facil": "fácil", "sencilla": "fácil", "baja": "fácil", "media": "media", "media-baja": "media", "dificil": "difícil", "alta": "difícil", "compleja": "difícil"}


def normalize_meal_type(valor: str) -> str:
    """«Desayuno», «comida», «Smoothie»… → uno de MEAL_TYPES (lo desconocido pasa a «otro»)."""
    clave = normalize_name(valor)
    clave = _MEAL_ALIASES.get(clave, clave)
    return clave if clave in MEAL_TYPES else "otro"


def normalize_difficulty(valor: str) -> str:
    clave = normalize_name(valor)
    return _DIFFICULTY_ALIASES.get(clave) or (clave if clave in DIFFICULTIES else "")


class _RecipeIngredient(serializers.Serializer):
    name = serializers.CharField()
    quantity = serializers.CharField(allow_blank=True, required=False, default="")


class _Suggestion(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False, default="")
    meal_type = serializers.CharField(allow_blank=True, required=False, default="otro")
    ingredients = _RecipeIngredient(many=True, required=False, default=list)
    ingredients_used = serializers.ListField(child=serializers.CharField(), default=list)
    missing_ingredients = serializers.ListField(child=serializers.CharField(), default=list)
    steps = serializers.ListField(child=serializers.CharField(), default=list)
    estimated_minutes = serializers.IntegerField(min_value=0, required=False, allow_null=True, default=None)
    servings = serializers.IntegerField(min_value=1, required=False, allow_null=True, default=None)
    difficulty = serializers.CharField(allow_blank=True, required=False, default="")

    def validate_meal_type(self, value):
        return normalize_meal_type(value)

    def validate_difficulty(self, value):
        return normalize_difficulty(value)


class SuggestionsOutput(serializers.Serializer):
    suggestions = _Suggestion(many=True)


class _Substitution(serializers.Serializer):
    original = serializers.CharField()
    substitute = serializers.CharField()
    note = serializers.CharField(allow_blank=True, required=False, default="")


class AdaptOutput(serializers.Serializer):
    substitutions = _Substitution(many=True)
    adapted_steps = serializers.ListField(child=serializers.CharField(), default=list)
    warnings = serializers.ListField(child=serializers.CharField(), default=list)


class _MissingItem(serializers.Serializer):
    name = serializers.CharField()
    quantity = serializers.CharField(allow_blank=True, required=False, default="")


class ShoppingOutput(serializers.Serializer):
    missing = _MissingItem(many=True)


class TranslationOutput(serializers.Serializer):
    translations = serializers.ListField(child=serializers.CharField(allow_blank=True))


# --- Interfaz común ---


class AIRecipeService(ABC):
    @abstractmethod
    def suggest_recipes(self, ingredients: list[str], constraints: dict | None = None) -> dict: ...

    @abstractmethod
    def adapt_recipe(self, recipe: dict, available_ingredients: list[str]) -> dict: ...

    @abstractmethod
    def generate_shopping_list(self, recipe: dict, available_ingredients: list[str]) -> dict: ...

    @abstractmethod
    def translate(self, texts: list[str], source: str = "en", target: str = "es") -> list[str]: ...


class OpenAICompatibleService(AIRecipeService):
    def __init__(self, api_key: str, model: str, base_url: str, session: requests.Session | None = None, timeout: int = TIMEOUT):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    # -- comunicación con el proveedor --

    def _chat(self, system: str, user: str) -> str:
        cuerpo = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "temperature": 0.4,
        }
        try:
            respuesta = self.session.post(
                f"{self.base_url}/chat/completions",
                json=cuerpo,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise AIServiceError("La IA tardó demasiado en responder. Puedes seguir usando la búsqueda normal.", status_code=504, code="ai_timeout") from exc
        except requests.RequestException as exc:
            raise AIServiceError("No se pudo conectar con la IA. Puedes seguir usando la búsqueda normal.", status_code=502, code="ai_unreachable") from exc
        if respuesta.status_code >= 400:
            raise AIServiceError(
                f"La IA respondió con un error ({respuesta.status_code}). Puedes seguir usando la búsqueda normal.",
                status_code=502,
                code="ai_http_error",
            )
        try:
            return respuesta.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIServiceError("La IA devolvió una respuesta inesperada.", status_code=502, code="ai_invalid_response") from exc

    def _ask(self, user_prompt: str, output: type[serializers.Serializer]) -> dict:
        """Pide JSON, lo valida y reintenta una vez si no es válido."""
        for intento in range(2):
            contenido = self._chat(SYSTEM_PROMPT, user_prompt)
            try:
                datos = json.loads(contenido)
            except (TypeError, ValueError):
                continue
            validador = output(data=datos)
            if validador.is_valid():
                return validador.data
        raise AIServiceError(
            "La IA no devolvió una respuesta válida. Puedes seguir usando la búsqueda normal.",
            status_code=502,
            code="ai_invalid_json",
        )

    # -- operaciones --

    def suggest_recipes(self, ingredients: list[str], constraints: dict | None = None) -> dict:
        c = constraints or {}
        tipo = c.get("meal_type")
        prompt = (
            f"Ingredientes disponibles: {', '.join(ingredients)}.\n"
            f"Propón hasta {c.get('max_results', 5)} recetas reales y conocidas que se puedan preparar sobre todo con ellos"
            + (f", todas de tipo «{tipo}»" if tipo else "")
            + ".\n"
            f"Dieta: {c.get('diet') or 'sin restricciones'}. Evitar: {', '.join(c.get('avoid') or []) or 'nada'}.\n"
            "Usa el nombre habitual del plato en español (sin inventar nombres de fantasía). "
            "Cada receta lleva TODOS sus ingredientes con cantidad para el número de raciones indicado, los pasos "
            "detallados, el tiempo total en minutos, la dificultad y el tipo de comida.\n"
            'Devuelve {"suggestions": [{"title", "description", "meal_type": "' + "|".join(MEAL_TYPES) + '", '
            '"servings": número, "ingredients": [{"name", "quantity"}], "ingredients_used": [de los que tengo], '
            '"missing_ingredients": [los que me faltan], "steps": [], "estimated_minutes": número, '
            '"difficulty": "fácil|media|difícil"}]}.'
        )
        return self._ask(prompt, SuggestionsOutput)

    def adapt_recipe(self, recipe: dict, available_ingredients: list[str]) -> dict:
        prompt = (
            f"Receta: {json.dumps(recipe, ensure_ascii=False)}\n"
            f"Ingredientes que tengo: {', '.join(available_ingredients)}.\n"
            "Adapta la receta a lo que tengo: propón sustitutos para lo que falte, reescribe los pasos y avisa "
            "si la receta pierde sentido sin algún ingrediente clave.\n"
            'Devuelve {"substitutions": [{"original", "substitute", "note"}], "adapted_steps": [], "warnings": []}.'
        )
        return self._ask(prompt, AdaptOutput)

    def generate_shopping_list(self, recipe: dict, available_ingredients: list[str]) -> dict:
        prompt = (
            f"Receta: {json.dumps(recipe, ensure_ascii=False)}\n"
            f"Ingredientes que tengo: {', '.join(available_ingredients)}.\n"
            "Devuelve SOLO los ingredientes que me faltan para prepararla, con la cantidad si se conoce, "
            "y con los nombres en español.\n"
            'Formato: {"missing": [{"name", "quantity"}]}.'
        )
        return self._ask(prompt, ShoppingOutput)

    def translate(self, texts: list[str], source: str = "en", target: str = "es") -> list[str]:
        """Traduce una lista de textos manteniendo el orden y la longitud de la lista."""
        idiomas = {"en": "inglés", "es": "español"}
        prompt = (
            f"Traduce del {idiomas.get(source, source)} al {idiomas.get(target, target)} estos textos de recetas de cocina. "
            "Respeta números, unidades y el orden; usa español neutro y el imperativo en los pasos. "
            f"Textos: {json.dumps(texts, ensure_ascii=False)}\n"
            'Devuelve {"translations": [...]} con exactamente un elemento por cada texto, en el mismo orden.'
        )
        for _ in range(2):
            resultado = self._ask(prompt, TranslationOutput)["translations"]
            if len(resultado) == len(texts):
                return resultado
        raise AIServiceError("La IA no devolvió todas las traducciones.", status_code=502, code="ai_invalid_json")


PROVIDERS = {"openai": OpenAICompatibleService}
DEFAULT_BASE_URLS = {"openai": "https://api.openai.com/v1"}


def get_ai_service() -> AIRecipeService:
    """Servicio según AI_PROVIDER. Falla con un error controlado si la IA no está configurada."""
    proveedor = (settings.AI_PROVIDER or "").lower()
    clase = PROVIDERS.get(proveedor)
    if clase is None:
        raise AIServiceError(f"El proveedor de IA «{settings.AI_PROVIDER}» no está soportado.", status_code=503, code="ai_unsupported_provider")
    if not settings.AI_API_KEY:
        raise AIServiceError(
            "La IA no está configurada en el servidor. Puedes seguir usando la búsqueda normal.",
            status_code=503,
            code="ai_not_configured",
        )
    return clase(
        api_key=settings.AI_API_KEY,
        model=settings.AI_MODEL,
        base_url=settings.AI_BASE_URL or DEFAULT_BASE_URLS[proveedor],
    )
