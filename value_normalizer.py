from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from structured_warnings import make_warning


NULL_TOKENS = {
    "",
    "-",
    "--",
    "n/a",
    "na",
    "null",
    "none",
    "s/d",
    "sd",
    "sin dato",
    "sin datos",
    "no aplica",
    "nulo",
}


def is_null_like(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in NULL_TOKENS
    return False


def normalize_null(value: Any) -> dict[str, Any]:
    if is_null_like(value):
        return {
            "normalized_value": None,
            "confidence": "high",
            "warnings": [],
        }
    return {
        "normalized_value": value,
        "confidence": "high",
        "warnings": [],
    }


def normalize_date(value: Any) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []

    if is_null_like(value):
        return {"normalized_value": None, "confidence": "high", "warnings": warnings}

    if isinstance(value, datetime):
        return {
            "normalized_value": value.date().isoformat(),
            "confidence": "high",
            "warnings": warnings,
        }
    if isinstance(value, date):
        return {
            "normalized_value": value.isoformat(),
            "confidence": "high",
            "warnings": warnings,
        }

    text = str(value).strip()
    if not text:
        return {"normalized_value": None, "confidence": "high", "warnings": warnings}

    day_first_formats = [
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]
    month_first_formats = ["%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y"]

    for fmt in day_first_formats:
        try:
            parsed = datetime.strptime(text, fmt)
            return {
                "normalized_value": parsed.date().isoformat(),
                "confidence": "high",
                "warnings": warnings,
            }
        except ValueError:
            pass

    for fmt in month_first_formats:
        try:
            parsed = datetime.strptime(text, fmt)
            warnings.append(
                make_warning(
                    code="date_inferred_month_first",
                    message="Fecha interpretada con formato mes/dia por incompatibilidad con formato argentino.",
                    severity="medium",
                    category="value_normalization",
                    raw_ref={"input": text},
                )
            )
            return {
                "normalized_value": parsed.date().isoformat(),
                "confidence": "low",
                "warnings": warnings,
            }
        except ValueError:
            pass

    warnings.append(
        make_warning(
            code="date_unparseable",
            message="No se pudo normalizar la fecha con confianza.",
            severity="high",
            category="value_normalization",
            raw_ref={"input": text},
        )
    )
    return {"normalized_value": None, "confidence": "low", "warnings": warnings}


def normalize_amount(value: Any) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []

    if is_null_like(value):
        return {"normalized_value": None, "confidence": "high", "warnings": warnings}

    if isinstance(value, (int, float)):
        return {"normalized_value": float(value), "confidence": "high", "warnings": warnings}

    text = str(value).strip()
    if not text:
        return {"normalized_value": None, "confidence": "high", "warnings": warnings}

    upper = text.upper()
    if "USD" in upper or "US$" in upper or "U$S" in upper:
        currency = "USD"
        if "US$" in upper or "U$S" in upper:
            currency = "US$"
        warnings.append(
            make_warning(
                code="amount_currency_ambiguous",
                message="Monto con moneda no-peso o ambigua para el MVP.",
                severity="high",
                category="value_normalization",
                raw_ref={"input": text},
                details={"detected_currency": currency},
            )
        )
        return {"normalized_value": None, "confidence": "low", "warnings": warnings}

    negative = False
    used_parentheses = False
    used_minus_sign = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        used_parentheses = True
        text = text[1:-1].strip()
    if "-" in text:
        negative = True
        used_minus_sign = True

    cleaned = re.sub(r"[^0-9,.\-]", "", text).replace("-", "")
    if not cleaned:
        warnings.append(
            make_warning(
                code="amount_invalid_format",
                message="Monto sin contenido numerico interpretable.",
                severity="high",
                category="value_normalization",
                raw_ref={"input": value},
            )
        )
        return {"normalized_value": None, "confidence": "low", "warnings": warnings}

    if used_parentheses:
        warnings.append(
            make_warning(
                code="amount_accounting_sign_parentheses",
                message="Monto con signo contable por parentesis.",
                severity="low",
                category="value_normalization",
                raw_ref={"input": value},
            )
        )
    elif used_minus_sign:
        warnings.append(
            make_warning(
                code="amount_negative_sign_detected",
                message="Monto con signo negativo explicito.",
                severity="low",
                category="value_normalization",
                raw_ref={"input": value},
            )
        )

    if "," in cleaned and "." in cleaned:
        warnings.append(
            make_warning(
                code="amount_mixed_separators",
                message="Monto con separadores mixtos (coma y punto); se aplico inferencia de formato.",
                severity="medium",
                category="value_normalization",
                raw_ref={"input": value},
                details={"cleaned": cleaned},
            )
        )
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        if cleaned.count(",") == 1:
            left, right = cleaned.split(",")
            if right.isdigit() and len(right) <= 2:
                cleaned = left + "." + right
            else:
                warnings.append(
                    make_warning(
                        code="amount_separator_inferred_thousands",
                        message="Coma interpretada como separador de miles por patron detectado.",
                        severity="low",
                        category="value_normalization",
                        raw_ref={"input": value},
                        details={"cleaned": cleaned},
                    )
                )
                cleaned = left + right
        else:
            warnings.append(
                make_warning(
                    code="amount_separator_ambiguous",
                    message="Comas multiples detectadas; se forzo normalizacion por remocion de separadores.",
                    severity="medium",
                    category="value_normalization",
                    raw_ref={"input": value},
                    details={"cleaned": cleaned},
                )
            )
            cleaned = cleaned.replace(",", "")
    elif "." in cleaned:
        if cleaned.count(".") == 1:
            left, right = cleaned.split(".")
            if right.isdigit() and len(right) == 3:
                warnings.append(
                    make_warning(
                        code="amount_separator_inferred_thousands",
                        message="Punto interpretado como separador de miles por patron detectado.",
                        severity="low",
                        category="value_normalization",
                        raw_ref={"input": value},
                        details={"cleaned": cleaned},
                    )
                )
                cleaned = left + right
        else:
            parts = cleaned.split(".")
            if all(part.isdigit() for part in parts):
                warnings.append(
                    make_warning(
                        code="amount_separator_ambiguous",
                        message="Puntos multiples detectados; se forzo normalizacion por remocion de separadores.",
                        severity="medium",
                        category="value_normalization",
                        raw_ref={"input": value},
                        details={"cleaned": cleaned},
                    )
                )
                cleaned = "".join(parts)

    try:
        parsed = float(cleaned)
    except ValueError:
        warnings.append(
            make_warning(
                code="amount_invalid_format",
                message="No se pudo normalizar el monto con confianza.",
                severity="high",
                category="value_normalization",
                raw_ref={"input": value, "cleaned": cleaned},
            )
        )
        return {"normalized_value": None, "confidence": "low", "warnings": warnings}

    if negative:
        parsed *= -1

    return {"normalized_value": parsed, "confidence": "high", "warnings": warnings}


def _is_valid_cuit_check_digit(digits: str) -> bool:
    if len(digits) != 11 or not digits.isdigit():
        return False
    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(d) * w for d, w in zip(digits[:10], weights))
    mod = 11 - (total % 11)
    expected = 0 if mod == 11 else 9 if mod == 10 else mod
    return expected == int(digits[-1])


