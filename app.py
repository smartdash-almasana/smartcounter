import os
import json
import uuid
import logging

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query

from backend.routes.module_ingestions import router as module_ingestions_router
from backend.api.digest_router import router as digest_router
from backend.api.endpoints.message_ingest import router as message_ingest_router
from backend.api.endpoints.action_jobs import router as action_jobs_router
from backend.digest_builder import DigestBuilder
from backend.services.artifact_store import ArtifactStore
from revision_common import decide_next_action_from_issues, normalize_text, now_iso, sha256_bytes
from revision_pdf_text import (
    build_pdf_text_normalized_preview,
    run_pdf_text_profile,
)
from revision_tabular import (
    build_tabular_normalized_preview,
    load_dataframe_from_object,
    map_headers,
    normalize_amount_value,
    normalize_date_series,
    profile_dataframe,
    run_tabular_profile,
)

app = FastAPI()
app.include_router(module_ingestions_router)
app.include_router(digest_router)
app.include_router(message_ingest_router)
app.include_router(action_jobs_router)
app.state.artifact_store = ArtifactStore()

PROJECT_ID = os.getenv("PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "smartseller-490511"))
BUCKET_NAME = os.getenv("BUCKET_NAME", "smartcounter-review-dev")
LOCAL_DEV = os.getenv("LOCAL_DEV") == "true"
logger = logging.getLogger(__name__)

if not LOCAL_DEV:
    try:
        from google.cloud import storage
    except ImportError:
        storage = None
        logger.warning("Google Cloud Storage not available (local dev mode)")

    if storage is not None:
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
    else:
        storage_client = None
        bucket = None
else:
    storage = None
    storage_client = None
    bucket = None

ALLOWED_ADAPTERS = {"google", "microsoft"}


def raise_if_job_confirmed(result: dict):
    if result.get("status") == "handoff_confirmed":
        raise HTTPException(
            status_code=409,
            detail="El job ya fue confirmado y quedó cerrado para nuevas mutaciones.",
        )


def load_json_from_gcs(object_name: str):
    blob = bucket.blob(object_name)
    if not blob.exists():
        raise FileNotFoundError(object_name)
    return json.loads(blob.download_as_text())


def save_json_to_gcs(object_name: str, payload: dict):
    bucket.blob(object_name).upload_from_string(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        content_type="application/json",
    )


def _is_effectively_empty(value) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    return str(value).strip() == ""


def _normalize_importe_curated(value):
    if pd.isna(value):
        return None

    s = str(value).strip()
    if not s:
        return None

    is_paren_negative = s.startswith("(") and s.endswith(")")
    if is_paren_negative:
        s = s[1:-1].strip()

    s = (
        s.replace("US$", "")
        .replace("U$S", "")
        .replace("USD", "")
        .replace("usd", "")
        .strip()
    )

    normalized = normalize_amount_value(s)
    if isinstance(normalized, (int, float)):
        if is_paren_negative:
            return -abs(normalized)
        return normalized
    return None


def build_export_final_from_canonical(df_canonical: pd.DataFrame, original_importe_series: pd.Series) -> pd.DataFrame:
    df_export_final = df_canonical.copy()

    if "importe" not in df_export_final.columns:
        return df_export_final

    export_importe_values = []
    for idx, canonical_value in df_canonical["importe"].items():
        raw_value = original_importe_series.loc[idx] if idx in original_importe_series.index else None

        if canonical_value is None:
            if _is_effectively_empty(raw_value):
                export_importe_values.append(None)
            else:
                export_importe_values.append(str(raw_value).strip())
        else:
            export_importe_values.append(canonical_value)

    df_export_final["importe"] = export_importe_values
    return df_export_final


def canonicalize_curated_return_object(curated_return_object: str):
    loaded = load_dataframe_from_object(bucket, curated_return_object)
    raw_df = loaded["dataframe"].copy()

    mapped_headers, unknown_headers = map_headers(raw_df.columns.tolist())
    recognized_fields = sorted(set(mapped_headers.values()))

    df = raw_df.rename(columns=mapped_headers).copy()
    canonical_columns = ["cliente", "fecha", "fecha_vencimiento", "importe", "estado"]

    for col in canonical_columns:
        if col not in df.columns:
            df[col] = None

    original_importe_series = (
        df["importe"].copy()
        if "importe" in df.columns
        else pd.Series([None] * len(df), index=df.index)
    )
    original_fecha_series = (
        df["fecha"].copy()
        if "fecha" in df.columns
        else pd.Series([None] * len(df), index=df.index)
    )
    original_fecha_vto_series = (
        df["fecha_vencimiento"].copy()
        if "fecha_vencimiento" in df.columns
        else pd.Series([None] * len(df), index=df.index)
    )

    if "importe" in df.columns:
        df["importe"] = df["importe"].apply(_normalize_importe_curated)

    if "fecha" in df.columns:
        df["fecha"] = normalize_date_series(df["fecha"])

    if "fecha_vencimiento" in df.columns:
        df["fecha_vencimiento"] = normalize_date_series(df["fecha_vencimiento"])

    df = df[canonical_columns]
    df = df.astype(object).where(pd.notnull(df), None)

    row_count = len(df)
    duplicate_row_count_raw = int(raw_df.duplicated().sum()) if len(raw_df) > 0 else 0
    duplicate_row_count = int(df.duplicated().sum()) if row_count > 0 else 0

    null_cliente_count = int(df["cliente"].isna().sum()) if "cliente" in df.columns else row_count
    null_importe_count = int(df["importe"].isna().sum()) if "importe" in df.columns else row_count

    original_importe_non_empty = original_importe_series.apply(lambda v: not _is_effectively_empty(v))
    original_fecha_non_empty = original_fecha_series.apply(lambda v: not _is_effectively_empty(v))
    original_fecha_vto_non_empty = original_fecha_vto_series.apply(lambda v: not _is_effectively_empty(v))

    invalid_importe_count = int(
        (original_importe_non_empty & pd.Series(df["importe"], index=df.index).isna()).sum()
    ) if len(original_importe_series) > 0 else 0

    invalid_fecha_count = int(
        (original_fecha_non_empty & pd.Series(df["fecha"], index=df.index).isna()).sum()
    ) if len(original_fecha_series) > 0 else 0

    invalid_fecha_vencimiento_count = int(
        (
            original_fecha_vto_non_empty
            & pd.Series(df["fecha_vencimiento"], index=df.index).isna()
        ).sum()
    ) if len(original_fecha_vto_series) > 0 else 0

    return {
        "raw_df": raw_df,
        "df_canonical": df,
        "df_export_final": build_export_final_from_canonical(df, original_importe_series),
        "original_importe_series": original_importe_series,
        "canonical_columns": canonical_columns,
        "mapped_headers": mapped_headers,
        "recognized_fields": recognized_fields,
        "unknown_headers": unknown_headers,
        "row_count": row_count,
        "duplicate_row_count_raw": duplicate_row_count_raw,
        "duplicate_row_count": duplicate_row_count,
        "invalid_fecha_count": invalid_fecha_count,
        "invalid_fecha_vencimiento_count": invalid_fecha_vencimiento_count,
        "invalid_importe_count": invalid_importe_count,
        "null_cliente_count": null_cliente_count,
        "null_importe_count": null_importe_count,
    }


@app.get("/health")
def health():
    return {"ok": True, "project": PROJECT_ID, "bucket": BUCKET_NAME}


@app.post("/revision-jobs")
async def create_revision_job(
    tenant_id: str = Form(...),
    source_type: str = Form("excel"),
    file: UploadFile = File(...),
):
    job_id = f"rev_{uuid.uuid4().hex[:12]}"
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"

    content = await file.read()
    file_hash = sha256_bytes(content)

    original_object_name = f"{prefix}/original_{file.filename}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"

    blob = bucket.blob(original_object_name)
    blob.upload_from_string(content, content_type=file.content_type or "application/octet-stream")

    profile = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "uploaded",
        "source_type": source_type,
        "adapter": None,
        "original_filename": file.filename,
        "stored_object": original_object_name,
        "sha256": file_hash,
        "sheet_candidates": [],
        "selected_sheet": None,
        "header_row_idx": None,
        "header_values": [],
        "issues": [],
        "confidence_score": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }

    result = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "pending_profile",
        "summary": None,
        "validated_schema": None,
        "next_action": "run_profiler",
    }

    save_json_to_gcs(profile_object_name, profile)
    save_json_to_gcs(result_object_name, result)

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "uploaded",
        "prefix": prefix,
        "original_object": original_object_name,
    }


