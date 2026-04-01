import json
import sys
from urllib import error, request

URL = "http://127.0.0.1:8000/revision-jobs/rev_fcb826458aa6/google-adapter-plan"

BOUNDARY = "----SmartCounterGoogleAdapterPlanBoundary7MA4YWxkTrZu0gW"


def fail(msg, payload=None):
    print(f"FALLÓ: {msg}")
    if payload is not None:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(1)


def build_body(fields: dict):
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
    lines.append(f"--{BOUNDARY}--")
    lines.append("")
    body = "\r\n".join(lines).encode("utf-8")
    headers = {"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"}
    return body, headers


fields = {"tenant_id": "demo001"}
body, headers = build_body(fields)
req = request.Request(URL, data=body, headers=headers, method="POST")

try:
    with request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
except error.URLError as e:
    fail(f"error de conexión: {e}")

if data.get("ok") is not True:
    fail("ok != true", data)

checks = [
    ("job_id", data.get("job_id"), "rev_fcb826458aa6"),
    ("tenant_id", data.get("tenant_id"), "demo001"),
    ("status", data.get("status"), "google_adapter_plan_ready"),
]

for name, got, expected in checks:
    if got != expected:
        fail(f"{name} esperado={expected} recibido={got}", data)

plan_object = data.get("google_adapter_plan_object")
if not isinstance(plan_object, str) or not plan_object.strip():
    fail("google_adapter_plan_object vacío o ausente", data)

if not plan_object.endswith("/google_adapter_plan.json"):
    fail("google_adapter_plan_object con sufijo inesperado", data)

canonical_columns = data.get("canonical_columns")
expected_columns = ["cliente", "fecha", "fecha_vencimiento", "importe", "estado"]
if canonical_columns != expected_columns:
    fail(f"canonical_columns inesperadas: {canonical_columns}", data)

prompt = data.get("google_adapter_prompt")
if not isinstance(prompt, str) or not prompt.strip():
    fail("google_adapter_prompt vacío o ausente", data)

required_fragments = [
    "Google Sheets",
    "demo_confuso.csv",
    "alias_headers_used",
    "currency_noise",
    "fecha_vencimiento_needs_normalization",
    "cliente, fecha, fecha_vencimiento, importe, estado",
    "Renombrar alias",
    "Normalizar importe",
    "Normalizar fechas",
    "Preservar todas las filas",
]

for fragment in required_fragments:
    if fragment not in prompt:
        fail(f"faltó fragmento esperado en google_adapter_prompt: {fragment}", data)

print("OK: google-adapter-plan consistente")
print(f"google_adapter_plan_object={plan_object}")
sys.exit(0)
