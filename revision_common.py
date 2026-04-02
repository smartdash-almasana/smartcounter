import hashlib
from datetime import datetime, timezone

HUMAN_REVIEW_ISSUE_CODES = {
    "missing_core_fields",
    "too_few_columns",
    "empty_dataset",
}

GUIDED_CURATION_ISSUE_CODES = {
    "alias_headers_used",
    "currency_noise",
    "fecha_needs_normalization",
    "fecha_vencimiento_needs_normalization",
    "unknown_headers",
    "mostly_empty_columns",
    "duplicate_rows",
    "pdf_text_manual_review",
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_text(value: str) -> str:
    return str(value).strip().lower().replace("\n", " ").replace("\r", " ")


def decide_next_action_from_issues(issues):
    issue_codes = {issue.get("code") for issue in issues}

    if issue_codes & HUMAN_REVIEW_ISSUE_CODES:
        return "human_review_required"

    if issue_codes & GUIDED_CURATION_ISSUE_CODES:
        return "guided_curation"

    return "direct_parse"
