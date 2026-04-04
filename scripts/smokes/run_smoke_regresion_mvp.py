from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import smartcounter_ui as ui
from run_local import run_pipeline_curated


PACK_FILES = [
    "03_encabezado_desplazado_representativo.xlsx",
    "04_semantica_inestable_representativo.xlsx",
    "07_formulas_ocultos_representativo.xlsx",
    "08_montos_mixtos_signos_representativo.csv",
]


def run_materialize_tests() -> dict:
    loader = unittest.defaultTestLoader
    suite = loader.discover(str(REPO_ROOT / "tests"), pattern="test_materialize_for_pipeline.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    ok = total - failed
    return {"total": total, "ok": ok, "fail": failed}


def run_pack_validation(base_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for filename in PACK_FILES:
        fp = base_dir / filename
        row = {
            "archivo": filename,
            "sheet": None,
            "header_row_1based": None,
            "warning_codes": [],
            "error": None,
        }
        if not fp.exists():
            row["error"] = "Archivo no encontrado en validation_pack_mvp."
            rows.append(row)
            continue

        try:
            data = fp.read_bytes()
            preview = ui._build_preview(filename, data)
            if preview.get("state") != "ready":
                row["error"] = "No carga bien en preview."
                rows.append(row)
                continue

            materialized = ui._materialize_for_pipeline(filename, data)
            result = run_pipeline_curated(materialized)
            summary = ui._summarize_pipeline(result, metadata={})
            row["sheet"] = summary.get("sheet")
            row["header_row_1based"] = summary.get("header_row_1based")
            row["warning_codes"] = summary.get("warning_codes", [])
        except Exception as exc:
            row["error"] = str(exc)
        rows.append(row)
    return rows


def print_consolidated_output(test_summary: dict, pack_rows: list[dict]) -> None:
    print("\n=== Smoke/Regresión MVP ===")
    print(
        f"Tests unittest: OK {test_summary['ok']} / "
        f"FAIL {test_summary['fail']} / TOTAL {test_summary['total']}"
    )
    print("\nResultado por archivo:")
    for row in pack_rows:
        status = "OK" if not row["error"] else "ERROR"
        warning_codes = row["warning_codes"] if row["warning_codes"] else []
        print(
            f"- {row['archivo']} | {status} | hoja={row['sheet']} | "
            f"header={row['header_row_1based']} | warning_codes={warning_codes} | "
            f"error={row['error']}"
        )


def main() -> int:
    validation_dir = REPO_ROOT / "validation_pack_mvp"

    test_summary = run_materialize_tests()
    pack_rows = run_pack_validation(validation_dir)
    print_consolidated_output(test_summary, pack_rows)

    out = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "tests": test_summary,
        "pack_resultados": pack_rows,
    }
    output_path = validation_dir / "resultado_smoke_regresion_mvp.json"
    validation_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSalida JSON: {output_path}")

    if test_summary["fail"] > 0:
        return 1
    if any(row["error"] for row in pack_rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