@app.post("/revision-jobs/{job_id}/profile")
def run_profile(job_id: str, tenant_id: str = Form(...)):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"

    try:
        profile = load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        source_type = normalize_text(profile.get("source_type") or "excel")

        if source_type in {"excel", "csv"}:
            profiled = run_tabular_profile(bucket, profile)
            loaded = profiled["loaded"]
            analysis = profiled["analysis"]
            profile["sheet_candidates"] = loaded["sheet_candidates"]
            profile["selected_sheet"] = loaded["selected_sheet"]
            profile["header_row_idx"] = loaded["header_row_idx"]
            profile["header_values"] = loaded["header_values"]
        elif source_type == "pdf_text":
            profiled = run_pdf_text_profile(bucket, profile)
            analysis = profiled["analysis"]
            profile["sheet_candidates"] = []
            profile["selected_sheet"] = None
            profile["header_row_idx"] = None
            profile["header_values"] = []
        else:
            raise HTTPException(status_code=400, detail=f"source_type no soportado: {source_type}")

        profile["status"] = "profiled"
        profile["issues"] = analysis["issues"]
        profile["confidence_score"] = analysis["confidence_score"]
        profile["updated_at"] = now_iso()

        result = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "profiled",
            "summary": {
                "row_count": analysis["row_count"],
                "column_count": analysis["column_count"],
                "recognized_fields": analysis["recognized_fields"],
            },
            "validated_schema": {
                "columns": analysis["columns"],
                "mapped_headers": analysis["mapped_headers"],
            },
            "next_action": analysis["next_action"],
        }

        save_json_to_gcs(profile_object_name, profile)
        save_json_to_gcs(result_object_name, result)

        return {
            "ok": True,
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "profiled",
            "confidence_score": analysis["confidence_score"],
            "issues": analysis["issues"],
            "next_action": analysis["next_action"],
            "selected_sheet": profile["selected_sheet"],
            "header_row_idx": profile["header_row_idx"],
        }

    except Exception as e:
        fail_result = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "failed",
            "summary": None,
            "validated_schema": None,
            "next_action": "investigate_error",
            "error": str(e),
        }
        save_json_to_gcs(result_object_name, fail_result)
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/revision-jobs/{job_id}")
def get_revision_job(job_id: str, tenant_id: str):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"

    try:
        profile = load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        result = None

    result = result or {}
    profile = profile or {}

    artifacts = {
        "profile_object": profile_object_name,
        "result_object": result_object_name,
        "selected_adapter_object": result.get("selected_adapter_object"),
        "google_adapter_plan_object": result.get("google_adapter_plan_object"),
        "microsoft_adapter_prompt_object": result.get("microsoft_adapter_prompt_object"),
        "normalized_preview_object": result.get("normalized_preview_object"),
        "canonical_export_object": result.get("canonical_export_object"),
        "adapter_package_object": result.get("adapter_package_object"),
        "handoff_summary_object": result.get("handoff_summary_object"),
        "handoff_confirmation_object": result.get("handoff_confirmation_object"),
        "curated_return_object": result.get("curated_return_object"),
        "curated_return_validation_object": result.get("curated_return_validation_object"),
        "final_parse_object": result.get("final_parse_object"),
        "final_canonical_object": result.get("final_canonical_object"),
    }

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "profile": profile,
        "result": result,
        "job_identity": {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "prefix": prefix,
        },
        "source_profile": {
            "status": profile.get("status"),
            "source_type": profile.get("source_type"),
            "original_filename": profile.get("original_filename"),
            "stored_object": profile.get("stored_object"),
            "adapter": profile.get("adapter"),
            "selected_sheet": profile.get("selected_sheet"),
            "header_row_idx": profile.get("header_row_idx"),
            "header_values": profile.get("header_values", []),
            "confidence_score": profile.get("confidence_score"),
            "issues": profile.get("issues", []),
            "created_at": profile.get("created_at"),
            "updated_at": profile.get("updated_at"),
        },
        "latest_execution": {
            "status": result.get("status"),
            "next_action": result.get("next_action"),
            "selected_adapter": result.get("selected_adapter"),
            "curated_return_valid": result.get("curated_return_valid"),
            "curated_return_filename": result.get("curated_return_filename"),
            "curated_return_received_at": result.get("curated_return_received_at"),
            "curated_return_summary": result.get("curated_return_summary"),
            "final_parse_completed_at": result.get("final_parse_completed_at"),
            "handoff_confirmed_at": result.get("handoff_confirmed_at"),
        },
        "artifacts": artifacts,
        "status_summary": {
            "profile_status": profile.get("status"),
            "result_status": result.get("status"),
            "next_action": result.get("next_action"),
            "has_handoff_confirmation": bool(result.get("handoff_confirmation_object")),
            "has_curated_return": bool(result.get("curated_return_object")),
            "has_final_parse": bool(result.get("final_parse_object")),
            "has_final_canonical": bool(result.get("final_canonical_object")),
        },
    }


