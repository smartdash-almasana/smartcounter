from __future__ import annotations

import json
import sys
import types
import unittest
from datetime import datetime, timezone
from unittest.mock import patch


if "google.cloud.storage" not in sys.modules:
    google_mod = types.ModuleType("google")
    cloud_mod = types.ModuleType("google.cloud")
    storage_mod = types.ModuleType("google.cloud.storage")

    class _DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def bucket(self, *args, **kwargs):
            return None

    storage_mod.Client = _DummyClient
    google_mod.cloud = cloud_mod
    cloud_mod.storage = storage_mod
    sys.modules["google"] = google_mod
    sys.modules["google.cloud"] = cloud_mod
    sys.modules["google.cloud.storage"] = storage_mod


from backend.schemas.module_ingestions import ModuleIngestionRequest
from backend.services import module_ingestion_service as svc


class FakeBlob:
    def __init__(self, store: dict[str, bytes], name: str):
        self.store = store
        self.name = name

    def exists(self) -> bool:
        return self.name in self.store

    def upload_from_string(self, data, content_type=None):
        if isinstance(data, str):
            self.store[self.name] = data.encode("utf-8")
        elif isinstance(data, bytes):
            self.store[self.name] = data
        else:
            self.store[self.name] = str(data).encode("utf-8")

    def download_as_text(self) -> str:
        return self.store[self.name].decode("utf-8")


class FakeBucket:
    def __init__(self):
        self._store: dict[str, bytes] = {}

    def blob(self, name: str) -> FakeBlob:
        return FakeBlob(self._store, name)


class TestNormalizedSignalsV1(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_bucket = FakeBucket()
        self._bucket_patcher = patch.object(svc, "bucket", self.fake_bucket)
        self._id_patcher = patch.object(svc, "build_ingestion_id", return_value="ing_sig_001")
        self._bucket_patcher.start()
        self._id_patcher.start()

    def tearDown(self) -> None:
        self._id_patcher.stop()
        self._bucket_patcher.stop()

    def _base_payload(self, module: str, findings: list[dict]) -> ModuleIngestionRequest:
        return ModuleIngestionRequest(
            contract_version="module-ingestions.v2",
            tenant_id="demo001",
            module=module,
            source_type="google_sheets" if module == "stock_simple" else "upload",
            generated_at="2026-04-06T12:00:00Z",
            canonical_rows=[
                {
                    "row_id": "stock_row_1",
                    "sku": "SKU-123",
                    "producto": "Prod A",
                    "stock_actual": 1,
                    "stock_minimo": 5,
                    "consumo_promedio_diario": 1,
                    "requires_review": False,
                }
            ]
            if module == "stock_simple"
            else [
                {
                    "request_id": "REQ-1",
                    "submitted_at": "2026-04-06T12:00:00Z",
                    "requester_name": "Ana",
                    "merchant_name": "Comercio",
                    "document_type": "invoice",
                    "document_date": "2026-04-06",
                    "document_cuit": "30712345678",
                    "amount": 1000,
                    "currency": "ARS",
                    "payment_method": "transfer",
                    "category": "viaticos",
                    "evidence_list": [],
                    "status": "ready",
                }
            ],
            findings=findings,
            summary={"total_rows": 1, "valid_rows": 1, "invalid_rows": 0}
            if module == "stock_simple"
            else {
                "total_cases": 1,
                "ready_for_approval_cases": 1,
                "needs_completion_cases": 0,
                "low_quality_cases": 0,
                "duplicate_suspected_cases": 0,
                "high_amount_cases": 0,
                "invalid_cases": 0,
            },
            suggested_actions=[] if module == "stock_simple" else [{
                "action_type": "notify",
                "priority": "low",
                "description": "desc",
                "context": {},
            }],
        )

    def test_mapping_basico_stock_simple(self):
        payload = self._base_payload(
            "stock_simple",
            [{"finding_id": "f1", "code": "critical_stock_detected", "severity": "high", "score": 0.9}],
        )
        signals = svc.build_normalized_signals_from_payload(payload)

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["signal_code"], "stock_break_risk")
        self.assertEqual(signals[0]["module"], "stock_simple")

    def test_mapping_basico_expense_evidence(self):
        payload = self._base_payload(
            "expense_evidence",
            [{"finding_id": "f1", "finding_type": "missing_evidence", "severity": "critical", "score": 0.95}],
        )
        signals = svc.build_normalized_signals_from_payload(payload)

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["signal_code"], "expense_evidence_missing")

    def test_mapper_preparado_concili_simple(self):
        payload = ModuleIngestionRequest(
            contract_version="module-ingestions.v2",
            tenant_id="demo001",
            module="stock_simple",
            source_type="google_sheets",
            generated_at="2026-04-06T12:00:00Z",
            canonical_rows=[],
            findings=[],
            summary={"total_rows": 0, "valid_rows": 0, "invalid_rows": 0},
            suggested_actions=[],
        )
        # testea el mapper sin depender de enum de module-ingestions
        signal_code = svc._extract_signal_code("concili_simple", {"code": "amount_mismatch"})
        self.assertEqual(signal_code, "conciliation_amount_mismatch")
        signals = svc.build_normalized_signals_from_payload(payload)
        self.assertEqual(signals, [])

    def test_consolidacion_por_clave_semantica(self):
        findings = [
            {"finding_id": "f1", "code": "critical_stock_detected", "severity": "medium", "score": 0.7, "row_id": "stock_row_1"},
            {"finding_id": "f2", "code": "critical_stock_detected", "severity": "high", "score": 0.9, "row_id": "stock_row_1"},
        ]
        payload = self._base_payload("stock_simple", findings)
        signals = svc.build_normalized_signals_from_payload(payload)

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["severity"], "high")
        self.assertAlmostEqual(signals[0]["score"], 0.9)
        self.assertEqual(set(signals[0]["evidence"]["finding_ids"]), {"f1", "f2"})

    def test_prioridad_p0_p1_p2_p3(self):
        self.assertEqual(svc._derive_priority("critical", 0.9), "p0")
        self.assertEqual(svc._derive_priority("high", 0.7), "p1")
        self.assertEqual(svc._derive_priority("medium", 0.5), "p2")
        self.assertEqual(svc._derive_priority("low", 0.2), "p3")

    def test_states_active_resolved_expired(self):
        now_dt = datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)

        active = svc._resolve_signal_state({"code": "critical_stock_detected"}, now_dt)
        resolved = svc._resolve_signal_state({"code": "critical_stock_detected", "status": "resolved"}, now_dt)
        expired = svc._resolve_signal_state({"code": "critical_stock_detected", "expires_at": "2026-04-01T00:00:00Z"}, now_dt)

        self.assertEqual(active, "active")
        self.assertEqual(resolved, "resolved")
        self.assertEqual(expired, "expired")

    def test_persistencia_normalized_signals_json(self):
        payload = self._base_payload(
            "stock_simple",
            [{"finding_id": "f1", "code": "critical_stock_detected", "severity": "high", "score": 0.9}],
        )
        result = svc.persist_module_ingestion(payload)

        self.assertIn("normalized_signals", result["artifacts"])
        path = result["artifacts"]["normalized_signals"]
        self.assertIn(path, self.fake_bucket._store)
        persisted = json.loads(self.fake_bucket._store[path].decode("utf-8"))
        self.assertIsInstance(persisted, list)
        self.assertEqual(persisted[0]["signal_code"], "stock_break_risk")


if __name__ == "__main__":
    unittest.main()
