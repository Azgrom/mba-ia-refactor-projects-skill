# Architecture audit: Flask store API

## Scope and result

I audited the complete `fixture/` target and refactored it from two horizontal,
all-purpose modules into contextual MVC feature slices. The HTTP paths, methods,
status codes, and payload shapes were intentionally retained. Product, user, and
order SQL now binds request data as parameters.

The composition flow is now:

`app.py` → context blueprint (`routes.py`) → HTTP controller (`controller.py`) →
SQLite model (`model.py`) → shared `database.py`.

`app.py:12-24` is only the composition root. Products, users, orders, reports,
and system operations own their respective routes/controllers/models under
`contexts/`. For example, the product path/method contract is localized at
`contexts/products/routes.py:6-31`, while order paths are localized at
`contexts/orders/routes.py:6-25`.

## Findings

### P0 — unauthenticated arbitrary SQL and destructive database reset remain

Evidence:

- `contexts/system/routes.py:8-13` publishes both admin operations without an
  authentication or authorization guard.
- `contexts/system/controller.py:29-41` accepts the caller's `sql` string and
  returns query output or execution errors.
- `contexts/system/model.py:14-21` passes that string directly to
  `cursor.execute`, permitting reads, writes, schema changes, and destructive
  statements with the application's database privileges.
- `contexts/system/model.py:4-11` deletes every business table, and
  `contexts/system/controller.py:23-26` exposes it directly.

Impact: any network caller able to reach the app can extract or destroy the
database. This is the highest-priority production gate.

Recommendation: remove these routes from production. If an operational endpoint
is unavoidable, require strong admin authentication/authorization, split read
diagnostics from migrations, allowlist operations, add CSRF protection where
cookie authentication is used, and audit every invocation. I did not change
these endpoints because removing or restricting them would deliberately change
the requested HTTP contract.

### P0 — credentials and application secrets are stored and returned in plaintext

Evidence:

- `database.py:26-34` defines a plaintext `senha` column, and
  `database.py:75-82` seeds plaintext passwords.
- `contexts/users/model.py:4-20` includes `senha` in every user returned by the
  list endpoint; that endpoint is public at `contexts/users/routes.py:8-10`.
- `contexts/users/model.py:30-34` authenticates by direct plaintext comparison.
- `app.py:15-16` hard-codes the secret key and enables debug configuration;
  `app.py:37` starts the development debugger.
- `contexts/system/controller.py:44-58` returns debug state and the secret key
  from `/health`.

Impact: a simple `GET /usuarios` discloses all passwords; `/health` discloses the
application secret; database compromise immediately yields reusable credentials;
debug mode increases remote-code-execution risk when exposed incorrectly.

Recommendation: hash passwords with a modern password hasher, never serialize
the password field, migrate the seeded users, load secrets from deployment
configuration, disable debug outside local development, and reduce health output
to non-sensitive readiness data. These changes need an explicit compatibility
and credential-migration decision, so they are reported rather than silently
changing responses/login behavior.

### P1 — one process-global SQLite connection crosses request boundaries

Evidence: `database.py:3-11` keeps one module-global connection and disables
SQLite's same-thread check. There is no per-request acquisition/teardown and no
transaction ownership boundary.

Impact: concurrent requests can share cursor/transaction state, one request's
failure can affect another request's transaction, and the connection is never
closed during normal application lifecycle.

Recommendation: move connection ownership to Flask application/request context,
register teardown, and make transactions explicit in the model operation that
owns them. This should be done with concurrency-focused integration tests.

### P1 — order and relational invariants are not enforced

Evidence:

- `contexts/orders/controller.py:12-21` checks only that `usuario_id` and a
  non-empty item list are present. It does not require positive integer
  quantities or confirm that the user exists.
- `contexts/orders/model.py:9-17` checks product existence and available stock,
  but negative quantities pass; `contexts/orders/model.py:37-40` would then add
  stock rather than subtract it.
- `contexts/orders/model.py:92-98` reports success even if the order ID does not
  exist.
- `database.py:14-53` declares nullable columns without foreign keys, uniqueness,
  status checks, or non-negative stock/quantity checks.

Impact: phantom-user orders, negative totals/quantities, duplicate emails, and
orphaned records are possible, and nonexistent order updates return HTTP 200.

Recommendation: define request/domain validation and database constraints
together, then migrate existing data. This was deferred because correcting the
invalid-input responses changes observable HTTP behavior.

