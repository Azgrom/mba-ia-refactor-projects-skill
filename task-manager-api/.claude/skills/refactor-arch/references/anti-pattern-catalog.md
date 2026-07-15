# Anti-Pattern Catalog

Use these rules as hypotheses, not keyword detectors. Confirm execution path, callers, ownership, exploitability, and actual impact before emitting a finding.

## Contents

- Severity policy
- Evidence and deduplication
- CRITICAL rules
- HIGH rules
- MEDIUM rules
- LOW rules
- Deprecated-API authority

## Severity policy

| Severity | Meaning |
|---|---|
| CRITICAL | Severe security, data, or architectural failure that enables sensitive exposure/destructive control, breaks essential correctness, or collapses unrelated system responsibilities. |
| HIGH | Strong MVC/SOLID boundary violation, weak authentication, missing atomicity, or coupling that makes important behavior unsafe to change or test. |
| MEDIUM | Material validation, duplication, performance, lifecycle, or verified deprecation problem with bounded impact. |
| LOW | Local readability, naming, dead-code, magic-value, or serialization duplication problem. |

Severity follows demonstrated consequence and reach. Downgrade when exposure is unreachable or impact is bounded; upgrade only with concrete exploitability or failure evidence.

## Evidence and deduplication

- Trace the route/command caller to the relevant source before claiming a finding.
- Quote only enough source to identify the issue; exact file and line range remain authoritative.
- Merge symptoms fixed by one responsibility change. Example: a route that validates, calculates, queries, and formats is one root responsibility finding with secondary-rule cross-references, not four count-padding findings.
- Treat tests, samples, generated files, and unused code as non-executable until proven otherwise.
- Keep secret values redacted in reports. Identify type and location, not the value.
- A catalog rule classifies evidence; it is never an answer key for a filename or fixture.

## CRITICAL rules

### critical-arbitrary-data-execution

- **Detection signals:** request-controlled SQL/commands/templates evaluated with privileged access; administrative endpoints accept raw statements; unsafe interpolation reaches execution.
- **False-positive checks:** parameter placeholders; fixed allowlisted operations; unreachable samples; strongly typed query builders with no raw escape.
- **Impact:** arbitrary read/write/destruction, privilege escalation, or remote execution.
- **Remediation direction:** remove general execution surfaces; expose narrow authorized use cases; parameterize values; apply least privilege.
- **Evidence authority:** route-to-sink trace plus input control and privilege context.

### critical-exposed-runtime-secret

- **Detection signals:** production-like secret keys, database credentials, tokens, or private connection strings embedded in executable configuration or returned by an endpoint.
- **False-positive checks:** obvious test fixtures; placeholders; public identifiers; dead examples; values injected only from environment.
- **Impact:** session forgery, unauthorized integration/database access, or environment compromise.
- **Remediation direction:** load required secrets from protected configuration, rotate exposed values, fail safely when missing, and prevent response/log leakage.
- **Evidence authority:** executable configuration path and secret use; redact the value.

### critical-sensitive-auth-payment-exposure

- **Detection signals:** plaintext passwords, password hashes, tokens, or full payment-card data logged, serialized, stored unnecessarily, or returned to clients.
- **False-positive checks:** masked last-four values; non-sensitive payment-provider references; isolated synthetic fixtures; protected one-way hashes not exposed.
- **Impact:** credential takeover, payment-data compromise, regulatory exposure.
- **Remediation direction:** minimize collection, hash credentials with a maintained adaptive primitive, tokenize payment data, redact logs, and use explicit safe serializers.
- **Evidence authority:** data flow from sensitive source to log/storage/response sink.

### critical-uncontrolled-privileged-operation

- **Detection signals:** destructive reset/delete/export/administration behavior is reachable without authentication, authorization, confirmation, or environment restriction.
- **False-positive checks:** local-only development commands outside HTTP; authenticated least-privilege checks; idempotent non-sensitive health operations.
- **Impact:** destructive data loss, unauthorized administration, or sensitive bulk extraction.
- **Remediation direction:** remove or isolate the endpoint, enforce authorization and safe environment policy, and require explicit constrained operations.
- **Evidence authority:** route reachability, missing controls, and affected state.

