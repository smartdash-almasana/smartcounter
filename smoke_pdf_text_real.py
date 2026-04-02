import json
import os
import sys
from urllib import error, parse, request

from google.cloud import storage

BASE_URL = "http://127.0.0.1:8000"
BOUNDARY = "----SmartCounterPdfTextRealBoundary7MA4YWxkTrZu0gW"

PROJECT_ID = os.getenv("PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "smartseller-490511"))
BUCKET_NAME = os.getenv("BUCKET_NAME", "smartcounter-review-dev")


def fail(msg, payload=None):
    print(f"FALLO: {msg}")
    if payload is not None:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    sys.exit(1)


def _escape_pdf_text(value):
    return value.replace("\\\\", "\\\\\\\\").replace("(", "\\\\(").replace(")", "\\\\)")


def build_text_pdf_bytes(text="Factura Demo"):
    text = _escape_pdf_text(text)
    stream = f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET\n"
    stream_bytes = stream.encode("latin-1")

    objects = []
    objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        "3 0 obj\n"
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\n"
        "endobj\n"
    )
    objects.append(
        f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n{stream}endstream\nendobj\n"
    )
    objects.append("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n")

    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj.encode("latin-1"))

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("latin-1"))

    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(offsets)} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode("latin-1")
    )
    return bytes(pdf)


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
        fail(f"error de conexion: {e}")


def get_json(url):
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.URLError as e:
        fail(f"error de conexion: {e}")


def load_json_from_gcs(object_name):
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(object_name)
    if not blob.exists():
        fail("normalized_preview_object no existe en GCS", {"object": object_name})
    return json.loads(blob.download_as_text())


tenant_id = "demo001"
pdf_bytes = build_text_pdf_bytes("Factura Demo")

create_data = post_json(
    f"{BASE_URL}/revision-jobs",
    fields={
        "tenant_id": tenant_id,
        "source_type": "pdf_text",
    },
    files={
        "file": {
            "filename": "text_pdf_text.pdf",
            "content": pdf_bytes,
            "content_type": "application/pdf",
        }
    },
)

if create_data.get("ok") is not True:
    fail("create_revision_job ok != true", create_data)

job_id = create_data.get("job_id")
if not isinstance(job_id, str) or not job_id.startswith("rev_"):
    fail("job_id invalido al crear job", create_data)

profile_data = post_json(
    f"{BASE_URL}/revision-jobs/{job_id}/profile",
    fields={"tenant_id": tenant_id},
)
if profile_data.get("ok") is not True:
    fail("profile ok != true", profile_data)

if profile_data.get("next_action") != "guided_curation":
    fail("profile.next_action debe ser guided_curation", profile_data)

normalized_data = post_json(
    f"{BASE_URL}/revision-jobs/{job_id}/normalized-preview",
    fields={"tenant_id": tenant_id},
)
if normalized_data.get("ok") is not True:
    fail("normalized-preview ok != true", normalized_data)

preview_rows = normalized_data.get("preview_rows")
if not isinstance(preview_rows, list) or len(preview_rows) != 1:
    fail("normalized-preview.preview_rows debe tener 1 fila", normalized_data)

job_state = get_json(
    f"{BASE_URL}/revision-jobs/{job_id}?{parse.urlencode({'tenant_id': tenant_id})}"
)
normalized_object = (job_state.get("result") or {}).get("normalized_preview_object")
if not isinstance(normalized_object, str) or not normalized_object.strip():
    fail("result.normalized_preview_object vacio o ausente", job_state)

normalized_payload = load_json_from_gcs(normalized_object)
if normalized_payload.get("row_count_preview") != 1:
    fail("row_count_preview debe ser 1", normalized_payload)

print("OK: pdf_text con texto real cae en guided_curation y normalized-preview con una fila")
print(f"job_id={job_id}")
print(f"normalized_preview_object={normalized_object}")
sys.exit(0)
