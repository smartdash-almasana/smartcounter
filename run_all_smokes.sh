#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python smoke_test.py
python smoke_job_state.py
python smoke_get_revision_job.py
python smoke_curation_plan.py
python smoke_select_adapter.py
python smoke_google_adapter_plan.py
echo "OK: todos los smokes pasaron"
