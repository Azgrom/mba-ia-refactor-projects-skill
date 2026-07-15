#!/usr/bin/env python3
"""Validate refactor-arch Markdown reports without rewriting them."""

from __future__ import annotations

import argparse
import hashlib
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import NamedTuple


SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
REQUIRED_SECTIONS = (
    "Target",
    "Project Fingerprint",
    "Source Scope",
    "Behavioral Baseline",
    "Audit Limitations",
    "Severity Summary",
    "Findings",
    "Proposed Refactoring Scope",
    "Security-Driven Contract Changes",
    "Approval Required",
    "Audit Snapshot Digest",
)
REQUIRED_FINDING_FIELDS = (
    "Rule",
    "Severity",
    "Location",
    "Evidence",
    "Impact",
    "Recommendation",
    "Status",
    "Evidence authority",
)


class ValidationResult(NamedTuple):
    valid: bool
    errors: tuple[str, ...]


class Finding(NamedTuple):
    finding_id: str
    title: str
    fields: dict[str, str]


def _sections(text: str) -> list[str]:
    return re.findall(r"^## (.+?)\s*$", text, flags=re.MULTILINE)


def _parse_summary(text: str) -> list[tuple[str, int]]:
    return [
        (severity, int(count))
        for severity, count in re.findall(
            r"^\|\s*(CRITICAL|HIGH|MEDIUM|LOW)\s*\|\s*(\d+)\s*\|\s*$",
            text,
            flags=re.MULTILINE,
        )
    ]


