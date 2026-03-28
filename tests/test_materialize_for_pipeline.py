from __future__ import annotations

import io
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from openpyxl import Workbook

import smartcounter_ui as ui
from run_local import run_pipeline_curated


class TestMaterializeForPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_root = Path("tests/.smartcounter_tmp_test").resolve()
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root, ignore_errors=True)
        self.tmp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _xlsx_bytes(self) -> bytes:
        wb = Workbook()
        ws = wb.active
        ws.title = "Cobranzas"
        ws.append(["Cliente", "Fecha", "Monto"])
        ws.append(["Cliente A", "2026-03-01", "1200"])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def _csv_bytes(self) -> bytes:
        df = pd.DataFrame(
            {
                "Cliente": ["Cliente A", "Cliente B"],
                "Fecha": ["01/03/2026", "02/03/2026"],
                "Monto": ["1200", "1300"],
            }
        )
        return df.to_csv(index=False).encode("utf-8")

    def _assert_pipeline_works(self, path: str) -> None:
        result = run_pipeline_curated(path)
        self.assertIsNotNone(result.get("sheet"))
        self.assertIsInstance(result.get("header_row_1based"), int)
        self.assertIn("warnings_estructurados", result)

    def test_materialize_xlsx_inside_local_tmp_and_pipeline_works(self) -> None:
        with patch.object(ui, "LOCAL_TMP_ROOT", self.tmp_root):
            materialized = ui._materialize_for_pipeline(
                "archivo_xlsx_test.xlsx",
                self._xlsx_bytes(),
            )
        materialized_path = Path(materialized).resolve()
        self.assertTrue(materialized_path.exists())
        self.assertTrue(str(materialized_path).startswith(str(self.tmp_root)))
        self.assertEqual(materialized_path.suffix.lower(), ".xlsx")
        self._assert_pipeline_works(str(materialized_path))

    def test_materialize_csv_inside_local_tmp_and_pipeline_works(self) -> None:
        with patch.object(ui, "LOCAL_TMP_ROOT", self.tmp_root):
            materialized = ui._materialize_for_pipeline(
                "archivo_csv_test.csv",
                self._csv_bytes(),
            )
        materialized_path = Path(materialized).resolve()
        self.assertTrue(materialized_path.exists())
        self.assertTrue(str(materialized_path).startswith(str(self.tmp_root)))
        self.assertEqual(materialized_path.suffix.lower(), ".xlsx")
        self._assert_pipeline_works(str(materialized_path))

    def test_cleanup_keeps_only_30_recent_runs(self) -> None:
        with patch.object(ui, "LOCAL_TMP_ROOT", self.tmp_root):
            for i in range(35):
                old_run = self.tmp_root / f"run_20000101_000000_{i:06d}"
                old_run.mkdir(parents=True, exist_ok=True)

            ui._materialize_for_pipeline("archivo_cleanup_test.xlsx", self._xlsx_bytes())
            run_dirs = [p for p in self.tmp_root.iterdir() if p.is_dir() and p.name.startswith("run_")]
            self.assertLessEqual(len(run_dirs), 30)


if __name__ == "__main__":
    unittest.main()