@app.post("/revision-jobs/{job_id}/curation-plan")
def build_curation_plan(job_id: str, tenant_id: str = Form(...), adapter_hint: str = Form("auto")):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"
    curation_plan_object_name = f"{prefix}/curation_plan.json"

    try:
        profile = load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="result.json no encontrado")

    raise_if_job_confirmed(result)

    confidence_score = profile.get("confidence_score")
    issues = profile.get("issues", [])
    original_filename = profile.get("original_filename", "")
    recognized_fields = (result.get("summary") or {}).get("recognized_fields", [])

    if confidence_score is None:
        raise HTTPException(status_code=400, detail="El job todavía no fue perfilado")

    decision = decide_next_action_from_issues(issues)

    if decision == "direct_parse":
        recommended_adapter = None
        instructions = [
            "El archivo tiene estructura suficiente para pasar al parser normal.",
        ]
    elif decision == "guided_curation":
        if adapter_hint == "microsoft":
            recommended_adapter = "microsoft"
        elif adapter_hint == "google":
            recommended_adapter = "google"
        else:
            if original_filename.lower().endswith((".xlsx", ".xls")):
                recommended_adapter = "microsoft"
            else:
                recommended_adapter = "google"

        if recommended_adapter == "microsoft":
            instructions = [
                "Abrir el archivo en Excel.",
                "Usar Copilot para convertir la hoja en tabla estructurada.",
                "Normalizar encabezados a nombres claros y consistentes.",
                "No inventar datos faltantes.",
                "Guardar una versión curada y re-subirla.",
            ]
        else:
            instructions = [
                "Abrir o importar el archivo en Google Sheets.",
                "Aplicar una normalización guiada con Apps Script o Gemini.",
                "Unificar encabezados y tipos básicos.",
                "Conservar filas ambiguas marcadas en observaciones.",
                "Exportar o validar la versión curada.",
            ]
    else:
        recommended_adapter = None
        instructions = [
            "El archivo presenta demasiada ambigüedad para curación automática segura.",
            "Se recomienda revisión humana asistida antes de continuar.",
        ]

    curation_plan = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "curation_planned",
        "decision": decision,
        "recommended_adapter": recommended_adapter,
        "adapter_hint": adapter_hint,
        "confidence_score": confidence_score,
        "recognized_fields": recognized_fields,
        "issues": issues,
        "instructions": instructions,
    }

    save_json_to_gcs(curation_plan_object_name, curation_plan)

    result["next_action"] = decision
    save_json_to_gcs(result_object_name, result)

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "decision": decision,
        "recommended_adapter": recommended_adapter,
        "instructions": instructions,
    }


@app.post("/revision-jobs/{job_id}/select-adapter")
def select_adapter(job_id: str, tenant_id: str = Form(...), adapter: str = Form(...)):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"
    curation_plan_object_name = f"{prefix}/curation_plan.json"
    selection_object_name = f"{prefix}/selected_adapter.json"

    adapter = normalize_text(adapter)

    try:
        profile = load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="result.json no encontrado")

    raise_if_job_confirmed(result)

    if adapter not in ALLOWED_ADAPTERS:
        raise HTTPException(status_code=400, detail="adapter inválido. Usa google o microsoft")

    if result.get("next_action") != "guided_curation":
        raise HTTPException(status_code=400, detail="El job no está en guided_curation")

    try:
        curation_plan = load_json_from_gcs(curation_plan_object_name)
    except FileNotFoundError:
        curation_plan = None

    selection = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "adapter_selected",
        "selected_adapter": adapter,
        "recommended_adapter": (curation_plan or {}).get("recommended_adapter"),
        "original_filename": profile.get("original_filename"),
        "issues": profile.get("issues", []),
        "selected_at": now_iso(),
    }

    save_json_to_gcs(selection_object_name, selection)

    profile["adapter"] = adapter
    profile["updated_at"] = now_iso()
    save_json_to_gcs(profile_object_name, profile)

    result["selected_adapter_object"] = selection_object_name
    result["selected_adapter"] = adapter
    save_json_to_gcs(result_object_name, result)

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "adapter_selected",
        "selected_adapter": adapter,
        "selected_adapter_object": selection_object_name,
    }


