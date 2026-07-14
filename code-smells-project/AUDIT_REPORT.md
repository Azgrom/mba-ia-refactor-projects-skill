# Architecture Audit Report

## Target
- Project: code-smells-project (API de E-commerce "Loja")
- Target root: /run/media/rafael/master_backup/Repos/AI Works/FullCycle-IA-MBA/challenge/ArchitectureAuditAndRefactoring/code-smells-project
- Stack: Python 3.14 / Flask 3.1.1 (flask-cors 5.0.1)

## Project Fingerprint
- Language: Python (interpreter present: 3.14.5; source uses no version-specific syntax)
- Framework: Flask, declared and pinned at 3.1.1 in requirements.txt; flask-cors 5.0.1. Not installed in this environment (no venv), so audit is static.
- Entry points: app.py (WSGI app + route registration + `__main__` boot)
- Persistence: SQLite file `loja.db`, created and seeded on first `get_db()` call; single module-global connection with `check_same_thread=False`.
- Architecture shape: MVC by filename only. app.py owns transport/composition plus two data-touching admin handlers; controllers.py owns transport + business validation + notification side effects + one raw SQL handler; models.py owns data access + domain policy (stock, totals, discount tiers) + use-case orchestration; database.py owns connection lifecycle + schema DDL + seed data.

## Source Scope
- Included: all executable application source reachable from the entry point — app.py (88 lines), controllers.py (292 lines), models.py (314 lines), database.py (86 lines); 4 files / 780 lines. Schema/seed live inside database.py.
- Excluded: `.git/` (VCS state); `.claude/` (session/tooling state, untracked); `.agents/skills/refactor-arch/` (the audit skill itself — its own scripts/tests/references, not the audited application); README.md and requirements.txt read as evidence but contain no executable application logic. No generated, vendored, test, or dead-module files exist in the app path.

## Behavioral Baseline
- Boot: `pip install -r requirements.txt` then `python app.py`; listens on http://0.0.0.0:5000; readiness = console banner "SERVIDOR INICIADO"; `loja.db` auto-created and seeded with 10 produtos and 3 usuarios on first boot. Not executed during this audit (Flask not installed; no disposable runtime available).
- Endpoints: 17 total. Produtos: `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<int:id>`, `POST /produtos`, `PUT /produtos/<int:id>`, `DELETE /produtos/<int:id>`. Usuarios/auth: `GET /usuarios`, `GET /usuarios/<int:id>`, `POST /usuarios`, `POST /login`. Pedidos: `POST /pedidos`, `GET /pedidos`, `GET /pedidos/usuario/<int:usuario_id>`, `PUT /pedidos/<int:pedido_id>/status`. Ops/report: `GET /relatorios/vendas`, `GET /health`, `GET /`. Undocumented admin: `POST /admin/reset-db`, `POST /admin/query`. (19 rules; index `/` and the two `/admin/*` are not listed in the `/` self-description.)
- Domain flows: (1) create produto → create pedido (validates stock, computes total, inserts pedido + itens_pedido, decrements estoque) → update status → sales report with tiered discount. (2) register usuario → login by email+senha.
- Persistence: writes to produtos, usuarios, pedidos, itens_pedido. `criar_pedido` performs multiple dependent writes on one shared connection with a single terminal `commit()` and no rollback. `ativo` and `criado_em` columns exist but `ativo` is never written or filtered.
- Proposed security exceptions: see Security-Driven Contract Changes. Remediating F-001, F-003, F-004, F-005 necessarily changes current (unsafe) response/endpoint contracts.

## Audit Limitations
- Static audit only: Flask/flask-cors are not installed and no disposable runtime was available, so endpoints and domain flows were traced from source rather than executed. Line ranges, call paths, and SQL construction are verified statically against the current snapshot.
- No deprecated-API finding is emitted: Context7 `/pallets/flask/3_1_1` confirms `add_url_rule`, `jsonify`, and `request.get_json()` are current in Flask 3.1.1 (`request.json` was the deprecated form; `get_json()` is the recommended one). Deprecation authority was checked and produced no finding.

## Severity Summary
| Severity | Count |
|---|---:|
| CRITICAL | 5 |
| HIGH | 4 |
| MEDIUM | 4 |
| LOW | 3 |

## Findings

