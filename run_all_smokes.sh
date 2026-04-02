#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-./.venv/bin/python}"
"$PYTHON_BIN" smoke_test.py
"$PYTHON_BIN" smoke_job_state.py
"$PYTHON_BIN" smoke_get_revision_job.py
"$PYTHON_BIN" smoke_curation_plan.py
"$PYTHON_BIN" smoke_select_adapter.py
"$PYTHON_BIN" smoke_google_adapter_plan.py
"$PYTHON_BIN" smoke_microsoft_adapter_prompt.py
"$PYTHON_BIN" smoke_pdf_text_empty.py
"$PYTHON_BIN" smoke_pdf_text_real.py
"$PYTHON_BIN" smoke_auto_curate_preview.py
"$PYTHON_BIN" smoke_apply_auto_curation.py
echo "OK: todos los smokes pasaron"
