"""Catálogo de ingredientes comunes.

TheMealDB está en inglés y el usuario escribe en español, así que hay una pequeña tabla es → en
(con la categoría de cada uno). Sirve para tres cosas: traducir al consultar TheMealDB, adivinar la
categoría de un ingrediente nuevo y mostrar nombres en español. Lo que no esté en la tabla se trata
tal cual: si el usuario escribe «chicken» funciona igual.
"""

from .normalization import normalize_name

CATEGORIES = ["verdura", "fruta", "carne", "pescado", "lacteo", "cereal", "legumbre", "especia", "bebida", "otro"]

# nombre normalizado en español → (nombre en inglés, categoría)
INGREDIENTS: dict[str, tuple[str, str]] = {
    # carne
    "pollo": ("chicken", "carne"), "pechuga de pollo": ("chicken breast", "carne"), "ternera": ("beef", "carne"),
    "carne picada": ("minced beef", "carne"), "cerdo": ("pork", "carne"), "cordero": ("lamb", "carne"),
    "jamon": ("ham", "carne"), "bacon": ("bacon", "carne"), "panceta": ("bacon", "carne"), "salchicha": ("sausages", "carne"),
    "chorizo": ("chorizo", "carne"), "pavo": ("turkey", "carne"), "huevo": ("eggs", "carne"), "huevos": ("eggs", "carne"),
    # pescado
    "pescado": ("fish", "pescado"), "salmon": ("salmon", "pescado"), "atun": ("tuna", "pescado"),
    "bacalao": ("cod", "pescado"), "gambas": ("prawns", "pescado"), "gamba": ("prawns", "pescado"),
    "mejillones": ("mussels", "pescado"), "calamar": ("squid", "pescado"), "sardinas": ("sardines", "pescado"),
    # verdura
    "tomate": ("tomatoes", "verdura"), "tomate cherry": ("cherry tomatoes", "verdura"), "cebolla": ("onion", "verdura"),
    "ajo": ("garlic", "verdura"), "patata": ("potatoes", "verdura"), "zanahoria": ("carrots", "verdura"),
    "pimiento": ("red pepper", "verdura"), "pimiento rojo": ("red pepper", "verdura"), "pimiento verde": ("green pepper", "verdura"),
    "calabacin": ("courgettes", "verdura"), "berenjena": ("aubergine", "verdura"), "espinacas": ("spinach", "verdura"),
    "lechuga": ("lettuce", "verdura"), "pepino": ("cucumber", "verdura"), "champiñones": ("mushrooms", "verdura"),
    "champiñon": ("mushrooms", "verdura"), "setas": ("mushrooms", "verdura"), "brocoli": ("broccoli", "verdura"),
    "coliflor": ("cauliflower", "verdura"), "calabaza": ("pumpkin", "verdura"), "puerro": ("leek", "verdura"),
    "apio": ("celery", "verdura"), "maiz": ("sweetcorn", "verdura"), "judias verdes": ("green beans", "verdura"),
    "guisantes": ("peas", "verdura"), "boniato": ("sweet potato", "verdura"), "aguacate": ("avocado", "verdura"),
    "col": ("cabbage", "verdura"), "remolacha": ("beetroot", "verdura"), "perejil": ("parsley", "verdura"),
    "cilantro": ("coriander", "verdura"), "albahaca": ("basil", "verdura"), "jengibre": ("ginger", "verdura"),
    # fruta
    "limon": ("lemon", "fruta"), "naranja": ("orange", "fruta"), "manzana": ("apple", "fruta"), "platano": ("banana", "fruta"),
    "fresa": ("strawberries", "fruta"), "uvas": ("grapes", "fruta"), "pera": ("pear", "fruta"), "piña": ("pineapple", "fruta"),
    "lima": ("lime", "fruta"), "coco": ("coconut", "fruta"), "arandanos": ("blueberries", "fruta"), "melocoton": ("peach", "fruta"),
    # lácteo
    "leche": ("milk", "lacteo"), "mantequilla": ("butter", "lacteo"), "queso": ("cheese", "lacteo"), "yogur": ("yogurt", "lacteo"),
    "nata": ("double cream", "lacteo"), "crema de leche": ("double cream", "lacteo"), "mozzarella": ("mozzarella", "lacteo"),
    "parmesano": ("parmesan", "lacteo"), "queso feta": ("feta", "lacteo"), "leche de coco": ("coconut milk", "lacteo"),
    # cereal
    "arroz": ("rice", "cereal"), "pasta": ("pasta", "cereal"), "espaguetis": ("spaghetti", "cereal"), "macarrones": ("macaroni", "cereal"),
    "pan": ("bread", "cereal"), "harina": ("flour", "cereal"), "avena": ("oats", "cereal"), "cuscus": ("couscous", "cereal"),
    "tortilla de trigo": ("tortillas", "cereal"), "pan rallado": ("breadcrumbs", "cereal"), "azucar": ("sugar", "cereal"),
    # legumbre
    "garbanzos": ("chickpeas", "legumbre"), "lentejas": ("lentils", "legumbre"), "alubias": ("beans", "legumbre"),
    "frijoles": ("kidney beans", "legumbre"), "judias": ("beans", "legumbre"), "soja": ("soy sauce", "legumbre"),
    # especia y básicos
    "sal": ("salt", "especia"), "pimienta": ("black pepper", "especia"), "comino": ("cumin", "especia"),
    "pimenton": ("paprika", "especia"), "oregano": ("oregano", "especia"), "canela": ("cinnamon", "especia"),
    "curry": ("curry powder", "especia"), "laurel": ("bay leaves", "especia"), "tomillo": ("thyme", "especia"),
    "azafran": ("saffron", "especia"), "aceite": ("olive oil", "especia"), "aceite de oliva": ("olive oil", "especia"),
    "vinagre": ("vinegar", "especia"), "mostaza": ("mustard", "especia"), "miel": ("honey", "especia"),
    "caldo de pollo": ("chicken stock", "especia"), "salsa de tomate": ("tomato puree", "especia"), "tomate frito": ("tomato puree", "especia"),
    # bebida
    "vino": ("white wine", "bebida"), "vino tinto": ("red wine", "bebida"), "vino blanco": ("white wine", "bebida"),
    "cerveza": ("beer", "bebida"), "agua": ("water", "bebida"), "cafe": ("coffee", "bebida"),
}

