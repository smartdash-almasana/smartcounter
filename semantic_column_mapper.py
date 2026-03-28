from __future__ import annotations

from typing import Any

from excel_reader import _normalize_text
from structured_warnings import make_warning


DEFAULT_CANONICAL_ALIASES: dict[str, list[str]] = {
    "cliente": ["cliente", "nom cliente", "nombre cliente", "empresa", "razon social", "rsocial"],
    "proveedor": ["proveedor", "prov", "nombre proveedor", "suplidor", "tercero"],
    "razon_social": ["razon social", "rsocial", "denominacion", "empresa"],
    "cuit": ["cuit", "cuil", "doc tercero", "documento", "doc", "nro doc", "ruc"],
    "tipo_comprobante": ["tipo", "tipo comp", "t comprobante", "tipo comprobante"],
    "punto_venta": ["pv", "punto venta", "pto vta", "pvta"],
    "numero_comprobante": ["nro", "nro comp", "nro factura", "num", "folio"],
    "comprobante": ["comprobante", "comp", "factura", "recibo", "remito", "nc", "nd"],
    "importe": ["importe", "impte", "importe total", "valor"],
    "monto": ["monto", "monto neto", "monto total"],
    "total": ["total", "importe total"],
    "neto_gravado": ["neto", "neto gravado", "base imponible", "total sin iva"],
    "saldo": ["saldo", "saldo final"],
    "saldo_pendiente": ["saldo pendiente", "pendiente", "saldo deuda"],
    "deuda": ["deuda", "monto adeudado", "por cobrar"],
    "iva_debito": ["iva debito", "iva deb", "debito fiscal", "iva 21"],
    "iva_credito": ["iva credito", "iva cre", "credito iva", "iva acreditable"],
    "alicuota_iva": ["alicuota iva", "alic", "tasa iva", "porcentaje iva"],
    "retencion": ["retencion", "ret", "imp retenido"],
    "percepcion_iibb": ["percepcion iibb", "perc iibb", "percepcion"],
    "estado": ["estado", "situacion", "status", "condicion"],
    "condicion_pago": ["condicion pago", "terminos", "plazo", "neto 30"],
    "medio_pago": ["medio pago", "forma pago", "canal"],
    "fecha_pago": ["fecha pago", "pago", "fecha cobro", "cancelacion"],
    "cobrado": ["cobrado", "importe cobrado", "pagado"],
    "fecha": ["fecha", "fec", "fecha doc"],
    "fecha_emision": ["fecha emision", "emision", "f emi", "fecha documento"],
    "fecha_vencimiento": ["fecha vencimiento", "vencimiento", "vto", "vence", "fvto", "fec vto"],
    "periodo_fiscal": ["periodo fiscal", "periodo iva", "periodo contable"],
    "fecha_valor": ["fecha valor", "fec valor", "fecha acreditacion"],
    "descripcion": ["descripcion", "detalle", "concepto", "glosa"],
}


def _normalized_alias_dictionary(alias_dictionary: dict[str, list[str]]) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    for canonical, aliases in alias_dictionary.items():
        values = {_normalize_text(canonical)}
        values.update(_normalize_text(alias) for alias in aliases)
        values.discard("")
        normalized[canonical] = sorted(values)
    return normalized


def _candidate_scores(source_norm: str, alias_dictionary: dict[str, list[str]]) -> dict[str, int]:
    scores: dict[str, int] = {}
    for canonical, aliases in alias_dictionary.items():
        if source_norm in aliases:
            scores[canonical] = 100
            continue

        partial_hits = [alias for alias in aliases if alias and (alias in source_norm or source_norm in alias)]
        if partial_hits:
            scores[canonical] = 60
    return scores


def map_semantic_columns(
    columnas_detectadas: dict[str, dict[str, str]],
    alias_dictionary: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    alias_dict = _normalized_alias_dictionary(alias_dictionary or DEFAULT_CANONICAL_ALIASES)
    items: list[dict[str, Any]] = []
    global_warnings: list[dict[str, Any]] = []

    for _, detected in columnas_detectadas.items():
        source_column = str(detected.get("source_column", "")).strip()
        matched_alias = str(detected.get("matched_alias", "")).strip()
        source_norm = _normalize_text(matched_alias or source_column)

        row_warnings: list[dict[str, Any]] = []
        if not source_norm:
            row_warnings.append(
                make_warning(
                    code="mapper_empty_source_column",
                    message="La columna de origen esta vacia o no se pudo normalizar.",
                    severity="high",
                    category="semantic_mapping",
                    raw_ref={"source_column": source_column},
                )
            )
            items.append(
                {
                    "source_column": source_column,
                    "canonical_field": None,
                    "match_status": "unmapped",
                    "confidence": "low",
                    "warnings": row_warnings,
                }
            )
            continue

        scores = _candidate_scores(source_norm, alias_dict)
        if not scores:
            row_warnings.append(
                make_warning(
                    code="mapper_unmapped_column",
                    message="No se encontro campo canonico para la columna detectada.",
                    severity="medium",
                    category="semantic_mapping",
                    raw_ref={"source_column": source_column},
                    details={"normalized_source": source_norm},
                )
            )
            items.append(
                {
                    "source_column": source_column,
                    "canonical_field": None,
                    "match_status": "unmapped",
                    "confidence": "low",
                    "warnings": row_warnings,
                }
            )
            continue

        best_score = max(scores.values())
        best_candidates = sorted([k for k, v in scores.items() if v == best_score])

        if len(best_candidates) > 1:
            ambiguity_reason = "Coincidencia equivalente con multiples campos canonicos segun aliases."
            row_warnings.append(
                make_warning(
                    code="mapper_ambiguous_column",
                    message="La columna coincide con multiples campos canonicos.",
                    severity="high",
                    category="semantic_mapping",
                    raw_ref={"source_column": source_column},
                    details={"normalized_source": source_norm, "candidates": best_candidates},
                )
            )
            items.append(
                {
                    "source_column": source_column,
                    "canonical_field": None,
                    "match_status": "ambiguous",
                    "confidence": "low",
                    "possible_candidates": best_candidates,
                    "ambiguity_reason": ambiguity_reason,
                    "warnings": row_warnings,
                }
            )
            continue

        canonical = best_candidates[0]
        confidence = "high" if best_score == 100 else "medium"
        items.append(
            {
                "source_column": source_column,
                "canonical_field": canonical,
                "match_status": "mapped",
                "confidence": confidence,
                "warnings": row_warnings,
            }
        )

    if not items:
        global_warnings.append(
            make_warning(
                code="mapper_no_columns_input",
                message="No se recibieron columnas detectadas para mapear.",
                severity="high",
                category="semantic_mapping",
            )
        )

    return {
        "mappings": items,
        "warnings": global_warnings,
    }
