import json
import sys
from urllib import error, request

BASE_URL = "http://127.0.0.1:8000"
BOUNDARY = "----SmartCounterGetRevisionJobBoundary7MA4YWxkTrZu0gW"


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


def get_json(url):
    req = request.Request(url, method="GET")
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
            "filename": "demo_get_revision_job.csv",
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

data = get_json(f"{BASE_URL}/revision-jobs/{job_id}?tenant_id={tenant_id}")

if data.get("ok") is not True:
    fail("ok != true", data)

required_blocks = [
    "profile",
    "result",
    "job_identity",
    "source_profile",
    "latest_execution",
    "artifacts",
    "status_summary",
]
for key in required_blocks:
    if key not in data:
        fail(f"falta bloque '{key}'", data)

job_identity = data["job_identity"] or {}
source_profile = data["source_profile"] or {}
latest_execution = data["latest_execution"] or {}
artifacts = data["artifacts"] or {}
status_summary = data["status_summary"] or {}

checks = [
    ("job_identity.job_id", job_identity.get("job_id"), job_id),
    ("job_identity.tenant_id", job_identity.get("tenant_id"), tenant_id),
    ("source_profile.status", source_profile.get("status"), "profiled"),
    ("latest_execution.status", latest_execution.get("status"), "profiled"),
    ("status_summary.profile_status", status_summary.get("profile_status"), "profiled"),
    ("status_summary.result_status", status_summary.get("result_status"), "profiled"),
]
for name, got, expected in checks:
    if got != expected:
        fail(f"{name} esperado={expected} recibido={got}", data)

if not isinstance(job_identity.get("prefix"), str) or f"/{job_id}" not in job_identity.get("prefix", ""):
    fail("job_identity.prefix inválido", data)

if not artifacts.get("profile_object"):
    fail("artifacts.profile_object vacío o ausente", data)
if not artifacts.get("result_object"):
    fail("artifacts.result_object vacío o ausente", data)

if "next_action" not in status_summary:
    fail("status_summary.next_action ausente", data)

print("OK: GET /revision-jobs endurecido y consistente")
print(f"job_id={job_id}")
print(f"next_action={status_summary.get('next_action')}")
sys.exit(0)
