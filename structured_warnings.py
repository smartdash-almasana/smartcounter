from __future__ import annotations

from typing import Any


ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}


def make_warning(
    *,
    code: str,
    message: str,
    severity: str,
    category: str,
    raw_ref: Any = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_severity = severity if severity in ALLOWED_SEVERITIES else "medium"
    return {
        "code": code,
        "message": message,
        "severity": normalized_severity,
        "category": category,
        "raw_ref": raw_ref,
        "details": details or {},
    }


def w_header_low_confidence(*, best_score: int) -> dict[str, Any]:
    return make_warning(
        code="header_low_confidence",
        message="No se detecto un encabezado claro por aliases esperados.",
        severity="high",
        category="header_detection",
        raw_ref={"best_score": best_score},
        details={"best_score": best_score},
    )


def w_ambiguous_header_candidates(
    *,
    best_row_1based: int,
    best_score: int,
    second_row_1based: int,
    second_score: int,
) -> dict[str, Any]:
    return make_warning(
        code="ambiguous_header_candidates",
        message="Hay multiples filas candidatas de encabezado con puntajes similares.",
        severity="medium",
        category="header_detection",
        raw_ref={
            "candidate_rows_1based": [best_row_1based, second_row_1based],
        },
        details={
            "top_candidates": [
                {"row_1based": best_row_1based, "score": best_score},
                {"row_1based": second_row_1based, "score": second_score},
            ]
        },
    )


def w_header_shifted(*, header_row_1based: int) -> dict[str, Any]:
    return make_warning(
        code="header_shifted",
        message="El encabezado detectado no esta en la primera fila.",
        severity="low",
        category="header_detection",
        raw_ref={"header_row_1based": header_row_1based},
        details={"header_row_1based": header_row_1based},
    )


def w_missing_expected_columns(*, missing: list[str]) -> dict[str, Any]:
    return make_warning(
        code="missing_expected_columns",
        message="Faltan columnas esperadas para el flujo base.",
        severity="high",
        category="column_detection",
        raw_ref={"missing": missing},
        details={"missing": missing},
    )


def w_interleaved_empty_columns(*, columns: list[str]) -> dict[str, Any]:
    return make_warning(
        code="interleaved_empty_columns",
        message="Hay columnas vacias o sin encabezado explicito en la tabla detectada.",
        severity="medium",
        category="table_structure",
        raw_ref={"columns": columns},
        details={"columns": columns},
    )


def w_multiple_table_blocks_possible(
    *,
    gap_start_row_1based: int,
    empty_rows_count: int,
) -> dict[str, Any]:
    return make_warning(
        code="multiple_table_blocks_possible",
        message="Se detectaron cortes de filas vacias con datos posteriores; podria haber mas de un bloque tabular.",
        severity="medium",
        category="table_structure",
        raw_ref={"gap_start_row_1based": gap_start_row_1based},
        details={
            "gap_start_row_1based": gap_start_row_1based,
            "empty_rows_count": empty_rows_count,
        },
    )