@app.post("/revision-jobs/{job_id}/google-adapter-plan")
def build_google_adapter_plan(job_id: str, tenant_id: str = Form(...)):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"
    adapter_plan_object_name = f"{prefix}/google_adapter_plan.json"

    try:
        profile = load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="result.json no encontrado")

    raise_if_job_confirmed(result)

    if result.get("next_action") != "guided_curation":
        raise HTTPException(status_code=400, detail="El job no está en guided_curation")

    issues = profile.get("issues", [])
    issue_codes = [i.get("code") for i in issues]
    canonical_columns = ["cliente", "fecha", "fecha_vencimiento", "importe", "estado"]

    prompt = "\n".join(
        [
            "Actua como curador de planillas en Google Sheets.",
            "Objetivo: normalizar una hoja de cobranzas al esquema canonico exacto.",
            "No inventes datos faltantes.",
            "No elimines filas sin dejar rastro.",
            "Si un valor es ambiguo, conservarlo y marcar observacion.",
            "Encabezados canonicos obligatorios: cliente, fecha, fecha_vencimiento, importe, estado.",
            "",
            f"Archivo original: {profile.get('original_filename', '')}",
            f"Issues detectados: {', '.join(issue_codes) if issue_codes else 'ninguno'}",
            "",
            "Transformaciones requeridas:",
            "- Renombrar alias de encabezados al esquema canonico.",
            "- Normalizar importe quitando simbolos monetarios y dejando numero.",
            "- Normalizar fechas a YYYY-MM-DD con criterio dayfirst.",
            "- Mantener columnas no canonicas separadas como observaciones si aportan contexto.",
            "- Preservar todas las filas de datos.",
        ]
    )

    plan = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "google_adapter_plan_ready",
        "source_next_action": result.get("next_action"),
        "canonical_columns": canonical_columns,
        "issues": issues,
        "google_adapter_prompt": prompt,
        "generated_at": now_iso(),
    }

    save_json_to_gcs(adapter_plan_object_name, plan)
    result["google_adapter_plan_object"] = adapter_plan_object_name
    save_json_to_gcs(result_object_name, result)

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "google_adapter_plan_ready",
        "google_adapter_plan_object": adapter_plan_object_name,
        "canonical_columns": canonical_columns,
        "google_adapter_prompt": prompt,
    }


@app.post("/revision-jobs/{job_id}/microsoft-adapter-prompt")
def build_microsoft_adapter_prompt(job_id: str, tenant_id: str = Form(...)):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"
    adapter_prompt_object_name = f"{prefix}/microsoft_adapter_prompt.json"

    try:
        profile = load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="result.json no encontrado")

    raise_if_job_confirmed(result)

    if result.get("next_action") != "guided_curation":
        raise HTTPException(status_code=400, detail="El job no está en guided_curation")

    issues = profile.get("issues", [])
    issue_codes = [i.get("code") for i in issues]
    canonical_columns = ["cliente", "fecha", "fecha_vencimiento", "importe", "estado"]

    prompt = "\n".join(
        [
            "Actua como curador de planillas en Microsoft Excel con Copilot.",
            "Objetivo: convertir una hoja de cobranzas a un esquema canonico exacto.",
            "No inventes datos faltantes.",
            "No elimines filas sin dejar rastro.",
            "Si un valor es ambiguo, conservarlo y marcar observacion.",
            "Encabezados canonicos obligatorios: cliente, fecha, fecha_vencimiento, importe, estado.",
            "",
            f"Archivo original: {profile.get('original_filename', '')}",
            f"Issues detectados: {', '.join(issue_codes) if issue_codes else 'ninguno'}",
            "",
            "Transformaciones requeridas:",
            "- Renombrar alias de encabezados al esquema canonico.",
            "- Normalizar importe quitando simbolos monetarios y dejando numero.",
            "- Normalizar fechas a YYYY-MM-DD con criterio dayfirst.",
            "- Mantener columnas no canonicas separadas como observaciones si aportan contexto.",
            "- Preservar todas las filas de datos.",
            "",
            "Salida esperada:",
            "- Tabla final con columnas: cliente, fecha, fecha_vencimiento, importe, estado",
            "- Sin formato monetario en importe",
            "- Sin texto extra en fechas",
            "- Breve listado de cambios aplicados",
        ]
    )

    payload = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "microsoft_adapter_prompt_ready",
        "source_next_action": result.get("next_action"),
        "canonical_columns": canonical_columns,
        "issues": issues,
        "microsoft_adapter_prompt": prompt,
        "generated_at": now_iso(),
    }

    save_json_to_gcs(adapter_prompt_object_name, payload)
    result["microsoft_adapter_prompt_object"] = adapter_prompt_object_name
    save_json_to_gcs(result_object_name, result)

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "microsoft_adapter_prompt_ready",
        "microsoft_adapter_prompt_object": adapter_prompt_object_name,
        "canonical_columns": canonical_columns,
        "microsoft_adapter_prompt": prompt,
    }