### P2 — exception details leak and order reads use N+1 queries

Evidence:

- Controllers return raw exception text, for example
  `contexts/products/controller.py:81-83` and
  `contexts/orders/controller.py:38-40`, exposing storage details to callers.
- `contexts/orders/model.py:46-63` queries items and then queries the product once
  per item; `contexts/orders/model.py:66-79` invokes that work once per order.

Impact: internal details become part of 500 responses and list latency/query
count grows with both orders and line items.

Recommendation: map expected domain errors to stable public messages, log an
internal correlation ID, and load order/item/product data with a bounded joined
query while preserving the current JSON nesting.

## Refactoring completed

### Contextual MVC boundaries

- `app.py:12-24` creates the Flask app, configures cross-origin handling, and
  registers five blueprints. It no longer contains business/admin handlers.
- Each feature owns its HTTP mapping and controller/model pair:
  `contexts/products/`, `contexts/users/`, `contexts/orders/`,
  `contexts/reports/`, and `contexts/system/`.
- The original monolithic `controllers.py` and `models.py` were removed, so new
  work has an obvious feature-local home rather than expanding cross-domain
  modules.
- `README.md:14-27` documents the structure and test command.

### Bound SQL for request-controlled values

- Product lookups, writes, updates, deletion, and search filters bind values at
  `contexts/products/model.py:22-25`, `contexts/products/model.py:29-39`,
  `contexts/products/model.py:42-60`, and `contexts/products/model.py:63-80`.
- User lookup/login/creation binds values at `contexts/users/model.py:23-44`.
- Order creation, item writes, stock changes, reads, and status updates bind
  values at `contexts/orders/model.py:9-40`, `contexts/orders/model.py:46-68`,
  and `contexts/orders/model.py:82-98`.
- `tests/test_models.py:84-93` proves that quote-containing product data is stored
  correctly and that a classic injected search term is treated as data.

The admin SQL console is intentionally called out as an unresolved P0 exception;
it cannot be parameterized while retaining its arbitrary-query semantics.

### Duplication reduced without contract changes

- Shared product validation lives at
  `contexts/products/controller.py:36-56`; the create/update-specific validation
  differences from the original behavior remain explicit at
  `contexts/products/controller.py:59-64` and
  `contexts/products/controller.py:86-94`.
- Shared order serialization lives at `contexts/orders/model.py:46-79`, replacing
  duplicate all-orders/user-orders assembly code while retaining the same nested
  item representation.

## HTTP compatibility and verification

The pre-refactor route table contained 19 path/method pairs. The executable route
contract at `tests/test_http_contract.py:33-61` specifies those same 19 pairs,
including both methods on shared paths. The representative workflow at
`tests/test_http_contract.py:63-138` specifies the important status codes and JSON
shapes for root, product create/not-found, user create/login, order create/status,
sales report, admin query, health, and reset.

Verification performed:

- Pre-refactor model workflow captured: 10 seeded products; created product/user
  IDs 11/4; login shape unchanged; order ID 1 and total 20.0; nested order item
  shape unchanged; approved-order report unchanged.
- `python -m unittest discover -s tests -v`: **pass** for both model integration
  tests; 4 discovered, 2 passed, 2 HTTP tests skipped.
- All 26 Python files parsed successfully with `ast.parse`.
- A prior `python -m compileall -q fixture` run passed.

Verification limitation: the assigned environment had no Flask installation.
Installing the pinned requirements was attempted first in an isolated local
virtual environment, but package download failed because DNS/network access was
unavailable, and the required escalated retry was rejected by the environment's
usage limit. Consequently, the full Flask test-client workflow is committed but
was not executed here. After dependencies are available, run from `fixture/`:

```bash
python -m unittest discover -s tests -v
```

## Baseline evidence record

The following references are from the inspected pre-refactor snapshot; those two
files were removed as part of the feature-slice migration:

- Original `controllers.py:5-292` mixed products, users, authentication, orders,
  reports, and health in one controller module.
- Original `models.py:4-314` mixed every context's persistence and reporting.
- Original `models.py:28`, `models.py:47-50`, `models.py:57-60`,
  `models.py:109-111`, `models.py:126-129`, and `models.py:289-299` built SQL by
  concatenating request-controlled values.
- Original `app.py:11-30` registered all business routes in the application
  bootstrap, while `app.py:47-78` implemented database administration directly.

These baseline issues motivated the contextual split and parameter binding above.
