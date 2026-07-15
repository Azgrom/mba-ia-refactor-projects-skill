---
name: refactor-arch
description: Use when auditing or modernizing an unfamiliar backend for architecture, MVC or SOLID responsibility boundaries, legacy code smells, exact-line security findings, or behavior-preserving refactoring across Flask, Express, or other backend stacks—even when the request only says to review, clean up, restructure, or make the architecture maintainable.
---

# Refactor Arch

## Overview

Understand the backend before judging it, produce a validated evidence-backed audit before changing it, and validate approved changes against captured behavior.

**Core invariant:** an audit request is not mutation authority. The only valid output before approval is project analysis, a validated audit report, and a report-specific approval request.

## Invocation contract

Resolve these values before finalizing the audit:

| Input | Rule |
|---|---|
| `target_root` | Default to the current project root. Reject missing, unreadable, or ambiguous roots. |
| `report_path` | Require the user to supply or confirm it before completing Architecture Audit. Keep it inside the user's authorized workspace. |
| `requested_phase` | Default to Project Analysis plus Architecture Audit. Refactoring is unavailable without matching approval. |
| `user_instruction` | Preserve it as context, but never interpret “continue,” “complete,” or “refactor if needed” in the initial request as approval of a report that did not yet exist. |

Follow repository instructions before this skill. If a referenced file, command, or documentation source is unavailable, surface the limitation rather than inventing evidence.

## Track the run

Copy and maintain this checklist:

```text
Refactor Arch
- [ ] Invocation resolved
- [ ] Project fingerprint complete
- [ ] Behavioral baseline complete
- [ ] Audit report validated
- [ ] Waiting for report-specific approval
- [ ] Approved transformations planned
- [ ] Transformations applied in small batches
- [ ] Behavioral and security validation passed
```

## Phase state machine

| State | Permitted work | Exit condition |
|---|---|---|
| `PROJECT_ANALYSIS` | Read repository material; perform side-effect-free or isolated discovery. | Fingerprint and baseline are complete enough to audit. |
| `ARCHITECTURE_AUDIT` | Read scoped source; verify evidence; write only `report_path`. | Report validator passes and digest is displayed. |
| `WAITING_FOR_APPROVAL` | Explain findings, proposed scope, deferrals, and contract changes. | User explicitly approves the displayed report path and digest, optionally with a finding subset. |
| `REFACTORING` | Apply only approved transformations and approved contract changes. | Every approved finding is resolved or explicitly deferred within the approved scope. |
| `VALIDATION` | Run the baseline-derived validation suite on isolated state. | Every mandatory check passes; otherwise the run remains incomplete. |

Transitions only move forward in that order. A scope expansion returns the run to `ARCHITECTURE_AUDIT` for a revised report and new digest.

## Phase 1: Project Analysis

Read `references/project-analysis.md` completely. Produce both:

1. `ProjectFingerprint`: language, framework, declared/resolved dependency versions, domain, entry points, route surface, persistence lifecycle, realistic source scope/exclusions, present responsibility boundaries, boot procedure, and discovery limitations.
2. `BehavioralBaseline`: boot commands, endpoint contracts, representative domain flows, persistence expectations, and potential security-driven contract exceptions.

Record a pre-audit mutation snapshot. Prefer repository status/diff in Git projects; otherwise hash scoped source and configuration. Runtime discovery that could write a database, cache, log, lockfile, or generated file must run in a disposable copy or be recorded as unavailable.

Do not audit architecture until the source boundary and responsibility map are credible. Do not refactor when boot, routes, or persistence effects remain materially unknown.

## Phase 2: Architecture Audit

Read these files completely:

- `references/anti-pattern-catalog.md`
- `references/audit-report-contract.md`

Apply catalog rules only to scoped executable source. Trace callers and responsibility ownership; merge symptoms with one root cause; cross-reference secondary rules rather than inflating counts.

Every finding must have a unique ID, catalog rule, impact-based severity, repository-relative file, valid one-based inclusive range, concise source evidence, separate impact, contextual recommendation, disposition, and evidence authority.

For deprecated APIs, detect the installed or locked version and use current authoritative documentation according to repository rules. If authority is unavailable, record an Audit Limitation—do not emit a deprecation finding from memory.

