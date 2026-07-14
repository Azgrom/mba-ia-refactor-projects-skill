import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EVALS_PATH = SKILL_ROOT / "eval" / "evals.json"
FACTS_PATH = SKILL_ROOT / "eval" / "facts.json"


class EvalSuiteTests(unittest.TestCase):
    def load_json(self, path: Path):
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_eval_suite_and_fact_suite_stay_in_lockstep(self):
        evals = self.load_json(EVALS_PATH)
        facts = self.load_json(FACTS_PATH)

        self.assertEqual("refactor-arch", evals["skill_name"])
        self.assertEqual(evals["skill_name"], facts["skill_name"])

        evals_by_id = {entry["id"]: entry for entry in evals["evals"]}
        facts_by_id = {entry["eval_id"]: entry for entry in facts["eval_facts"]}
        self.assertEqual(set(evals_by_id), set(facts_by_id))

        for eval_id, eval_entry in evals_by_id.items():
            fact_entry = facts_by_id[eval_id]
            expectations = eval_entry["expectations"]
            expectation_facts = fact_entry["facts"]

            self.assertEqual(len(expectations), len(expectation_facts))
            self.assertEqual(expectations, [fact["expectation"] for fact in expectation_facts])

            for fact in expectation_facts:
                self.assertTrue(fact["observable"].strip())
                self.assertTrue(fact["assertion_method"].strip())
                self.assertTrue(fact["discriminator"].strip())


if __name__ == "__main__":
    unittest.main()
