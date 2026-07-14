import importlib.util
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "verify_skill_distribution.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_skill_distribution", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class VerifySkillDistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.canonical = base / "canonical"
        self.copy = base / "copy"
        for root in (self.canonical, self.copy):
            (root / "references").mkdir(parents=True)
            (root / "SKILL.md").write_text("skill\n", encoding="utf-8")
            (root / "references" / "one.md").write_text("reference\n", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def verify(self):
        return load_module().verify_distribution(self.canonical, [self.copy])

    def test_accepts_equivalent_trees_and_ignores_runtime_cache(self):
        (self.copy / "__pycache__").mkdir()
        (self.copy / "__pycache__" / "cache.pyc").write_bytes(b"runtime")
        result = self.verify()
        self.assertTrue(result.equivalent, result.errors)
        self.assertEqual((), result.errors)

    def test_reports_first_missing_relative_path(self):
        (self.copy / "references" / "one.md").unlink()
        result = self.verify()
        self.assertFalse(result.equivalent)
        self.assertIn("missing", result.errors[0].lower())
        self.assertIn("references/one.md", result.errors[0])

    def test_reports_first_extra_relative_path(self):
        (self.copy / "extra.md").write_text("extra\n", encoding="utf-8")
        result = self.verify()
        self.assertFalse(result.equivalent)
        self.assertIn("extra", result.errors[0].lower())
        self.assertIn("extra.md", result.errors[0])

    def test_reports_first_content_digest_difference(self):
        (self.copy / "SKILL.md").write_text("changed\n", encoding="utf-8")
        result = self.verify()
        self.assertFalse(result.equivalent)
        self.assertIn("digest", result.errors[0].lower())
        self.assertIn("SKILL.md", result.errors[0])

    def test_reports_missing_copy_root(self):
        result = load_module().verify_distribution(
            self.canonical, [Path(self.temp_dir.name) / "absent"]
        )
        self.assertFalse(result.equivalent)
        self.assertIn("does not exist", result.errors[0].lower())


if __name__ == "__main__":
    unittest.main()
