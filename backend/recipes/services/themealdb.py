"""Cliente de TheMealDB. Aísla las llamadas externas y devuelve recetas en el formato interno."""

import requests
from django.conf import settings

from ..exceptions import TheMealDBError

SOURCE = "themealdb"
MAX_INGREDIENTS = 20


def normalize_meal(meal: dict) -> dict:
    """Pasa una receta de TheMealDB al formato interno."""
    ingredients = []
    for n in range(1, MAX_INGREDIENTS + 1):
        nombre = (meal.get(f"strIngredient{n}") or "").strip()
        if nombre:
            ingredients.append({"ingredient": nombre, "measure": (meal.get(f"strMeasure{n}") or "").strip()})
    return {
        "external_id": str(meal.get("idMeal", "")),
        "title": meal.get("strMeal") or "",
        "image": meal.get("strMealThumb") or "",
        "category": meal.get("strCategory") or "",
        "area": meal.get("strArea") or "",
        "instructions": meal.get("strInstructions") or "",
        "ingredients": ingredients,
        "source": SOURCE,
    }


def _summary(meal: dict) -> dict:
    """Las listas de `filter.php` solo traen id, título e imagen."""
    return {"external_id": str(meal.get("idMeal", "")), "title": meal.get("strMeal") or "", "image": meal.get("strMealThumb") or ""}


class TheMealDBClient:
    def __init__(self, base_url: str | None = None, timeout: int = 10, session: requests.Session | None = None):
        self.base_url = (base_url or settings.THEMEALDB_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            respuesta = self.session.get(f"{self.base_url}/{path}", params=params, timeout=self.timeout)
        except requests.Timeout as exc:
            raise TheMealDBError(
                "TheMealDB tardó demasiado en responder. Inténtalo de nuevo en unos segundos.",
                status_code=504,
                code="themealdb_timeout",
            ) from exc
        except requests.RequestException as exc:
            raise TheMealDBError("No se pudo conectar con TheMealDB.", status_code=502, code="themealdb_unreachable") from exc
        if respuesta.status_code >= 400:
            raise TheMealDBError(
                f"TheMealDB respondió con un error ({respuesta.status_code}).", status_code=502, code="themealdb_http_error"
            )
        try:
            datos = respuesta.json()
        except ValueError as exc:
            raise TheMealDBError("TheMealDB devolvió una respuesta que no se pudo leer.", status_code=502, code="themealdb_invalid_json") from exc
        if not isinstance(datos, dict):
            raise TheMealDBError("TheMealDB devolvió una respuesta inesperada.", status_code=502, code="themealdb_invalid_json")
        return datos

    @staticmethod
    def _meals(datos: dict) -> list[dict]:
        meals = datos.get("meals")
        return meals if isinstance(meals, list) else []  # sin resultados llega null (o la cadena "None")

    def search_by_name(self, name: str) -> list[dict]:
        return [normalize_meal(m) for m in self._meals(self._get("search.php", {"s": name}))]

    def get_by_id(self, external_id: str) -> dict | None:
        meals = self._meals(self._get("lookup.php", {"i": external_id}))
        return normalize_meal(meals[0]) if meals else None

    def list_categories(self) -> list[str]:
        return [c.get("strCategory", "") for c in self._meals(self._get("list.php", {"c": "list"}))]

    def filter_by_category(self, category: str) -> list[dict]:
        return [_summary(m) for m in self._meals(self._get("filter.php", {"c": category}))]

    def filter_by_ingredient(self, ingredient: str) -> list[dict]:
        """El ingrediente va en inglés y con guiones bajos: `chicken_breast`."""
        return [_summary(m) for m in self._meals(self._get("filter.php", {"i": ingredient.replace(" ", "_")}))]

    def random(self) -> dict | None:
        meals = self._meals(self._get("random.php"))
        return normalize_meal(meals[0]) if meals else None
