import csv
import io
import json
import os
import sys
from urllib import error, parse, request

from google.cloud import storage

BASE_URL = "http://127.0.0.1:8000"
BOUNDARY = "----SmartCounterCuratedFinalParsePack08Boundary7MA4YWxkTrZu0gW"

PROJECT_ID = os.getenv("PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "smartseller-490511"))
BUCKET_NAME = os.getenv("BUCKET_NAME", "smartcounter-review-dev")
PACK_PATH = os.path.join("validation_pack_mvp", "08_montos_mixtos_signos_representativo.csv")


def fail(msg, payload=None):
    print(f"FALLÓ: {msg}")
    if payload is not None:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(1)


def build_multipart(fields=None, files=None):
    fields = fields or {}
    files = files or {}
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{BOUNDARY}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    for name, fileinfo in files.items():
        filename = fileinfo["filename"]
        content = fileinfo["content"]
        if isinstance(content, str):
            content = content.encode("utf-8")
        content_type = fileinfo.get("content_type", "application/octet-stream")

        body.extend(f"--{BOUNDARY}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8")
        )
        body.extend(content)
        body.extend(b"\r\n")

    body.extend(f"--{BOUNDARY}--\r\n".encode("utf-8"))
    headers = {"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"}
    return bytes(body), headers


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


def load_text_from_gcs(object_name):
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(object_name)
    if not blob.exists():
        fail("final_canonical_object no existe en GCS", {"object": object_name})
    return blob.download_as_text()


def as_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return float(text)


if not os.path.exists(PACK_PATH):
    fail("No existe el CSV de validación", {"path": PACK_PATH})

with open(PACK_PATH, "r", encoding="utf-8") as fh:
    pack_csv = fh.read()

tenant_id = "demo001"

create_data = post_json(
    f"{BASE_URL}/revision-jobs",
    fields={"tenant_id": tenant_id, "source_type": "excel"},
    files={
        "file": {
            "filename": "seed_pack08.csv",
            "content": pack_csv,
            "content_type": "text/csv",
        }
    },
)
if create_data.get("ok") is not True:
    fail("create revision-job falló", create_data)

job_id = create_data.get("job_id")
if not isinstance(job_id, str) or not job_id.startswith("rev_"):
    fail("job_id inválido", create_data)

profile_data = post_json(f"{BASE_URL}/revision-jobs/{job_id}/profile", fields={"tenant_id": tenant_id})
if profile_data.get("ok") is not True:
    fail("profile falló", profile_data)

curation_plan = post_json(
    f"{BASE_URL}/revision-jobs/{job_id}/curation-plan",
    fields={"tenant_id": tenant_id, "adapter_hint": "google"},
)
if curation_plan.get("ok") is not True:
    fail("curation-plan falló", curation_plan)

select_adapter = post_json(
    f"{BASE_URL}/revision-jobs/{job_id}/select-adapter",
    fields={"tenant_id": tenant_id, "adapter": "google"},
)
if select_adapter.get("ok") is not True:
    fail("select-adapter falló", select_adapter)

for endpoint in [
    "google-adapter-plan",
    "microsoft-adapter-prompt",
    "normalized-preview",
    "handoff-summary",
    "adapter-package",
    "canonical-export",
]:
    data = post_json(f"{BASE_URL}/revision-jobs/{job_id}/{endpoint}", fields={"tenant_id": tenant_id})
    if data.get("ok") is not True:
        fail(f"{endpoint} falló", data)

confirm_data = post_json(
    f"{BASE_URL}/revision-jobs/{job_id}/confirm-handoff",
    fields={"tenant_id": tenant_id, "confirmation": "confirm", "notes": "smoke"},
)
if confirm_data.get("ok") is not True:
    fail("confirm-handoff falló", confirm_data)

curated_return = post_json(
    f"{BASE_URL}/revision-jobs/{job_id}/curated-return",
    fields={"tenant_id": tenant_id},
    files={
        "file": {
            "filename": "08_montos_mixtos_signos_representativo.csv",
            "content": pack_csv,
            "content_type": "text/csv",
        }
    },
)
if curated_return.get("ok") is not True:
    fail("curated-return falló", curated_return)

final_parse = post_json(
    f"{BASE_URL}/revision-jobs/{job_id}/final-parse",
    fields={"tenant_id": tenant_id},
)
if final_parse.get("ok") is not True:
    fail("final-parse falló", final_parse)

status = final_parse.get("status")
next_action = final_parse.get("next_action")
if status not in {"final_parse_ready", "final_parse_invalid"}:
    fail("status final inesperado", final_parse)
if status == "final_parse_ready" and next_action != "done":
    fail("next_action incoherente para final_parse_ready", final_parse)
if status == "final_parse_invalid" and next_action != "investigate_final_parse":
    fail("next_action incoherente para final_parse_invalid", final_parse)

job_state = get_json(f"{BASE_URL}/revision-jobs/{job_id}?{parse.urlencode({'tenant_id': tenant_id})}")
final_canonical_object = (job_state.get("result") or {}).get("final_canonical_object")
if not isinstance(final_canonical_object, str) or not final_canonical_object.endswith("/final_canonical.csv"):
    fail("final_canonical_object faltante/inválido", job_state)

final_csv_text = load_text_from_gcs(final_canonical_object)
rows = list(csv.DictReader(io.StringIO(final_csv_text)))
by_cliente = {row.get("cliente"): row for row in rows}

if "B" not in by_cliente or "C" not in by_cliente or "D" not in by_cliente:
    fail("No se encontraron filas clave B/C/D en final_canonical.csv", rows)

try:
    importe_b = as_float(by_cliente["B"].get("importe"))
except Exception:
    fail("importe de cliente B no es numérico", by_cliente["B"])
if importe_b >= 0:
    fail("importe de cliente B debía ser negativo", by_cliente["B"])

try:
    as_float(by_cliente["C"].get("importe"))
except Exception:
    fail("importe de cliente C debía ser numérico", by_cliente["C"])

try:
    as_float(by_cliente["D"].get("importe"))
    fail("importe de cliente D debía quedar inválido/no numérico", by_cliente["D"])
except Exception:
    pass

print("OK: carril curated-return -> final-parse validado con pack08")
print(f"job_id={job_id}")
print(f"status={status}")
print(f"next_action={next_action}")
print(f"final_canonical_object={final_canonical_object}")
sys.exit(0)
