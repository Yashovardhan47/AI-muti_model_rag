"""Metric checks without a running model, database, or HTTP service."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "evaluate.py"
spec = importlib.util.spec_from_file_location("atlas_evaluate", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EvaluationTests(unittest.TestCase):
    def test_recall_rank_and_abstention(self):
        gold = [{"file_id": "report", "location": "page 2"}, {"file_id": "log", "location": "JSON"}]
        hits = [{"file_id": "other", "location": "text"}, {"file_id": "report", "location": "page 2"}]
        result = module.score_case(gold, hits, True, {"abstained": False, "status": "citation_checked"})
        self.assertEqual(result["evidence_recall"], 0.5)
        self.assertEqual(result["reciprocal_rank"], 0.5)
        self.assertTrue(result["abstention_correct"])
        self.assertIsNone(module.score_case([], hits, False)["evidence_recall"])

    def test_latency_and_group_summary(self):
        report = module.summarize([{"latency_ms": value, "evidence_recall": 1, "reciprocal_rank": 1}
                                   for value in range(1, 21)])
        self.assertEqual(report["p95_latency_ms"], 19)
        self.assertEqual(report["median_latency_ms"], 10.5)


if __name__ == "__main__":
    unittest.main()
