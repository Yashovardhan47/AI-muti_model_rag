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


if __name__ == "__main__":
    unittest.main()
