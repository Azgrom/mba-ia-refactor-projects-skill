# Architecture Audit Report

## Target
- Project: ecommerce-api-legacy
- Target root: fixture/
- Stack: Node.js (runtime version unresolved), Express 4.22.1 resolved from lockfile / ^4.18.2 declared, sqlite3 5.1.7 resolved from lockfile / ^5.1.6 declared

## Project Fingerprint
- Language: Node.js CommonJS JavaScript; runtime version unresolved because no `engines` field or executed runtime metadata was available
- Framework: Express declared in `package.json` and resolved to 4.22.1 in `package-lock.json`; sqlite3 resolved to 5.1.7 for persistence
- Entry points: `src/app.js`
- Persistence: In-memory SQLite database created in `new sqlite3.Database(':memory:')`, schema and seed data loaded during `AppManager.initDb()`, state resets on every boot
- Architecture shape: `src/app.js` composes the server, while `src/AppManager.js` owns database lifecycle, schema seeding, route registration, checkout orchestration, admin reporting, and user deletion; `src/utils.js` mixes configuration, secrets, pseudo-crypto, and a process-global cache

## Source Scope
- Included: 7 relevant files (`README.md`, `api.http`, `package.json`, `package-lock.json`, `src/app.js`, `src/AppManager.js`, `src/utils.js`) traced from the Express entry point and route registration
- Excluded: `.agents/` skill harness files, dependency directories (`node_modules/` absent), generated caches, logs, databases outside the in-memory runtime, and non-application evaluation scaffolding

## Behavioral Baseline
- Boot: `npm start` runs `node src/app.js`; `src/app.js` creates the Express app, installs JSON parsing, initializes the in-memory SQLite schema/seeds, registers routes, and listens on `config.port` (3000) with a console readiness log. Live boot was not executed because `fixture/node_modules` is absent and dependency installation/network use were out of scope.
- Endpoints: `POST /api/checkout` creates or reuses a user, simulates payment acceptance by card prefix, inserts enrollment/payment/audit data on paid checkouts, and returns `{ msg: "Sucesso", enrollment_id }`; `GET /api/admin/financial-report` returns per-course revenue and enrolled students assembled from nested SQLite reads; `DELETE /api/users/:id` deletes only the user row and returns a message acknowledging orphaned enrollments/payments.
- Domain flows: Successful checkout for an existing or newly created user; denied checkout when card does not start with `4`; anonymous financial reporting across all courses/enrollments; anonymous user deletion that leaves related rows behind.
- Persistence: Boot seeds one user, two active courses, one enrollment, and one paid payment. Successful paid checkout writes enrollment, payment, audit log, and cache state; a denied checkout for a new email still creates the user before returning 400; deleting a user does not clean dependent enrollment/payment rows.

## Audit Limitations
- Live endpoint execution was not performed because installed dependencies were unavailable locally and the task prohibited dependency installation/network use.
- No deprecated-API findings were emitted. Version-sensitive deprecation review would require authoritative current documentation lookup, which was unavailable under the no-network constraint.

## Severity Summary
| Severity | Count |
|---|---:|
| CRITICAL | 3 |
| HIGH | 3 |
| MEDIUM | 1 |
| LOW | 0 |

## Findings

### F-001 — Executable configuration embeds production-like secrets
- Rule: critical-exposed-runtime-secret
- Severity: CRITICAL
- Location: src/utils.js:1-6
- Evidence: The exported `config` object hardcodes a database password and a live-like payment gateway key inside executable source.
- Impact: Anyone with source or runtime access can recover credentials that would enable database or payment integration compromise, and the secrets are easy to leak further through logs or stack traces.
- Recommendation: Move required secrets to protected environment-based configuration, fail closed when they are absent, and rotate every exposed value before reusing this code anywhere outside a disposable fixture.
- Status: proposed
- Evidence authority: Static source evidence in `src/utils.js`, imported by `src/app.js` and `src/AppManager.js`, shows the values are part of the booted application configuration.

### F-002 — Checkout logs raw card data together with a gateway secret
- Rule: critical-sensitive-auth-payment-exposure
- Severity: CRITICAL
- Location: src/AppManager.js:43-46
- Evidence: `processPaymentAndEnroll` logs `${cc}` from the request body and `${config.paymentGatewayKey}` before any masking or redaction.
- Impact: Payment-card data and integration credentials can be exposed to application logs, operators, and log aggregation systems, creating direct payment-data and secret-compromise risk.
- Recommendation: Remove PAN logging entirely, log only non-sensitive payment event metadata, and ensure payment integrations receive secrets through an isolated adapter that never prints them.
- Status: proposed
- Evidence authority: Request-controlled `req.body.card` is read in `src/AppManager.js:33` and written to `console.log` in `src/AppManager.js:45` alongside the imported gateway key from `src/utils.js`.

