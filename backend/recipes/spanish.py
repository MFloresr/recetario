"""Datos y reglas para mostrar TheMealDB en español sin necesidad de un traductor automático.

Categorías, países, nombres de ingredientes frecuentes y medidas se traducen con tablas. Lo que no
está aquí (títulos, instrucciones, ingredientes raros) lo traduce `services/translation.py`.
"""

import re

from .catalog import to_spanish
from .normalization import normalize_name

CATEGORIES_ES = {
    "Beef": "Ternera", "Breakfast": "Desayuno", "Chicken": "Pollo", "Dessert": "Postre", "Goat": "Cabra",
    "Lamb": "Cordero", "Miscellaneous": "Variado", "Pasta": "Pasta", "Pork": "Cerdo", "Seafood": "Marisco y pescado",
    "Side": "Guarnición", "Starter": "Entrante", "Vegan": "Vegano", "Vegetarian": "Vegetariano",
}

AREAS_ES = {
    "American": "Estadounidense", "British": "Británica", "Canadian": "Canadiense", "Chinese": "China", "Croatian": "Croata",
    "Dutch": "Holandesa", "Egyptian": "Egipcia", "Filipino": "Filipina", "French": "Francesa", "Greek": "Griega",
    "Indian": "India", "Irish": "Irlandesa", "Italian": "Italiana", "Jamaican": "Jamaicana", "Japanese": "Japonesa",
    "Kenyan": "Keniana", "Malaysian": "Malasia", "Mexican": "Mexicana", "Moroccan": "Marroquí", "Polish": "Polaca",
    "Portuguese": "Portuguesa", "Russian": "Rusa", "Spanish": "Española", "Thai": "Tailandesa", "Tunisian": "Tunecina",
    "Turkish": "Turca", "Ukrainian": "Ucraniana", "Uruguayan": "Uruguaya", "Vietnamese": "Vietnamita", "Unknown": "Desconocida",
}

# Ingredientes habituales de TheMealDB que la tabla es→en del catálogo no cubre (en minúsculas)
EXTRA_INGREDIENTS_ES = {
    "chicken thighs": "muslos de pollo", "chicken breasts": "pechugas de pollo", "minced beef": "carne picada de ternera",
    "soy sauce": "salsa de soja", "brown sugar": "azúcar moreno", "caster sugar": "azúcar glas fino", "icing sugar": "azúcar glas",
    "plain flour": "harina común", "self-raising flour": "harina con levadura", "cornstarch": "maicena", "cornflour": "maicena",
    "double cream": "nata para montar", "single cream": "nata líquida", "spring onions": "cebolletas", "red onions": "cebollas rojas",
    "vegetable oil": "aceite vegetal", "sunflower oil": "aceite de girasol", "olive oil": "aceite de oliva", "sesame seed oil": "aceite de sésamo",
    "black pepper": "pimienta negra", "sea salt": "sal marina", "chopped tomatoes": "tomate troceado", "tomato puree": "puré de tomate",
    "tomato ketchup": "kétchup", "garlic clove": "diente de ajo", "garlic cloves": "dientes de ajo", "minced garlic": "ajo picado",
    "ground ginger": "jengibre molido", "fresh ginger": "jengibre fresco", "ground cumin": "comino molido", "cumin seeds": "semillas de comino",
    "chilli powder": "chile en polvo", "chili powder": "chile en polvo", "turmeric": "cúrcuma", "garam masala": "garam masala",
    "bay leaf": "hoja de laurel", "bay leaves": "hojas de laurel", "mixed herbs": "hierbas variadas", "dried oregano": "orégano seco",
    "baking powder": "levadura química", "bicarbonate of soda": "bicarbonato", "vanilla extract": "extracto de vainilla",
    "dark chocolate": "chocolate negro", "lemon juice": "zumo de limón", "lime juice": "zumo de lima", "egg yolks": "yemas de huevo",
    "egg": "huevo", "eggs": "huevos", "egg white": "clara de huevo", "worcestershire sauce": "salsa Worcestershire", "fish sauce": "salsa de pescado",
    "basmati rice": "arroz basmati", "long-grain rice": "arroz de grano largo", "brown rice": "arroz integral", "chicken stock": "caldo de pollo",
    "beef stock": "caldo de ternera", "vegetable stock": "caldo de verduras", "red wine": "vino tinto", "white wine": "vino blanco",
    "coconut milk": "leche de coco", "cheddar cheese": "queso cheddar", "parmesan cheese": "queso parmesano", "feta cheese": "queso feta",
    "green beans": "judías verdes", "kidney beans": "alubias rojas", "chickpeas": "garbanzos", "sweet potato": "boniato", "red pepper": "pimiento rojo",
    "green pepper": "pimiento verde", "red chilli": "chile rojo", "green chilli": "chile verde", "salt": "sal", "pepper": "pimienta", "water": "agua",
    "butter": "mantequilla", "milk": "leche", "sugar": "azúcar", "flour": "harina", "honey": "miel", "ginger": "jengibre", "coriander": "cilantro",
    "parsley": "perejil", "thyme": "tomillo", "rosemary": "romero", "basil": "albahaca", "mint": "menta", "paprika": "pimentón", "cinnamon": "canela",
    "nutmeg": "nuez moscada", "oregano": "orégano", "lemon": "limón", "lime": "lima", "orange": "naranja", "onion": "cebolla", "garlic": "ajo",
    "potatoes": "patatas", "carrots": "zanahorias", "tomatoes": "tomates", "mushrooms": "champiñones", "peas": "guisantes", "spinach": "espinacas",
    "chicken": "pollo", "beef": "ternera", "pork": "cerdo", "lamb": "cordero", "bacon": "beicon", "prawns": "gambas", "salmon": "salmón", "rice": "arroz",
    "pasta": "pasta", "spaghetti": "espaguetis", "bread": "pan", "yogurt": "yogur", "yoghurt": "yogur", "cheese": "queso", "cream": "nata",
}