@app.post("/revision-jobs/{job_id}/handoff-summary")
def build_handoff_summary(job_id: str, tenant_id: str = Form(...)):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"
    curation_plan_object_name = f"{prefix}/curation_plan.json"
    google_adapter_plan_object_name = f"{prefix}/google_adapter_plan.json"
    microsoft_adapter_prompt_object_name = f"{prefix}/microsoft_adapter_prompt.json"
    normalized_object_name = f"{prefix}/normalized_preview.json"
    canonical_csv_object_name = f"{prefix}/canonical_export.csv"
    handoff_summary_object_name = f"{prefix}/handoff_summary.json"

    try:
        profile = load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="result.json no encontrado")

    try:
        curation_plan = load_json_from_gcs(curation_plan_object_name)
    except FileNotFoundError:
        curation_plan = None

    try:
        google_adapter_plan = load_json_from_gcs(google_adapter_plan_object_name)
    except FileNotFoundError:
        google_adapter_plan = None

    try:
        microsoft_adapter_prompt = load_json_from_gcs(microsoft_adapter_prompt_object_name)
    except FileNotFoundError:
        microsoft_adapter_prompt = None

    try:
        normalized_preview = load_json_from_gcs(normalized_object_name)
    except FileNotFoundError:
        normalized_preview = None

    canonical_export_exists = bucket.blob(canonical_csv_object_name).exists()

    issues = profile.get("issues", [])
    issue_codes = [i.get("code") for i in issues]
    summary_block = result.get("summary") or {}
    validated_schema = result.get("validated_schema") or {}

    handoff_summary = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "handoff_summary_ready",
        "original_filename": profile.get("original_filename"),
        "selected_sheet": profile.get("selected_sheet"),
        "header_row_idx": profile.get("header_row_idx"),
        "header_values": profile.get("header_values", []),
        "confidence_score": profile.get("confidence_score"),
        "issues": issues,
        "issue_codes": issue_codes,
        "next_action": result.get("next_action"),
        "recognized_fields": summary_block.get("recognized_fields", []),
        "mapped_headers": validated_schema.get("mapped_headers", {}),
        "curation_decision": (curation_plan or {}).get("decision"),
        "recommended_adapter": (curation_plan or {}).get("recommended_adapter"),
        "selected_adapter": result.get("selected_adapter"),
        "google_adapter_available": google_adapter_plan is not None,
        "microsoft_adapter_available": microsoft_adapter_prompt is not None,
        "normalized_preview_available": normalized_preview is not None,
        "canonical_export_available": canonical_export_exists,
        "normalized_preview_rows": (normalized_preview or {}).get("preview_rows", []),
        "artifacts": {
            "profile_object": profile_object_name,
            "result_object": result_object_name,
            "curation_plan_object": curation_plan_object_name if curation_plan else None,
            "google_adapter_plan_object": google_adapter_plan_object_name if google_adapter_plan else None,
            "microsoft_adapter_prompt_object": microsoft_adapter_prompt_object_name if microsoft_adapter_prompt else None,
            "normalized_preview_object": normalized_object_name if normalized_preview else None,
            "canonical_export_object": canonical_csv_object_name if canonical_export_exists else None,
            "selected_adapter_object": result.get("selected_adapter_object"),
        },
        "summary_text": "\n".join(
            [
                f"Job: {job_id}",
                f"Archivo: {profile.get('original_filename')}",
                f"Decision: {result.get('next_action')}",
                f"Adapter recomendado: {(curation_plan or {}).get('recommended_adapter')}",
                f"Adapter seleccionado: {result.get('selected_adapter')}",
                f"Issues: {', '.join(issue_codes) if issue_codes else 'ninguno'}",
                f"Campos reconocidos: {', '.join(summary_block.get('recognized_fields', [])) or 'ninguno'}",
                f"Canonical export disponible: {'si' if canonical_export_exists else 'no'}",
            ]
        ),
        "generated_at": now_iso(),
    }

    save_json_to_gcs(handoff_summary_object_name, handoff_summary)
    result["handoff_summary_object"] = handoff_summary_object_name
    save_json_to_gcs(result_object_name, result)

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "handoff_summary_ready",
        "handoff_summary_object": handoff_summary_object_name,
        "summary_text": handoff_summary["summary_text"],
    }


@app.post("/revision-jobs/{job_id}/adapter-package")
def build_adapter_package(job_id: str, tenant_id: str = Form(...)):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"
    curation_plan_object_name = f"{prefix}/curation_plan.json"
    google_adapter_plan_object_name = f"{prefix}/google_adapter_plan.json"
    microsoft_adapter_prompt_object_name = f"{prefix}/microsoft_adapter_prompt.json"
    adapter_package_object_name = f"{prefix}/adapter_package.json"

    try:
        profile = load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="result.json no encontrado")

    raise_if_job_confirmed(result)

    if result.get("next_action") != "guided_curation":
        raise HTTPException(status_code=400, detail="El job no está en guided_curation")

    try:
        curation_plan = load_json_from_gcs(curation_plan_object_name)
    except FileNotFoundError:
        curation_plan = None

    try:
        google_adapter_plan = load_json_from_gcs(google_adapter_plan_object_name)
    except FileNotFoundError:
        google_adapter_plan = None

    try:
        microsoft_adapter_prompt = load_json_from_gcs(microsoft_adapter_prompt_object_name)
    except FileNotFoundError:
        microsoft_adapter_prompt = None

    package = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "adapter_package_ready",
        "original_filename": profile.get("original_filename"),
        "issues": profile.get("issues", []),
        "next_action": result.get("next_action"),
        "selected_adapter": result.get("selected_adapter"),
        "recognized_fields": (result.get("summary") or {}).get("recognized_fields", []),
        "mapped_headers": (result.get("validated_schema") or {}).get("mapped_headers", {}),
        "curation_plan": curation_plan,
        "google_adapter_plan": google_adapter_plan,
        "microsoft_adapter_prompt": microsoft_adapter_prompt,
        "generated_at": now_iso(),
    }

    save_json_to_gcs(adapter_package_object_name, package)
    result["adapter_package_object"] = adapter_package_object_name
    save_json_to_gcs(result_object_name, result)

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "adapter_package_ready",
        "adapter_package_object": adapter_package_object_name,
    }


