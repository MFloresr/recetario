"""Varias fuentes de fotos: Wikipedia → Pexels → Wikimedia Commons."""

import requests

from recipes.services.images import find_dish_image


def pagina(titulo, miniatura="https://upload.wikimedia.org/x.jpg", index=1):
    return {"title": titulo, "thumbnail": {"source": miniatura}, "fullurl": f"https://es.wikipedia.org/wiki/{titulo}", "index": index}


def archivo(nombre, miniatura="https://upload.wikimedia.org/commons/x.jpg", autor="<a>Ana Pérez</a>", index=1):
    return {
        "title": f"Archivo:{nombre}",
        "index": index,
        "imageinfo": [
            {"thumburl": miniatura, "descriptionurl": f"https://commons.wikimedia.org/wiki/Archivo:{nombre}", "extmetadata": {"Artist": {"value": autor}}}
        ],
    }


def test_sin_articulo_pero_con_clave_de_pexels_usa_pexels(wikipedia, settings):
    settings.PEXELS_API_KEY = "clave-pexels"
    wikipedia.pexels = [{"src": {"large": "https://images.pexels.com/lasagna.jpg"}, "photographer": "Juan", "url": "https://www.pexels.com/photo/1/"}]
    foto = find_dish_image("Lasaña de carne tradicional", photo_query="lasaña", photo_query_en="lasagna")
    assert foto == {"url": "https://images.pexels.com/lasagna.jpg", "credit": "Juan (Pexels)", "page": "https://www.pexels.com/photo/1/"}
    llamada = wikipedia.pexels_calls[0]
    assert llamada["headers"]["Authorization"] == "clave-pexels"
    assert llamada["params"]["query"] == "lasagna food dish"  # busca con el nombre en inglés


def test_sin_clave_de_pexels_no_se_llama_a_pexels(wikipedia, settings):
    settings.PEXELS_API_KEY = ""
    wikipedia.pexels = [{"src": {"large": "x"}, "photographer": "J", "url": "u"}]
    assert find_dish_image("Lasaña", photo_query_en="lasagna") is None
    assert wikipedia.pexels_calls == []


def test_wikipedia_gana_a_pexels(wikipedia, settings):
    settings.PEXELS_API_KEY = "k"
    wikipedia.pages = [pagina("Lasaña", "https://img/wiki.jpg")]
    wikipedia.pexels = [{"src": {"large": "https://img/pexels.jpg"}, "photographer": "J", "url": "u"}]
    assert find_dish_image("Lasaña de carne", photo_query="Lasaña")["url"] == "https://img/wiki.jpg"
    assert wikipedia.pexels_calls == []


def test_busca_primero_con_el_nombre_corto_y_luego_con_el_titulo(wikipedia):
    find_dish_image("Arroz con leche casero", photo_query="postre de arroz")
    assert [c["gsrsearch"] for c in wikipedia.calls[:2]] == ["postre de arroz", "Arroz con leche casero"]


def test_commons_acepta_un_archivo_con_el_mismo_nombre_y_da_credito_al_autor(wikipedia):
    wikipedia.commons = [archivo("Gazpacho andaluz.jpg", index=1), archivo("Gazpacho.jpg", "https://img/gaz.jpg", index=2)]
    foto = find_dish_image("Gazpacho", photo_query="gazpacho")
    assert foto["url"] == "https://img/gaz.jpg"
    assert foto["credit"] == "Ana Pérez (Wikimedia Commons)"
    assert foto["page"].endswith("Archivo:Gazpacho.jpg")


def test_commons_rechaza_archivos_de_otro_plato(wikipedia):
    wikipedia.commons = [archivo("Tarta de queso japonesa.jpg"), archivo("Mapa de Gazpacho Valley.jpg")]
    assert find_dish_image("Tarta de queso", photo_query="tarta de queso") is None


def test_si_una_fuente_falla_se_prueba_la_siguiente(wikipedia, settings, monkeypatch):
    settings.PEXELS_API_KEY = "k"
    wikipedia.pexels = [{"src": {"large": "https://img/p.jpg"}, "photographer": "J", "url": "u"}]
    original = wikipedia.get

    def solo_wikipedia_falla(url, params=None, **kw):
        if "es.wikipedia.org" in url:
            raise requests.ConnectionError()
        return original(url, params, **kw)

    monkeypatch.setattr(wikipedia, "get", solo_wikipedia_falla)
    assert find_dish_image("Lasaña", photo_query_en="lasagna")["url"] == "https://img/p.jpg"


def test_un_fallo_temporal_no_se_recuerda_como_sin_foto(wikipedia):
    wikipedia.fail = True
    assert find_dish_image("Paella") is None
    wikipedia.fail = False
    wikipedia.pages = [pagina("Paella", "https://img/paella.jpg")]
    assert find_dish_image("Paella")["url"] == "https://img/paella.jpg"


def test_si_de_verdad_no_hay_foto_se_recuerda_para_no_repetir_la_busqueda(wikipedia):
    assert find_dish_image("Plato inventado") is None
    llamadas = len(wikipedia.calls)
    assert find_dish_image("Plato inventado") is None
    assert len(wikipedia.calls) == llamadas