def _parse_findings(text: str) -> list[Finding]:
    match = re.search(
        r"^## Findings\s*$\n(?P<body>.*?)(?=^## Proposed Refactoring Scope\s*$)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []

    body = match.group("body")
    header_pattern = re.compile(
        r"^###\s+([A-Za-z0-9][A-Za-z0-9-]*)\s+—\s+(.+?)\s*$",
        flags=re.MULTILINE,
    )
    headers = list(header_pattern.finditer(body))
    findings: list[Finding] = []
    for index, header in enumerate(headers):
        block_end = headers[index + 1].start() if index + 1 < len(headers) else len(body)
        block = body[header.end() : block_end]
        fields: dict[str, str] = {}
        for key, value in re.findall(
            r"^- ([A-Za-z][A-Za-z ]+):[ \t]*(.*?)[ \t]*$", block, re.MULTILINE
        ):
            fields[key] = value
        findings.append(Finding(header.group(1), header.group(2), fields))
    return findings


def _validate_location(
    finding: Finding, project_root: Path, errors: list[str]
) -> None:
    location = finding.fields.get("Location", "")
    match = re.fullmatch(r"(.+):(\d+)-(\d+)", location)
    if not match:
        errors.append(
            f"{finding.finding_id}: Location must use path:start-end with one-based inclusive lines"
        )
        return

    raw_path, start_text, end_text = match.groups()
    posix_path = PurePosixPath(raw_path)
    if posix_path.is_absolute() or ".." in posix_path.parts:
        errors.append(
            f"{finding.finding_id}: source path must be contained in the project root: {raw_path}"
        )
        return

    root = project_root.resolve()
    source_path = (root / Path(*posix_path.parts)).resolve()
    try:
        source_path.relative_to(root)
    except ValueError:
        errors.append(
            f"{finding.finding_id}: source path must be contained in the project root: {raw_path}"
        )
        return

    if not source_path.is_file():
        errors.append(f"{finding.finding_id}: source file does not exist: {raw_path}")
        return

    start, end = int(start_text), int(end_text)
    line_count = len(source_path.read_text(encoding="utf-8", errors="replace").splitlines())
    if start < 1 or end < start or end > line_count:
        errors.append(
            f"{finding.finding_id}: invalid line range {start}-{end} for {raw_path} ({line_count} lines)"
        )


def _validate_snapshot_digest(text: str, errors: list[str]) -> None:
    marker = "## Audit Snapshot Digest\n"
    if marker not in text:
        return
    _, suffix = text.split(marker, 1)
    digest_match = re.match(r"`sha256:([0-9a-f]{64})`\s*$", suffix)
    if not digest_match:
        errors.append("Audit Snapshot Digest must contain one lowercase sha256 value")
        return
    expected = compute_snapshot_digest(text)
    if digest_match.group(1) != expected:
        errors.append(
            f"Audit snapshot digest mismatch: expected sha256:{expected}"
        )


def compute_snapshot_digest(text: str) -> str:
    """Hash the normalized report prefix before the digest heading."""

    marker = "## Audit Snapshot Digest\n"
    if marker not in text:
        raise ValueError("Report is missing the Audit Snapshot Digest heading")
    prefix = text.split(marker, 1)[0].replace("\r\n", "\n")
    return hashlib.sha256(prefix.encode("utf-8")).hexdigest()


def validate_report(
    report_path: Path, project_root: Path, minimum_findings: int = 5
) -> ValidationResult:
    """Return structural and evidence diagnostics for one audit report."""

    report_path = Path(report_path)
    project_root = Path(project_root)
    errors: list[str] = []

    if minimum_findings < 1:
        errors.append("minimum_findings must be at least 1")
    if not project_root.is_dir():
        errors.append(f"Project root does not exist or is not a directory: {project_root}")
    if not report_path.is_file():
        errors.append(f"Report does not exist: {report_path}")
        return ValidationResult(False, tuple(errors))

    text = report_path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    if not text.startswith("# Architecture Audit Report\n"):
        errors.append("Report must start with '# Architecture Audit Report'")

    actual_sections = _sections(text)
    missing_sections = [section for section in REQUIRED_SECTIONS if section not in actual_sections]
    for section in missing_sections:
        errors.append(f"Missing required section: {section}")
    if not missing_sections:
        positions = [actual_sections.index(section) for section in REQUIRED_SECTIONS]
        if positions != sorted(positions):
            errors.append("Required report sections are out of order")

    summary = _parse_summary(text)
    summary_order = [severity for severity, _ in summary]
    if summary_order != list(SEVERITIES):
        errors.append("Severity summary order must be CRITICAL, HIGH, MEDIUM, LOW")

    findings = _parse_findings(text)
    if len(findings) < minimum_findings:
        errors.append(
            f"Report must contain at least {minimum_findings} findings; found {len(findings)}"
        )

    ids = [finding.finding_id for finding in findings]
    duplicates = sorted(identifier for identifier, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append(f"Duplicate finding IDs: {', '.join(duplicates)}")

    detail_severities: list[str] = []
    for finding in findings:
        for field in REQUIRED_FINDING_FIELDS:
            if not finding.fields.get(field, "").strip():
                errors.append(f"{finding.finding_id}: missing or empty {field}")
        severity = finding.fields.get("Severity", "")
        if severity not in SEVERITIES:
            errors.append(f"{finding.finding_id}: invalid severity {severity!r}")
        else:
            detail_severities.append(severity)
        if project_root.is_dir():
            _validate_location(finding, project_root, errors)

    severity_rank = {severity: index for index, severity in enumerate(SEVERITIES)}
    if detail_severities and [severity_rank[item] for item in detail_severities] != sorted(
        severity_rank[item] for item in detail_severities
    ):
        errors.append("Findings must be ordered CRITICAL, HIGH, MEDIUM, LOW")

    detail_counts = Counter(detail_severities)
    if summary_order == list(SEVERITIES):
        for severity, expected_count in summary:
            actual_count = detail_counts[severity]
            if actual_count != expected_count:
                errors.append(
                    f"Severity count mismatch for {severity}: summary={expected_count}, findings={actual_count}"
                )

    if not (detail_counts["CRITICAL"] or detail_counts["HIGH"]):
        errors.append("Report must contain at least one CRITICAL or HIGH finding")

    _validate_snapshot_digest(text, errors)
    return ValidationResult(not errors, tuple(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_path", type=Path)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--minimum-findings", type=int, default=5)
    parser.add_argument(
        "--print-digest",
        action="store_true",
        help="print the digest expected for the current report prefix without rewriting it",
    )
    args = parser.parse_args()

    if args.print_digest:
        try:
            text = args.report_path.read_text(encoding="utf-8", errors="replace")
            print(f"sha256:{compute_snapshot_digest(text)}")
            return 0
        except (OSError, ValueError) as error:
            print(f"ERROR: {error}")
            return 1

    result = validate_report(
        args.report_path, args.project_root, minimum_findings=args.minimum_findings
    )
    if result.valid:
        print(f"VALID: {args.report_path}")
        return 0
    for error in result.errors:
        print(f"ERROR: {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
