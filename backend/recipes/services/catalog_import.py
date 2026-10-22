"""Carga del catálogo de platos desde Wikidata (nombre, país, foto) y TheMealDB (receta, área, categoría)."""

import re
import time
from urllib.parse import unquote

import requests

from ..exceptions import TheMealDBError
from .themealdb import TheMealDBClient

WIKIDATA_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "recetario-catalogo/1.0 (mrsitofull@gmail.com)"
# países con más platos en Wikidata; se consultan de uno en uno porque la consulta global se agota
PAISES = [
    "IT", "ES", "MX", "FR", "ID", "US", "TR", "JP", "CN", "IN", "DE", "GR", "PT", "PE", "AR", "BR", "CO", "CL", "VE", "BO",
    "CU", "GB", "TH", "VN", "KR", "MA", "EG", "LB", "PL", "RU", "HU", "NL", "BE", "CH", "AT", "SE", "UA", "PH", "MY", "IL",
]
# áreas de TheMealDB (gentilicio inglés) → ISO
AREAS = {
    "American": "US", "British": "GB", "Canadian": "CA", "Chinese": "CN", "Croatian": "HR", "Dutch": "NL", "Egyptian": "EG",
    "Filipino": "PH", "French": "FR", "Greek": "GR", "Indian": "IN", "Irish": "IE", "Italian": "IT", "Jamaican": "JM",
    "Japanese": "JP", "Kenyan": "KE", "Malaysian": "MY", "Mexican": "MX", "Moroccan": "MA", "Polish": "PL", "Portuguese": "PT",
    "Russian": "RU", "Spanish": "ES", "Thai": "TH", "Tunisian": "TN", "Turkish": "TR", "Ukrainian": "UA", "Uruguayan": "UY",
    "Vietnamese": "VN",
}
# categoría de TheMealDB → tipo de comida
TIPOS = {"Breakfast": "desayuno", "Dessert": "postre", "Starter": "entrante", "Side": "guarnicion"}
LICENCIA_COMMONS = "Wikimedia Commons"


def consulta_pais(iso: str) -> str:
    return f"""SELECT ?d ?label ?en ?img ?desc WHERE {{
  ?c wdt:P297 "{iso}" .
  ?d wdt:P31/wdt:P279? wd:Q746549 ; wdt:P495 ?c ; wdt:P18 ?img .
  ?d rdfs:label ?label . FILTER(LANG(?label)="es")
  OPTIONAL {{ ?d rdfs:label ?en . FILTER(LANG(?en)="en") }}
  OPTIONAL {{ ?d schema:description ?desc . FILTER(LANG(?desc)="es") }}
}}"""


def foto_commons(url: str) -> tuple[str, str]:
    """Devuelve (url https redimensionada, crédito) de un enlace `Special:FilePath` de Commons."""
    archivo = unquote(url.rsplit("/", 1)[-1])
    https = url.replace("http://", "https://", 1)
    return f"{https}?width=640", f"Commons: {archivo}"[:200]


def platos_wikidata(iso: str, session=None, timeout: int = 60) -> list[dict]:
    """Platos de un país con nombre en español y foto, sin repetidos (una fila por plato)."""
    sesion = session or requests
    respuesta = sesion.get(
        WIKIDATA_URL,
        params={"query": consulta_pais(iso), "format": "json"},
        headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT},
        timeout=timeout,
    )
    respuesta.raise_for_status()
    vistos: dict[str, dict] = {}
    for fila in respuesta.json()["results"]["bindings"]:
        qid = fila["d"]["value"].rsplit("/", 1)[-1]
        nombre = fila["label"]["value"].strip()
        if qid in vistos or re.fullmatch(r"Q\d+", nombre):  # sin etiqueta real, Wikidata devuelve el Q-id
            continue
        imagen, credito = foto_commons(fila["img"]["value"])
        vistos[qid] = {
            "source": "wikidata",
            "source_id": qid,
            "name_es": nombre[:200],
            "name_en": fila.get("en", {}).get("value", "")[:200],
            "description": fila.get("desc", {}).get("value", "")[:400],
            "country": iso,
            "image": imagen,
            "image_credit": credito,
            "image_license": LICENCIA_COMMONS,
        }
    return list(vistos.values())


def _receta(cliente, external_id, espera):
    """Una receta, con un reintento si TheMealDB limita las peticiones (429)."""
    for intento in range(2):
        try:
            return cliente.get_by_id(external_id)
        except TheMealDBError:
            if intento:
                return None
            time.sleep(espera * 10)


def platos_themealdb(client: TheMealDBClient | None = None, ya_cargados: set[str] = frozenset(), pausa: float = 0.4) -> list[dict]:
    """Recetas de TheMealDB (en inglés) con su país y tipo de comida. Salta las ya cargadas y las que fallan."""
    cliente = client or TheMealDBClient()
    platos = []
    for categoria in cliente.list_categories():
        for resumen in cliente.filter_by_category(categoria):
            if resumen["external_id"] in ya_cargados:
                continue
            time.sleep(pausa)
            receta = _receta(cliente, resumen["external_id"], pausa)
            if not receta:
                continue
            platos.append({
                "source": "themealdb",
                "source_id": receta["external_id"],
                "name_es": receta["title"][:200],  # sin traducir todavía: lo completa la IA o el traductor
                "name_en": receta["title"][:200],
                "country": AREAS.get(receta["area"], ""),
                "meal_type": TIPOS.get(receta["category"], ""),
                "ingredients": receta["ingredients"],
                "steps": receta["instructions"],
                "image": receta["image"],
                "image_credit": "TheMealDB",
            })
    return platos
