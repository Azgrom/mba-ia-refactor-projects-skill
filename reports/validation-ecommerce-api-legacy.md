# Validation Report

Validation of `ecommerce-api-legacy/` against the approved subset of
`reports/audit-project-ecommerce-api-legacy.md` —
`sha256:63f187e87c55938227c7f90434d718948eda16f7ecbc6c0d2f1367352c93fdeb`.

Approved scope: `F-006,F-010`.

Validation ran from a disposable copy at
`/tmp/ecommerce-api-legacy-validation.A7gH2d`; the target application root was
edited only for the approved source changes and regression tests. Runtime
dependency install and boot state stayed outside the target root.

## Environment

- Host runtime: Node.js v26.2.0, npm 11.16.0.
- Resolved dependencies from lockfile/disposable install: Express 4.22.1,
  sqlite3 5.1.7.
- State: in-memory SQLite, deterministic boot seed per app instance.
- Validation env: `ADMIN_TOKEN=validation-admin-token`, isolated ports 5317 and
  5318.

## Validation Summary

- Boot: PASS
- Endpoints: 12/12 PASS
- Domain flows: 4/4 PASS
- Persistence/transactions: 2/2 PASS
- Security/errors: 6/6 PASS in the configured validation env
- Performance/data access: 2/2 PASS
- Cleanup: PASS for runtime state
- Blocking failures: none

## Checks

### V-BOOT-001 — Dependency Install And Real Boot
- Covers: baseline boot contract, dependency validation.
- Command: `npm ci`; `env ADMIN_TOKEN=validation-admin-token PORT=5318 npm start`
- Fixture state: disposable copy, in-memory SQLite seed.
- Input/request: process boot only.
- Expected: dependencies resolve from lockfile; server listens and logs readiness.
- Actual: `npm ci` installed 191 packages; `require('express')` and
  `require('sqlite3')` loaded; boot logged `LMS API rodando na porta 5318...`.
- Result: PASS
- Evidence: resolved packages `express@4.22.1`, `sqlite3@5.1.7`.
- Artifact: `reports/validation-ecommerce-api-legacy.md`

### V-REG-001 — Focused Regression Tests
- Covers: `F-006,F-010`.
- Command: `node --test tests/regression.test.js`
- Fixture state: disposable copy, in-memory SQLite seed per app instance.
- Input/request: denied new-user checkout; authorized
  `GET /api/admin/financial-report?limit=1`; authorized
  `GET /api/admin/financial-report?limit=abc`.
- Expected: denied checkout creates no partial user state; bounded report keeps
  the array response and returns one course; invalid bounds return 400.
- Actual: 3/3 tests passed.
- Result: PASS
- Evidence: `pass 3`, `fail 0`, duration 379.570146ms.
- Artifact: `ecommerce-api-legacy/tests/regression.test.js`

### V-ENDPOINT-001 — Checkout Contracts
- Covers: F-006, F-008, F-011, baseline `POST /api/checkout`.
- Command: `node validate-current-app.js` in the disposable copy.
- Fixture state: fresh in-memory seed.
- Input/request: success checkout, missing card, numeric card, missing course,
  denied payment.
- Expected: success stays `200 {"msg":"Sucesso","enrollment_id":N}`; invalid input
  returns 400; missing course returns 404; denied payment returns 400 without a
  process crash or partial new-user write.
- Actual: success returned `200 {"msg":"Sucesso","enrollment_id":2}`; invalid and
  numeric card returned `400 Bad Request`; missing course returned
  `404 Curso nao encontrado`; denied payment returned `400 Pagamento recusado`;
  direct service probe recorded `events: []`.
- Result: PASS
- Evidence: validation script reported all checkout and
  `payment-denial-user-creation-gap` checks passing.
- Artifact: `reports/validation-ecommerce-api-legacy.md`

### V-ENDPOINT-002 — Admin Authorization And Legacy Delete Contract
- Covers: F-003, F-010, baseline admin endpoints, approved security replacement.
- Command: `node validate-current-app.js` in the disposable copy.
- Fixture state: fresh in-memory seed, `ADMIN_TOKEN=validation-admin-token`.
- Input/request: anonymous and authorized
  `GET /api/admin/financial-report`; anonymous and authorized
  `DELETE /api/users/1`.
- Expected: anonymous admin calls reject; authorized report returns the financial
  report; authorized delete preserves the documented legacy response.
- Actual: anonymous report and delete returned 401; authorized report returned
  course revenue/student projections; authorized delete returned the preserved
  legacy text and the follow-up report represented the orphaned seeded
  enrollment as `Unknown`.
- Result: PASS
- Evidence: validation script reported admin authorization and follow-up report
  checks passing.
- Artifact: `reports/validation-ecommerce-api-legacy.md`