@app.post("/revision-jobs/{job_id}/normalized-preview")
def build_normalized_preview(job_id: str, tenant_id: str = Form(...)):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"
    normalized_object_name = f"{prefix}/normalized_preview.json"

    try:
        profile = load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="result.json no encontrado")

    raise_if_job_confirmed(result)

    try:
        source_type = normalize_text(profile.get("source_type") or "excel")
        if source_type in {"excel", "csv"}:
            preview = build_tabular_normalized_preview(bucket, profile, result)
        elif source_type == "pdf_text":
            preview = build_pdf_text_normalized_preview(bucket, profile, result)
        else:
            raise HTTPException(status_code=400, detail=f"source_type no soportado: {source_type}")

        normalized_preview = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "normalized_preview_ready",
            "canonical_columns": preview["canonical_columns"],
            "missing_canonical_columns": preview["missing_canonical_columns"],
            "preview_rows": preview["preview_rows"],
            "row_count_preview": preview["row_count_preview"],
        }

        save_json_to_gcs(normalized_object_name, normalized_preview)

        result["status"] = "normalized_preview_ready"
        result["normalized_preview_object"] = normalized_object_name
        save_json_to_gcs(result_object_name, result)

        return {
            "ok": True,
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "normalized_preview_ready",
            "canonical_columns": preview["canonical_columns"],
            "missing_canonical_columns": preview["missing_canonical_columns"],
            "preview_rows": preview["preview_rows"],
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/revision-jobs/{job_id}/auto-curate-preview")
def build_auto_curate_preview(job_id: str, tenant_id: str = Form(...)):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"
    auto_curate_preview_object_name = f"{prefix}/auto_curate_preview.json"

    try:
        profile = load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="result.json no encontrado")

    raise_if_job_confirmed(result)

    try:
        source_type = normalize_text(profile.get("source_type") or "excel")
        if source_type in {"excel", "csv"}:
            preview = build_tabular_normalized_preview(bucket, profile, result)
        elif source_type == "pdf_text":
            preview = build_pdf_text_normalized_preview(bucket, profile, result)
        else:
            raise HTTPException(status_code=400, detail=f"source_type no soportado: {source_type}")

        save_json_to_gcs(auto_curate_preview_object_name, preview)

        result["status"] = "auto_curate_preview_ready"
        result["next_action"] = preview["next_action"]
        result["auto_curate_preview_object"] = auto_curate_preview_object_name
        save_json_to_gcs(result_object_name, result)

        return {
            "ok": True,
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "auto_curate_preview_ready",
            "next_action": preview["next_action"],
            "canonical_columns": preview["canonical_columns"],
            "missing_canonical_columns": preview["missing_canonical_columns"],
            "changes_applied": preview["changes_applied"],
            "warnings": preview["warnings"],
            "confidence_score": preview["confidence_score"],
            "preview_rows": preview["preview_rows"],
            "auto_curate_preview_object": auto_curate_preview_object_name,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/revision-jobs/{job_id}/apply-auto-curation")
def apply_auto_curation(job_id: str, tenant_id: str = Form(...)):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"
    normalized_object_name = f"{prefix}/normalized_preview.json"
    canonical_csv_object_name = f"{prefix}/canonical_export.csv"

    try:
        load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="result.json no encontrado")

    raise_if_job_confirmed(result)

    auto_curate_preview_object_name = result.get(
        "auto_curate_preview_object",
        f"{prefix}/auto_curate_preview.json",
    )

    try:
        preview = load_json_from_gcs(auto_curate_preview_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="auto_curate_preview.json no encontrado")

    canonical_columns = preview.get("canonical_columns", [])
    preview_rows = preview.get("preview_rows", [])
    missing_canonical_columns = preview.get("missing_canonical_columns", [])
    row_count_preview = preview.get("row_count_preview", len(preview_rows))

    normalized_preview = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "normalized_preview_ready",
        "canonical_columns": canonical_columns,
        "missing_canonical_columns": missing_canonical_columns,
        "preview_rows": preview_rows,
        "row_count_preview": row_count_preview,
    }

    save_json_to_gcs(normalized_object_name, normalized_preview)

    df = pd.DataFrame(preview_rows, columns=canonical_columns)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    bucket.blob(canonical_csv_object_name).upload_from_string(
        csv_bytes,
        content_type="text/csv",
    )

    result["status"] = "auto_curation_applied"
    result["next_action"] = "ready_for_final_parse"
    result["normalized_preview_object"] = normalized_object_name
    result["canonical_export_object"] = canonical_csv_object_name
    result["auto_curate_preview_object"] = auto_curate_preview_object_name
    save_json_to_gcs(result_object_name, result)

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "auto_curation_applied",
        "next_action": "ready_for_final_parse",
        "normalized_preview_object": normalized_object_name,
        "canonical_export_object": canonical_csv_object_name,
        "row_count": len(preview_rows),
        "canonical_columns": canonical_columns,
    }


@app.post("/revision-jobs/{job_id}/confirm-handoff")
def confirm_handoff(
    job_id: str,
    tenant_id: str = Form(...),
    confirmation: str = Form(...),
    notes: str = Form(""),
):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"
    handoff_confirmation_object_name = f"{prefix}/handoff_confirmation.json"

    confirmation = normalize_text(confirmation)
    if confirmation not in {"confirm", "confirmed", "ok"}:
        raise HTTPException(status_code=400, detail="confirmation inválida. Usa confirm")

    try:
        profile = load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="result.json no encontrado")

    existing_confirmation_object = result.get("handoff_confirmation_object")
    if result.get("status") == "handoff_confirmed" and existing_confirmation_object:
        if bucket.blob(existing_confirmation_object).exists():
            return {
                "ok": True,
                "job_id": job_id,
                "tenant_id": tenant_id,
                "status": "handoff_confirmed",
                "already_confirmed": True,
                "selected_adapter": result.get("selected_adapter"),
                "next_action": result.get("next_action", "await_external_execution"),
                "handoff_confirmation_object": existing_confirmation_object,
            }

    required_result_fields = [
        "canonical_export_object",
        "handoff_summary_object",
        "adapter_package_object",
        "selected_adapter_object",
        "selected_adapter",
    ]
    missing = [field for field in required_result_fields if not result.get(field)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Faltan artefactos o campos requeridos para confirmar handoff: {', '.join(missing)}",
        )

    required_objects = [
        result["canonical_export_object"],
        result["handoff_summary_object"],
        result["adapter_package_object"],
        result["selected_adapter_object"],
    ]
    missing_objects = [obj for obj in required_objects if not bucket.blob(obj).exists()]
    if missing_objects:
        raise HTTPException(
            status_code=400,
            detail=f"No existen en GCS algunos artefactos requeridos: {', '.join(missing_objects)}",
        )

    confirmed_at = now_iso()
    handoff_confirmation = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "handoff_confirmed",
        "selected_adapter": result.get("selected_adapter"),
        "original_filename": profile.get("original_filename"),
        "confirmed_at": confirmed_at,
        "confirmation": "confirm",
        "notes": notes.strip(),
        "artifacts": {
            "canonical_export_object": result.get("canonical_export_object"),
            "handoff_summary_object": result.get("handoff_summary_object"),
            "adapter_package_object": result.get("adapter_package_object"),
            "selected_adapter_object": result.get("selected_adapter_object"),
        },
    }

    save_json_to_gcs(handoff_confirmation_object_name, handoff_confirmation)

    result["status"] = "handoff_confirmed"
    result["next_action"] = "await_external_execution"
    result["handoff_confirmed_at"] = confirmed_at
    result["handoff_confirmation_object"] = handoff_confirmation_object_name
    save_json_to_gcs(result_object_name, result)

    profile["updated_at"] = now_iso()
    save_json_to_gcs(profile_object_name, profile)

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "handoff_confirmed",
        "selected_adapter": result.get("selected_adapter"),
        "next_action": "await_external_execution",
        "handoff_confirmation_object": handoff_confirmation_object_name,
    }