# (patrón en inglés, sustitución en español) aplicados en orden a las cantidades
_MEASURE_RULES = [
    (r"\btablespoons?\b|\btbsp?\b|\btbs\b|\btblsp?\b|\bTbls\b", "cda."),
    (r"\bteaspoons?\b|\btsp\b", "cdta."),
    (r"\bcups?\b", "taza"),
    (r"\bpinch(es)?\b", "pizca"),
    (r"\bdash\b", "chorrito"),
    (r"\bhandful\b", "puñado"),
    (r"\bcloves?\b", "diente(s)"),
    (r"\bslices?\b", "rodaja(s)"),
    (r"\bsprigs?\b", "ramita(s)"),
    (r"\bcans?\b|\btins?\b", "lata"),
    (r"\bbunch\b", "manojo"),
    (r"\bpieces?\b", "trozo(s)"),
    (r"\blarge\b", "grande"),
    (r"\bsmall\b", "pequeño"),
    (r"\bmedium\b", "mediano"),
    (r"\bfinely\b", "finamente"),
    (r"\broughly\b", "en trozos grandes"),
    (r"\bchopped\b", "picado"),
    (r"\bsliced\b", "en rodajas"),
    (r"\bdiced\b", "en dados"),
    (r"\bminced\b", "picado fino"),
    (r"\bcrushed\b", "machacado"),
    (r"\bgrated\b", "rallado"),
    (r"\bmelted\b", "derretido"),
    (r"\bwhole\b", "entero"),
    (r"\bfresh\b", "fresco"),
    (r"\bground\b", "molido"),
    (r"\bdried\b", "seco"),
    (r"\bto taste\b", "al gusto"),
    (r"\bto serve\b", "para servir"),
    (r"\bto garnish\b", "para decorar"),
    (r"\bas needed\b", "al gusto"),
    (r"\bof\b", "de"),
    (r"\band\b", "y"),
    (r"\boz\b", "oz"),
]


def category_es(valor: str) -> str:
    return CATEGORIES_ES.get(valor, valor)


def area_es(valor: str) -> str:
    return AREAS_ES.get(valor, valor)


def ingredient_known_es(nombre: str) -> str | None:
    """Nombre en español si lo conocemos por tabla (sin traductor automático)."""
    clave = normalize_name(nombre)
    return EXTRA_INGREDIENTS_ES.get(clave) or to_spanish(clave)


def measure_es(medida: str) -> str:
    """«1 tblsp» → «1 cda.»; «2 Large Chopped» → «2 grande picado». Lo que no reconoce se deja igual."""
    texto = medida or ""
    for patron, cambio in _MEASURE_RULES:
        texto = re.sub(patron, cambio, texto, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", texto).strip()
