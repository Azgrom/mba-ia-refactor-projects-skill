# Architecture Audit Report

## Target
- Project: ecommerce-api-legacy (Frankenstein LMS checkout API)
- Target root: /run/media/rafael/master_backup/Repos/AI Works/FullCycle-IA-MBA/challenge/ArchitectureAuditAndRefactoring/ecommerce-api-legacy
- Stack: Node.js (v26.2.0 host) / Express 4.22.1 + sqlite3 5.1.7 (resolved from package-lock.json)

## Project Fingerprint
- Language: JavaScript (CommonJS); host runtime Node v26.2.0; no engines constraint declared
- Framework: Express `^4.18.2` declared, resolved 4.22.1; sqlite3 `^5.1.6` declared, resolved 5.1.7
- Entry points: src/app.js (boot), src/AppManager.js (routes + persistence), src/utils.js (config + helpers)
- Persistence: SQLite in-memory (`:memory:`), single shared connection created in AppManager constructor; schema + seed created on boot in `initDb()`; state is ephemeral per process
- Architecture shape: one `AppManager` class owns schema definition, seeding, HTTP route registration, request parsing, payment decisioning, all persistence, audit logging, and response formatting; config and mutable global cache live in `utils.js`

## Source Scope
- Included: all executable application source reachable from the entry point — src/app.js, src/AppManager.js, src/utils.js (3 files); package.json and package-lock.json for version evidence; api.http as request-contract evidence
- Excluded: node_modules/ (not installed in target root; deps resolved from lockfile), .git/, .claude/ and .agents/ skill tooling, api.http from executable scope. No generated, vendored, or test code exists in the app path.

## Behavioral Baseline
- Boot: `npm install` then `npm start` (`node src/app.js`); readiness = log line "Frankenstein LMS rodando na porta 3000..." and port 3000 answering; DB is in-memory and re-seeded every boot. Baseline captured in a disposable copy under the session scratchpad, never in the target root.
- Endpoints (3 registered):
  - `POST /api/checkout` — creates user if email unknown, then enrollment + payment + audit log. Success `200 application/json {"msg":"Sucesso","enrollment_id":N}`. `400 text/html "Bad Request"` on missing usr/eml/c_id/card; `400 text/html "Pagamento recusado"` when card does not start with "4"; `404 text/html "Curso não encontrado"` for inactive/unknown course; `500 text/html` on DB errors.
  - `GET /api/admin/financial-report` — `200 application/json` array of `{course, revenue, students:[{student, paid}]}` over all courses/enrollments/users/payments. No authentication.
  - `DELETE /api/users/:id` — always `200 text/html "Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."` even for nonexistent ids. No authentication.
- Domain flows: (1) new-user checkout inserts users→enrollments→payments→audit_logs and caches last course title; (2) existing-user checkout re-enrolls (no idempotency; duplicate enrollment created); (3) report aggregates paid revenue per course; (4) user deletion orphans enrollments/payments.
- Persistence: observed seed report `[{Docker,0,[]},{Clean Architecture,997,[Leonan 997]}]`; report course ordering is nondeterministic across identical calls (async fan-out race); deleting user 1 turns their report entry into `"Unknown"` while revenue is retained (orphan rows).
- Proposed security exceptions: none required to preserve. All identified unsafe behaviors (secret logging, plaintext credentials, unauthenticated destructive/admin endpoints) are defects, not contracts a client depends on.

## Audit Limitations
- Deprecated-API analysis: no deprecated Express/sqlite3 API is invoked by the source (`express.json()`, `app.METHOD`, `db.run/get/all` are all current in the resolved versions), so no deprecation finding is emitted and none was fabricated from memory.
- Concurrency behavior is inferred from single-process in-memory runtime observation; no load/race test harness was run beyond repeated sequential calls demonstrating nondeterministic report ordering.

## Severity Summary
| Severity | Count |
|---|---:|
| CRITICAL | 3 |
| HIGH | 4 |
| MEDIUM | 3 |
| LOW | 1 |

## Findings

