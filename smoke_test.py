import json
import os
import sys
from urllib import error, request

BASE_URL = "http://127.0.0.1:8000"
JOB_ID = "rev_fcb826458aa6"
TENANT_ID = "demo001"
GOOD_CSV_PATH = "demo.csv"
BAD_CSV_PATH = "demo_bad.csv"


def _check_file_exists(file_path: str) -> None:
    if not os.path.exists(file_path):
        print(
            f"ERROR: Archivo de prueba no encontrado en '{file_path}'. "
            "Asegúrate de que el archivo existe y el script se ejecuta desde el directorio correcto."
        )
        sys.exit(1)


def _multipart_form_data(fields: dict, file_field_name: str, file_path: str, content_type: str = "text/csv"):
    boundary = "----SmartCounterSmokeBoundary7MA4YWxkTrZu0gW"
    lines = []

    for name, value in fields.items():
        lines.extend(
            [
                f"--{boundary}",
                f'Content-Disposition: form-data; name="{name}"',
                "",
                str(value),
            ]
        )

    filename = os.path.basename(file_path)
    lines.extend(
        [
            f"--{boundary}",
            f'Content-Disposition: form-data; name="{file_field_name}"; filename="{filename}"',
            f"Content-Type: {content_type}",
            "",
        ]
    )

    body = b""
    for line in lines:
        body += line.encode("utf-8") + b"\r\n"

    with open(file_path, "rb") as f:
        body += f.read() + b"\r\n"

    body += f"--{boundary}--\r\n".encode("utf-8")

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    }
    return body, headers


def _form_urlencoded(fields: dict):
    from urllib.parse import urlencode

    body = urlencode(fields).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Content-Length": str(len(body)),
    }
    return body, headers


def _do_post(url: str, fields: dict, file_path: str | None = None):
    if file_path is not None:
        body, headers = _multipart_form_data(fields=fields, file_field_name="file", file_path=file_path)
    else:
        body, headers = _form_urlencoded(fields=fields)

    req = request.Request(url=url, data=body, headers=headers, method="POST")
    with request.urlopen(req) as resp:
        status_code = resp.getcode()
        raw = resp.read().decode("utf-8")
        return status_code, json.loads(raw)


def _handle_request(description: str, url: str, fields: dict, expected_response: dict, file_path: str | None = None):
    print(f"CASO: {description}... ", end="")
    try:
        status_code, response_json = _do_post(url=url, fields=fields, file_path=file_path)

        if status_code != 200:
            print(f"FALLÓ (Status Code: {status_code}, esperado: 200)")
            print(f"Respuesta: {response_json}")
            sys.exit(1)

        for key, value in expected_response.items():
            if response_json.get(key) != value:
                print(f"FALLÓ (Respuesta inesperada para '{key}')")
                print(f"  - Esperado: {value}")
                print(f"  - Recibido:  {response_json.get(key)}")
                print(f"  - Respuesta completa: {response_json}")
                sys.exit(1)

        print("OK")
        return response_json

    except error.HTTPError as e:
        print(f"FALLÓ (HTTP {e.code})")
        try:
            print(f"Respuesta: {e.read().decode('utf-8')}")
        except Exception:
            pass
        sys.exit(1)
    except error.URLError as e:
        print(f"FALLÓ (Error de conexión: {e})")
        print(f"Asegúrate de que el backend FastAPI está corriendo en {BASE_URL}")
        sys.exit(1)
    except Exception as e:
        print(f"FALLÓ ({e})")
        sys.exit(1)


def main():
    print("--- Iniciando Smoke Test para SmartCounter MVP ---")

    _check_file_exists(GOOD_CSV_PATH)
    _check_file_exists(BAD_CSV_PATH)

    common_fields = {"tenant_id": TENANT_ID}

    url_curated = f"{BASE_URL}/revision-jobs/{JOB_ID}/curated-return"
    url_final = f"{BASE_URL}/revision-jobs/{JOB_ID}/final-parse"

    _handle_request(
        description="curated-return con CSV válido",
        url=url_curated,
        fields=common_fields,
        file_path=GOOD_CSV_PATH,
        expected_response={
            "status": "curated_return_valid",
            "next_action": "ready_for_final_parse",
        },
    )

    _handle_request(
        description="final-parse después de CSV válido",
        url=url_final,
        fields=common_fields,
        expected_response={
            "status": "final_parse_ready",
            "next_action": "done",
        },
    )

    _handle_request(
        description="curated-return con CSV inválido",
        url=url_curated,
        fields=common_fields,
        file_path=BAD_CSV_PATH,
        expected_response={
            "status": "curated_return_invalid",
            "next_action": "investigate_curated_return",
        },
    )

    _handle_request(
        description="final-parse después de CSV inválido",
        url=url_final,
        fields=common_fields,
        expected_response={
            "status": "final_parse_invalid",
            "next_action": "investigate_final_parse",
        },
    )

    print("\n--- Smoke Test completado con éxito. Todos los casos pasaron. ---")
    sys.exit(0)


if __name__ == "__main__":
    main()