Write the exact report contract, compute its snapshot digest, then run:

```bash
python .agents/skills/refactor-arch/scripts/validate_audit_report.py \
  "$report_path" "$target_root" --minimum-findings 5
```

Fix report-generation defects and rerun until valid. If fewer than five genuine findings exist, do not fabricate findings: report the threshold failure as a blocking limitation and stop.

Compare the pre-audit mutation snapshot after writing the report. Revert only changes created by this run; preserve pre-existing user work. The report must be the only new target-root artifact.

## Approval boundary

End the audit response with this concrete contract:

```text
Audit complete and validated: <report_path>
Snapshot: sha256:<digest>
Proposed findings: <IDs>
Security-driven contract changes: <none or explicit list>

No target application files have been changed.
To authorize mutation, reply: Approve <report_path> sha256:<digest> [all findings | finding IDs]
```

Accept approval only when it matches the current report path and digest and identifies all findings or a subset. Silence, “looks good,” a prior request to refactor, an audit file's existence, or an agent's belief that changes are safe does not create an `ApprovedAuditSnapshot`.

When approval excludes findings, record them as deferred. When implementation reveals a new finding or contract change, stop and propose a revised report or addendum with a new digest.

## Phase 3: Refactoring

After matching approval, read these files completely:

- `references/mvc-target-guidelines.md`
- `references/refactoring-playbook.md`

Create a dependency-ordered `RefactoringPlan`. Each transformation names approved finding IDs, affected files, responsibility change, compatibility boundary, rollback boundary, and completion criterion.

Preserve endpoint paths/methods, status semantics, response meaning, public imports where useful, and persistence effects unless the approved snapshot explicitly authorizes a security-driven replacement. Prefer extraction and dependency correction over a whole-project rewrite. Retain existing modules that already own one coherent responsibility.

For behavior-affecting work, capture a failing regression check first when practical, apply the smallest coherent batch, and rerun focused checks before continuing.

## Validation

Read `references/validation-playbook.md` completely. Derive validation from the pre-change baseline and approved security exceptions—not from the refactoring report.

Run dependency, database, boot, every-endpoint, representative domain-flow, persistence, rollback, security, error-contract, and cleanup checks. Save command, fixture state, expected result, actual result, pass/fail, relevant output, and artifact path.

Any failed or skipped mandatory boot, endpoint, domain-flow, persistence, or security check blocks a completion claim. Report failures and the last known safe boundary.

## Quick reference

| Situation | Action |
|---|---|
| Unknown or mixed stack | Produce a partial fingerprint with limitations; do not force MVC or guess commands. |
| Already sound non-MVC architecture | Evaluate responsibilities, not directory names; recommend only evidenced changes. |
| Dynamic route registration | Combine static tracing with safe runtime inspection in disposable state. |
| Fewer than five genuine findings | Fail the requested threshold transparently; never manufacture evidence. |
| Documentation lookup blocked | Record a limitation; omit the deprecation finding. |
| User approves a different report/digest | Stay at `WAITING_FOR_APPROVAL`. |
| New issue appears during refactoring | Stop scope expansion and request a new disposition. |
| Mandatory validation unavailable | Mark the run incomplete. |

## Common mistakes

| Mistake | Correction |
|---|---|
| Refactoring because the initial prompt says “continue independently” | That instruction predates the audit and cannot approve its findings. Stop after the validated report. |
| Describing architecture after already rewriting it | Fingerprint and audit the original snapshot first. |
| Treating one file as one finding | Merge related symptoms under their root cause; use secondary-rule cross-references. |
| Calling an API deprecated from recollection | Require detected version plus authoritative current evidence. |
| Rebuilding a partially layered project into a template tree | Preserve coherent layers and correct only demonstrated responsibility leaks. |
| Claiming success after syntax or boot checks | Exercise all inventoried endpoints, domain flows, persistence effects, and mandatory security checks. |

## Completion report

State the phase reached, audit path/digest, approved/resolved/deferred finding IDs, approved contract changes, validation evidence path, blocking failures, and whether the run is complete. Never describe an incomplete validation as successful.