### F-003 — Anonymous DELETE endpoint performs destructive account removal
- Rule: critical-uncontrolled-privileged-operation
- Severity: CRITICAL
- Location: src/AppManager.js:131-136
- Evidence: `DELETE /api/users/:id` executes `DELETE FROM users WHERE id = ?` directly and does not perform any authentication, authorization, confirmation, or environment restriction.
- Impact: Any caller who can reach the server can delete users and intentionally leave corrupted enrollment/payment relationships behind, causing unauthorized data loss and integrity damage.
- Recommendation: Remove or isolate destructive administration from the public surface, require authenticated admin authorization, and execute user-removal semantics through a controlled workflow that preserves relational consistency.
- Status: proposed
- Evidence authority: Route registration and handler body in `src/AppManager.js` show the endpoint is publicly mounted by `setupRoutes(app)` from `src/app.js` with no upstream auth middleware.

### F-004 — AppManager concentrates composition, schema bootstrap, transport, and business workflows
- Rule: high-god-component
- Severity: HIGH
- Location: src/AppManager.js:1-138
- Evidence: The same class opens the SQLite connection, creates/seeds schema, registers every route, orchestrates checkout, builds the financial report, and performs destructive user deletion.
- Impact: Any change to boot, HTTP behavior, enrollment/payment rules, or persistence details converges on one file, which raises the blast radius of edits and makes isolated testing or incremental refactoring difficult.
- Recommendation: Split the class along responsibility boundaries: keep composition/bootstrap in startup code, move checkout/report/delete orchestration into controllers or application services, and isolate persistence access behind dedicated repositories.
- Status: proposed
- Evidence authority: `src/app.js` instantiates one `AppManager`, and all executable route and database behavior flows through that class.

### F-005 — Checkout can leave partial writes because dependent changes have no transaction boundary
- Rule: high-missing-transaction-boundary
- Severity: HIGH
- Location: src/AppManager.js:43-71
- Evidence: New-user checkout inserts the user before payment acceptance is finalized, then enrollment, payment, and audit-log writes are chained with separate `db.run` calls and no `BEGIN`/`COMMIT`/`ROLLBACK`.
- Impact: Failed or denied checkouts can still create durable user records, and mid-flow failures can leave enrollments, payments, and audit history out of sync with one another.
- Recommendation: Own checkout as one application-service transaction, validate payment outcome before mutating durable state where possible, and verify rollback behavior for injected failures after each dependent write.
- Status: proposed
- Evidence authority: The `if (!user)` branch in `src/AppManager.js:66-72` creates the user before `processPaymentAndEnroll`, and the downstream write chain in `src/AppManager.js:50-60` has no surrounding transaction control.

### F-006 — Password storage uses a custom reversible-looking hash and a silent default password
- Rule: high-weak-credential-handling
- Severity: HIGH
- Location: src/utils.js:17-22
- Evidence: `badCrypto` repeatedly base64-encodes the input and truncates the result to 10 characters, while checkout calls it with `p || "123456"` when creating a new user.
- Impact: Stored credentials are weak enough to crack or collide cheaply, and a missing password can silently become a known default, making account takeover materially easier.
- Recommendation: Replace the helper with a maintained adaptive password hash, require an explicit password for account creation, and migrate existing stored credentials behind a verified upgrade path.
- Status: proposed
- Evidence authority: Credential creation flows through `badCrypto` in `src/utils.js`, is invoked from `src/AppManager.js:68-69`, and seeded user storage also demonstrates insecure password handling in `src/AppManager.js:18`.

### F-007 — Financial report performs nested per-row database lookups
- Rule: medium-query-in-loop
- Severity: MEDIUM
- Location: src/AppManager.js:83-125
- Evidence: The report handler loads all courses, then all enrollments per course, then one user lookup and one payment lookup per enrollment inside nested loops.
- Impact: Query count and latency grow with the number of courses and enrollments, turning the admin report into an avoidable N+1 workload as data volume increases.
- Recommendation: Replace the nested callback fan-out with a joined or aggregated query (or a small bounded batch of queries) and keep response shaping at the transport boundary.
- Status: proposed
- Evidence authority: The handler body in `src/AppManager.js` contains one `db.all` over courses, one `db.all` per course, and two `db.get` calls per enrollment.

## Proposed Refactoring Scope
- F-004,F-005 → Extract checkout orchestration from `AppManager` into a dedicated controller/application service plus repository boundary, while preserving `POST /api/checkout` path, success payload, payment-denied behavior, and enrollment side effects except for explicitly approved security corrections.
- F-001,F-002,F-006 → Move secrets and credential handling into infrastructure/configuration adapters, remove sensitive logging, and preserve checkout endpoint meaning while hardening password creation and operational telemetry.
- F-003,F-007 → Split administrative reporting and destructive user management into dedicated admin-facing components, add approved authorization boundaries, and replace the financial-report N+1 query pattern without changing the successful report payload’s meaning.

## Security-Driven Contract Changes
- `GET /api/admin/financial-report` should require authenticated administrative access instead of anonymous access, with unauthorized callers receiving 401/403.
- `DELETE /api/users/:id` should require authenticated administrative access instead of anonymous access, with unauthorized callers receiving 401/403.
- `POST /api/checkout` should reject account creation when `pwd` is omitted instead of silently hashing `"123456"` for the new user.

## Approval Required
Reply with explicit approval of this report path and snapshot digest before any target mutation. Identify all findings or the approved finding IDs.

## Audit Snapshot Digest
`sha256:3679fa983a8646d1aa6efad74790948554e2de39c2b294fba616ee3cb26fdbae`
