import uuid


def build_ingestion_id() -> str:
    return f"ing_{uuid.uuid4().hex[:16]}"
