# Audit Report Contract

Use this exact structure so findings are reviewable, approval is traceable, and `scripts/validate_audit_report.py` can reject malformed evidence.

## Contents

- Report template
- Finding rules
- Snapshot digest
- Validation loop
- Approval semantics

## Report template

```markdown
# Architecture Audit Report

## Target
- Project: [project identity]
- Target root: [target root]
- Stack: [language/version and framework/version]

## Project Fingerprint
- Language: [value]
- Framework: [value]
- Entry points: [repository-relative paths]
- Persistence: [technology and lifecycle]
- Architecture shape: [responsibility ownership]

## Source Scope
- Included: [rule, files/count, and relevant schema/config]
- Excluded: [categories and rationale]

## Behavioral Baseline
- Boot: [command and readiness]
- Endpoints: [complete inventory artifact/summary]
- Domain flows: [representative flows]
- Persistence: [observable expectations]

## Audit Limitations
- [limitation or `None.`]

## Severity Summary
| Severity | Count |
|---|---:|
| CRITICAL | [count] |
| HIGH | [count] |
| MEDIUM | [count] |
| LOW | [count] |

## Findings

### [FINDING-ID] — [Concise root-cause title]
- Rule: [catalog-rule-id]
- Severity: [CRITICAL|HIGH|MEDIUM|LOW]
- Location: [repository-relative/path:start-end]
- Evidence: [minimum source fact that proves the issue]
- Impact: [security, correctness, operability, maintainability, or performance consequence]
- Recommendation: [contextual remediation direction]
- Status: proposed
- Evidence authority: [source/caller/runtime/version-doc evidence]

[Repeat in CRITICAL, HIGH, MEDIUM, LOW order.]

## Proposed Refactoring Scope
- [finding IDs → responsibility changes and compatibility boundaries]

## Security-Driven Contract Changes
- [none or exact unsafe behavior and proposed secure replacement]

## Approval Required
Reply with explicit approval of this report path and snapshot digest before any target mutation. Identify all findings or the approved finding IDs.

## Audit Snapshot Digest
`sha256:[64 lowercase hexadecimal characters]`
```

Keep headings and finding field labels exact. The validator reads them literally.

## Finding rules

- Use stable kebab-case or `F-001`-style unique IDs.
- Use repository-relative POSIX paths. Absolute paths and `..` are invalid.
- Use one-based inclusive line ranges that exist in the audited snapshot.
- Keep Evidence factual and minimal. Put consequences in Impact and action in Recommendation.
- Assign severity from actual exploitability and consequence, not a keyword or file length.
- Use one finding per root cause. Cross-reference secondary catalog rules in Evidence when useful.
- Do not count generated, vendored, dead, test-only, or example code unless it executes in the target path.
- A deprecated-API finding requires detected version plus authoritative current evidence in Evidence authority.
- If fewer than the requested minimum genuine findings exist, say so in Audit Limitations and fail validation rather than splitting or inventing findings.

## Snapshot digest

The immutable snapshot is the UTF-8 report prefix before the `## Audit Snapshot Digest` heading, with CRLF normalized to LF. The prefix includes the newline immediately before the digest heading.

1. Write the complete report with the digest heading and a placeholder value.
2. Print the expected digest without modifying the report:

```bash
python .agents/skills/refactor-arch/scripts/validate_audit_report.py \
  "$report_path" "$target_root" --print-digest
```

3. Replace only the placeholder with the printed `sha256:<digest>` value.
4. Do not edit the report after approval. Any edit produces a new snapshot and requires new approval.

## Validation loop

Run:

```bash
python .agents/skills/refactor-arch/scripts/validate_audit_report.py \
  "$report_path" "$target_root" --minimum-findings 5
```

Correct report-generation defects only, recompute the digest, and rerun. The validator checks required sections/order, severity summary/detail counts, finding order and IDs, path containment, file existence, line bounds, required fields, minimum coverage, CRITICAL/HIGH presence, and digest integrity.

## Approval semantics

Display report path, digest, proposed finding IDs, and proposed security contract changes together. Request this form:

```text
Approve <report_path> sha256:<digest> all findings
```

or:

```text
Approve <report_path> sha256:<digest> F-001,F-003,F-007
```

An approval creates an immutable snapshot of approved findings, approved contract changes, and deferred findings. A reply tied to an older digest, a different path, or no finding scope does not authorize mutation.
