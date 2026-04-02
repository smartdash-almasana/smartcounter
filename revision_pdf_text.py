import io

from revision_common import decide_next_action_from_issues, now_iso


def load_pdf_text_from_object(bucket, object_name):
    blob = bucket.blob(object_name)
    if not blob.exists():
        raise FileNotFoundError(object_name)

    raw_bytes = blob.download_as_bytes()
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Dependencia faltante para pdf_text: instala 'pypdf' para poder leer PDFs."
        ) from e

    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        decoded = "\n".join(text_parts)
    except Exception as e:
        raise RuntimeError(f"No se pudo leer el PDF en modo texto: {str(e)}") from e

    return {
        "object_name": object_name,
        "full_text": decoded.strip(),
        "page_count": len(reader.pages),
        "char_count": len(decoded.strip()),
    }


def detect_pdf_document_type(full_text):
    text = (full_text or "").lower()
    if "factura" in text:
        return "invoice"
    if "recibo" in text:
        return "receipt"
    if "estado de cuenta" in text:
        return "statement"
    return "unknown"


def extract_pdf_key_fields(full_text, document_type):
    return {
        "document_type": document_type,
        "text_sample": (full_text or "")[:200],
    }


def profile_pdf_text(loaded_pdf):
    full_text = loaded_pdf.get("full_text", "")
    document_type = detect_pdf_document_type(full_text)
    extracted_fields = extract_pdf_key_fields(full_text, document_type)
    has_text = bool((full_text or "").strip())

    issues = []
    if not has_text:
        issues.append(
            {
                "code": "empty_dataset",
                "severity": "high",
                "message": "No se extrajo texto del PDF.",
            }
        )
    else:
        issues.append(
            {
                "code": "pdf_text_manual_review",
                "severity": "medium",
                "message": "Perfilado inicial de PDF en modo texto sin OCR.",
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
    next_action = "human_review_required" if not has_text else decide_next_action_from_issues(issues)

    return {
        "row_count": 0,
        "column_count": 0,
        "columns": [],
        "mapped_headers": {},
        "recognized_fields": sorted(extracted_fields.keys()),
        "empty_ratio_by_col": {},
        "issues": issues,
        "confidence_score": confidence_score,
        "next_action": next_action,
        "document_type": document_type,
        "extracted_fields": extracted_fields,
    }


def run_pdf_text_profile(bucket, profile):
    loaded_pdf = load_pdf_text_from_object(bucket, profile["stored_object"])
    analysis = profile_pdf_text(loaded_pdf)
    return {
        "loaded_pdf": loaded_pdf,
        "analysis": analysis,
    }


def build_pdf_text_normalized_preview(bucket, profile, result):
    job_id = profile.get("job_id")
    tenant_id = profile.get("tenant_id")
    loaded_pdf = load_pdf_text_from_object(bucket, profile["stored_object"])

    document_type = detect_pdf_document_type(loaded_pdf.get("full_text", ""))
    extracted_fields = extract_pdf_key_fields(loaded_pdf.get("full_text", ""), document_type)
    canonical_columns = ["document_type", "text_sample"]
    issue_codes = [issue.get("code") for issue in profile.get("issues", []) if issue.get("code")]
    warnings = [issue.get("message") for issue in profile.get("issues", []) if issue.get("message")]

    next_action = result.get("next_action") or "guided_curation"
    has_text = bool((loaded_pdf.get("full_text") or "").strip())
    preview_rows = [extracted_fields] if has_text else []
    row_count_preview = 1 if has_text else 0

    return {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "auto_curate_preview_ready",
        "original_columns": [],
        "mapped_headers": {},
        "canonical_columns": canonical_columns,
        "missing_canonical_columns": [],
        "preview_rows": preview_rows,
        "row_count_preview": row_count_preview,
        "issue_codes": issue_codes,
        "warnings": warnings,
        "confidence_score": profile.get("confidence_score"),
        "changes_applied": [],
        "next_action": next_action,
        "generated_at": now_iso(),
        "pdf_text_char_count": loaded_pdf.get("char_count", 0),
    }
