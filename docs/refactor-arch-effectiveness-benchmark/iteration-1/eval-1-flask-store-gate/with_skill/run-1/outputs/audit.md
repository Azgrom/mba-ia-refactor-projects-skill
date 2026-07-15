# Architecture Audit Report

## Target
- Project: `code-smells-project` e-commerce API fixture
- Target root: `fixture`
- Stack: Python (project version undeclared; discovery runtime 3.14.5), Flask 3.1.1 and flask-cors 5.0.1 declared exactly in `requirements.txt`; installed/resolved framework versions unavailable

## Project Fingerprint
- Language: Python; four reachable application modules, with no project-level Python version constraint
- Framework: Flask route decorators plus `app.add_url_rule`, with application-wide flask-cors; declared pins are Flask 3.1.1 and flask-cors 5.0.1
- Entry points: `app.py` constructs the application, registers all routes, initializes SQLite on direct execution, and starts the development server
- Persistence: SQLite file `loja.db`; `database.py` creates schema and seeds data lazily on first `get_db()`, then retains one process-global connection used by every route and model operation
- Architecture shape: `app.py` owns composition plus administrative persistence handlers; `controllers.py` maps HTTP but also validates, performs health queries, and emits side-effect notifications; `models.py` combines product, user/authentication, order, inventory, reporting, SQL, and serialization responsibilities; `database.py` owns connection, schema, and seed lifecycle

## Source Scope
- Included: the reachable executable application in `app.py`, `controllers.py`, `models.py`, and `database.py` (4 files), plus `requirements.txt` and `README.md` as dependency and boot evidence; schema and seed statements in `database.py` are included because they determine runtime behavior
- Excluded: `fixture/.agents/` skill references/scripts as non-application tooling; caches, bytecode, generated databases, virtual environments, logs, build output, vendored code, and editor state; no tests, migrations, lockfile, or generated application source are present