@app.post("/revision-jobs/{job_id}/canonical-export")
def build_canonical_export(job_id: str, tenant_id: str = Form(...)):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    normalized_object_name = f"{prefix}/normalized_preview.json"
    canonical_csv_object_name = f"{prefix}/canonical_export.csv"
    result_object_name = f"{prefix}/result.json"

    try:
        normalized = load_json_from_gcs(normalized_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="normalized_preview.json no encontrado")

    preview_rows = normalized.get("preview_rows", [])
    canonical_columns = normalized.get("canonical_columns", [])

    df = pd.DataFrame(preview_rows, columns=canonical_columns)
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    bucket.blob(canonical_csv_object_name).upload_from_string(
        csv_bytes,
        content_type="text/csv",
    )

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        result = {
            "job_id": job_id,
            "tenant_id": tenant_id,
        }

    if result.get("status") != "handoff_confirmed":
        result["status"] = "canonical_export_ready"

    result["canonical_export_object"] = canonical_csv_object_name
    save_json_to_gcs(result_object_name, result)

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": result.get("status", "canonical_export_ready"),
        "canonical_export_object": canonical_csv_object_name,
    }


@app.post("/revision-jobs/{job_id}/curated-return")
async def submit_curated_return(
    job_id: str,
    tenant_id: str = Form(...),
    file: UploadFile = File(...),
):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    profile_object_name = f"{prefix}/profile.json"
    result_object_name = f"{prefix}/result.json"

    try:
        load_json_from_gcs(profile_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="profile.json no encontrado")

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="result.json no encontrado")

    allowed_statuses = {
        "handoff_confirmed",
        "curated_return_valid",
        "curated_return_invalid",
        "final_parse_ready",
        "final_parse_invalid",
    }
    if result.get("status") not in allowed_statuses:
        raise HTTPException(
            status_code=409,
            detail="El job debe estar en un estado compatible para submitir curated return.",
        )

    content = await file.read()
    file_hash = sha256_bytes(content)

    original_filename = file.filename or "curated_return.csv"
    curated_return_object_name = f"{prefix}/curated_return_{original_filename}"

    blob = bucket.blob(curated_return_object_name)
    blob.upload_from_string(content, content_type=file.content_type or "application/octet-stream")

    try:
        canonicalized = canonicalize_curated_return_object(curated_return_object_name)
        raw_df = canonicalized["raw_df"]
        analysis = profile_dataframe(raw_df)
    except Exception as e:
        validation = {
            "valid": False,
            "warnings": [f"Error al cargar archivo: {str(e)}"],
            "recognized_fields": [],
            "mapped_headers": {},
            "row_count": 0,
            "column_count": 0,
            "file_hash": file_hash,
            "duplicate_row_count": 0,
            "invalid_importe_count": 0,
            "invalid_fecha_count": 0,
            "invalid_fecha_vencimiento_count": 0,
        }
        raw_df = None
        analysis = None

    if raw_df is not None:
        mapped_headers = canonicalized["mapped_headers"]
        recognized_fields = canonicalized["recognized_fields"]

        required_core = {"cliente", "importe"}
        recognized_core = set(recognized_fields)

        warning_map = {}

        if not required_core.issubset(recognized_core):
            missing = sorted(required_core - recognized_core)
            warning_map["missing_core"] = (
                f"Columnas canónicas mínimas faltantes: {', '.join(missing)}"
            )

        invalid_fecha_count = canonicalized["invalid_fecha_count"]
        invalid_fecha_vencimiento_count = canonicalized["invalid_fecha_vencimiento_count"]
        invalid_importe_count = canonicalized["invalid_importe_count"]
        duplicate_row_count = canonicalized["duplicate_row_count_raw"]

        if invalid_fecha_count > 0:
            warning_map["invalid_fecha"] = f"Fechas inválidas en fecha: {invalid_fecha_count}"

        if invalid_fecha_vencimiento_count > 0:
            warning_map["invalid_fecha_vto"] = (
                f"Fechas inválidas en fecha_vencimiento: {invalid_fecha_vencimiento_count}"
            )

        if invalid_importe_count > 0:
            warning_map["invalid_importe"] = (
                f"Importes no numéricos o no normalizables: {invalid_importe_count}"
            )

        if duplicate_row_count > 0:
            warning_map["duplicate_rows"] = (
                f"Filas duplicadas detectadas: {duplicate_row_count}"
            )

        for issue in analysis.get("issues", []):
            if issue.get("severity") not in ("high", "medium"):
                continue

            code = issue.get("code")
            if not code:
                continue

            if code == "duplicate_rows" and "duplicate_rows" in warning_map:
                continue
            if code == "fecha_needs_normalization" and "invalid_fecha" in warning_map:
                continue
            if (
                code == "fecha_vencimiento_needs_normalization"
                and "invalid_fecha_vto" in warning_map
            ):
                continue

            warning_map[code] = f"{code}: {issue.get('message', '')}"

        warnings = list(warning_map.values())

        valid = (
            required_core.issubset(recognized_core)
            and invalid_importe_count == 0
            and invalid_fecha_count == 0
            and invalid_fecha_vencimiento_count == 0
            and duplicate_row_count == 0
        )

        validation = {
            "valid": valid,
            "warnings": warnings,
            "recognized_fields": recognized_fields,
            "mapped_headers": mapped_headers,
            "row_count": analysis.get("row_count", 0),
            "column_count": analysis.get("column_count", 0),
            "file_hash": file_hash,
            "duplicate_row_count": duplicate_row_count,
            "invalid_importe_count": invalid_importe_count,
            "invalid_fecha_count": invalid_fecha_count,
            "invalid_fecha_vencimiento_count": invalid_fecha_vencimiento_count,
        }

    validation_object_name = f"{prefix}/curated_return_validation.json"
    save_json_to_gcs(validation_object_name, validation)

    received_at = now_iso()
    summary = {
        "row_count": validation.get("row_count", 0),
        "column_count": validation.get("column_count", 0),
        "recognized_fields": validation["recognized_fields"],
        "valid": validation["valid"],
        "file_hash": file_hash,
        "duplicate_row_count": validation.get("duplicate_row_count", 0),
        "invalid_importe_count": validation.get("invalid_importe_count", 0),
        "invalid_fecha_count": validation.get("invalid_fecha_count", 0),
        "invalid_fecha_vencimiento_count": validation.get("invalid_fecha_vencimiento_count", 0),
    }

    if validation["valid"]:
        result["status"] = "curated_return_valid"
        result["next_action"] = "ready_for_final_parse"
    else:
        result["status"] = "curated_return_invalid"
        result["next_action"] = "investigate_curated_return"

    result["curated_return_object"] = curated_return_object_name
    result["curated_return_validation_object"] = validation_object_name
    result["curated_return_filename"] = original_filename
    result["curated_return_received_at"] = received_at
    result["curated_return_valid"] = validation["valid"]
    result["curated_return_summary"] = summary
    save_json_to_gcs(result_object_name, result)

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": result["status"],
        "next_action": result["next_action"],
        "valid": validation["valid"],
        "warnings": validation["warnings"],
        "recognized_fields": validation["recognized_fields"],
        "mapped_headers": validation["mapped_headers"],
        "curated_return_object": curated_return_object_name,
    }


