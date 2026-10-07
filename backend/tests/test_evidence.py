"""Run with pytest or `python -m unittest tests.test_evidence` without ML dependencies."""
import unittest
from types import SimpleNamespace

from app.rag.evidence import audit_answer, safe_answer


class EvidenceAuditTests(unittest.TestCase):
    def setUp(self):
        self.hits = [SimpleNamespace(number=1, file_name="risk.txt", location="text",
                                     excerpt="Pump pressure reached 12% on Tuesday.")]

    def test_citation_and_exact_number_are_traceable_but_not_semantically_verified(self):
        audit = audit_answer("Pump pressure reached 12% on Tuesday [1].", self.hits)
        self.assertEqual(audit["status"], "citation_checked")
        self.assertIn("semantic support", audit["warnings"][0])

    def test_unsupported_number_is_withheld(self):
        answer, audit = safe_answer("Pump pressure reached 99% on Tuesday [1].", self.hits)
        self.assertEqual(audit["status"], "withheld")
        self.assertNotIn("99%", answer)
        self.assertIn("12%", answer)
        self.assertEqual(audit["checks"], [])

    def test_each_claim_requires_a_real_citation(self):
        for answer in ("An uncited claim.", "A claim [2].", "Supported [1]. An uncited second claim."):
            with self.subTest(answer=answer):
                _, audit = safe_answer(answer, self.hits)
                self.assertTrue(audit["abstained"])

    def test_percentage_does_not_match_a_bare_number(self):
        audit = audit_answer("It was 12 [1].", self.hits)
        self.assertEqual(audit["status"], "withheld")

    def test_direct_excerpts_and_missing_sources_are_labeled(self):
        self.assertEqual(audit_answer("[1] pressure 12%", self.hits, extractive=True)["status"], "source_excerpts")
        self.assertEqual(audit_answer("No sources", [])["status"], "insufficient")

    def test_ocr_only_numerical_claim_is_withheld_and_flagged(self):
        self.hits[0].quality = {"flags": ["ocr"], "ocr_signal": 0.54}
        answer, audit = safe_answer("Pump pressure reached 12% [1].", self.hits)
        self.assertEqual(audit["status"], "withheld")
        self.assertNotIn("12% [1].", answer)
        self.assertEqual(audit["checks"], [])

    def test_multilingual_sentences_each_need_a_citation(self):
        result = audit_answer("पंप बंद हुआ [1]। दबाव बढ़ा।", self.hits)
        self.assertEqual(result["status"], "withheld")


if __name__ == "__main__":
    unittest.main()