def normalize_cuit(value: Any) -> dict[str, Any]:
    warnings: list[dict[str, Any]] = []

    if is_null_like(value):
        return {"normalized_value": None, "confidence": "high", "warnings": warnings}

    digits = re.sub(r"\D", "", str(value))
    if len(digits) != 11:
        warnings.append(
            make_warning(
                code="cuit_invalid_length",
                message="CUIT/CUIL con longitud invalida.",
                severity="high",
                category="value_normalization",
                raw_ref={"input": value},
                details={"digits_length": len(digits)},
            )
        )
        return {"normalized_value": None, "confidence": "low", "warnings": warnings}

    if not _is_valid_cuit_check_digit(digits):
        warnings.append(
            make_warning(
                code="cuit_invalid_pattern",
                message="CUIT/CUIL no cumple patron valido (digito verificador).",
                severity="high",
                category="value_normalization",
                raw_ref={"input": value},
            )
        )
        return {"normalized_value": None, "confidence": "low", "warnings": warnings}

    formatted = f"{digits[0:2]}-{digits[2:10]}-{digits[10]}"
    return {"normalized_value": formatted, "confidence": "high", "warnings": warnings}


def normalize_value(value: Any, value_type: str) -> dict[str, Any]:
    value_type_normalized = str(value_type or "").strip().lower()

    if value_type_normalized == "date":
        result = normalize_date(value)
    elif value_type_normalized == "amount":
        result = normalize_amount(value)
    elif value_type_normalized == "cuit":
        result = normalize_cuit(value)
    elif value_type_normalized == "null":
        result = normalize_null(value)
    else:
        result = {
            "normalized_value": None,
            "confidence": "low",
            "warnings": [
                make_warning(
                    code="normalizer_unsupported_type",
                    message="Tipo de normalizacion no soportado.",
                    severity="high",
                    category="value_normalization",
                    raw_ref={"value_type": value_type},
                )
            ],
        }

    return {
        "input_value": value,
        "value_type": value_type_normalized,
        **result,
    }
