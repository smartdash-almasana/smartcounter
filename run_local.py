import argparse
import json
import re
import sys
from collections import Counter
from collections import defaultdict

import pandas as pd

from excel_reader import get_top_debtors
from semantic_column_mapper import map_semantic_columns
from structured_warnings import make_warning
from tabular_header_detector import detect_tabular_header
from value_normalizer import normalize_value


def _infer_value_type(canonical_field: str | None) -> str | None:
    if not canonical_field:
        return None
    field = canonical_field.lower()
    if field == "cuit":
        return "cuit"
    if "fecha" in field or "vencimiento" in field or "periodo" in field:
        return "date"
    if field in {
        "importe",
        "monto",
        "total",
        "neto_gravado",
        "saldo",
        "saldo_pendiente",
        "deuda",
        "iva_debito",
        "iva_credito",
        "cobrado",
    }:
        return "amount"
    return None


def _is_potentially_conflictive(value: object, value_type: str) -> bool:
    text = str(value or "").strip()
    upper = text.upper()
    if value_type == "amount":
        if any(token in upper for token in ("USD", "US$", "U$S")):
            return True
        if "(" in text and ")" in text:
            return True
        if "-" in text:
            return True
        if re.search(r"[A-Za-z]", text):
            return True
        if "," in text and "." in text:
            return True
        if text.count(",") > 1 or text.count(".") > 1:
            return True
    if value_type == "date":
        m = re.match(r"^\s*(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\s*$", text)
        if m:
            d = int(m.group(1))
            mo = int(m.group(2))
            if d <= 12 and mo <= 12:
                return True
    return False