## Behavioral Baseline
- Boot: documented sequence is `pip install -r requirements.txt` then `python app.py`; direct execution calls `get_db()`, creates/seeds `loja.db`, prints a startup banner, and invokes Flask on `0.0.0.0:5000` with debug enabled. Dynamic readiness was not exercised because the declared Flask packages are not installed in the discovery environment.
- Endpoints: 19 application routes are statically registered (excluding Flask's built-in static route): `GET /` returns API metadata (200); `GET /produtos` lists products (200/500); `GET /produtos/busca` filters by query/category/price (200/500); `GET /produtos/<id>` returns one product (200/404/500); `POST /produtos` creates one (201/400/500); `PUT /produtos/<id>` replaces its fields (200/400/404/500); `DELETE /produtos/<id>` deletes one (200/404/500); `GET /usuarios` lists users (200/500); `GET /usuarios/<id>` returns one user (200/404/500); `POST /usuarios` creates a user (201/400/500); `POST /login` authenticates (200/400/401/500); `POST /pedidos` creates an order (201/400/500); `GET /pedidos` lists all orders (200/500); `GET /pedidos/usuario/<usuario_id>` lists one user's orders (200/500); `PUT /pedidos/<pedido_id>/status` updates status (200/400/500); `GET /relatorios/vendas` returns aggregate sales data (200/500); `GET /health` queries database counts and returns runtime details (200/500); `POST /admin/reset-db` deletes all business rows (200); `POST /admin/query` executes client-supplied SQL (200/400/500).
- Domain flows: product create/update/delete each writes and commits independently; user creation stores credentials and login compares them; order creation validates product existence/stock, calculates total, creates an order and line items, decrements inventory, then commits; status updates commit an unrestricted enum value, while cancellation prints a restock message but performs no restock; sales reporting counts orders and applies revenue-based discount thresholds.
- Persistence: first access creates four tables and seeds 10 products plus 3 users when the product table is empty; product/user/status operations commit on success; order creation performs dependent parent/item/inventory writes before one final commit but has no explicit rollback; reset deletes items, orders, products, and users then commits; non-`SELECT` admin SQL commits. No foreign keys, uniqueness constraints, connection teardown, or transaction owner is defined.

## Audit Limitations
- Flask and flask-cors are declared but absent from the discovery Python 3.14.5 environment, so server boot, test-client requests, actual response bodies, CORS behavior, and framework error handling were not dynamically verified. No dependencies were installed during audit.
- No automated tests or request collection exists. Endpoint contracts and persistence effects above are therefore source-traced baselines, not executed observations.
- No deprecation finding is proposed; resolved package metadata and version-specific documentation were not needed or inferred from memory.

## Severity Summary
| Severity | Count |
|---|---:|
| CRITICAL | 5 |
| HIGH | 3 |
| MEDIUM | 3 |
| LOW | 1 |

## Findings

### F-001 — Public endpoint executes arbitrary client-supplied SQL
- Rule: critical-arbitrary-data-execution
- Severity: CRITICAL
- Location: app.py:59-78
- Evidence: `POST /admin/query` reads the request's `sql` value and passes it directly to `cursor.execute`; non-`SELECT` statements are committed, and the handler contains no authentication, authorization, or allowlist.
- Impact: Any network caller can read, alter, or destroy the entire SQLite data set and can enumerate schema or credential data under the application's database privileges.
- Recommendation: Remove the general SQL execution surface. If operational diagnostics are required, expose narrowly typed, allowlisted use cases behind administrator authorization and return sanitized results.
- Status: proposed
- Evidence authority: Executable decorator registration at `app.py:59`, request-to-SQL sink trace at `app.py:61-75`, and the shared privileged connection returned by `database.py:7-12`.

### F-002 — Public reset endpoint can erase all business data
- Rule: critical-uncontrolled-privileged-operation
- Severity: CRITICAL
- Location: app.py:47-57
- Evidence: `POST /admin/reset-db` deletes every row from order items, orders, products, and users and commits without authentication, authorization, environment restriction, or confirmation.
- Impact: Any caller can cause immediate, irreversible application-level data loss and denial of service.
- Recommendation: Remove this HTTP operation from production composition; if development reset support is necessary, restrict it to an explicit non-production command or require strong administrator authorization and environment policy.
- Status: proposed
- Evidence authority: Executable Flask route and full destructive write set are co-located at `app.py:47-57`; no application route registers an authentication or authorization layer.

### F-003 — Health response discloses the live Flask secret
- Rule: critical-exposed-runtime-secret
- Severity: CRITICAL
- Location: controllers.py:264-290
- Evidence: The public health handler returns a `secret_key` field containing the same inline secret configured as Flask's `SECRET_KEY` in `app.py:7`; the report intentionally redacts its value.
- Impact: Disclosure of the signing secret can enable forged Flask-signed data such as sessions if those features are introduced or used, and also reveals debug and database-path internals to unauthenticated callers.
- Recommendation: Load required secrets from protected configuration, rotate the exposed value, fail safely when missing, and reduce health output to non-sensitive readiness information.
- Status: proposed
- Evidence authority: Route registration at `app.py:30`, executable secret configuration at `app.py:7`, and response serialization at `controllers.py:276-290`.

### F-004 — User APIs expose credentials stored in plaintext
- Rule: critical-sensitive-auth-payment-exposure
- Severity: CRITICAL
- Location: models.py:72-103
- Evidence: Both user projections include the `senha` credential field, and unprotected `GET /usuarios` and `GET /usuarios/<id>` return those projections; creation and seed paths store raw passwords and login compares raw values.
- Impact: A single unauthenticated request discloses every stored password, enabling direct account takeover and credential stuffing against other services.
- Recommendation: Introduce a user/authentication context with adaptive password hashing, migration or reset handling for existing rows, explicit safe response serializers that never include credentials, and maintained verification at login.
- Status: proposed
- Evidence authority: Route-to-response trace `app.py:18-19` → `controllers.py:128-144` → `models.py:72-103`; plaintext creation/comparison is at `models.py:105-131`, and plaintext seed data is at `database.py:75-83`.

### F-005 — Login credentials are interpolated into executable SQL
- Rule: critical-arbitrary-data-execution
- Severity: CRITICAL
- Location: models.py:105-111
- Evidence: Public login values `email` and `senha` are concatenated into the `WHERE` clause passed to SQLite, with no parameter placeholders or upstream escaping.
- Impact: Crafted credentials can alter the predicate and bypass authentication, including selecting the seeded administrator row, while the same interpolation pattern also expands injection risk across product and user writes/searches.
- Recommendation: Make parameterized statements mandatory in context-specific repositories and keep authentication verification outside raw query construction; add regression tests for quote and tautology payloads.
- Status: proposed
- Evidence authority: Input-to-sink trace `app.py:21` → `controllers.py:167-183` → `models.py:105-111`; related request-controlled concatenation appears at `models.py:43-60`, `models.py:122-129`, and `models.py:285-300`.

### F-006 — One mutable SQLite connection is shared across all requests
- Rule: high-process-global-mutable-state
- Severity: HIGH
- Location: database.py:4-11
- Evidence: `db_connection` is a module global lazily assigned once, opened with `check_same_thread=False`, and returned to every controller/model call without request teardown or synchronization.
- Impact: Concurrent requests and tests share transaction and cursor-visible state, so failures and commits can leak across use cases, race, or make behavior order-dependent.
- Recommendation: Create the connection through application composition, bind it to Flask's request/application context with teardown, and inject a transaction/repository boundary into services.
- Status: proposed
- Evidence authority: Global initialization and reuse at `database.py:4-11`; callers in `app.py`, `controllers.py`, and every persistence function in `models.py` all import the same `get_db` provider.

### F-007 — Order writes have no explicit rollback boundary
- Rule: high-missing-transaction-boundary
- Severity: HIGH
- Location: models.py:133-169
- Evidence: Order creation inserts the order and items and decrements stock across multiple statements, commits only at the end, and defines no rollback path; the controller catches exceptions and returns 500 without cleaning the shared connection's pending transaction.
- Impact: A mid-flow failure can leave pending partial order/inventory changes that a later request commits through the process-global connection, corrupting order totals, line items, or stock.
- Recommendation: Move the complete order use case into an order application service that owns an explicit unit of work, rolls back on every failure, and proves rollback with an injected failure between item writes.
- Status: proposed
- Evidence authority: Dependent read/write set and sole success commit at `models.py:133-169`, exception swallowing at `controllers.py:218-220`, and shared connection lifecycle at `database.py:4-11`.

### F-008 — The data module combines unrelated contexts and layers
- Rule: high-god-component
- Severity: HIGH
- Location: models.py:133-314
- Evidence: This range alone coordinates order creation and inventory, serializes order graphs, calculates reporting discounts, updates order status, and builds product-search SQL; earlier functions in the same module also implement product CRUD and user authentication.
- Impact: Product, user/auth, order, inventory, and reporting changes converge on one module whose tests require database state, increasing blast radius and obscuring MVC ownership.
- Recommendation: Evolve toward contextual MVC slices: thin Flask controllers, per-context application services for use-case coordination, domain policies for order/status/report calculations, and focused SQLite repositories/models; retain compatibility facades while moving callers incrementally.
- Status: proposed
- Evidence authority: Controller imports the entire module at `controllers.py:2` and delegates every use case to it; responsibility evidence spans product/user functions at `models.py:4-131` and order/report/search functions at `models.py:133-314`.

### F-009 — Order input bypasses essential domain validation
- Rule: medium-missing-boundary-validation
- Severity: MEDIUM
- Location: controllers.py:188-220
- Evidence: The handler checks only that `usuario_id` is truthy and `itens` is non-empty before delegation; it does not validate item object shape, numeric types, positive quantity, duplicate products, or user existence, while downstream code indexes fields directly and subtracts the supplied quantity.
- Impact: Malformed items become 500 responses, nonexistent users can own orders, and zero/negative quantities can create invalid totals or increase inventory.
- Recommendation: Validate and normalize the request at the controller boundary, then enforce user existence and positive quantity/order invariants again in an order domain/application service.
- Status: proposed
- Evidence authority: Public body source and incomplete checks at `controllers.py:188-203`; downstream assumptions and arithmetic at `models.py:139-166`; schema has no foreign key at `database.py:37-52`.

### F-010 — Order listing performs nested per-record queries
- Rule: medium-query-in-loop
- Severity: MEDIUM
- Location: models.py:203-233
- Evidence: After fetching all orders, the function queries line items once per order and then queries the product name once per item.
- Impact: Query count grows as `1 + orders + items`, so the unbounded list endpoint's latency and database contention increase with normal sales growth.
- Recommendation: Fetch the order graph with joins or bounded batch queries, group rows in repository mapping, and preserve the existing JSON order/item shape at the controller boundary.
- Status: proposed
- Evidence authority: `GET /pedidos` route at `app.py:24` calls `controllers.py:229-235`, which calls the nested SQLite query loops at `models.py:203-233`.

### F-011 — Product validation is duplicated and already inconsistent
- Rule: medium-duplicated-business-or-transport-policy
- Severity: MEDIUM
- Location: controllers.py:24-96
- Evidence: Create and update independently parse the same required fields, defaults, and non-negative price/stock rules, but only create enforces name length and category membership.
- Impact: The update endpoint can persist values that the create endpoint rejects, and future product policy fixes require synchronized controller edits.
- Recommendation: Centralize shared request shape mapping at the product controller boundary and move product invariants into one product-domain constructor/update policy used by both application services.
- Status: proposed
- Evidence authority: Side-by-side executable create policy at `controllers.py:24-58` and update policy at `controllers.py:64-93`; both are registered from `app.py:14-15`.

### F-012 — Product serialization is manually repeated
- Rule: low-duplicated-serialization
- Severity: LOW
- Location: models.py:4-41
- Evidence: List and single-product reads independently construct the same eight-field dictionary, and search repeats the projection again at `models.py:301-313`.
- Impact: Field additions, omissions, or redaction fixes can drift among product endpoints and keep transport representation coupled to SQLite row mapping.
- Recommendation: Define one explicit product projection/serializer at the contextual boundary and reuse it across repository reads while preserving current response fields.
- Status: proposed
- Evidence authority: Duplicate mappings at `models.py:4-41` and third mapping at `models.py:301-313`, reached by the registered list/get/search routes at `app.py:11-13`.

## Proposed Refactoring Scope
- F-001, F-002, F-003 → move administration and health behavior out of the composition root/controller SQL path into narrowly typed admin/health services and protected configuration; keep route paths/methods only where a safe operation remains, subject to the explicit contract changes below.
- F-004, F-005 → establish a user/auth context with a safe serializer, password hasher/verifier, and parameterized user repository; preserve normal create/login status and response meaning while removing credential leakage and injection behavior.
- F-006, F-007 → replace the process global with application/request-scoped connection composition and an order-service unit of work; preserve successful SQLite write effects while guaranteeing failure rollback and cleanup.
- F-008 → incrementally split product, user/auth, order/inventory, and reporting responsibilities into contextual MVC slices (`controller` → application service/domain policy → repository/model), retaining thin compatibility facades until all route callers move.
- F-009 → add transport schemas and order-domain invariants before writes; preserve valid-order behavior while rejecting invalid shapes, identities, and quantities consistently.
- F-010 → batch/join order graph reads behind the order repository without changing the successful `GET /pedidos` JSON meaning.
- F-011, F-012 → consolidate product invariant policy and product projection in the product context while preserving accepted valid inputs and response fields.

## Security-Driven Contract Changes
- `POST /admin/query`: stop accepting or executing arbitrary SQL; replace it with authorized, typed, allowlisted diagnostics (or remove/disable the route), so prior arbitrary read/write requests no longer return success.
- `POST /admin/reset-db`: make the operation unavailable in production and require explicit administrator authorization in allowed environments; unauthenticated calls no longer delete data and return a non-success response.
- `GET /health`: omit `secret_key`, `db_path`, and debug/configuration internals; expose only non-sensitive liveness/readiness information.
- `GET /usuarios` and `GET /usuarios/<id>`: omit `senha` from every response. Existing and newly created credentials are migrated/stored as adaptive hashes, while valid login request/response meaning remains unchanged.
- Injection payloads against login, product, user, and search inputs are treated strictly as values and cannot alter SQL; order payloads with nonexistent users, malformed items, or non-positive quantities are rejected with 4xx responses rather than succeeding or surfacing 500 details.

## Approval Required
Reply with explicit approval of this report path and snapshot digest before any target mutation. Identify all findings or the approved finding IDs.

## Audit Snapshot Digest
`sha256:28083a6bc72e9ad03f06191065e4b183a52516f7a509c7e930d69d1c3f258084`
