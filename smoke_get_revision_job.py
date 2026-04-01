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

if data.get("ok") is not True:
    fail("ok != true", data)

for key in ["profile", "result", "job_identity", "source_profile", "latest_execution", "artifacts", "status_summary"]:
    if key not in data:
        fail(f"falta bloque '{key}'", data)

job_identity = data["job_identity"] or {}
source_profile = data["source_profile"] or {}
latest_execution = data["latest_execution"] or {}
artifacts = data["artifacts"] or {}
status_summary = data["status_summary"] or {}

checks = [
    ("job_identity.job_id", job_identity.get("job_id"), "rev_fcb826458aa6"),
    ("job_identity.tenant_id", job_identity.get("tenant_id"), "demo001"),
    ("source_profile.adapter", source_profile.get("adapter"), "google"),
    ("latest_execution.selected_adapter", latest_execution.get("selected_adapter"), "google"),
]

for name, got, expected in checks:
    if got != expected:
        fail(f"{name} esperado={expected} recibido={got}", data)

required_artifacts = [
    "profile_object",
    "result_object",
    "handoff_confirmation_object",
    "curated_return_object",
    "final_parse_object",
    "final_canonical_object",
]

for key in required_artifacts:
    if not artifacts.get(key):
        fail(f"artifacts.{key} vacío o ausente", data)

result_status = status_summary.get("result_status")
next_action = status_summary.get("next_action")

if result_status not in {"final_parse_ready", "final_parse_invalid"}:
    fail(f"status_summary.result_status inválido: {result_status}", data)

if result_status == "final_parse_ready" and next_action != "done":
    fail(f"para final_parse_ready se esperaba next_action=done y vino {next_action}", data)

if result_status == "final_parse_invalid" and next_action != "investigate_final_parse":
    fail(
        f"para final_parse_invalid se esperaba next_action=investigate_final_parse y vino {next_action}",
        data,
    )

print("OK: GET /revision-jobs endurecido y consistente")
print(f"result_status={result_status}")
print(f"next_action={next_action}")
sys.exit(0)