# nombre en inglés → nombre en español (el primero de la tabla gana)
_REVERSE: dict[str, str] = {}
for _es, (_en, _cat) in INGREDIENTS.items():
    _REVERSE.setdefault(_en, _es)

# Sugerencias para el autocompletado de la app
COMMON_INGREDIENTS = [
    "pollo", "arroz", "ajo", "cebolla", "tomate", "huevo", "patata", "pasta", "zanahoria", "pimiento", "leche", "queso",
    "mantequilla", "aceite de oliva", "sal", "pimienta", "limon", "atun", "ternera", "cerdo", "salmon", "champiñones",
    "espinacas", "calabacin", "garbanzos", "lentejas", "harina", "azucar", "nata", "yogur",
]


def _variants(nombre: str) -> list[str]:
    """El nombre tal cual y sus posibles singulares: «tomates» → tomates, tomate, tomat."""
    variantes = [nombre]
    if len(nombre) > 4 and nombre.endswith("s"):
        variantes.append(nombre[:-1])
    if len(nombre) > 5 and nombre.endswith("es"):
        variantes.append(nombre[:-2])
    return variantes


def lookup(name: str) -> tuple[str, str] | None:
    """(inglés, categoría) del nombre en español, probando también el singular."""
    for candidata in _variants(normalize_name(name)):
        if candidata in INGREDIENTS:
            return INGREDIENTS[candidata]
    return None


def to_english(name: str) -> str:
    """Nombre en inglés si lo conocemos; si no, el mismo nombre (puede que ya esté en inglés)."""
    encontrado = lookup(name)
    return encontrado[0] if encontrado else normalize_name(name)


def to_spanish(name: str) -> str | None:
    """Nombre en español de un ingrediente de TheMealDB, o None si no lo conocemos."""
    for candidata in _variants(normalize_name(name)):
        if candidata in _REVERSE:
            return _REVERSE[candidata]
    return None


def guess_category(name: str) -> str:
    encontrado = lookup(name)
    return encontrado[1] if encontrado else ""
