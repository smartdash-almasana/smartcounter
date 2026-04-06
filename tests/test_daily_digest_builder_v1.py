from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.services.daily_digest_builder import build_daily_digest_v1


class TestDailyDigestBuilderV1(unittest.TestCase):
    def test_builder_estructura_basica_tres_bloques(self):
        digest = build_daily_digest_v1(
            tenant_id="demo001",
            normalized_signals=[
                {
                    "signal_id": "sig_1",
                    "module": "stock_simple",
                    "signal_code": "stock_break_risk",
                    "state": "active",
                    "severity": "high",
                    "priority": "p1",
                    "score": 0.85,
                    "summary": "Stock critico en SKU-1",
                    "entity_scope": {"entity_type": "item", "entity_id": "SKU-1"},
                }
            ],
            summaries_by_module={"stock_simple": {"total_rows": 10}},
            generated_at=datetime(2026, 4, 6, 15, 0, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(digest["digest_version"], "daily_digest.v1")
        self.assertIn("foto_de_hoy", digest)
        self.assertIn("lo_que_importa_ahora", digest)
        self.assertIn("pregunta_del_dia", digest)
        self.assertEqual(digest["foto_de_hoy"]["total_senales_activas"], 1)

    def test_consume_solo_signals_activas(self):
        digest = build_daily_digest_v1(
            tenant_id="demo001",
            normalized_signals=[
                {
                    "signal_id": "sig_a",
                    "module": "stock_simple",
                    "signal_code": "stock_break_risk",
                    "state": "active",
                    "severity": "medium",
                    "priority": "p2",
                    "score": 0.65,
                    "summary": "Activa",
                },
                {
                    "signal_id": "sig_r",
                    "module": "stock_simple",
                    "signal_code": "stock_break_risk",
                    "state": "resolved",
                    "severity": "high",
                    "priority": "p1",
                    "score": 0.85,
                    "summary": "Resuelta",
                },
                {
                    "signal_id": "sig_e",
                    "module": "stock_simple",
                    "signal_code": "stock_break_risk",
                    "state": "expired",
                    "severity": "high",
                    "priority": "p1",
                    "score": 0.85,
                    "summary": "Expirada",
                },
            ],
        )

        self.assertEqual(digest["foto_de_hoy"]["total_senales_activas"], 1)
        self.assertEqual(len(digest["lo_que_importa_ahora"]["alertas"]), 1)
        self.assertEqual(digest["lo_que_importa_ahora"]["alertas"][0]["signal_id"], "sig_a")

    def test_prioriza_por_priority_severity_score(self):
        digest = build_daily_digest_v1(
            tenant_id="demo001",
            normalized_signals=[
                {
                    "signal_id": "sig_low",
                    "module": "stock_simple",
                    "signal_code": "s1",
                    "state": "active",
                    "severity": "critical",
                    "priority": "p3",
                    "score": 0.99,
                    "summary": "P3",
                },
                {
                    "signal_id": "sig_mid",
                    "module": "expense_evidence",
                    "signal_code": "s2",
                    "state": "active",
                    "severity": "high",
                    "priority": "p1",
                    "score": 0.70,
                    "summary": "P1",
                },
                {
                    "signal_id": "sig_top",
                    "module": "stock_simple",
                    "signal_code": "s3",
                    "state": "active",
                    "severity": "critical",
                    "priority": "p0",
                    "score": 0.80,
                    "summary": "P0",
                },
            ],
        )

        ordered = [a["signal_id"] for a in digest["lo_que_importa_ahora"]["alertas"]]
        self.assertEqual(ordered[0], "sig_top")
        self.assertEqual(ordered[1], "sig_mid")
        self.assertEqual(ordered[2], "sig_low")

    def test_limita_alertas_visibles(self):
        signals = []
        for idx in range(10):
            signals.append(
                {
                    "signal_id": f"sig_{idx}",
                    "module": "stock_simple",
                    "signal_code": f"s{idx}",
                    "state": "active",
                    "severity": "medium",
                    "priority": "p2",
                    "score": 0.5,
                    "summary": "alerta",
                }
            )

        digest = build_daily_digest_v1(
            tenant_id="demo001",
            normalized_signals=signals,
            max_visible_alerts=5,
        )

        self.assertEqual(digest["foto_de_hoy"]["total_senales_activas"], 10)
        self.assertEqual(digest["foto_de_hoy"]["total_alertas_visibles"], 5)
        self.assertEqual(len(digest["lo_que_importa_ahora"]["alertas"]), 5)

    def test_pregunta_del_dia_sin_alertas_activas(self):
        digest = build_daily_digest_v1(
            tenant_id="demo001",
            normalized_signals=[],
        )

        question = digest["pregunta_del_dia"]
        self.assertIsNone(question["signal_id_referencia"])
        self.assertIsNone(question["prioridad_objetivo"])


if __name__ == "__main__":
    unittest.main()
