"""Servicio de IA con una interfaz común. Cambiar de proveedor no obliga a tocar vistas ni serializadores.

Hoy hay un proveedor compatible con la API de OpenAI (`/chat/completions`). Muchos otros lo ofrecen
(Gemini, Groq, OpenRouter, Ollama...): basta con cambiar `AI_BASE_URL` y `AI_MODEL`. Para un proveedor con
otro protocolo se escribe otra subclase de `AIRecipeService` y se registra en `PROVIDERS`.
"""

import json
import re
from abc import ABC, abstractmethod

import requests
from django.conf import settings
from rest_framework import serializers

from ..exceptions import AIServiceError
from ..normalization import normalize_name

TIMEOUT = 60
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

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


def _to_minutes(valor) -> int | None:
    """15 → 15; «15-20 min» → 15; null/«» → None."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return max(0, int(valor))
    encontrado = re.search(r"\d+", str(valor))
    return int(encontrado.group()) if encontrado else None


class StepField(serializers.Field):
    """Un paso de la receta: admite un texto suelto o {text, minutes} y siempre devuelve {text, minutes}."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            texto, minutos = data.strip(), None
        elif isinstance(data, dict):
            texto, minutos = str(data.get("text") or data.get("texto") or "").strip(), _to_minutes(data.get("minutes"))
        else:
            raise serializers.ValidationError("Un paso debe ser un texto o un objeto con `text` y `minutes`.")
        if not texto:
            raise serializers.ValidationError("El paso no puede estar vacío.")
        if len(texto) > 1500:
            raise serializers.ValidationError("El paso es demasiado largo.")
        return {"text": texto, "minutes": minutos}

    def to_representation(self, value):
        return value


class _Suggestion(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False, default="")
    meal_type = serializers.CharField(allow_blank=True, required=False, default="otro")
    ingredients = _RecipeIngredient(many=True, required=False, default=list)
    ingredients_used = serializers.ListField(child=serializers.CharField(), default=list)
    missing_ingredients = serializers.ListField(child=serializers.CharField(), default=list)
    steps = serializers.ListField(child=StepField(), default=list)
    tips = serializers.ListField(child=serializers.CharField(), default=list, required=False)
    estimated_minutes = serializers.IntegerField(min_value=0, required=False, allow_null=True, default=None)
    prep_minutes = serializers.IntegerField(min_value=0, required=False, allow_null=True, default=None)
    cook_minutes = serializers.IntegerField(min_value=0, required=False, allow_null=True, default=None)
    photo_query = serializers.CharField(allow_blank=True, required=False, default="")
    photo_query_en = serializers.CharField(allow_blank=True, required=False, default="")
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


PLAN_MEAL_TYPES = ["desayuno", "almuerzo", "merienda", "cena", "snack"]
PLAN_DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


class _PlanMeal(serializers.Serializer):
    type = serializers.CharField()
    title = serializers.CharField(max_length=160)
    description = serializers.CharField(allow_blank=True, required=False, default="", max_length=300)
    calories = serializers.IntegerField(min_value=0, max_value=5000, required=False, allow_null=True, default=None)
    ingredients = serializers.ListField(child=serializers.CharField(max_length=80), required=False, default=list, max_length=15)

    def validate_type(self, value):
        clave = normalize_name(value)
        clave = {"comida": "almuerzo", "cenar": "cena", "tentempie": "snack", "media manana": "snack", "colacion": "snack"}.get(clave, clave)
        return clave if clave in PLAN_MEAL_TYPES else "snack"


class _PlanDay(serializers.Serializer):
    day = serializers.CharField()
    meals = _PlanMeal(many=True)


class MealPlanOutput(serializers.Serializer):
    title = serializers.CharField(allow_blank=True, required=False, default="", max_length=120)
    days = _PlanDay(many=True)
    notes = serializers.CharField(allow_blank=True, required=False, default="", max_length=600)

    def validate_days(self, value):
        if len(value) != 7:
            raise serializers.ValidationError("El plan debe tener 7 días.")
        # los días se fijan en el orden de la semana, sea cual sea la forma en que los nombre la IA
        for dia, nombre in zip(value, PLAN_DAYS):
            dia["day"] = nombre
            if not dia["meals"]:
                raise serializers.ValidationError("Cada día necesita comidas.")
        return value


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
    def generate_meal_plan(self, options: dict) -> dict: ...

    @abstractmethod
    def translate(self, texts: list[str], source: str = "en", target: str = "es") -> list[str]: ...


