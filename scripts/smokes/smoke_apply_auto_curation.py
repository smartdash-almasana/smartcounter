import json
import sys
from urllib import error, request

BASE_URL = "http://127.0.0.1:8000"
BOUNDARY = "----SmartCounterApplyAutoCurationBoundary7MA4YWxkTrZu0gW"


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
            "filename": "demo_apply_auto_curation.csv",
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

profile_data = post_json(
    f"{BASE_URL}/revision-jobs/{job_id}/profile",
    fields={"tenant_id": tenant_id},
)
if profile_data.get("ok") is not True:
    fail("profile ok != true", profile_data)

auto_curate_data = post_json(
    f"{BASE_URL}/revision-jobs/{job_id}/auto-curate-preview",
    fields={"tenant_id": tenant_id},
)
if auto_curate_data.get("ok") is not True:
    fail("auto-curate-preview ok != true", auto_curate_data)

apply_data = post_json(
    f"{BASE_URL}/revision-jobs/{job_id}/apply-auto-curation",
    fields={"tenant_id": tenant_id},
)
if apply_data.get("ok") is not True:
    fail("apply-auto-curation ok != true", apply_data)

checks = [
    ("job_id", apply_data.get("job_id"), job_id),
    ("tenant_id", apply_data.get("tenant_id"), tenant_id),
    ("status", apply_data.get("status"), "auto_curation_applied"),
    ("next_action", apply_data.get("next_action"), "ready_for_final_parse"),
    ("row_count", apply_data.get("row_count"), 1),
]

for name, got, expected in checks:
    if got != expected:
        fail(f"{name} esperado={expected} recibido={got}", apply_data)

normalized_object = apply_data.get("normalized_preview_object")
if not isinstance(normalized_object, str) or not normalized_object.endswith("/normalized_preview.json"):
    fail("normalized_preview_object inválido", apply_data)

canonical_export_object = apply_data.get("canonical_export_object")
if not isinstance(canonical_export_object, str) or not canonical_export_object.endswith("/canonical_export.csv"):
    fail("canonical_export_object inválido", apply_data)

expected_columns = ["cliente", "fecha", "fecha_vencimiento", "importe", "estado"]
if apply_data.get("canonical_columns") != expected_columns:
    fail("canonical_columns inesperadas", apply_data)

print("OK: apply-auto-curation consistente")
print(f"job_id={job_id}")
print(f"normalized_preview_object={normalized_object}")
print(f"canonical_export_object={canonical_export_object}")
sys.exit(0)
