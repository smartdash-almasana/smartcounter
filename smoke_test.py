import json
import sys
from urllib import error, request

BASE_URL = "http://127.0.0.1:8000"
BOUNDARY = "----SmartCounterSmokeTestBoundary7MA4YWxkTrZu0gW"


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
            "filename": "demo_smoke_test_base.csv",
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

checks = [
    ("job_id", profile_data.get("job_id"), job_id),
    ("tenant_id", profile_data.get("tenant_id"), tenant_id),
    ("status", profile_data.get("status"), "profiled"),
]

for name, got, expected in checks:
    if got != expected:
        fail(f"{name} esperado={expected} recibido={got}", profile_data)

next_action = profile_data.get("next_action")
if next_action not in {"guided_curation", "human_review_required", "direct_parse"}:
    fail(f"next_action inválido para flujo base: {next_action}", profile_data)

issues = profile_data.get("issues")
if not isinstance(issues, list):
    fail("issues inválido: se esperaba lista", profile_data)

confidence_score = profile_data.get("confidence_score")
if not isinstance(confidence_score, int):
    fail("confidence_score inválido: se esperaba entero", profile_data)

selected_sheet = profile_data.get("selected_sheet")
if selected_sheet != "csv_main":
    fail(f"selected_sheet inesperado: {selected_sheet}", profile_data)

header_row_idx = profile_data.get("header_row_idx")
if header_row_idx != 0:
    fail(f"header_row_idx inesperado: {header_row_idx}", profile_data)

print("OK: smoke_test flujo base consistente")
print(f"job_id={job_id}")
print(f"status={profile_data['status']}")
print(f"next_action={next_action}")
sys.exit(0)