## HIGH rules

### high-god-component

- **Detection signals:** one component owns unrelated transport, multiple use cases, domain policy, persistence, configuration, and composition; many independent reasons to change converge there.
- **False-positive checks:** cohesive large modules; generated schema; composition roots that wire but do not implement behavior; facades delegating cleanly.
- **Impact:** changes have broad blast radius, isolated tests require most of the system, and ownership becomes ambiguous.
- **Remediation direction:** split by coherent responsibility/use case while retaining useful public facades during migration.
- **Evidence authority:** responsibility map, callers, imports, and distinct change reasons—not line count alone.

### high-weak-credential-handling

- **Detection signals:** plaintext, MD5/SHA-only, reversible/custom password storage; fake/static tokens; authentication comparisons without maintained verification primitives.
- **False-positive checks:** checksums for non-secret integrity; legacy hashes only inside an approved migration verifier; external identity provider ownership.
- **Impact:** inexpensive offline cracking, account takeover, or authentication bypass.
- **Remediation direction:** use a maintained adaptive password hash and migration strategy; issue verifiable expiring credentials through an established auth boundary.
- **Evidence authority:** credential creation, storage, comparison, and serialization flow.

### high-missing-transaction-boundary

- **Detection signals:** one business action performs multiple dependent writes without atomic commit/rollback; failures can leave partial records, inventory, balances, or ownership.
- **False-positive checks:** single atomic statement; idempotent independent writes; datastore transaction already owned by a caller; compensating workflow with proven guarantees.
- **Impact:** corrupted business state and hard-to-repair partial success.
- **Remediation direction:** own the transaction at the application-service boundary and verify rollback on an injected mid-flow failure.
- **Evidence authority:** complete use-case call path, write set, and failure behavior.

### high-transport-owns-domain-and-persistence

- **Detection signals:** route/middleware parses HTTP then calculates policy, coordinates multi-step use cases, constructs queries, commits, and formats persistence records.
- **False-positive checks:** thin CRUD delegation; framework-native transaction decorator around a service call; simple validation/serialization at the boundary.
- **Impact:** domain behavior is coupled to HTTP and persistence, making reuse, error consistency, and focused testing difficult.
- **Remediation direction:** keep HTTP mapping in routes, move use-case coordination to application services/controllers, and move query details to persistence ownership.
- **Evidence authority:** handler body plus downstream ownership and tests required to exercise it.

### high-process-global-mutable-state

- **Detection signals:** process-global database connections, sessions, current-user state, repositories, or domain collections mutate across requests without lifecycle control.
- **False-positive checks:** immutable configuration; thread-safe connection pools; explicit application-scoped caches with synchronization and invalidation; intentionally ephemeral single-process tools.
- **Impact:** request leakage, races, order-dependent tests, stale state, and unsafe concurrency.
- **Remediation direction:** bind lifecycle to request/application scope and inject dependencies at composition.
- **Evidence authority:** initialization location, mutation sites, concurrency model, and request reuse.

## MEDIUM rules

### medium-query-in-loop

- **Detection signals:** repeated database/API lookup inside a loop over prior results; serializers lazily load relationships per item.
- **False-positive checks:** bounded tiny constant loops; in-memory lookups; deliberate streaming where batching is impossible; datastore prefetch hidden by framework.
- **Impact:** query count and latency grow with result size.
- **Remediation direction:** join, eager load, batch by IDs, aggregate in storage, or pre-index fetched data.
- **Evidence authority:** caller loop plus actual I/O sink; measure query count when possible.

### medium-missing-boundary-validation

- **Detection signals:** unchecked types, ranges, required fields, enum/status values, pagination, or identifiers enter application/domain code; malformed input becomes internal errors.
- **False-positive checks:** validated schema/middleware before the shown handler; domain constructor enforcing the invariant; trusted internal-only calls.
- **Impact:** inconsistent errors, invalid state attempts, injection surface, or avoidable crashes.
- **Remediation direction:** validate/normalize transport shape at the boundary and enforce business invariants again in domain code.
- **Evidence authority:** input source, absent upstream validation, and downstream assumption.

