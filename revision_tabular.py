import io

import pandas as pd

from revision_common import decide_next_action_from_issues, normalize_text, now_iso

EXPECTED_HEADER_ALIASES = {
    "cliente": ["cliente", "razon social", "empresa", "nombre cliente"],
    "fecha": ["fecha", "fecha comprobante", "fec", "fecha emision"],
    "fecha_vencimiento": ["fecha_vencimiento", "vencimiento", "fecha vto", "fec.vto", "vto"],
    "importe": ["importe", "monto", "saldo", "total"],
    "estado": ["estado", "situacion", "status"],
}


def flatten_aliases():
    out = {}
    for canonical, aliases in EXPECTED_HEADER_ALIASES.items():
        for alias in aliases:
            out[normalize_text(alias)] = canonical
    return out


ALIASES_MAP = flatten_aliases()


def detect_header_row_csv(df_raw: pd.DataFrame, max_scan_rows: int = 5):
    best_idx = 0
    best_score = -1
    best_values = []

    scan_rows = min(max_scan_rows, len(df_raw))
    for idx in range(scan_rows):
        row = [normalize_text(x) for x in df_raw.iloc[idx].tolist()]
        non_empty = sum(1 for x in row if x and x != "nan")
        alias_hits = sum(1 for x in row if x in ALIASES_MAP)
        score = alias_hits * 10 + non_empty
        if score > best_score:
            best_score = score
            best_idx = idx
            best_values = row

    return best_idx, best_values


def map_headers(headers):
    mapped = {}
    unknown = []
    for header in headers:
        norm = normalize_text(header)
        canonical = ALIASES_MAP.get(norm)
        if canonical:
            mapped[header] = canonical
        else:
            unknown.append(header)
    return mapped, unknown


def profile_dataframe(df: pd.DataFrame):
    issues = []
    row_count = len(df)
    col_count = len(df.columns)

    empty_ratio_by_col = {}
    for col in df.columns:
        empty_ratio = float(df[col].isna().mean()) if row_count > 0 else 1.0
        empty_ratio_by_col[str(col)] = round(empty_ratio, 3)

    mapped_headers, unknown_headers = map_headers(df.columns.tolist())

    recognized = sorted(set(mapped_headers.values()))
    required_core = {"cliente", "importe"}
    recognized_core = set(recognized)

    alias_headers_used = [
        str(orig)
        for orig, canon in mapped_headers.items()
        if normalize_text(orig) != canon
    ]
    if alias_headers_used:
        issues.append(
            {
                "code": "alias_headers_used",
                "severity": "medium",
                "message": "Se detectaron encabezados alias que requieren estandarización.",
                "headers": alias_headers_used,
            }
        )

    mapped_df = df.rename(columns=mapped_headers).copy()

    if "importe" in mapped_df.columns:
        importe_as_text = mapped_df["importe"].astype(str)
        currency_noise_ratio = float(
            importe_as_text.str.contains(r"[$€£]", regex=True, na=False).mean()
        )
        if currency_noise_ratio > 0:
            issues.append(
                {
                    "code": "currency_noise",
                    "severity": "medium",
                    "message": "La columna importe contiene símbolos o formato monetario no normalizado.",
                    "ratio": round(currency_noise_ratio, 3),
                }
            )

    for date_col in ["fecha", "fecha_vencimiento"]:
        if date_col in mapped_df.columns:
            date_as_text = mapped_df[date_col].astype(str)
            non_std_date_ratio = float(
                date_as_text.str.contains(r"-|/", regex=True, na=False).mean()
            )
            if non_std_date_ratio > 0:
                issues.append(
                    {
                        "code": f"{date_col}_needs_normalization",
                        "severity": "medium",
                        "message": f"La columna {date_col} requiere normalización de fecha.",
                        "ratio": round(non_std_date_ratio, 3),
                    }
                )

    if row_count == 0:
        issues.append(
            {
                "code": "empty_dataset",
                "severity": "high",
                "message": "El dataset no tiene filas de datos.",
            }
        )

    if col_count < 2:
        issues.append(
            {
                "code": "too_few_columns",
                "severity": "high",
                "message": "Muy pocas columnas para análisis útil.",
            }
        )

    if unknown_headers:
        issues.append(
            {
                "code": "unknown_headers",
                "severity": "medium",
                "message": "Se detectaron encabezados no reconocidos.",
                "headers": [str(h) for h in unknown_headers],
            }
        )

    if not required_core.issubset(recognized_core):
        issues.append(
            {
                "code": "missing_core_fields",
                "severity": "high",
                "message": "Faltan campos clave mínimos para el caso base.",
                "required": sorted(required_core),
                "recognized": recognized,
            }
        )

    mostly_empty_cols = [col for col, ratio in empty_ratio_by_col.items() if ratio >= 0.8]
    if mostly_empty_cols:
        issues.append(
            {
                "code": "mostly_empty_columns",
                "severity": "medium",
                "message": "Hay columnas casi vacías.",
                "columns": mostly_empty_cols,
            }
        )

    duplicate_ratio = 0.0
    if row_count > 0:
        duplicate_ratio = float(df.duplicated().mean())

    if duplicate_ratio > 0:
        issues.append(
            {
                "code": "duplicate_rows",
                "severity": "medium",
                "message": "Se detectaron filas duplicadas.",
                "duplicate_ratio": round(duplicate_ratio, 3),
            }
        )

    confidence_score = 100
    for issue in issues:
        if issue["severity"] == "high":
            confidence_score -= 30
        elif issue["severity"] == "medium":
            confidence_score -= 15
        else:
            confidence_score -= 5

    confidence_score = max(0, min(100, confidence_score))
    next_action = decide_next_action_from_issues(issues)

    return {
        "row_count": row_count,
        "column_count": col_count,
        "columns": [str(c) for c in df.columns.tolist()],
        "mapped_headers": mapped_headers,
        "recognized_fields": recognized,
        "empty_ratio_by_col": empty_ratio_by_col,
        "issues": issues,
        "confidence_score": confidence_score,
        "next_action": next_action,
    }


