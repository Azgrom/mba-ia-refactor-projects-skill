import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = SKILL_ROOT / "scripts" / "validate_audit_report.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_audit_report", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def finding(finding_id: str, severity: str, line: int) -> str:
    return f"""### {finding_id} — Demonstrated {severity.lower()} issue
- Rule: {severity.lower()}-demonstrated-issue
- Severity: {severity}
- Location: src/app.py:{line}-{line}
- Evidence: The source line demonstrates the issue directly.
- Impact: The issue has an observable architectural or security impact.
- Recommendation: Apply the smallest responsibility-focused remediation.
- Status: proposed
- Evidence authority: scoped source inspection
"""


def compliant_report() -> str:
    prefix = """# Architecture Audit Report

## Target
- Project: sample-api
- Target root: .
- Stack: Python 3 / Flask

## Project Fingerprint
- Language: Python
- Framework: Flask
- Entry points: src/app.py
- Persistence: SQLite
- Architecture shape: route-owned orchestration and persistence

## Source Scope
- Included: src/app.py
- Excluded: generated and vendored files

## Behavioral Baseline
- Boot: `python src/app.py`
- Endpoints: `GET /health`
- Domain flows: create and retrieve an item
- Persistence: successful creation writes one row

## Audit Limitations
- Runtime endpoint checks were unavailable in this static fixture.

## Severity Summary
| Severity | Count |
|---|---:|
| CRITICAL | 1 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 1 |

## Findings

"""
    prefix += finding("F-001", "CRITICAL", 1)
    prefix += "\n" + finding("F-002", "HIGH", 2)
    prefix += "\n" + finding("F-003", "MEDIUM", 3)
    prefix += "\n" + finding("F-004", "MEDIUM", 4)
    prefix += "\n" + finding("F-005", "LOW", 5)
    prefix += """
## Proposed Refactoring Scope
- Separate transport parsing from application orchestration.

## Security-Driven Contract Changes
- None proposed.

## Approval Required
Reply with explicit approval of this report and its snapshot digest before any target mutation.

"""
    digest = hashlib.sha256(prefix.replace("\r\n", "\n").encode("utf-8")).hexdigest()
    return prefix + f"## Audit Snapshot Digest\n`sha256:{digest}`\n"


class ValidateAuditReportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "project"
        (self.root / "src").mkdir(parents=True)
        (self.root / "src" / "app.py").write_text(
            "one\ntwo\nthree\nfour\nfive\n", encoding="utf-8"
        )
        self.report_path = Path(self.temp_dir.name) / "audit.md"
        self.report_path.write_text(compliant_report(), encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def validate(self, minimum_findings: int = 5):
        return load_module().validate_report(
            self.report_path, self.root, minimum_findings=minimum_findings
        )

    def write_report(self, text: str):
        self.report_path.write_text(text, encoding="utf-8")

    def test_accepts_compliant_report(self):
        result = self.validate()
        self.assertTrue(result.valid, result.errors)
        self.assertEqual((), result.errors)

    def test_computes_snapshot_digest_from_report_prefix(self):
        module = load_module()
        text = compliant_report()
        prefix = text.split("## Audit Snapshot Digest\n", 1)[0]
        expected = hashlib.sha256(prefix.encode("utf-8")).hexdigest()
        self.assertEqual(expected, module.compute_snapshot_digest(text))

    def test_rejects_missing_required_section(self):
        self.write_report(compliant_report().replace("## Behavioral Baseline", "## Missing"))
        result = self.validate()
        self.assertFalse(result.valid)
        self.assertTrue(any("Behavioral Baseline" in error for error in result.errors))

    def test_rejects_severity_summary_out_of_order(self):
        text = compliant_report().replace(
            "| CRITICAL | 1 |\n| HIGH | 1 |",
            "| HIGH | 1 |\n| CRITICAL | 1 |",
        )
        self.write_report(text)
        result = self.validate()
        self.assertFalse(result.valid)
        self.assertTrue(any("severity summary order" in error.lower() for error in result.errors))

    def test_rejects_summary_detail_count_mismatch(self):
        self.write_report(compliant_report().replace("| LOW | 1 |", "| LOW | 2 |"))
        result = self.validate()
        self.assertFalse(result.valid)
        self.assertTrue(any("count" in error.lower() for error in result.errors))

    def test_rejects_duplicate_finding_ids(self):
        self.write_report(compliant_report().replace("### F-005", "### F-004"))
        result = self.validate()
        self.assertFalse(result.valid)
        self.assertTrue(any("duplicate" in error.lower() for error in result.errors))

    def test_rejects_path_outside_project(self):
        self.write_report(compliant_report().replace("src/app.py:5-5", "../outside.py:5-5"))
        result = self.validate()
        self.assertFalse(result.valid)
        self.assertTrue(any("contained" in error.lower() for error in result.errors))

    def test_rejects_missing_source_file(self):
        self.write_report(compliant_report().replace("src/app.py:5-5", "src/missing.py:5-5"))
        result = self.validate()
        self.assertFalse(result.valid)
        self.assertTrue(any("does not exist" in error.lower() for error in result.errors))

    def test_rejects_invalid_or_out_of_bounds_line_range(self):
        self.write_report(compliant_report().replace("src/app.py:5-5", "src/app.py:5-9"))
        result = self.validate()
        self.assertFalse(result.valid)
        self.assertTrue(any("line range" in error.lower() for error in result.errors))

    def test_rejects_empty_evidence_impact_or_recommendation(self):
        self.write_report(
            compliant_report().replace(
                "- Evidence: The source line demonstrates the issue directly.",
                "- Evidence:",
                1,
            )
        )
        result = self.validate()
        self.assertFalse(result.valid)
        self.assertTrue(any("evidence" in error.lower() for error in result.errors))

    def test_rejects_finding_threshold_failure(self):
        result = self.validate(minimum_findings=6)
        self.assertFalse(result.valid)
        self.assertTrue(any("at least 6" in error.lower() for error in result.errors))

    def test_rejects_report_without_critical_or_high(self):
        text = compliant_report()
        text = text.replace("| CRITICAL | 1 |", "| CRITICAL | 0 |")
        text = text.replace("| HIGH | 1 |", "| HIGH | 0 |")
        text = text.replace("| MEDIUM | 2 |", "| MEDIUM | 4 |")
        text = text.replace("- Severity: CRITICAL", "- Severity: MEDIUM")
        text = text.replace("- Severity: HIGH", "- Severity: MEDIUM")
        self.write_report(text)
        result = self.validate()
        self.assertFalse(result.valid)
        self.assertTrue(any("critical or high" in error.lower() for error in result.errors))

    def test_rejects_incorrect_snapshot_digest(self):
        text = compliant_report()
        marker = "`sha256:"
        start = text.index(marker) + len(marker)
        self.write_report(text[:start] + ("0" * 64) + text[start + 64 :])
        result = self.validate()
        self.assertFalse(result.valid)
        self.assertTrue(any("snapshot digest" in error.lower() for error in result.errors))


if __name__ == "__main__":
    unittest.main()