### medium-duplicated-business-or-transport-policy

- **Detection signals:** the same calculation, authorization, validation, error mapping, or response transformation is independently implemented in several handlers.
- **False-positive checks:** coincidental syntax with different semantics; tiny idiomatic framework calls; duplication introduced intentionally for boundary independence.
- **Impact:** behavior drifts and fixes require synchronized edits.
- **Remediation direction:** centralize the shared policy at its natural owner, not in a generic dumping-ground utility.
- **Evidence authority:** at least two concrete sites and the shared semantic rule.

### medium-unbounded-or-overbroad-data-access

- **Detection signals:** list/report endpoints fetch all records or full sensitive columns without pagination, projection, filtering, or authorization appropriate to expected growth.
- **False-positive checks:** proven tiny reference tables; offline administrative jobs; explicit bounded export with access control.
- **Impact:** memory/latency growth and unnecessary sensitive-data exposure.
- **Remediation direction:** bound queries, project required fields, paginate/stream, and apply authorization at the use-case boundary.
- **Evidence authority:** query, endpoint contract, expected cardinality, and returned fields.

### medium-deprecated-api

- **Detection signals:** detected dependency version plus authoritative documentation marks the exact API deprecated/removed and identifies a supported direction.
- **False-positive checks:** docs for another version; merely old style; transitive/internal API not called; replacement incompatible with locked version.
- **Impact:** upgrade blockers, warnings, removed behavior, or missed fixes.
- **Remediation direction:** use the version-compatible supported API; separate dependency upgrade approval when required.
- **Evidence authority:** manifest/lock/installed version and current primary documentation citation. Without both, record a limitation instead.

## LOW rules

### low-misleading-name

- **Detection signals:** names contradict behavior/domain language, hide units, or reuse one vague term for different concepts.
- **False-positive checks:** established framework terminology; public compatibility names; concise names with obvious local scope.
- **Impact:** slower comprehension and higher change error rate.
- **Remediation direction:** rename toward domain intent and preserve public aliases when compatibility matters.
- **Evidence authority:** declaration, uses, and actual behavior.

### low-magic-value

- **Detection signals:** unexplained repeated statuses, thresholds, role strings, ports, or calculation constants embedded in logic.
- **False-positive checks:** universally obvious values; single-use values clearer inline; protocol constants already defined by framework.
- **Impact:** hidden policy and inconsistent updates.
- **Remediation direction:** name the domain/configuration concept at its owner; avoid speculative constants.
- **Evidence authority:** repeated or policy-bearing use and missing explanation.

### low-dead-or-unused-code

- **Detection signals:** unreachable branches, unused imports/helpers, obsolete wrappers, or duplicate modules with no executable caller.
- **False-positive checks:** reflection/plugin entry points; CLI commands; framework registration side effects; public compatibility surfaces.
- **Impact:** misleading maintenance surface and stale behavior assumptions.
- **Remediation direction:** remove after caller verification or document/cover the dynamic entry point.
- **Evidence authority:** reference search plus framework registration analysis.

### low-duplicated-serialization

- **Detection signals:** repeated manual dictionaries/JSON shapes for the same entity expose inconsistent fields or sensitive data.
- **False-positive checks:** intentionally different projections; tiny one-off error responses; API-version-specific representations.
- **Impact:** response drift and accidental data exposure.
- **Remediation direction:** use explicit projection/serializer functions close to the transport boundary.
- **Evidence authority:** concrete response sites and field differences.

## Deprecated-API authority

Follow the target repository's documentation-fetch rules. When Context7 is required:

```bash
npx ctx7@latest library "<Official Library Name>" "<exact API and detected version question>"
npx ctx7@latest docs /org/project[/version] "<exact API and detected version question>"
```

Resolve the library before fetching docs unless the repository already supplies a valid `/org/project` ID. Keep queries free of credentials and proprietary source. Cite the authoritative page or documentation identity in Evidence authority.

If documentation access fails because of network, quota, unavailable version, or ambiguous package identity, record the failure in Audit Limitations. Do not silently substitute recollection or a static blacklist.
