import json
import sys
from urllib import error, request

URL = "http://127.0.0.1:8000/revision-jobs/rev_fcb826458aa6?tenant_id=demo001"

def fail(msg, payload=None):
    print(f"FALLÓ: {msg}")
    if payload is not None:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(1)

try:
    with request.urlopen(URL) as resp:
        data = json.loads(resp.read().decode("utf-8"))
except error.URLError as e:
    fail(f"error de conexión: {e}")

profile = data.get("profile") or {}
result = data.get("result") or {}

checks = [
    ("profile.job_id", profile.get("job_id"), "rev_fcb826458aa6"),
    ("profile.tenant_id", profile.get("tenant_id"), "demo001"),
    ("result.selected_adapter", result.get("selected_adapter"), "google"),
]

for name, got, expected in checks:
    if got != expected:
        fail(f"{name} esperado={expected} recibido={got}", data)

required_non_empty = [
    "handoff_confirmation_object",
    "final_parse_object",
    "final_canonical_object",
]

for key in required_non_empty:
    if not result.get(key):
        fail(f"result.{key} vacío o ausente", data)

status = result.get("status")
next_action = result.get("next_action")

if status not in {"final_parse_ready", "final_parse_invalid"}:
    fail(f"result.status inválido: {status}", data)

if status == "final_parse_ready" and next_action != "done":
    fail(f"para final_parse_ready se esperaba next_action=done y vino {next_action}", data)

if status == "final_parse_invalid" and next_action != "investigate_final_parse":
    fail(
        f"para final_parse_invalid se esperaba next_action=investigate_final_parse y vino {next_action}",
        data,
    )

print("OK: estado del job consistente")
print(f"status={status}")
print(f"next_action={next_action}")
sys.exit(0)
