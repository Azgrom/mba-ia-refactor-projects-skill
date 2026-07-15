# Refactor Arch Evaluation Method

This package treats skill effectiveness as a behavior change that must be visible in artifacts, not as a claim about subjective code quality.

## Paired comparison

Each evaluation prompt is designed to run twice against the same disposable fixture:

- Baseline: the agent receives the prompt without `refactor-arch`.
- With skill: the agent receives the same prompt with `refactor-arch`.

The comparison is valid only if both runs share the same target root, output path, and pre-approval mutation constraint.

## What is being asserted

The facts in [facts.json](/tmp/refactor-arch-skill/code-smells-project/.agents/skills/refactor-arch/eval/facts.json) consolidate the discriminating expectations used to judge the skill:

- It must fingerprint an unfamiliar backend before judging architecture.
- It must capture a behavioral baseline before proposing changes.
- It must emit a validated audit contract with exact evidence and a snapshot digest.
- It must stop at an explicit approval gate before mutating the target.
- It must propose contextual, responsibility-based remediation instead of template rewrites.

## Why these facts were kept

Every retained fact satisfies all three filters:

1. Observable from generated artifacts or deterministic verifier outputs.
2. Portable across the Flask monolith, Express monolith, and partially layered Flask fixture.
3. Discriminating enough to catch baseline failure modes that commonly appear without the skill.

Expectations that depended on fixture-specific answer keys or subjective style judgments were excluded.

## Consolidation rules

- Keep one expectation per objective behavior, even if multiple prompts exercise it.
- Prefer validator-backed checks over human interpretation when possible.
- Encode cross-stack portability and refactoring conservatism explicitly so the suite does not overfit to a single framework.
- Preserve the no-mutation approval boundary as a first-class evaluation dimension.

## Packaged evidence

- [evals.json](/tmp/refactor-arch-skill/code-smells-project/.agents/skills/refactor-arch/eval/evals.json) captures the prompts and expected outputs.
- [facts.json](/tmp/refactor-arch-skill/code-smells-project/.agents/skills/refactor-arch/eval/facts.json) captures the assertion facts used to evaluate the runs.
- [test_eval_suite.py](/tmp/refactor-arch-skill/code-smells-project/.agents/skills/refactor-arch/tests/test_eval_suite.py) keeps the eval suite and fact suite aligned.
- [test_validate_audit_report.py](/tmp/refactor-arch-skill/code-smells-project/.agents/skills/refactor-arch/tests/test_validate_audit_report.py) and [test_verify_skill_distribution.py](/tmp/refactor-arch-skill/code-smells-project/.agents/skills/refactor-arch/tests/test_verify_skill_distribution.py) preserve the deterministic validators the skill relies on.