### V-SEC-001 — Secret, PAN, Password, And Mutable Global Removal
- Covers: F-001, F-002, F-004, F-007.
- Command: `rg -n "pk_live|dbPassword|smtp|badCrypto|globalCache|totalRevenue|console\\.log\\(.*card|Processando cartao|AppManager|utils" ecommerce-api-legacy/src ecommerce-api-legacy/package.json ecommerce-api-legacy/README.md`
- Fixture state: target source only.
- Input/request: static source scan.
- Expected: old hardcoded secrets, card/gateway logging, custom password helper,
  and global mutable cache are absent.
- Actual: no matches for those legacy symbols or secret patterns.
- Result: PASS
- Evidence: source scan returned no matching legacy secret/cache/payment-log sites.
- Artifact: `reports/validation-ecommerce-api-legacy.md`

### V-SEC-002 — Password Hashing
- Covers: F-004.
- Command: `node validate-current-app.js` in the disposable copy.
- Fixture state: direct call to `src/domain/password.js`.
- Input/request: `hashPassword("senhaforte")`, then `verifyPassword`.
- Expected: stored value is not plaintext and verifies through the maintained
  Node `crypto.scrypt` boundary.
- Actual: hash shape was `32:128` (`salt:derivedKey`) and verification passed.
- Result: PASS
- Evidence: validation script `password-hashing` check passed.
- Artifact: `reports/validation-ecommerce-api-legacy.md`

### V-PERSIST-001 — Complete Checkout Transaction Boundary
- Covers: F-006.
- Command: `node --test tests/regression.test.js`; static source inspection.
- Fixture state: disposable direct `CheckoutService` test with fake repositories.
- Input/request: new-user checkout with denied card `5111222233334444`.
- Expected: payment denial throws before any persisted user/enrollment/payment/audit
  write, or all writes roll back in one transaction.
- Actual: service threw `PaymentDeniedError` and recorded no write events; source
  decides payment before user lookup/write and creates new users inside
  `this.db.transaction(...)`.
- Result: PASS
- Evidence: `ecommerce-api-legacy/src/services/checkoutService.js:25-37`;
  `ecommerce-api-legacy/tests/regression.test.js:51-90`.
- Artifact: `reports/validation-ecommerce-api-legacy.md`

### V-DATA-001 — Financial Report Bounds
- Covers: F-010.
- Command: `node --test tests/regression.test.js`; static source inspection.
- Fixture state: disposable in-memory seed.
- Input/request: authorized `GET /api/admin/financial-report?limit=1` and
  `?limit=abc`.
- Expected: report query is authorized, projected, deterministic, and bounded by
  pagination parameters while preserving the existing array response shape.
- Actual: `limit=1` returned a 200 array with one course; invalid limit returned
  `400 Bad Request`; source parses bounded `limit`/`offset` and uses
  `LIMIT ? OFFSET ?` over an ordered `bounded_courses` CTE before joining rows.
- Result: PASS
- Evidence: `ecommerce-api-legacy/src/http/reportController.js:6-30`;
  `ecommerce-api-legacy/src/repositories/reportRepository.js:10-30`;
  `ecommerce-api-legacy/tests/regression.test.js:93-114`.
- Artifact: `reports/validation-ecommerce-api-legacy.md`

### V-PERF-001 — Report N+1 Removal And Bounded Query
- Covers: F-009, F-010.
- Command: static source inspection plus authorized report endpoint checks.
- Fixture state: disposable in-memory seed after one successful checkout.
- Input/request: `GET /api/admin/financial-report` and
  `GET /api/admin/financial-report?limit=1` with admin token.
- Expected: query fan-out is replaced with a bounded query count and deterministic
  order.
- Actual: `ReportRepository.fetchReportRows()` uses one `LEFT JOIN` over bounded
  courses with `ORDER BY c.id ASC, e.id ASC`; authorized default report returned
  projected fields for the seeded courses and bounded report returned one course.
- Result: PASS
- Evidence: validation script reported `report-authorized-projection` and
  `report-bounded-limit` passing.
- Artifact: `reports/validation-ecommerce-api-legacy.md`

## Resolved Findings

- `F-006`: resolved for the approved scope. Denied payments no longer leave a
  partial new-user write; successful checkout user/enrollment/payment/audit writes
  are in the transaction boundary.
- `F-010`: resolved for the approved scope. The report remains authorized and
  projected, keeps the existing array response shape, and is now bounded by
  validated `limit`/`offset` query parameters.

## Repository State

- Target app mutation: approved source changes under `ecommerce-api-legacy/src/`
  and a focused regression test under `ecommerce-api-legacy/tests/`.
- Updated artifacts: `reports/validation-ecommerce-api-legacy.md` and
  `reports/audit-project-ecommerce-api-legacy.md`.
- Pre-existing unrelated workspace state remains unrelated: `README.md` modified
  and `.idea/` untracked.
- Disposable install/runtime state: outside target root under `/tmp`.

## Completion Status

Validation reached the `VALIDATION` phase and passed for the approved
`F-006,F-010` scope. No blocking failures remain.
