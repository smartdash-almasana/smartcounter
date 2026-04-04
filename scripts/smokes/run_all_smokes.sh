#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"
"$PYTHON_BIN" scripts/smokes/smoke_test.py
"$PYTHON_BIN" scripts/smokes/smoke_job_state.py
"$PYTHON_BIN" scripts/smokes/smoke_get_revision_job.py
"$PYTHON_BIN" scripts/smokes/smoke_curation_plan.py
"$PYTHON_BIN" scripts/smokes/smoke_select_adapter.py
"$PYTHON_BIN" scripts/smokes/smoke_google_adapter_plan.py
"$PYTHON_BIN" scripts/smokes/smoke_microsoft_adapter_prompt.py
"$PYTHON_BIN" scripts/smokes/smoke_pdf_text_empty.py
"$PYTHON_BIN" scripts/smokes/smoke_pdf_text_real.py
"$PYTHON_BIN" scripts/smokes/smoke_auto_curate_preview.py
"$PYTHON_BIN" scripts/smokes/smoke_apply_auto_curation.py
"$PYTHON_BIN" scripts/smokes/smoke_curated_final_parse_pack08.py
echo "OK: todos los smokes pasaron"