class OpenAICompatibleService(AIRecipeService):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        session: requests.Session | None = None,
        timeout: int = TIMEOUT,
        fallback_models: list[str] | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.fallback_models = [m for m in (fallback_models or []) if m and m != model]
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    # -- comunicación con el proveedor --

    def _chat(self, system: str, user: str) -> str:
        """Pide la respuesta al modelo principal; si está saturado (429/5xx) prueba con los de reserva."""
        respuesta = None
        for modelo in [self.model, *self.fallback_models]:
            cuerpo = {
                "model": modelo,
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
            if respuesta.status_code not in RETRYABLE_STATUS:
                break
        if respuesta.status_code >= 400:
            saturada = respuesta.status_code in RETRYABLE_STATUS
            raise AIServiceError(
                ("La IA está saturada ahora mismo" if saturada else "La IA respondió con un error")
                + f" ({respuesta.status_code}). Puedes seguir usando la búsqueda normal.",
                status_code=502,
                code="ai_overloaded" if saturada else "ai_http_error",
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
        consulta = (c.get("query") or "").strip()
        if consulta:
            cabecera = (
                f"Busca recetas reales y conocidas de «{consulta}» (el plato exacto y variantes habituales). "
                + (f"Ingredientes que tengo, por si ayudan: {', '.join(ingredients)}.\n" if ingredients else "\n")
                + f"Propón hasta {c.get('max_results', 5)} recetas"
            )
        else:
            cabecera = (
                f"Ingredientes disponibles: {', '.join(ingredients)}.\n"
                f"Propón hasta {c.get('max_results', 5)} recetas reales y conocidas que se puedan preparar sobre todo con ellos"
            )
        prompt = (
            cabecera
            + (f", todas de tipo «{tipo}»" if tipo else "")
            + ".\n"
            f"Dieta: {c.get('diet') or 'sin restricciones'}. Evitar: {', '.join(c.get('avoid') or []) or 'nada'}.\n"
            "Usa el nombre habitual del plato en español (sin inventar nombres de fantasía). "
            "Cada receta lleva TODOS sus ingredientes con cantidad para el número de raciones indicado, la dificultad "
            "y el tipo de comida.\n"
            "Los pasos deben ser MUY detallados, como los de un libro de cocina: qué hacer exactamente, cómo cortar o "
            "preparar cada ingrediente, a qué fuego o temperatura del horno, en qué utensilio, cuánto tiempo y cómo "
            "saber que está listo (color, textura, olor). Un paso = una acción concreta; si un paso lleva tiempo de "
            "cocción, reposo o horno, indica los minutos en `minutes` (un número; null si no hay espera). Da entre 6 y 14 "
            "pasos. Añade `prep_minutes` (preparación), `cook_minutes` (cocción), `estimated_minutes` (total) y de 2 a 4 "
            "consejos en `tips` (trucos, cómo conservarla, errores típicos).\n"
            "`photo_query` es el nombre corto y genérico del plato en español (p. ej. «lasaña», «arroz con leche») y "
            "`photo_query_en` el mismo en inglés, para buscar una foto de muestra.\n"
            'Devuelve {"suggestions": [{"title", "description", "meal_type": "' + "|".join(MEAL_TYPES) + '", '
            '"servings": número, "ingredients": [{"name", "quantity"}], "ingredients_used": [de los que tengo], '
            '"missing_ingredients": [los que me faltan], "steps": [{"text", "minutes"}], "tips": [], '
            '"prep_minutes": número, "cook_minutes": número, "estimated_minutes": número, '
            '"difficulty": "fácil|media|difícil", "photo_query", "photo_query_en"}]}.'
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

    def generate_meal_plan(self, options: dict) -> dict:
        comidas = options.get("meals") or ["desayuno", "almuerzo", "merienda", "cena"]
        objetivo = options.get("goal") or "mantener el peso"
        calorias = options.get("calories")
        despensa = options.get("pantry") or []
        prompt = (
            "Prepara una dieta semanal equilibrada y variada, de lunes a domingo, con platos reales y fáciles de cocinar "
            "en casa (nombres habituales en español, sin repetir el mismo plato principal en la semana).\n"
            f"Comidas de cada día: {', '.join(comidas)}.\n"
            f"Objetivo: {objetivo}."
            + (f" Unas {calorias} kcal al día en total." if calorias else "")
            + f"\nDieta: {options.get('diet') or 'sin restricciones'}. Evitar: {', '.join(options.get('avoid') or []) or 'nada'}.\n"
            + (f"Intenta aprovechar estos ingredientes que ya tengo: {', '.join(despensa)}.\n" if despensa else "")
            + "Cada comida lleva: `type` (uno de las comidas indicadas), `title` (nombre del plato), `description` "
            "(una frase de máximo 90 caracteres), `calories` (kcal aproximadas de una ración) e `ingredients` "
            "(de 3 a 7 ingredientes principales). Pon en `notes` un consejo breve para seguir la semana.\n"
            'Devuelve {"title": "título corto del plan", "days": [{"day": "Lunes", "meals": [{"type", "title", "description", '
            '"calories", "ingredients": []}]}, ... los 7 días], "notes": ""}.'
        )
        return self._ask(prompt, MealPlanOutput)

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
        fallback_models=settings.AI_FALLBACK_MODELS,
    )
