import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
TENANT_ID = os.getenv("TENANT_ID", "demo001")
JOB_ID = os.getenv("JOB_ID", "rev_330e905da20b")
CURATED_RETURN_PATH = os.getenv(
    "CURATED_RETURN_PATH",
    "validation_pack_mvp/08_montos_mixtos_signos_representativo.csv",
)


def post_multipart(url: str, fields: dict[str, str], file_field: str | None = None, file_path: str | None = None):
    boundary = "----SmartCounterSmokeBoundary7MA4YWxkTrZu0gW"
    body = bytearray()

    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    if file_field and file_path:
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as fh:
            file_bytes = fh.read()

        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        body.extend(b"Content-Type: text/csv\r\n\r\n")
        body.extend(file_bytes)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        return e.code, raw


def get_json(url: str):
    with urllib.request.urlopen(url) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def fail(message: str, extra=None):
    payload = {"ok": False, "error": message}
    if extra is not None:
        payload["extra"] = extra
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(1)


def main():
    if not os.path.exists(CURATED_RETURN_PATH):
        fail("No existe el archivo curated return para el smoke.", {"path": CURATED_RETURN_PATH})

    curated_url = f"{BASE_URL}/revision-jobs/{JOB_ID}/curated-return"
    final_parse_url = f"{BASE_URL}/revision-jobs/{JOB_ID}/final-parse"
    get_job_url = f"{BASE_URL}/revision-jobs/{JOB_ID}?{urllib.parse.urlencode({'tenant_id': TENANT_ID})}"

    curated_status, curated_raw = post_multipart(
        curated_url,
        fields={"tenant_id": TENANT_ID},
        file_field="file",
        file_path=CURATED_RETURN_PATH,
    )

    try:
        curated_json = json.loads(curated_raw)
    except json.JSONDecodeError:
        fail("La respuesta de curated-return no es JSON válido.", {"status": curated_status, "raw": curated_raw})

    if curated_status != 200:
        fail("curated-return no respondió 200.", {"status": curated_status, "body": curated_json})

    if curated_json.get("status") != "curated_return_invalid":
        fail(
            "curated-return no dejó el job en curated_return_invalid.",
            {"status": curated_status, "body": curated_json},
        )

    job_status_code, job_json = get_json(get_job_url)
    if job_status_code != 200:
        fail("GET revision-job no respondió 200.", {"status": job_status_code, "body": job_json})

    result_status = ((job_json or {}).get("result") or {}).get("status")
    if result_status != "curated_return_invalid":
        fail(
            "result.json no quedó en curated_return_invalid tras curated-return inválido.",
            {"result_status": result_status, "body": job_json},
        )

    final_status, final_raw = post_multipart(
        final_parse_url,
        fields={"tenant_id": TENANT_ID},
    )

    try:
        final_json = json.loads(final_raw)
    except json.JSONDecodeError:
        fail("La respuesta de final-parse no es JSON válido.", {"status": final_status, "raw": final_raw})

    expected_detail = "No se puede ejecutar final-parse cuando el curated return es inválido."

    if final_status != 409:
        fail("final-parse no respondió 409.", {"status": final_status, "body": final_json})

    if final_json.get("detail") != expected_detail:
        fail(
            "final-parse respondió 409 pero con detail inesperado.",
            {"status": final_status, "body": final_json},
        )

    print(
        json.dumps(
            {
                "ok": True,
                "job_id": JOB_ID,
                "tenant_id": TENANT_ID,
                "curated_return_status": curated_json.get("status"),
                "final_parse_http_status": final_status,
                "final_parse_detail": final_json.get("detail"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()