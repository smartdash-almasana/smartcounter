
import re

def normalize_amount(value) -> float:
    """
    Normaliza un string de monto a float de forma simple.
    Diseñado para ser compatible con la lógica de MessageAdapter.
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    
    text = str(value).strip()
    if not text:
        return 0.0
        
    # Limpieza básica
    cleaned = re.sub(r"[^0-9,.]", "", text)
    if not cleaned:
        return 0.0
        
    # Manejo de separadores decimales
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Si hay una sola coma y parece decimal
        if cleaned.count(",") == 1:
            parts = cleaned.split(",")
            if len(parts[1]) <= 2:
                cleaned = parts[0] + "." + parts[1]
            else:
                cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", "")
            
    try:
        return float(cleaned)
    except ValueError:
        return 0.0