### F-001 — Unauthenticated arbitrary SQL execution endpoint
- Rule: critical-arbitrary-data-execution
- Severity: CRITICAL
- Location: app.py:59-78
- Evidence: `POST /admin/query` reads `dados.get("sql", "")` and runs `cursor.execute(query)` directly, committing for non-SELECT statements; no authentication, authorization, or allowlist.
- Impact: Any client can read, modify, or destroy every table and exfiltrate all data (including plaintext passwords) — full database compromise and remote data control.
- Recommendation: Remove the endpoint. Replace with narrow, authorized, parameterized use cases; never expose raw statement execution over HTTP.
- Status: proposed
- Evidence authority: Route registered at app.py:59; handler body app.py:60-78; input `sql` fully client-controlled; privileged shared DB connection from database.get_db.

### F-002 — SQL built by string concatenation across all persistence, including auth
- Rule: critical-arbitrary-data-execution
- Severity: CRITICAL
- Location: models.py:105-120
- Evidence: `login_usuario` runs `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`; every other model query concatenates inputs the same way (e.g. models.py:28, 47-50, 109-111, 289-297).
- Impact: SQL injection on every data path; the login query is a direct authentication bypass (e.g. `senha` = `' OR '1'='1`), and search/create/update allow arbitrary injection. Secondary: high-god-component (models owns query building) is what centralizes the exposure.
- Recommendation: Replace all string-built SQL with parameterized queries (`?` placeholders) at a persistence/repository boundary; never interpolate request values into SQL text.
- Status: proposed
- Evidence authority: Concatenation sites models.py:28,47-50,58-60,68,92,109-111,126-129,140-166,174,188,192,206,220,224,279-281,289-297; login sink models.py:109-112 reached from controllers.login (controllers.py:176) and route app.py:21.

### F-003 — Unauthenticated destructive database reset endpoint
- Rule: critical-uncontrolled-privileged-operation
- Severity: CRITICAL
- Location: app.py:47-57
- Evidence: `POST /admin/reset-db` executes `DELETE FROM` on itens_pedido, pedidos, produtos, and usuarios and commits, with no authentication, authorization, confirmation, or environment guard.
- Impact: Any client can irreversibly wipe all business data (catalog, users, orders) in one request — total data-loss availability failure.
- Recommendation: Remove the endpoint, or restrict it to authenticated administrators in a non-production environment with explicit confirmation; keep destructive resets out of the HTTP surface.
- Status: proposed
- Evidence authority: Route app.py:47; handler app.py:48-57; no auth/authz middleware exists anywhere in app.py registration (app.py:11-30).

### F-004 — Hardcoded secret and unsafe production config, secret echoed to clients
- Rule: critical-exposed-runtime-secret
- Severity: CRITICAL
- Location: app.py:6-9
- Evidence: `SECRET_KEY = "minha-chave-super-secreta-123"` and `DEBUG = True` are literals; `app.run(host="0.0.0.0", ..., debug=True)` (app.py:88); `CORS(app)` allows all origins (app.py:9); `GET /health` returns `"secret_key": "minha-chave-super-secreta-123"` and `"debug": True` in the response body (controllers.py:288-289).
- Impact: The signing secret is committed and additionally leaked over the network, enabling session/token forgery; `debug=True` on `0.0.0.0` exposes the Werkzeug interactive-debugger RCE console; wildcard CORS removes browser origin protection. Secondary: low-duplicated-serialization (health builds an ad-hoc dict).
- Recommendation: Load `SECRET_KEY` from protected configuration and fail closed if absent; force `DEBUG=False` outside development; restrict CORS to known origins; remove secret/debug/db_path from the health payload. Rotate the exposed key.
- Status: proposed
- Evidence authority: Config literals app.py:7-8; bind/debug app.py:88; CORS app.py:9; secret returned to client controllers.py:287-289 via route app.py:30.

### F-005 — Plaintext passwords stored, compared, and returned to clients
- Rule: critical-sensitive-auth-payment-exposure
- Severity: CRITICAL
- Location: models.py:72-103
- Evidence: `get_todos_usuarios` and `get_usuario_por_id` include `"senha": row["senha"]` in the returned dict (models.py:83, 99); `criar_usuario` stores the raw password (models.py:126-129); the seed inserts plaintext passwords (database.py:76-78). `GET /usuarios` returns these dicts verbatim (controllers.py:130-132).
- Impact: Every user's password is exposed by an unauthenticated list endpoint and stored recoverably; credential theft and account takeover across the system. Secondary: high-weak-credential-handling (no hashing at all).
- Recommendation: Hash passwords with a maintained adaptive algorithm (e.g. bcrypt/argon2) at registration; never select or serialize the password column; verify by hash comparison at login. Migrate existing seeded credentials.
- Status: proposed
- Evidence authority: Serialization sink models.py:83,99 → controllers.py:131 → route app.py:18; storage models.py:126-129; seed database.py:76-78; login compare models.py:109-112.

