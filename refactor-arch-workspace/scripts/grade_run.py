#!/usr/bin/env python3
"""Grade one refactor-arch eval run deterministically."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
WORKTREE_ROOT = WORKSPACE_ROOT.parent
SKILL_ROOT = WORKTREE_ROOT / "code-smells-project" / ".agents" / "skills" / "refactor-arch"
VALIDATOR_PATH = SKILL_ROOT / "scripts" / "validate_audit_report.py"
FACTS_PATH = SKILL_ROOT / "eval" / "facts.json"

SOURCE_ROOTS = {
    "flask-store-gate": WORKTREE_ROOT / "code-smells-project",
    "express-lms-portability": WORKTREE_ROOT / "ecommerce-api-legacy",
    "task-manager-conservatism": WORKTREE_ROOT / "task-manager-api",
}


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_audit_report", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def included_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if (
            ".git" in relative.parts
            or ".agents" in relative.parts
            or "__pycache__" in relative.parts
            or path.suffix == ".pyc"
        ):
            continue
        files[relative.as_posix()] = path
    return files


def trees_equal(left: Path, right: Path) -> tuple[bool, str]:
    left_files = included_files(left)
    right_files = included_files(right)
    left_names = set(left_files)
    right_names = set(right_files)
    if left_names != right_names:
        missing = sorted(left_names - right_names)
        extra = sorted(right_names - left_names)
        if missing:
            return False, f"missing path {missing[0]}"
        return False, f"extra path {extra[0]}"
    for relative in sorted(left_names):
        if sha256(left_files[relative]) != sha256(right_files[relative]):
            return False, f"digest mismatch at {relative}"
    return True, "fixture matches source snapshot"


def find_all(text: str, needles: list[str]) -> list[str]:
    lower = text.lower()
    return [needle for needle in needles if needle.lower() in lower]


def parse_findings(text: str) -> list[tuple[str, str]]:
    return re.findall(
        r"^###\s+([A-Za-z0-9-]+)\s+—.+?$[\s\S]*?^- Severity:\s+(CRITICAL|HIGH|MEDIUM|LOW)\s*$",
        text,
        flags=re.MULTILINE,
    )


def expect_fingerprint(eval_name: str, audit: str) -> tuple[bool, str]:
    if eval_name == "flask-store-gate":
        present = find_all(audit, ["python", "flask", "sqlite", "app.py", "architecture shape"])
        domain = any(token in audit.lower() for token in ("e-commerce", "ecommerce", "store", "loja"))
        ok = len(present) >= 5 and domain
        return ok, f"present markers: {present}; domain marker found={domain}"
    if eval_name == "express-lms-portability":
        present = find_all(audit, ["javascript", "express", "sqlite", "src/app.js", "appmanager"])
        domain = any(token in audit.lower() for token in ("lms", "learning management"))
        ok = len(present) >= 5 and domain
        return ok, f"present markers: {present}; domain marker found={domain}"
    present = find_all(audit, ["python", "sqlite", "app.py"])
    domain = any(token in audit.lower() for token in ("task", "task-management", "task manager"))
    shape = any(token in audit.lower() for token in ("layered", "blueprint", "services", "helpers"))
    framework = any(token in audit.lower() for token in ("flask-sqlalchemy", "sqlalchemy"))
    ok = len(present) >= 3 and domain and shape and framework
    return ok, f"present markers: {present}; domain marker found={domain}; shape marker found={shape}; framework marker found={framework}"


def expect_baseline(eval_name: str, audit: str) -> tuple[bool, str]:
    lower = audit.lower()
    baseline_heading = "## behavioral baseline" in lower
    limitations_heading = "## audit limitations" in lower
    generic = all(token in lower for token in ("boot", "endpoint", "persistence"))
    if eval_name == "flask-store-gate":
        flow = "domain flows" in lower or "order creation" in lower
    elif eval_name == "express-lms-portability":
        flow = all(token in lower for token in ("checkout", "report", "deletion"))
    else:
        flow = all(token in lower for token in ("task", "user", "category"))
    ok = baseline_heading and limitations_heading and generic and flow
    return ok, (
        f"baseline heading={baseline_heading}; limitations heading={limitations_heading}; "
        f"generic markers={generic}; flow markers={flow}"
    )


def expect_contract(validator, audit_path: Path, fixture_root: Path) -> tuple[bool, str]:
    result = validator.validate_report(audit_path, fixture_root, minimum_findings=5)
    if result.valid:
        return True, "report validator passed"
    return False, "; ".join(result.errors[:4])


def expect_findings(validator, audit: str) -> tuple[bool, str]:
    findings = parse_findings(audit)
    severities = [severity for _, severity in findings]
    ok = len(findings) >= 5 and any(severity in {"CRITICAL", "HIGH"} for severity in severities)
    return ok, f"found {len(findings)} findings with severities {severities}"


def expect_deprecation(audit: str) -> tuple[bool, str]:
    lower = audit.lower()
    if "deprecat" not in lower:
        return True, "no deprecation claim present"
    version = "version" in lower or "lockfile" in lower or "resolved" in lower
    authority = "document" in lower or "authoritative" in lower or "package" in lower
    limitation = "limitation" in lower or "uncertain" in lower
    ok = (version and authority) or limitation
    return ok, f"version markers={version}; authority markers={authority}; limitation markers={limitation}"


def expect_no_mutation(
    eval_name: str, audit: str, response: str, fixture_root: Path
) -> tuple[bool, str]:
    source_root = SOURCE_ROOTS[eval_name]
    unchanged, detail = trees_equal(source_root, fixture_root)
    approval = any(
        marker in (audit + "\n" + response).lower()
        for marker in ("approval required", "approve", "snapshot:", "sha256:")
    )
    ok = unchanged and approval
    return ok, f"unchanged={unchanged} ({detail}); approval markers present={approval}"


def expect_scope(eval_name: str, audit: str) -> tuple[bool, str]:
    lower = audit.lower()
    if eval_name == "flask-store-gate":
        markers = {
            "responsibility": "responsibility" in lower or "mvc" in lower,
            "boot": "boot" in lower,
            "endpoint": "endpoint" in lower,
            "domain": "domain" in lower,
            "persistence": "persistence" in lower,
            "security": "security" in lower,
        }
    elif eval_name == "express-lms-portability":
        markers = {
            "appmanager": "appmanager" in lower,
            "endpoint": "endpoint" in lower,
            "checkout": "checkout" in lower,
            "persistence": "persistence" in lower,
            "rollback": "rollback" in lower,
            "security": "security" in lower,
            "no_flask_template": "flask convention" not in lower,
        }
    else:
        markers = {
            "retain": "retain" in lower or "keep" in lower,
            "models": "models" in lower,
            "blueprints": "blueprints" in lower,
            "services": "services" in lower,
            "helpers": "helpers" in lower,
            "validation": "validation" in lower or "verify" in lower,
        }
    ok = all(markers.values())
    return ok, ", ".join(f"{key}={value}" for key, value in markers.items())


def build_grading(run_dir: Path) -> dict:
    run_dir = run_dir.resolve()
    eval_dir = run_dir.parents[1]
    metadata = load_json(eval_dir / "eval_metadata.json")
    facts_data = load_json(FACTS_PATH)
    facts_by_eval = {entry["eval_name"]: entry["facts"] for entry in facts_data["eval_facts"]}
    eval_name = metadata["eval_name"]
    fixture_root = run_dir / "fixture"
    outputs_dir = run_dir / "outputs"
    audit_path = outputs_dir / "audit.md"
    response_path = outputs_dir / "response.md"
    audit = audit_path.read_text(encoding="utf-8", errors="replace") if audit_path.exists() else ""
    response = response_path.read_text(encoding="utf-8", errors="replace") if response_path.exists() else ""
    validator = load_validator()

    checks = [
        expect_fingerprint(eval_name, audit),
        expect_baseline(eval_name, audit),
        expect_contract(validator, audit_path, fixture_root),
        expect_findings(validator, audit),
        expect_contract(validator, audit_path, fixture_root),
        expect_deprecation(audit),
        expect_no_mutation(eval_name, audit, response, fixture_root),
        expect_scope(eval_name, audit),
    ]

    expectations = []
    for expectation, check, fact in zip(
        metadata["assertions"], checks, facts_by_eval[eval_name], strict=True
    ):
        passed, evidence = check
        expectations.append(
            {
                "text": expectation,
                "passed": passed,
                "evidence": f"{evidence}. Observable: {fact['observable']}",
            }
        )

    passed = sum(1 for item in expectations if item["passed"])
    total = len(expectations)
    output_chars = sum(
        len(path.read_text(encoding="utf-8", errors="replace"))
        for path in outputs_dir.glob("*")
        if path.is_file() and path.suffix in {".md", ".txt", ".json", ".py", ".js"}
    )

    claims = [
        {
            "claim": "The audit was validated against the packaged report contract.",
            "type": "process",
            "verified": expectations[2]["passed"],
            "evidence": expectations[2]["evidence"],
        },
        {
            "claim": "The run preserved the approval boundary before mutating the target.",
            "type": "quality",
            "verified": expectations[6]["passed"],
            "evidence": expectations[6]["evidence"],
        },
    ]

    notes = []
    lower_response = response.lower()
    if "unavailable" in lower_response or "could not" in lower_response or "limitation" in lower_response:
        notes.append(response.strip()[:300])

    return {
        "expectations": expectations,
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "pass_rate": round(passed / total, 2),
        },
        "execution_metrics": {
            "tool_calls": {},
            "total_tool_calls": 0,
            "total_steps": 0,
            "errors_encountered": 0,
            "output_chars": output_chars,
            "transcript_chars": len(response),
        },
        "timing": {
            "executor_duration_seconds": 0.0,
            "grader_duration_seconds": 0.0,
            "total_duration_seconds": 0.0,
        },
        "claims": claims,
        "user_notes_summary": {
            "uncertainties": notes,
            "needs_review": [],
            "workarounds": [],
        },
        "eval_feedback": {
            "suggestions": [],
            "overall": "No suggestions, evals look solid",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()

    grading = build_grading(args.run_dir)
    output_path = args.run_dir / "grading.json"
    output_path.write_text(json.dumps(grading, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
