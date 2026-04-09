"""
Detector de intenciones básico para MessageAdapter.
Extrae intenciones basadas en palabras clave.
"""
from typing import List, Tuple

def detect_intents(text: str) -> Tuple[str, List[str]]:
    """
    Detecta la intención primaria y todas las intenciones presentes.
    """
    intents = []
    text_lower = text.lower()
    
    # Mapeo simple de palabras clave a intenciones
    mapping = {
        "pagar": "payment",
        "pago": "payment",
        "cobrar": "collection",
        "cobro": "collection",
        "recordar": "reminder",
        "aviso": "reminder",
        "agendar": "schedule",
        "cita": "schedule"
    }
    
    for kw, intent in mapping.items():
        if kw in text_lower:
            intents.append(intent)
    
    # Deducir duplicados preservando orden
    seen = set()
    unique_intents = []
    for i in intents:
        if i not in seen:
            seen.add(i)
            unique_intents.append(i)
            
    primary_intent = unique_intents[0] if unique_intents else "unknown"
    return primary_intent, unique_intents
