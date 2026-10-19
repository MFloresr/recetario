"""Normalización de nombres de ingredientes: minúsculas, sin tildes y sin espacios sobrantes."""

import re
import unicodedata

_ENIE = "\u0001"  # la ñ es una letra distinta: se protege para que «caña» no pase a «cana»


def normalize_name(value: str) -> str:
    """«  Tomate   Cherry » → «tomate cherry»; «Pimiento Rojo Asado» → «pimiento rojo asado»; «Jamón» → «jamon»."""
    texto = (value or "").strip().lower().replace("ñ", _ENIE)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.replace(_ENIE, "ñ")
    return re.sub(r"\s+", " ", texto).strip()
