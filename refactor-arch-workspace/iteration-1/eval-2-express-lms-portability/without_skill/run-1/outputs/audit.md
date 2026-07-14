# LMS Express API architecture and risk audit

## Executive summary

The legacy implementation placed HTTP transport, validation, SQL, payment decisions, password handling, audit logging, reporting, caching, and process configuration in one `AppManager`. It also committed checkout records in separate callbacks, logged a full card number beside an embedded live-looking key, deleted users without cleaning dependent rows, and built the financial report with an N+1 query tree whose inner errors were ignored.

The current fixture has been modernized into a responsibility-based MVC/application structure:

- routes map the three existing endpoint roles;
- controllers translate HTTP requests and responses;
- services own checkout, reporting, and deletion use cases;
- repositories own SQL;
- infrastructure adapters own SQLite, password hashing, and payment authorization;
- middleware owns admin authentication and error translation;
- `app.js` composes an injectable application, while `server.js` owns process startup/shutdown.

This is an appropriate amount of separation for the fixture. Adding a generic ORM, dependency-injection framework, or domain-event system now would add more machinery than evidence warrants.

## Compatibility and checkout behavior

The API retains these public endpoint roles:

| Method and path | Preserved meaning |
|---|---|
| `POST /api/checkout` | Accepts `usr`, `eml`, `pwd`, `c_id`, and `card`; reuses an existing email; cards beginning with `4` succeed; success remains HTTP 200 with `{ "msg": "Sucesso", "enrollment_id": ... }`; inactive/missing courses remain 404; denied cards remain 400. Repeat successful checkouts remain allowed, matching the legacy behavior. |
| `GET /api/admin/financial-report` | Returns one entry per course with revenue and student/payment summaries. |
| `DELETE /api/users/:id` | Deletes the user; dependent enrollment/payment cleanup is now reliable rather than intentionally leaving corrupt rows. |

Compatibility-tightening changes are intentional and should be communicated:

- malformed email, card, course ID, and overlong values now receive 400 instead of reaching incidental runtime/database behavior;
- denied checkout is atomic and no longer leaves a newly created user behind;
- deleting a missing user now returns 404, and the success text no longer claims orphan records remain;
- when `ADMIN_API_KEY` is configured, the report and delete endpoints require `x-admin-key`; production refuses to boot without the key.

## Findings and disposition

### Critical — sensitive data and credential handling: remediated

Legacy evidence:

- database, SMTP, and live-looking payment keys were embedded in `utils.js`;
- checkout logged the full card number and payment key;
- `badCrypto` produced a short, deterministic Base64-derived password value;
- administrative endpoints had no authentication hook.

Current state:

- embedded secrets and card logging were removed;
- configuration comes from environment input;
- new passwords use salted `scrypt` through an isolated adapter;
- admin comparison uses `crypto.timingSafeEqual` and production fails closed without `ADMIN_API_KEY`;
- Express's identifying header is disabled, JSON is strict and capped at 32 KiB, and `nosniff` is set.

Remaining caveat: when no admin key is configured outside production, admin routes remain open for legacy/development compatibility. Non-production deployments exposed to untrusted networks must still set the key.

### Critical — partial checkout writes: remediated, with a payment-boundary caveat

Legacy enrollment, payment, and audit inserts committed independently; payment or audit failure could leave incomplete state, and audit errors were ignored. The new `BEGIN IMMEDIATE` transaction rolls back user/enrollment/payment/audit changes together. Database operations are queued so callbacks cannot interleave another request inside that transaction.

The current prefix gateway is only a deterministic fixture. A real remote payment authorization cannot be made atomic with SQLite. Holding a write transaction open while calling a real gateway would also increase lock time. Before replacing the mock, introduce a payment intent/idempotency key and reconciliation or outbox workflow; authorize outside the write transaction, then persist a uniquely identified result with safe retry behavior.

### High — relational integrity and money representation: remediated

The legacy schema had nullable columns, no foreign keys, no uniqueness, no checks, and used floating-point `REAL` for money. User deletion knowingly left orphan enrollments and payments.