### F-006 — models.py is a God Module mixing persistence, domain policy, and orchestration
- Rule: high-god-component
- Severity: HIGH
- Location: models.py:133-169
- Evidence: `criar_pedido` opens the connection, queries products, enforces stock rules, computes totals, inserts pedido and itens, and mutates estoque; `relatorio_vendas` (models.py:235-273) additionally computes tiered discount business policy inside a data-access module. The file has unrelated reasons to change (schema, pricing rules, order workflow) converging in one place.
- Impact: Business rules cannot be reused or unit-tested without the database; a pricing or workflow change forces edits in the persistence layer; broad blast radius. Secondary: high-transport-owns-domain (controllers duplicate the same mixing).
- Recommendation: Extract a domain/service layer that owns stock, totals, and discount policy, and a repository layer that owns only parameterized queries; keep useful function names as a thin facade during migration.
- Status: proposed
- Evidence authority: Responsibility spread across models.py:133-169 (orchestration+writes) and models.py:256-262 (pricing policy); callers controllers.criar_pedido (controllers.py:203) and controllers.relatorio_vendas (controllers.py:259).

### F-007 — Controllers own domain rules, side effects, and raw SQL
- Rule: high-transport-owns-domain-and-persistence
- Severity: HIGH
- Location: controllers.py:24-62
- Evidence: `criar_produto` inlines all business validation (price/stock sign, name length, category allowlist) at controllers.py:43-54; `criar_pedido` fires notification side effects via `print("ENVIANDO EMAIL...")` etc. (controllers.py:208-210); `atualizar_status_pedido` embeds status side effects (controllers.py:247-250); `health_check` executes raw SQL directly in the controller (controllers.py:266-274).
- Impact: Transport is coupled to domain policy, external-notification concerns, and persistence, so rules can't be reused across entry points and require the HTTP layer to test. Secondary: medium-duplicated-business-or-transport-policy.
- Recommendation: Keep controllers thin (parse, delegate, map response); move validation and notifications into domain/application services; move health's DB probe into a repository/health service.
- Status: proposed
- Evidence authority: controllers.py:43-62 (validation), controllers.py:208-210 and 247-250 (side effects), controllers.py:266-274 (raw SQL in transport).

### F-008 — Order creation has no transaction boundary and a TOCTOU stock check
- Rule: high-missing-transaction-boundary
- Severity: HIGH
- Location: models.py:148-169
- Evidence: `criar_pedido` inserts the pedido (models.py:148-151), loops inserting itens_pedido and decrementing estoque (models.py:154-166), and only commits once at the end (models.py:168); there is no explicit transaction/rollback, and the stock check (models.py:144) is separated from the decrement (models.py:163-166) with no locking.
- Impact: An exception mid-loop leaves a committed-or-partial order and inconsistent inventory; concurrent orders can oversell stock (check-then-act race). Corrupted, hard-to-repair business state.
- Recommendation: Wrap the whole use case in one transaction with explicit rollback on failure; re-check/decrement stock atomically (conditional UPDATE) at the service boundary; verify rollback with an injected mid-flow failure.
- Status: proposed
- Evidence authority: Full write path models.py:139-169; single commit models.py:168; check at models.py:144 vs decrement at models.py:163-166 on the shared connection (database.py).

### F-009 — Process-global mutable DB connection with schema/seed as a side effect
- Rule: high-process-global-mutable-state
- Severity: HIGH
- Location: database.py:4-13
- Evidence: `db_connection` is a module global (database.py:4) reused across all requests; `get_db` opens it with `check_same_thread=False` (database.py:10) and, on first call, runs all DDL and seed inserts (database.py:14-84) as a side effect.
- Impact: One connection shared across threads with `check_same_thread=False` invites races and cross-request state leakage; boot behavior (schema, seed) is entangled with first data access, so tests and requests are order-dependent. Secondary: medium/low around implicit initialization.
- Recommendation: Bind connection lifecycle to request/app scope (Flask `g`/teardown or a pooled session) and inject it; separate schema/seed setup from request-time access into an explicit initialization step.
- Status: proposed
- Evidence authority: Global at database.py:4; single-connection reuse database.py:7-13; thread flag database.py:10; DDL/seed side effect database.py:14-84; every model calls get_db (e.g. models.py:5,44,106).