### F-001 — Hardcoded production secrets in executable config
- Rule: critical-exposed-runtime-secret
- Severity: CRITICAL
- Location: src/utils.js:1-7
- Evidence: `config` literal embeds a database password, a live-looking payment gateway key (`pk_live_...`), and an SMTP user directly in source; values are `require`d and used at runtime, not injected from the environment.
- Impact: anyone with repository read access obtains payment-gateway and database credentials, enabling unauthorized charges, integration takeover, and data access; secrets cannot be rotated without a code change.
- Recommendation: load secrets from environment/protected configuration, fail fast when absent, rotate the exposed values, and keep them out of source and version control.
- Status: proposed
- Evidence authority: executable config path src/utils.js:1-7, consumed at src/AppManager.js:45 and src/app.js:12; values redacted here.

### F-002 — Full card number and gateway key logged; plaintext passwords stored
- Rule: critical-sensitive-auth-payment-exposure
- Severity: CRITICAL
- Location: src/AppManager.js:45-45
- Evidence: `console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`)` writes the full unmasked PAN and the gateway key to stdout on every checkout; seed users store plaintext passwords (`'123'`) and new passwords go through a non-cryptographic transform (see F-004).
- Impact: full payment-card data and the gateway key land in logs (PCI-DSS violation, replayable payment credentials); credential exposure enables account and payment compromise.
- Recommendation: never log PAN or keys; mask to last-four if logging is required; tokenize card data and never persist/serialize it; hash credentials with a maintained adaptive primitive.
- Status: proposed
- Evidence authority: data-flow from request `card` (src/AppManager.js:33) to log sink (src/AppManager.js:45); runtime stdout capture confirmed PAN + `pk_live_...` printed.

### F-003 — Unauthenticated destructive and admin endpoints
- Rule: critical-uncontrolled-privileged-operation
- Severity: CRITICAL
- Location: src/AppManager.js:131-137
- Evidence: `DELETE /api/users/:id` runs `DELETE FROM users WHERE id = ?` with no authentication, authorization, or confirmation and returns 200 even for nonexistent ids; the sibling `GET /api/admin/financial-report` (src/AppManager.js:80) is likewise unauthenticated (cross-ref: medium-unbounded-or-overbroad-data-access, F-010).
- Impact: any anonymous caller can destroy arbitrary user records and read all customers' names, emails, and payment amounts; destructive action is unrecoverable in the in-memory store.
- Recommendation: place both endpoints behind an authentication + authorization boundary, restrict admin operations to authorized roles, and remove the "admin" route from anonymous reach.
- Status: proposed
- Evidence authority: route reachability and absent controls at src/AppManager.js:131-137 and src/AppManager.js:80-129; runtime confirmed anonymous 200 on delete and report.

### F-004 — Custom non-cryptographic password hashing
- Rule: high-weak-credential-handling
- Severity: HIGH
- Location: src/utils.js:17-23
- Evidence: `badCrypto` builds a hash by repeating a 2-char base64 slice of the password and truncating to 10 chars; it is fast, low-entropy, unsalted, and collision-prone; seed users store plaintext (`pass = '123'`).
- Impact: stored password verifiers are trivially brute-forced/precomputed, enabling account takeover; mixing plaintext seeds and this transform defeats any authentication guarantee.
- Recommendation: replace with a maintained adaptive hash (bcrypt/scrypt/argon2) with per-user salt and a migration path; stop storing plaintext seed passwords.
- Status: proposed
- Evidence authority: credential creation/storage flow src/utils.js:17-23 called at src/AppManager.js:68-69; seed at src/AppManager.js:18.

### F-005 — AppManager is a God Component owning transport, domain, and persistence
- Rule: high-god-component
- Severity: HIGH
- Location: src/AppManager.js:4-139
- Evidence: a single class defines schema and seeds (`initDb`, lines 10-23), registers all HTTP routes and parses request bodies, decides payment status, executes every SQL statement, writes audit logs, and formats responses (cross-ref: high-transport-owns-domain-and-persistence — the checkout handler at lines 28-78 parses HTTP, computes payment policy, coordinates four writes, and serializes the result inline).
- Impact: unrelated reasons to change converge in one file; behavior cannot be unit-tested without a live DB and HTTP layer; blast radius of any change is the whole app.
- Recommendation: separate responsibilities — routes/controllers for HTTP mapping, an application/checkout service for use-case coordination, repositories for persistence, and a payment abstraction — while preserving endpoint paths, methods, and response semantics.
- Status: proposed
- Evidence authority: responsibility map and caller/import trace across src/AppManager.js:4-139; entry wiring at src/app.js:8-10.

### F-006 — Checkout multi-write has no transaction boundary
- Rule: high-missing-transaction-boundary
- Severity: HIGH
- Location: src/AppManager.js:43-75
- Evidence: checkout inserts a user (line 69), then enrollment (line 50), payment (line 54), and audit log (line 57) as independent statements with no `BEGIN/COMMIT/ROLLBACK`; a runtime probe sending `card` as a JSON number crashed the process at line 46 *after* the user row was inserted, leaving an orphan user with no enrollment or payment.
- Impact: partial failures corrupt business state (orphan users/enrollments/payments), producing inconsistent financial data that is hard to repair.
- Recommendation: own a single transaction at the checkout service boundary, commit on success and roll back on any failure, and verify rollback with an injected mid-flow failure.
- Status: proposed
- Evidence authority: full use-case write set src/AppManager.js:43-75; runtime orphan observed via numeric-card crash (cross-ref F-008).

### F-007 — Process-global mutable state and shared connection
- Rule: high-process-global-mutable-state
- Severity: HIGH
- Location: src/utils.js:9-15
- Evidence: module-level `globalCache = {}` and `totalRevenue = 0` mutate across requests via `logAndCache` (line 12-15); a single sqlite connection is created once in the constructor (src/AppManager.js:7) and shared by all requests with no lifecycle scoping.
- Impact: `globalCache` grows unboundedly per checkout (memory leak), state leaks across requests, and behavior becomes order-dependent and unsafe under concurrency; `totalRevenue` is dead-but-exported mutable state inviting misuse.
- Recommendation: bind cache/connection lifecycle to application scope with bounds/invalidation (or remove the cache), inject dependencies at composition, and delete unused mutable exports.
- Status: proposed
- Evidence authority: declaration/mutation sites src/utils.js:9-15 and connection init src/AppManager.js:7; usage at src/AppManager.js:59.

### F-008 — Missing input validation crashes the process
- Rule: medium-missing-boundary-validation
- Severity: MEDIUM
- Location: src/AppManager.js:29-46
- Evidence: request fields are read untyped (lines 29-33); the guard at line 35 checks presence but not type; a `card` supplied as a JSON number reaches `cc.startsWith("4")` at line 46 and throws `TypeError: cc.startsWith is not a function`, and with no error handler the entire server process exits.
- Impact: a single malformed request takes the whole API down (denial of service) and, per F-006, leaves partial data behind; malformed inputs generally become 500s instead of clean 400s.
- Recommendation: validate and normalize transport shape at the boundary (types, required fields, string coercion for card) and add an error-handling boundary so handler exceptions map to responses instead of crashing.
- Status: proposed
- Evidence authority: input read src/AppManager.js:29-33, guard 35, crash sink 46; runtime confirmed process exit on numeric `card`.

### F-009 — N+1 query fan-out with nondeterministic aggregation
- Rule: medium-query-in-loop
- Severity: MEDIUM
- Location: src/AppManager.js:83-127
- Evidence: the report runs one query per course, then per enrollment, then per user and per payment inside nested `forEach` callbacks (lines 89-125), coordinating completion with manual decrement counters; repeated identical calls returned courses in different orders (`[Docker, Clean Architecture]` vs `[Clean Architecture, Docker]`).
- Impact: query count and latency grow multiplicatively with data size, and the hand-rolled async fan-out yields nondeterministic response ordering — an unstable, hard-to-cache contract.
- Recommendation: replace nested per-row queries with a single joined/aggregated query (or batched ID lookups) and produce a deterministically ordered result.
- Status: proposed
- Evidence authority: nested query loops src/AppManager.js:83-127; runtime observed order variance across sequential calls.

### F-010 — Report exposes all PII and financials without bound or authorization
- Rule: medium-unbounded-or-overbroad-data-access
- Severity: MEDIUM
- Location: src/AppManager.js:80-104
- Evidence: `GET /api/admin/financial-report` runs `SELECT * FROM courses` / `... enrollments` and reads every user's `name, email` (line 104) and every payment, returning the full dataset with no pagination, projection limit, filtering, or authorization.
- Impact: unbounded memory/latency growth as data grows, and full customer PII plus revenue is disclosed to any caller (compounds F-003).
- Recommendation: paginate and project only needed fields, aggregate in SQL, and enforce authorization at the use-case boundary.
- Status: proposed
- Evidence authority: query and response construction src/AppManager.js:83-115; contract confirmed via runtime report body.

### F-011 — Magic values encode business policy inline
- Rule: low-magic-value
- Severity: LOW
- Location: src/AppManager.js:46-46
- Evidence: payment approval is `cc.startsWith("4") ? "PAID" : "DENIED"` — the `"4"` prefix, the `"PAID"`/`"DENIED"` status strings (also at lines 21, 54, 108), and the hardcoded port `3000` (src/utils.js:6) are unexplained literals embedding policy in logic.
- Impact: business rules (what makes a payment succeed, valid statuses) are hidden and must be changed in multiple places, risking drift.
- Recommendation: name these as domain constants/config at their owner (payment status enum, gateway decision rule, configurable port) once real payment logic replaces the placeholder.
- Status: proposed
- Evidence authority: literal use src/AppManager.js:46 with sibling status literals at src/AppManager.js:21,54,108 and port at src/utils.js:6.

## Proposed Refactoring Scope
- F-001, F-002: move secrets to environment configuration and strip PAN/key logging; add masked-logging helper (compatibility: endpoint contracts unchanged; log format changes only).
- F-003, F-010: introduce an authentication/authorization boundary in front of the admin report and user-delete routes (contract change — see Security-Driven Contract Changes).
- F-004: replace `badCrypto` with an adaptive hash behind a `PasswordHasher` abstraction; keep seed users but stop storing plaintext.
- F-005, F-006, F-008, F-009, F-011: extract `routes → controller → CheckoutService/ReportService → repositories`, wrapping checkout writes in a transaction, validating input and adding an error-handling boundary at the transport edge, replacing the report fan-out with a single aggregated query; preserve all paths, methods, status codes, and JSON response shapes captured in the baseline.
- F-007: scope cache/connection lifecycle to composition and remove unused mutable exports.

## Security-Driven Contract Changes
- Adding authentication/authorization to `GET /api/admin/financial-report` and `DELETE /api/users/:id` (F-003, F-010) will change their anonymous-access behavior: previously-anonymous 200 responses will become 401/403 without credentials. This is a proposed secure replacement of an unsafe contract, not yet authorized. All other endpoint paths, methods, success status codes, and response bodies are to be preserved exactly as captured in the Behavioral Baseline.

## Approval Required
Reply with explicit approval of this report path and snapshot digest before any target mutation. Identify all findings or the approved finding IDs.

## Audit Snapshot Digest
`sha256:63f187e87c55938227c7f90434d718948eda16f7ecbc6c0d2f1367352c93fdeb`

## Post-Approval Resolution Addendum

Approved mutation:
`Approve reports/audit-project-ecommerce-api-legacy.md sha256:63f187e87c55938227c7f90434d718948eda16f7ecbc6c0d2f1367352c93fdeb F-006,F-010`.

Resolved subset:

- `F-006`: checkout now decides payment before any new-user write and creates a
  new user inside the same transaction as enrollment, payment, and audit writes.
  Evidence: `ecommerce-api-legacy/src/services/checkoutService.js:25-37`;
  regression: `ecommerce-api-legacy/tests/regression.test.js:51-90`.
- `F-010`: financial report access remains authorized and projected, and is now
  bounded through validated `limit`/`offset` query parameters while preserving the
  existing array response shape. Evidence:
  `ecommerce-api-legacy/src/http/reportController.js:6-30` and
  `ecommerce-api-legacy/src/repositories/reportRepository.js:10-30`;
  regression: `ecommerce-api-legacy/tests/regression.test.js:93-114`.

Validation evidence: `reports/validation-ecommerce-api-legacy.md`.