The replacement schema enables foreign keys, cascading cleanup, uniqueness where one-to-one is intended, status/active/range checks, non-null columns, indexes, and integer cents. User email is unique case-insensitively. Repeat enrollments were deliberately not made unique because the legacy checkout allowed another successful purchase of the same course.

For a persistent pre-refactor database, this DDL is not a migration: `CREATE TABLE IF NOT EXISTS` will not retrofit constraints or rename `price`/`amount` columns. A production rollout needs an explicit versioned migration that copies and validates old data.

### High — financial report N+1 queries and swallowed errors: remediated

The old report performed courses → enrollments → user → payment callbacks, producing roughly `1 + C + 2E` queries, nondeterministic completion ordering, and unchecked inner errors. It could throw while reading `enrollments.length` after a query failure.

`ReportingRepository` now performs one ordered, parameter-free `LEFT JOIN`; `FinancialReportService` reduces those rows into the same course/revenue/student meaning. Errors flow to centralized middleware. The indexes support the join and paid-status access pattern.

### High — native SQLite dependency portability: open

The lockfile resolves `sqlite3` 5.1.7 and contains deprecated native-build transitive packages, including unsupported `npmlog`, `gauge`, and `are-we-there-yet`, deprecated `prebuild-install`, old `glob`, `rimraf`, and `tar`. In this environment, full runtime verification was unavailable because the interrupted local dependency state had no `node_sqlite3.node` binding for Node 26.

This is not evidence that the callback calls themselves are deprecated, but it is clear packaging/portability debt. Choose and test one supported deployment baseline:

1. pin a Node LTS version for which the locked driver publishes a tested prebuild; or
2. migrate the `SqliteDatabase` adapter to Node's built-in `node:sqlite` on an explicitly supported Node baseline; or
3. select a maintained adapter and keep the repository/service contracts unchanged.

Add CI for the declared Node versions. The current `"node": ">=18"` claim is broader than has been demonstrated.

### Medium — Express 4 async errors and deprecated APIs: handled

Current Express 4 documentation confirms that rejected Promise forwarding is not automatic as it is in Express 5. The router uses an `asyncHandler` wrapper and places four-argument error middleware after routes, which is correct for Express 4. The code uses current `express.json()` and `express.Router()` APIs; no deprecated Express API was found. The error handler now delegates to Express when headers were already sent.

An Express 5 upgrade is optional, not required for this architecture. If taken, it should be a separately tested dependency change; the wrapper can then be removed.

### Medium — seed policy and operational controls: open

Initialization always seeds a known user/course dataset, even for a persistent database. The password is hashed, but production data creation should be an explicit migration/bootstrap command guarded by environment, not an application-start side effect. Add structured logs with request IDs and audit actors; never reintroduce card or secret values.

### Medium — test coverage: open

No committed automated test suite is present. The injectable `createApplication`, repositories, and gateway/hasher seams now make contract tests practical. Minimum coverage should lock down:

- the complete route/status/payload matrix;
- existing-user, new-user, denied-card, missing-course, and repeat-checkout paths;
- rollback after enrollment, payment, and audit failures;
- deletion cascades;
- report totals and courses with no enrollments;
- admin authentication and malformed JSON.

## Verification performed

Network and dependency installation were explicitly excluded from this run.

Local-only verification completed:

```text
node --check for every src/**/*.js file: passed
validateCheckout assertions: passed
FinancialReportService aggregation assertions: passed
```

Full server/database tests were not reported as passing: the local partial `node_modules` state lacks the native SQLite binding. That dependency/runtime issue is captured above rather than hidden.

## Recommended next steps

1. Add the checkout/rollback/route contract suite before deployment.
2. Decide the supported Node/SQLite adapter matrix and make `engines` plus CI truthful.
3. Create a real schema migration for any persistent legacy database.
4. Design idempotent payment reconciliation before integrating a remote gateway.
5. Move fixture seeding to an explicit non-production bootstrap command.