### F-010 — N+1 query pattern in order listings
- Rule: medium-query-in-loop
- Severity: MEDIUM
- Location: models.py:171-201
- Evidence: `get_pedidos_usuario` loops over pedidos and issues a per-order `SELECT * FROM itens_pedido` (models.py:188) and then a per-item `SELECT nome FROM produtos` (models.py:192); `get_todos_pedidos` repeats the identical pattern (models.py:219-225).
- Impact: Query count grows as roughly 1 + orders + items; latency scales with data volume for both order-listing endpoints. Secondary: medium-duplicated-business-or-transport-policy (two near-identical loops).
- Recommendation: Fetch items and product names with joins or batched `IN (...)` lookups keyed by the collected IDs; assemble in memory once.
- Status: proposed
- Evidence authority: Nested query sinks models.py:188,192 (and duplicate 220,224); callers controllers.py:224 and controllers.py:232.

### F-011 — Unbounded, overbroad reads with no pagination or authorization
- Rule: medium-unbounded-or-overbroad-data-access
- Severity: MEDIUM
- Location: models.py:4-22
- Evidence: `get_todos_produtos` runs `SELECT * FROM produtos` with no limit/pagination (models.py:7); `get_todos_usuarios` runs `SELECT * FROM usuarios` returning all columns including `senha` (models.py:75,83); list endpoints have no authorization (app.py:11,18).
- Impact: Memory/latency grow unbounded with table size, and the user listing over-exposes sensitive columns to any caller. Secondary: critical-sensitive-auth-payment-exposure (cross-referenced by F-005).
- Recommendation: Add pagination/limits, project only required columns (exclude `senha`), and apply authorization on listing endpoints appropriate to expected growth.
- Status: proposed
- Evidence authority: Queries models.py:7,75; full-column serialization models.py:12-21,79-86; unauthenticated routes app.py:11,18.

### F-012 — Missing boundary validation on users, orders, and status updates
- Rule: medium-missing-boundary-validation
- Severity: MEDIUM
- Location: controllers.py:146-165
- Evidence: `criar_usuario` checks only presence, not email format or uniqueness, and accepts any string (controllers.py:153-158); numeric fields for produtos/pedidos are used without type coercion (e.g. `preco < 0` on an unparsed JSON value, controllers.py:43); `atualizar_status_pedido` calls `models.atualizar_status_pedido` without checking the order exists, returning 200 for a nonexistent id (controllers.py:245, models.py:275-283).
- Impact: Malformed input becomes inconsistent 500s or silent no-ops; duplicate/invalid emails and unvalidated numbers enter the domain; status updates falsely report success. Combined with F-002 the unvalidated strings widen the injection surface.
- Recommendation: Validate and normalize transport shape at the boundary (email format, required numeric types, existence checks) and re-enforce invariants in domain code.
- Status: proposed
- Evidence authority: controllers.py:153-158 (user), controllers.py:43-46 on unparsed JSON, controllers.py:245 + models.py:275-283 (status update returns True regardless of existence).

### F-013 — Duplicated request/error policy that has already drifted
- Rule: medium-duplicated-business-or-transport-policy
- Severity: MEDIUM
- Location: controllers.py:64-96
- Evidence: `atualizar_produto` re-implements the create-product checks but silently omits the name-length (controllers.py:47-50) and category-allowlist (controllers.py:52-54) validations that `criar_produto` enforces; the pattern `except Exception as e: return jsonify({"erro": str(e)}), 500` is copy-pasted across ~15 handlers (e.g. controllers.py:10-12, 21-22, 60-62, 95-96, 108-109).
- Impact: Validation has already diverged (a product invalid on create is valid on update), and raw exception text is leaked to clients on every error path, exposing internal details. Fixes require synchronized edits in many places.
- Recommendation: Centralize product validation in one domain function reused by create and update; introduce a shared error handler that maps exceptions to a sanitized contract instead of echoing `str(e)`.
- Status: proposed
- Evidence authority: Divergent duplication controllers.py:43-54 vs controllers.py:87-90; repeated error blocks controllers.py:10-12,21-22,60-62,95-96,108-109,125-126,133-134,143-144,164-165,185-186.