def read_original_file_bytes(bucket, object_name: str) -> bytes:
    blob = bucket.blob(object_name)
    if not blob.exists():
        raise FileNotFoundError(object_name)
    return blob.download_as_bytes()


def load_dataframe_from_object(bucket, object_name: str):
    lower_name = object_name.lower()
    content = read_original_file_bytes(bucket, object_name)

    if lower_name.endswith(".csv"):
        df_raw = pd.read_csv(io.BytesIO(content), header=None)
        header_row_idx, header_values = detect_header_row_csv(df_raw)
        df = pd.read_csv(io.BytesIO(content), header=header_row_idx)
        return {
            "kind": "csv",
            "sheet_candidates": ["csv_main"],
            "selected_sheet": "csv_main",
            "header_row_idx": int(header_row_idx),
            "header_values": [str(x) for x in header_values],
            "dataframe": df,
        }

    if lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
        excel = pd.ExcelFile(io.BytesIO(content))
        sheet_names = excel.sheet_names
        if not sheet_names:
            raise ValueError("No se encontraron hojas en el workbook.")

        selected_sheet = sheet_names[0]
        df_raw = pd.read_excel(io.BytesIO(content), sheet_name=selected_sheet, header=None)
        header_row_idx, header_values = detect_header_row_csv(df_raw)
        df = pd.read_excel(io.BytesIO(content), sheet_name=selected_sheet, header=header_row_idx)
        return {
            "kind": "excel",
            "sheet_candidates": sheet_names,
            "selected_sheet": selected_sheet,
            "header_row_idx": int(header_row_idx),
            "header_values": [str(x) for x in header_values],
            "dataframe": df,
        }

    raise ValueError("Formato no soportado. Usa CSV o XLSX/XLS.")


def normalize_amount_value(value):
    if pd.isna(value):
        return None

    s = str(value).strip()
    if not s:
        return None

    s = s.replace("$", "").replace("€", "").replace("£", "")
    s = s.replace(" ", "")

    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "." in s:
        parts = s.split(".")
        if len(parts) > 1 and all(part.isdigit() for part in parts):
            if all(len(part) == 3 for part in parts[1:]):
                s = "".join(parts)

    try:
        n = float(s)
        return int(n) if n.is_integer() else n
    except Exception:
        return value


def normalize_date_series(series: pd.Series):
    if series is None:
        return series

    parsed = pd.to_datetime(series, errors="coerce", dayfirst=True)
    return parsed.dt.strftime("%Y-%m-%d").where(parsed.notna(), None)


def run_tabular_profile(bucket, profile):
    original_object_name = profile["stored_object"]
    loaded = load_dataframe_from_object(bucket, original_object_name)
    analysis = profile_dataframe(loaded["dataframe"])
    return {
        "loaded": loaded,
        "analysis": analysis,
    }


def build_tabular_normalized_preview(bucket, profile, result):
    job_id = profile.get("job_id")
    tenant_id = profile.get("tenant_id")
    original_object_name = profile["stored_object"]

    loaded = load_dataframe_from_object(bucket, original_object_name)
    df = loaded["dataframe"].copy()

    original_columns = [str(c) for c in df.columns.tolist()]
    mapped_headers, _ = map_headers(df.columns.tolist())
    df = df.rename(columns=mapped_headers)

    canonical_columns = ["cliente", "fecha", "fecha_vencimiento", "importe", "estado"]

    for col in canonical_columns:
        if col not in df.columns:
            df[col] = None

    changes_applied = []
    if mapped_headers:
        changes_applied.append("headers_mapped")

    if "importe" in df.columns:
        df["importe"] = df["importe"].apply(normalize_amount_value)
        changes_applied.append("importe_normalized")

    if "fecha" in df.columns:
        df["fecha"] = normalize_date_series(df["fecha"])
        changes_applied.append("fecha_normalized")

    if "fecha_vencimiento" in df.columns:
        df["fecha_vencimiento"] = normalize_date_series(df["fecha_vencimiento"])
        changes_applied.append("fecha_vencimiento_normalized")

    df = df[canonical_columns]
    df = df.astype(object).where(pd.notnull(df), None)

    preview_rows = df.head(20).to_dict(orient="records")
    missing_canonical_columns = [c for c in canonical_columns if c not in mapped_headers.values()]

    confidence_score = profile.get("confidence_score")
    issue_codes = [issue.get("code") for issue in profile.get("issues", []) if issue.get("code")]
    warnings = [issue.get("message") for issue in profile.get("issues", []) if issue.get("message")]

    next_action = "apply_auto_curation"
    if result.get("next_action") == "human_review_required":
        next_action = "guided_curation"
    elif "missing_core_fields" in issue_codes:
        next_action = "guided_curation"

    return {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "auto_curate_preview_ready",
        "original_columns": original_columns,
        "mapped_headers": mapped_headers,
        "canonical_columns": canonical_columns,
        "missing_canonical_columns": missing_canonical_columns,
        "preview_rows": preview_rows,
        "row_count_preview": len(preview_rows),
        "issue_codes": issue_codes,
        "warnings": warnings,
        "confidence_score": confidence_score,
        "changes_applied": changes_applied,
        "next_action": next_action,
        "generated_at": now_iso(),
    }
