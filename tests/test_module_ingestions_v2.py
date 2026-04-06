from __future__ import annotations

import json
import sys
import types
import unittest
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


from backend.routes import module_ingestions as module_ingestions_route
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


class TestModuleIngestionsV2(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_bucket = FakeBucket()
        self._bucket_patcher = patch.object(svc, "bucket", self.fake_bucket)
        self._id_patcher = patch.object(svc, "build_ingestion_id", side_effect=["ing_test_001", "ing_test_002"])
        self._bucket_patcher.start()
        self._id_patcher.start()

    def tearDown(self) -> None:
        self._id_patcher.stop()
        self._bucket_patcher.stop()

    def _stock_payload(self) -> dict:
        return {
            "contract_version": "module-ingestions.v2",
            "tenant_id": "demo001",
            "module": "stock_simple",
            "source_type": "google_sheets",
            "generated_at": "2026-04-05T15:40:00Z",
            "canonical_rows": [
                {
                    "row_id": "stock_row_1",
                    "producto": "Producto A",
                    "stock_actual": 10,
                    "stock_minimo": 5,
                    "consumo_promedio_diario": 2,
                    "requires_review": False,
                }
            ],
            "findings": [{"code": "low_stock_detected"}],
            "summary": {
                "total_rows": 1,
                "valid_rows": 1,
                "invalid_rows": 0,
            },
            "suggested_actions": [],
            "parse_metadata": {"edge": "apps_script", "edge_version": "1.0.0"},
            "audit_metadata": {"trace_id": "trace-1", "request_id": "req-1"},
        }

    def _expense_payload(self) -> dict:
        return {
            "contract_version": "module-ingestions.v2",
            "tenant_id": "demo001",
            "module": "expense_evidence",
            "source_type": "upload",
            "generated_at": "2026-04-05T15:40:00Z",
            "canonical_rows": [
                {
                    "request_id": "REQ-1",
                    "submitted_at": "2026-04-05T15:00:00Z",
                    "requester_name": "Ana",
                    "merchant_name": "Comercio",
                    "document_type": "invoice",
                    "document_date": "2026-04-04",
                    "document_cuit": "30712345678",
                    "amount": 1000.0,
                    "currency": "ARS",
                    "payment_method": "transfer",
                    "category": "viaticos",
                    "evidence_list": [],
                    "status": "ready",
                }
            ],
            "findings": [{"finding_type": "ready_for_approval"}],
            "summary": {
                "total_cases": 1,
                "ready_for_approval_cases": 1,
                "needs_completion_cases": 0,
                "low_quality_cases": 0,
                "duplicate_suspected_cases": 0,
                "high_amount_cases": 0,
                "invalid_cases": 0,
            },
            "suggested_actions": [
                {
                    "action_type": "notify",
                    "priority": "low",
                    "description": "sin accion",
                    "context": {},
                }
            ],
        }

    def test_request_valido_v2(self):
        payload = ModuleIngestionRequest(**self._stock_payload())
        result = svc.persist_module_ingestion(payload)
        self.assertEqual(result["contract_version"], "module-ingestions.v2")
        self.assertEqual(result["status"], "accepted")

    def test_rechazo_contract_version_invalida(self):
        raw = self._stock_payload()
        raw["contract_version"] = "module-ingestions.v1"
        payload = ModuleIngestionRequest(**raw)
        with self.assertRaises(ValueError):
            svc.persist_module_ingestion(payload)

    def test_rechazo_generated_at_invalido(self):
        raw = self._stock_payload()
        raw["generated_at"] = "2026/04/05"
        payload = ModuleIngestionRequest(**raw)
        with self.assertRaises(ValueError):
            svc.persist_module_ingestion(payload)

    def test_calcula_content_hash_cuando_falta(self):
        payload = ModuleIngestionRequest(**self._stock_payload())
        self.assertIsNone(payload.content_hash)

        result = svc.persist_module_ingestion(payload)
        self.assertEqual(len(result["content_hash"]), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in result["content_hash"]))

    def test_acepta_content_hash_correcto(self):
        raw = self._stock_payload()
        tmp = ModuleIngestionRequest(**raw)
        raw["content_hash"] = svc._compute_content_hash(tmp)

        payload = ModuleIngestionRequest(**raw)
        result = svc.persist_module_ingestion(payload)
        self.assertEqual(result["content_hash"], raw["content_hash"])
        self.assertEqual(result["status"], "accepted")

    def test_dedupe_por_tenant_module_content_hash(self):
        raw = self._stock_payload()
        tmp = ModuleIngestionRequest(**raw)
        raw["content_hash"] = svc._compute_content_hash(tmp)

        first = svc.persist_module_ingestion(ModuleIngestionRequest(**raw))
        second = svc.persist_module_ingestion(ModuleIngestionRequest(**raw))

        self.assertEqual(first["ingestion_id"], second["ingestion_id"])
        self.assertTrue(second["deduped"])
        self.assertEqual(second["status"], "accepted_deduped")

    def test_respuesta_conserva_ingestion_id(self):
        result = svc.persist_module_ingestion(ModuleIngestionRequest(**self._stock_payload()))
        self.assertEqual(result["ingestion_id"], "ing_test_001")

    def test_stock_simple_validacion_minima_reforzada(self):
        raw = self._stock_payload()
        raw["canonical_rows"][0].pop("producto")
        payload = ModuleIngestionRequest(**raw)
        with self.assertRaises(ValueError):
            svc.persist_module_ingestion(payload)

    def test_expense_evidence_sigue_funcionando(self):
        result = svc.persist_module_ingestion(ModuleIngestionRequest(**self._expense_payload()))
        self.assertEqual(result["module"], "expense_evidence")
        self.assertEqual(result["status"], "accepted")

    def test_request_meta_json_se_persiste(self):
        result = svc.persist_module_ingestion(ModuleIngestionRequest(**self._stock_payload()))
        request_meta_path = result["artifacts"]["request_meta"]
        self.assertIn(request_meta_path, self.fake_bucket._store)

        request_meta = json.loads(self.fake_bucket._store[request_meta_path].decode("utf-8"))
        self.assertEqual(request_meta["module"], "stock_simple")
        self.assertIn("parse_metadata", request_meta)
        self.assertIn("audit_metadata", request_meta)

        digest_path = result["artifacts"]["digest"]
        self.assertIn(digest_path, self.fake_bucket._store)
        digest = json.loads(self.fake_bucket._store[digest_path].decode("utf-8"))
        self.assertEqual(digest["digest_version"], "daily_digest.v1")
        self.assertIn("foto_de_hoy", digest)
        self.assertIn("lo_que_importa_ahora", digest)
        self.assertIn("pregunta_del_dia", digest)

    def test_get_module_ingestions_por_ingestion_id(self):
        created = svc.persist_module_ingestion(ModuleIngestionRequest(**self._stock_payload()))
        fetched = module_ingestions_route.get_module_ingestion_by_id(created["ingestion_id"])

        self.assertEqual(fetched["ingestion_id"], created["ingestion_id"])
        self.assertEqual(fetched["status"], "accepted")


if __name__ == "__main__":
    unittest.main()