### F-014 — Hand-written row-to-dict serialization duplicated with inconsistent field exposure
- Rule: low-duplicated-serialization
- Severity: LOW
- Location: models.py:4-41
- Evidence: The produto dict shape is rebuilt in `get_todos_produtos`, `get_produto_por_id`, and `buscar_produtos` (models.py:12-21, 31-40, 304-313); the usuario shape appears in three variants that disagree on whether `senha` is included (models.py:79-86 and 95-102 include it; login's projection models.py:114-119 omits it).
- Impact: Response shapes drift between endpoints and the inconsistent `senha` handling is exactly how sensitive data leaks (F-005); every field change needs multiple synchronized edits.
- Recommendation: Define one explicit serializer/projection per entity near the transport boundary and reuse it; make the password-excluding projection the only public one.
- Status: proposed
- Evidence authority: Repeated produto dicts models.py:12-21,31-40,304-313; divergent usuario dicts models.py:79-86,95-102,114-119.

### F-015 — Magic values embedded in logic
- Rule: low-magic-value
- Severity: LOW
- Location: models.py:256-262
- Evidence: Discount thresholds and rates (`10000`/`0.1`, `5000`/`0.05`, `1000`/`0.02`) are inline in `relatorio_vendas` (models.py:257-262); status strings are hardcoded in both controller and model (controllers.py:242, models.py:247-253 context), the category allowlist is inline (controllers.py:52), and port/db path are literals (app.py:88, database.py:5).
- Impact: Business policy (pricing tiers, valid statuses/categories) is hidden in code and must be changed in multiple unnamed spots, inviting inconsistency.
- Recommendation: Name these as domain/configuration constants at their owner (pricing policy, order-status enum, category set, runtime config) rather than repeating literals.
- Status: proposed
- Evidence authority: Discount literals models.py:257-262; status list controllers.py:242; category list controllers.py:52; port app.py:88; db path database.py:5.

### F-016 — Dead imports and an unused schema column
- Rule: low-dead-or-unused-code
- Severity: LOW
- Location: models.py:1-3
- Evidence: `models.py` imports `sqlite3` (models.py:2) and never uses it; `database.py` imports `os` (database.py:2) and never uses it; the `ativo` column is created (database.py:22) and serialized (models.py:19) but never written, defaulted-by-app, or filtered on anywhere.
- Impact: Misleading maintenance surface — readers assume `ativo` is a functional soft-delete flag and that the imports are load-bearing.
- Recommendation: Remove the unused imports; either implement `ativo` (soft-delete filtering on reads) or drop it from schema and serialization to match actual behavior.
- Status: proposed
- Evidence authority: Unused import models.py:2 (no `sqlite3.` reference in file) and database.py:2 (no `os.` reference); `ativo` written nowhere — no INSERT/UPDATE lists it (models.py:47-50,58-60,126-129).

## Proposed Refactoring Scope
- F-001, F-003: remove or auth-gate the two `/admin/*` endpoints (compatibility boundary: these routes disappear or require credentials).
- F-002, F-012: introduce a repository layer with parameterized queries and boundary validation; preserve endpoint paths, methods, and success status codes.
- F-004: externalize secret/config, disable debug in prod, scope CORS, drop secret/debug/db_path from `/health` (compatibility boundary: `/health` body shrinks).
- F-005, F-011, F-014: hash passwords and stop serializing `senha`; add one projection per entity (compatibility boundary: `senha` leaves all responses; seeded plaintext logins require migration).
- F-006, F-007, F-008, F-009: extract domain/service and repository layers, own the order transaction, and scope the DB connection lifecycle while keeping route paths/methods and persistence effects intact.
- F-010, F-013, F-015, F-016: batch the order-listing queries, centralize duplicated validation/error mapping, name magic values, and remove dead code — all behavior-preserving.

## Security-Driven Contract Changes
- Remove `POST /admin/query` and `POST /admin/reset-db` (or place them behind authentication + non-production guard). Current unsafe behavior: unauthenticated arbitrary SQL and full data wipe. Proposed secure replacement: endpoints deleted or gated.
- Stop returning `senha` from `GET /usuarios` and `GET /usuarios/<id>` and hash stored passwords. Current unsafe behavior: plaintext credentials exposed. Proposed secure replacement: password never serialized; hashed at rest; existing seeded logins migrated (plaintext seeds stop working as-is).
- Stop returning `secret_key`, `debug`, and `db_path` from `GET /health`. Current unsafe behavior: signing secret and internals leaked. Proposed secure replacement: health returns only status and non-sensitive counts.
- Replace `jsonify({"erro": str(e)}), 500` with a sanitized error contract. Current unsafe behavior: internal exception text leaked to clients. Proposed secure replacement: generic 500 message; details logged server-side (error message text changes).

## Approval Required
Reply with explicit approval of this report path and snapshot digest before any target mutation. Identify all findings or the approved finding IDs.

## Audit Snapshot Digest
`sha256:09e145591707437dd7dcdeab9ae7c2da61c5d26b950f4d17ac5c34cf62d66ebe`