def run_pipeline_curated(excel_path: str, sheet_name: str | None = None) -> dict:
    detection = detect_tabular_header(excel_path, sheet_name=sheet_name)
    mapping = map_semantic_columns(detection.get("columnas_detectadas", {}))

    warnings_all = list(detection.get("warnings_estructurales", []))
    warnings_all.extend(mapping.get("warnings", []))

    header_row_1based = int(detection.get("header_row_1based", 1))
    selected_sheet = detection.get("sheet")
    df = pd.read_excel(excel_path, sheet_name=selected_sheet, header=header_row_1based - 1)

    normalized_preview: list[dict] = []
    normalization_warning_by_field: Counter[str] = Counter()
    normalization_warning_by_field_and_code: dict[str, Counter[str]] = defaultdict(Counter)
    normalization_warning_examples: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    mapping_items = mapping.get("mappings", [])
    for item in mapping_items:
        source_column = item.get("source_column")
        canonical_field = item.get("canonical_field")
        if not source_column or source_column not in df.columns:
            warnings_all.append(
                make_warning(
                    code="pipeline_source_column_missing_in_dataframe",
                    message="La columna mapeada no esta disponible en la tabla leida.",
                    severity="medium",
                    category="pipeline_review",
                    raw_ref={"source_column": source_column, "canonical_field": canonical_field},
                )
            )
            continue

        value_type = _infer_value_type(canonical_field)
        if not value_type:
            continue

        series = df[source_column]
        non_null_values = [v for v in series.tolist() if v is not None and str(v).strip() != ""]
        if value_type in {"amount", "date"}:
            conflictive = [v for v in non_null_values if _is_potentially_conflictive(v, value_type)]
            regular = [v for v in non_null_values if not _is_potentially_conflictive(v, value_type)]
            values = (conflictive + regular)[:10]
        else:
            values = non_null_values[:10]
        row_results = []
        for raw_value in values:
            normalized = normalize_value(raw_value, value_type)
            normalized_warnings = normalized.get("warnings", [])
            for w in normalized_warnings:
                if (
                    isinstance(w, dict)
                    and w.get("category") == "value_normalization"
                    and canonical_field
                ):
                    field = str(canonical_field)
                    code = w.get("code")
                    normalization_warning_by_field[field] += 1
                    if code:
                        code_str = str(code)
                        normalization_warning_by_field_and_code[field][code_str] += 1
                        examples = normalization_warning_examples[field][code_str]
                        raw_example = str(raw_value)
                        if raw_example not in examples and len(examples) < 3:
                            examples.append(raw_example)
            row_results.append(
                {
                    "source_value": raw_value,
                    "normalized_value": normalized.get("normalized_value"),
                    "confidence": normalized.get("confidence"),
                    "warnings": normalized_warnings,
                }
            )
            warnings_all.extend(normalized_warnings)

        normalized_preview.append(
            {
                "source_column": source_column,
                "canonical_field": canonical_field,
                "value_type": value_type,
                "samples": row_results,
            }
        )

    normalization_warning_counts = Counter(
        w.get("code")
        for w in warnings_all
        if isinstance(w, dict) and w.get("category") == "value_normalization" and w.get("code")
    )

    by_field_and_code_dict = {
        field: dict(counter) for field, counter in normalization_warning_by_field_and_code.items()
    }
    by_field_and_code_examples_dict = {
        field: {code: values for code, values in code_examples.items()}
        for field, code_examples in normalization_warning_examples.items()
    }

    return {
        "file": detection.get("file"),
        "sheet": selected_sheet,
        "header_row_1based": header_row_1based,
        "confianza_header": detection.get("confianza"),
        "semantic_mapping": mapping_items,
        "normalized_preview": normalized_preview,
        "warnings_estructurados": warnings_all,
        "normalization_summary": {
            "warning_counts": dict(normalization_warning_counts),
            "by_field": dict(normalization_warning_by_field),
            "by_field_and_code": by_field_and_code_dict,
            "by_field_and_code_examples": by_field_and_code_examples_dict,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Runner local minimo para SmartCounter usando excel_reader.py"
    )
    parser.add_argument(
        "--excel",
        required=False,
        help="Ruta al archivo Excel a procesar. Ejemplo: --excel .\\data\\archivo.xlsx",
    )
    parser.add_argument(
        "--detector",
        action="store_true",
        help="Ejecuta solo el detector tabular/header real.",
    )
    parser.add_argument(
        "--sheet",
        default=None,
        help="Nombre de hoja a evaluar (opcional). Si no se indica, toma la primera visible.",
    )
    parser.add_argument(
        "--mapper",
        action="store_true",
        help="Ejecuta detector + mapper semantico basico de columnas.",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Ejecuta normalizacion puntual de un valor.",
    )
    parser.add_argument(
        "--pipeline-curated",
        action="store_true",
        help="Ejecuta detector + mapper + normalizacion base y devuelve salida curada para revision.",
    )
    parser.add_argument(
        "--value-type",
        choices=["date", "amount", "cuit", "null"],
        default=None,
        help="Tipo de valor a normalizar cuando se usa --normalize.",
    )
    parser.add_argument(
        "--value",
        default=None,
        help="Valor de entrada a normalizar cuando se usa --normalize.",
    )
    args = parser.parse_args()

    try:
        if args.normalize:
            if not args.value_type:
                raise ValueError("Con --normalize debes informar --value-type.")
            normalized = normalize_value(args.value, args.value_type)
            print(json.dumps(normalized, ensure_ascii=False, indent=2, default=str))
        elif args.pipeline_curated:
            if not args.excel:
                raise ValueError("Con --pipeline-curated debes informar --excel.")
            curated = run_pipeline_curated(args.excel, sheet_name=args.sheet)
            print(json.dumps(curated, ensure_ascii=False, indent=2, default=str))
        elif args.mapper:
            if not args.excel:
                raise ValueError("Con --mapper debes informar --excel.")
            detection = detect_tabular_header(args.excel, sheet_name=args.sheet)
            mapping = map_semantic_columns(detection.get("columnas_detectadas", {}))
            print(
                json.dumps(
                    {
                        "file": detection.get("file"),
                        "sheet": detection.get("sheet"),
                        "header_row_1based": detection.get("header_row_1based"),
                        "confianza_header": detection.get("confianza"),
                        "warnings_estructurales": detection.get("warnings_estructurales", []),
                        "semantic_mapping": mapping,
                    },
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
        elif args.detector:
            if not args.excel:
                raise ValueError("Con --detector debes informar --excel.")
            detection = detect_tabular_header(args.excel, sheet_name=args.sheet)
            print(json.dumps(detection, ensure_ascii=False, indent=2, default=str))
        else:
            if not args.excel:
                raise ValueError("Debes informar --excel para el flujo actual.")
            findings = get_top_debtors(args.excel)
            print(json.dumps(findings, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:
        print(f"ERROR: no se pudo procesar el Excel: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
