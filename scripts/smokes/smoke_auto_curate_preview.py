import json
import sys
from urllib import error, request

BASE_URL = "http://127.0.0.1:8000"
BOUNDARY = "----SmartCounterAutoCuratePreviewBoundary7MA4YWxkTrZu0gW"


def fail(msg, payload=None):
    print(f"FALLÓ: {msg}")
    if payload is not None:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(1)


def build_multipart(fields=None, files=None):
    fields = fields or {}
    files = files or {}

    lines = []

    for name, value in fields.items():
        lines.extend(
            [
                f"--{BOUNDARY}",
                f'Content-Disposition: form-data; name="{name}"',
                "",
                str(value),
            ]
        )

    for name, fileinfo in files.items():
        filename = fileinfo["filename"]
        content = fileinfo["content"]
        content_type = fileinfo.get("content_type", "application/octet-stream")

        lines.extend(
            [
                f"--{BOUNDARY}",
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"',
                f"Content-Type: {content_type}",
                "",
                content,
            ]
        )

    lines.append(f"--{BOUNDARY}--")
    lines.append("")

    body = "\r\n".join(lines).encode("utf-8")
    headers = {"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"}
    return body, headers


def post_json(url, fields=None, files=None):
    body, headers = build_multipart(fields=fields, files=files)
    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.URLError as e:
        fail(f"error de conexión: {e}")


tenant_id = "demo001"

csv_content = """empresa,vto,saldo,situacion
Supermercado Diaz,29/03/2026,$380.000,vencido
"""

create_data = post_json(
    f"{BASE_URL}/revision-jobs",
    fields={
        "tenant_id": tenant_id,
        "source_type": "excel",
    },
    files={
        "file": {
            "filename": "demo_confuso_auto_preview.csv",
            "content": csv_content,
            "content_type": "text/csv",
        }
    },
)

if create_data.get("ok") is not True:
    fail("create_revision_job ok != true", create_data)

job_id = create_data.get("job_id")
if not isinstance(job_id, str) or not job_id.startswith("rev_"):
    fail("job_id inválido al crear job", create_data)
if job_id == "rev_fcb826458aa6":
    fail("el smoke no debe usar el job fijo rev_fcb826458aa6", create_data)

profile_data = post_json(
    f"{BASE_URL}/revision-jobs/{job_id}/profile",
    fields={"tenant_id": tenant_id},
)

if profile_data.get("ok") is not True:
    fail("profile ok != true", profile_data)

data = post_json(
    f"{BASE_URL}/revision-jobs/{job_id}/auto-curate-preview",
    fields={"tenant_id": tenant_id},
)

if data.get("ok") is not True:
    fail("ok != true", data)

checks = [
    ("job_id", data.get("job_id"), job_id),
    ("tenant_id", data.get("tenant_id"), tenant_id),
    ("status", data.get("status"), "auto_curate_preview_ready"),
    ("next_action", data.get("next_action"), "apply_auto_curation"),
]

for name, got, expected in checks:
    if got != expected:
        fail(f"{name} esperado={expected} recibido={got}", data)

preview_object = data.get("auto_curate_preview_object")
if not isinstance(preview_object, str) or not preview_object.strip():
    fail("auto_curate_preview_object vacío o ausente", data)

if not preview_object.endswith("/auto_curate_preview.json"):
    fail("auto_curate_preview_object con sufijo inesperado", data)

canonical_columns = data.get("canonical_columns")
expected_columns = ["cliente", "fecha", "fecha_vencimiento", "importe", "estado"]
if canonical_columns != expected_columns:
    fail(f"canonical_columns inesperadas: {canonical_columns}", data)

missing_canonical_columns = data.get("missing_canonical_columns")
if missing_canonical_columns != ["fecha"]:
    fail(f"missing_canonical_columns inesperadas: {missing_canonical_columns}", data)

changes_applied = data.get("changes_applied")
expected_changes = [
    "headers_mapped",
    "importe_normalized",
    "fecha_normalized",
    "fecha_vencimiento_normalized",
]
if changes_applied != expected_changes:
    fail(f"changes_applied inesperados: {changes_applied}", data)

warnings = data.get("warnings")
expected_warnings = [
    "Se detectaron encabezados alias que requieren estandarización.",
    "La columna importe contiene símbolos o formato monetario no normalizado.",
    "La columna fecha_vencimiento requiere normalización de fecha.",
]
if warnings != expected_warnings:
    fail(f"warnings inesperados: {warnings}", data)

confidence_score = data.get("confidence_score")
if confidence_score != 55:
    fail(f"confidence_score inesperado: {confidence_score}", data)

preview_rows = data.get("preview_rows")
if not isinstance(preview_rows, list) or len(preview_rows) != 1:
    fail("preview_rows debe tener exactamente 1 fila", data)

expected_row = {
    "cliente": "Supermercado Diaz",
    "fecha": None,
    "fecha_vencimiento": "2026-03-29",
    "importe": 380000,
    "estado": "vencido",
}
if preview_rows[0] != expected_row:
    fail(f"preview_rows[0] inesperada: {preview_rows[0]}", data)

print("OK: auto-curate-preview consistente")
print(f"job_id={job_id}")
print(f"auto_curate_preview_object={preview_object}")
sys.exit(0)
