import json
import sys
from urllib import error, request

URL = "http://127.0.0.1:8000/revision-jobs/rev_fcb826458aa6/select-adapter"

BOUNDARY = "----SmartCounterSelectAdapterBoundary7MA4YWxkTrZu0gW"


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


fields = {
    "tenant_id": "demo001",
    "adapter": "google",
}

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
    ("status", data.get("status"), "adapter_selected"),
    ("selected_adapter", data.get("selected_adapter"), "google"),
]

for name, got, expected in checks:
    if got != expected:
        fail(f"{name} esperado={expected} recibido={got}", data)

selected_adapter_object = data.get("selected_adapter_object")
if not isinstance(selected_adapter_object, str) or not selected_adapter_object.strip():
    fail("selected_adapter_object vacío o ausente", data)

if not selected_adapter_object.endswith("/selected_adapter.json"):
    fail("selected_adapter_object con sufijo inesperado", data)

print("OK: select-adapter consistente")
print(f"selected_adapter={data['selected_adapter']}")
print(f"selected_adapter_object={selected_adapter_object}")
sys.exit(0)