@app.post("/revision-jobs/{job_id}/final-parse")
def final_parse(job_id: str, tenant_id: str = Form(...)):
    prefix = f"tenant_{tenant_id}/revision_jobs/{job_id}"
    result_object_name = f"{prefix}/result.json"
    final_parse_object_name = f"{prefix}/final_parse.json"
    final_canonical_object_name = f"{prefix}/final_canonical.csv"

    try:
        result = load_json_from_gcs(result_object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="result.json no encontrado")

    allowed_statuses = {
        "curated_return_valid",
        "final_parse_ready",
        "final_parse_invalid",
    }
    if result.get("status") == "curated_return_invalid":
        raise HTTPException(
            status_code=409,
            detail="No se puede ejecutar final-parse cuando el curated return es inválido.",
        )
    if result.get("status") not in allowed_statuses:
        raise HTTPException(
            status_code=409,
            detail="El job debe estar en un estado compatible para ejecutar final-parse.",
        )

    curated_return_object = result.get("curated_return_object")
    if not curated_return_object:
        raise HTTPException(
            status_code=400,
            detail="Falta curated_return_object en result.json",
        )

    try:
        canonicalized = canonicalize_curated_return_object(curated_return_object)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo cargar curated return: {str(e)}",
        )

    df_canonical = canonicalized["df_canonical"]
    df_export_final = canonicalized["df_export_final"]
    canonical_columns = canonicalized["canonical_columns"]
    unknown_headers = canonicalized["unknown_headers"]
    row_count = canonicalized["row_count"]
    null_cliente_count = canonicalized["null_cliente_count"]
    null_importe_count = canonicalized["null_importe_count"]
    invalid_importe_count = canonicalized["invalid_importe_count"]
    invalid_fecha_count = canonicalized["invalid_fecha_count"]
    invalid_fecha_vencimiento_count = canonicalized["invalid_fecha_vencimiento_count"]
    duplicate_row_count = canonicalized["duplicate_row_count"]

    warnings = []
    if unknown_headers:
        warnings.append(
            f"Encabezados no reconocidos en curated return: {', '.join([str(x) for x in unknown_headers])}"
        )
    if null_cliente_count > 0:
        warnings.append(f"Filas sin cliente: {null_cliente_count}")
    if null_importe_count > 0:
        warnings.append(f"Filas sin importe: {null_importe_count}")
    if invalid_importe_count > 0:
        warnings.append(f"Importes no numéricos o no normalizables: {invalid_importe_count}")
    if invalid_fecha_count > 0:
        warnings.append(f"Fechas inválidas en fecha: {invalid_fecha_count}")
    if invalid_fecha_vencimiento_count > 0:
        warnings.append(f"Fechas inválidas en fecha_vencimiento: {invalid_fecha_vencimiento_count}")
    if duplicate_row_count > 0:
        warnings.append(f"Filas duplicadas detectadas: {duplicate_row_count}")

    valid = (
        row_count > 0
        and null_cliente_count < row_count
        and null_importe_count < row_count
        and invalid_importe_count == 0
        and invalid_fecha_count == 0
        and invalid_fecha_vencimiento_count == 0
        and duplicate_row_count == 0
    )

    records = df_canonical.to_dict(orient="records")
    csv_bytes = df_export_final.to_csv(index=False).encode("utf-8")

    bucket.blob(final_canonical_object_name).upload_from_string(
        csv_bytes,
        content_type="text/csv",
    )

    final_parse = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "final_parse_ready" if valid else "final_parse_invalid",
        "row_count": row_count,
        "canonical_columns": canonical_columns,
        "warnings": warnings,
        "null_cliente_count": null_cliente_count,
        "null_importe_count": null_importe_count,
        "invalid_importe_count": invalid_importe_count,
        "invalid_fecha_count": invalid_fecha_count,
        "invalid_fecha_vencimiento_count": invalid_fecha_vencimiento_count,
        "duplicate_row_count": duplicate_row_count,
        "records_preview": records[:20],
        "generated_at": now_iso(),
    }

    save_json_to_gcs(final_parse_object_name, final_parse)

    result["status"] = "final_parse_ready" if valid else "final_parse_invalid"
    result["next_action"] = "done" if valid else "investigate_final_parse"
    result["final_parse_object"] = final_parse_object_name
    result["final_canonical_object"] = final_canonical_object_name
    result["final_parse_completed_at"] = now_iso()
    save_json_to_gcs(result_object_name, result)

    return {
        "ok": True,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": result["status"],
        "next_action": result["next_action"],
        "row_count": row_count,
        "warnings": warnings,
        "final_parse_object": final_parse_object_name,
        "final_canonical_object": final_canonical_object_name,
    }

@app.get("/digest/latest")
def get_digest_latest(tenant_id: str = Query(...)):
    try:
        store = ArtifactStore()
        builder = DigestBuilder(store)
        digest = builder.build_latest(tenant_id)
        return digest
    except Exception as e:
        return {"error": str(e)}


