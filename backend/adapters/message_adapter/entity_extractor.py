"""
Extracción de entidades (personas, montos, fechas) con seguridad ReDoS.
Versión híbrida: tokenización para personas, regex segura para montos.
"""
import re
from typing import List, Dict, Set
from backend.utils.number_utils import normalize_amount

# Conjunto de palabras clave para fechas (sin mapeo, solo detección)
_DATE_KEYWORDS: Set[str] = {
    "hoy", "mañana", "pasado manana", "ayer", "manana",
    "lunes", "martes", "miercoles", "miércoles", "jueves", "viernes",
    "sabado", "sábado", "domingo"
}

# Stopwords en español para evitar falsos positivos en nombres
_STOPWORDS: Set[str] = {
    "a", "de", "con", "para", "por", "el", "la", "los", "las", "un", "una",
    "lo", "se", "no", "que", "y", "en", "o", "es", "le", "les", "me", "su",
    "sus", "del", "al", "ya", "si", "te", "tu"
}

# Indicadores que suelen preceder a una persona
_PERSON_INDICATORS: Set[str] = {
    "a", "de", "con", "para", "al", "del"
}

def extract_entities(text: str) -> Dict:
    """
    Extrae entidades estructuradas del texto.
    Retorna un diccionario con:
        - primary_person (str)
        - amount (float)                 # Mantenemos float para compatibilidad con ImageAdapter
        - date (str)
        - all_persons (List[str])
        - all_amounts (List[float])
    """
    fallback = {
        "primary_person": "Unknown",
        "amount": 0.0,
        "date": "",
        "all_persons": [],
        "all_amounts": []
    }
    if not text:
        return fallback

    # 1. Extracción de fechas mediante tokenización simple
    tokens = text.lower().split()
    detected_dates = []
    for kw in _DATE_KEYWORDS:
        # Búsqueda exacta del keyword como frase (seguro contra ReDoS)
        if kw in text.lower():
            detected_dates.append(kw)
    primary_date = detected_dates[0] if detected_dates else ""

    # 2. Extracción de montos usando regex segura (acotada por normalize_amount)
    #    Mantenemos float para no romper compatibilidad.
    raw_amounts = re.findall(r'\b\d{1,15}(?:[.,]\d{1,2})?\b', text)
    parsed_amounts = []
    for am_str in raw_amounts:
        norm = normalize_amount(am_str)
        if norm > 0.0:
            parsed_amounts.append(norm)
    primary_amount = parsed_amounts[0] if parsed_amounts else 0.0

    # 3. Extracción de personas usando tokenización simple (SIN REGEX COMPLEJA)
    candidates = []
    words = text.lower().split()
    n = len(words)
    for i, w in enumerate(words):
        # Si la palabra actual es un indicador de persona y hay siguiente palabra
        if w in _PERSON_INDICATORS and i + 1 < n:
            next_word = words[i + 1].strip('.,;:!?')
            # Validaciones: no stopword, no fecha, longitud razonable, solo letras
            if (next_word not in _STOPWORDS and
                next_word not in _DATE_KEYWORDS and
                2 <= len(next_word) <= 25 and
                next_word.isalpha()):
                candidates.append(next_word.title())

    # Deducir duplicados preservando orden
    seen = set()
    unique_persons = []
    for p in candidates:
        if p.lower() not in seen:
            seen.add(p.lower())
            unique_persons.append(p)

    return {
        "primary_person": unique_persons[0] if unique_persons else "Unknown",
        "amount": primary_amount,
        "date": primary_date,
        "all_persons": unique_persons,
        "all_amounts": parsed_amounts
    }
