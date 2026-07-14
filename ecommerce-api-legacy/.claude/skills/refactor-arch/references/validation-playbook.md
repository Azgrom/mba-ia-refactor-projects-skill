# Validation Playbook

Prove behavior against the pre-change `BehavioralBaseline`. A green refactoring report, syntax check, or boot check is not validation evidence by itself.

## Contents

- Preconditions
- Isolated state
- Dependency and boot checks
- Endpoint and domain-flow checks
- Persistence and transaction checks
- Security and error checks
- Performance checks
- Evidence format
- Failure and cleanup rules

## Preconditions

Require:

- current approved audit path/digest and finding scope;
- original fingerprint and behavioral baseline;
- approved security-driven contract changes;
- transformation list with resolved/deferred dispositions;
- safe commands and state-isolation method.

If the baseline was materially incomplete, stop. Post-change behavior cannot be compared to an unknown original contract.

## Isolated state

Select state handling from the detected persistence lifecycle:

| State type | Validation method |
|---|---|
| Persistent local database | Back up and validate on a disposable copy; never overwrite the original. |
| Ephemeral in-memory state | Restart per scenario or restore a deterministic seed. |
| ORM-managed local database | Use a disposable database path/schema and run documented initialization/seed. |
| External database/service | Use an authorized test environment or deterministic adapter; otherwise mark validation blocked. |

Use unique non-conflicting ports and temporary paths. Do not mutate manifests/lockfiles through an install command. Follow the existing lockfile/package-manager policy and avoid unrequested upgrades.

Capture fixture identity, seed command, environment overrides, and state hash/counts before each run.

## Dependency and boot checks

1. Install or restore dependencies using the repository's documented locked policy.
2. Record language/runtime and resolved dependency versions.
3. Initialize disposable state through documented commands.
4. Start the application on an isolated port and capture logs.
5. Poll a readiness condition with a bounded timeout; do not use an unbounded sleep.
6. Confirm startup produced no unexpected schema/database/config changes.
7. Stop the process reliably and verify the port/process is released.

A dependency download blocked by network or authorization is a blocking validation failure unless dependencies are already available. Syntax-only fallback does not prove boot.

## Endpoint and domain-flow checks

Exercise every endpoint in the fingerprint. For each applicable route include:

- representative success;
- malformed/invalid input;
- not found;
- conflict or invariant violation;
- unauthenticated/unauthorized access;
- approved secure replacement for unsafe legacy behavior;
- unexpected infrastructure failure through a controlled test double when practical.

Compare method/path, status class, response meaning, required fields, sensitive-field absence, and persistence side effects. Exact byte equality is unnecessary unless the original contract requires it; semantic drift must be explained and approved.

Then execute representative multi-step domain flows, including creation → retrieval/update/report → deletion or the project's actual lifecycle. Validate ordering, totals, inventory/capacity, ownership, state transitions, report aggregation, and external-integration calls relevant to the domain.

Unavailable payment, notification, or other external integration requires a deterministic local substitute with recorded behavior or blocks the flow. Never silently skip it.

## Persistence and transaction checks

For each write flow verify:

- expected records and relationships are created/updated/deleted;
- database constraints agree with domain rules;
- no password/payment/internal fields are persisted unnecessarily;
- parent deletion follows explicit restrict/cascade/reassignment/soft-delete policy;
- state survives restart when persistence is expected;
- repeated/idempotent requests behave as documented;
- error paths leave no unintended state.

For multi-write use cases, inject failure after each dependent write. Confirm the complete write set rolls back and no orphan/partial records remain. A successful happy path does not prove atomicity.

## Security and error checks

Confirm removal or control of every approved security finding:

- secrets come from protected configuration and missing required secrets fail safely;
- arbitrary query/command surfaces are removed or narrowly controlled;
- passwords use maintained adaptive hashing and never appear in responses/logs;
- tokens and full payment values are absent from storage/logs/responses unless explicitly required and protected;
- authorization protects privileged and ownership-sensitive operations;
- client errors use stable codes and safe messages;
- unexpected errors do not expose stack traces, SQL, paths, connection details, or internal causes;
- internal logs retain useful correlation context without sensitive values.

Search captured logs and responses for known fixture secrets and sensitive field names. Avoid printing the secret itself in validation evidence.

## Performance checks

For each approved performance finding:

1. use the same isolated state and request shape before/after;
2. warm up consistently;
3. record query count or external-call count;
4. run at least five measured iterations;
5. compare medians, not a single sample.

Query-in-loop remediation should make I/O count bounded relative to result size. Treat a median latency regression greater than 20% as unresolved unless the approved audit explains a necessary security/integrity tradeoff.

Do not claim broad performance improvement from tiny fixtures; report scope and variance.

## Evidence format

Record each check as:

```markdown
### [CHECK-ID] — [name]
- Covers: [finding IDs / baseline contract]
- Command: `[reproducible command]`
- Fixture state: [seed/database/environment identity]
- Input/request: [method, path, body or domain action]
- Expected: [baseline or approved secure replacement]
- Actual: [observed result]
- Result: PASS | FAIL | BLOCKED
- Evidence: [minimal output excerpt]
- Artifact: [repository-relative path]
```

Summarize:

```markdown
## Validation Summary
- Boot: [PASS/FAIL/BLOCKED]
- Endpoints: [passed/total]
- Domain flows: [passed/total]
- Persistence/transactions: [passed/total]
- Security/errors: [passed/total]
- Performance: [passed/total/not applicable]
- Cleanup: [PASS/FAIL]
- Blocking failures: [none or IDs]
```

## Failure and cleanup rules

- Any failed or blocked mandatory boot, endpoint, domain-flow, persistence, transaction, or security check makes `validationPassed()` false.
- Fix only defects within approved scope. A newly discovered architecture/security issue returns to audit for disposition.
- Rerun the focused failing check, then the complete validation set after a fix.
- Stop processes, release ports, and remove only disposable state created by the run.
- Preserve logs/evidence needed for diagnosis while excluding secrets and unrelated generated artifacts.
- Compare repository state with the pre-run snapshot and report unexpected files or modifications.

The completion response must distinguish passed, failed, blocked, deferred, and not-applicable checks. Never convert “not run” into “passed.”
