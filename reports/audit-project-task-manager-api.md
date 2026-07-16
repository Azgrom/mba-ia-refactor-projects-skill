# Architecture Audit Report

## Target
- Project: task-manager-api (Full Cycle IA MBA — Architecture Audit and Refactoring challenge)
- Target root: task-manager-api
- Stack: Python 3.14.5 / Flask 3.0.0 (declared and resolved), SQLAlchemy 2.0.51 (resolved transitively; unpinned)

## Project Fingerprint
- Language: Python 3.14.5 (host interpreter); no `python_requires` or version pin declared anywhere in the repository.
- Framework: Flask 3.0.0, Flask-SQLAlchemy 3.1.1, Flask-Cors 4.0.0 (all pinned with `==` in `requirements.txt`). SQLAlchemy is **not** pinned and resolves to 2.0.51; `marshmallow==3.20.1`, `requests==2.31.0`, `python-dotenv==1.0.0` are declared but never imported by any executable module.
- Entry points: `app.py` (module-level Flask app; `python app.py` per `README.md`), `seed.py` (CLI database seeding script that imports `app`).
- Persistence: SQLite via Flask-SQLAlchemy, `sqlite:///tasks.db` (resolves to `instance/tasks.db`). Schema is created by `db.create_all()` executed at **import time** in `app.py`. Session is the Flask-SQLAlchemy request-scoped session. `PRAGMA foreign_keys = 0` (SQLite default) — foreign keys are declared but not enforced by the engine; SQLAlchemy relationship cascade nulls child FKs on parent delete.
- Architecture shape: Directory names suggest layers (`models/`, `routes/`, `services/`, `utils/`), but responsibility ownership does not follow them. The three route blueprints own HTTP parsing, input validation, business rules, ORM query construction, transaction commits, and response serialization. `services/` contains exactly one class (`NotificationService`) with **zero importers** — there is no application-service layer. `models/` owns schema plus three unused validation/domain methods. `utils/helpers.py` defines nine functions and seven constants, of which **none** are called by executable code. Effectively: a two-layer app (routes + ORM models) wearing a four-layer directory costume.

## Source Scope
- Included: 12 Python modules reachable from the `app.py` entry point and `seed.py`, resolved by tracing imports and Flask blueprint registration — `app.py`, `database.py`, `seed.py`, `models/{__init__,user,task,category}.py`, `routes/{__init__,task_routes,user_routes,report_routes}.py`, `services/notification_service.py`, `utils/helpers.py`. Plus `requirements.txt` (dependency manifest) and `README.md` (documented boot procedure). Route surface confirmed against the live Flask `url_map`, not inferred from decorators alone.
- Excluded: `.git/` (VCS state); `.claude/` and `.agents/` (agent skill tooling, pre-existing untracked user work, not application code); `instance/`, `tasks.db`, `__pycache__/`, `.venv/` (generated/runtime state). No test suite, lockfile, CI config, Dockerfile, or `.env` exists in the repository — their absence is a finding-relevant fact, not an exclusion. `services/notification_service.py` is included in scope but proven non-executable (zero importers); it is therefore judged under the dead-code rule rather than the runtime-secret rule.

## Behavioral Baseline
- Boot: `pip install -r requirements.txt` → `python seed.py` → `python app.py`; serves on `0.0.0.0:5000` with `debug=True`. Readiness signal: `GET /health` → `200 {"status":"ok","timestamp":...}`. Baseline was captured in a disposable copy under the session scratchpad with its own virtualenv; the target root was never booted, installed into, or written to.
- Endpoints: 22 application routes (23 `url_map` rules including Flask's `static`), registered via three blueprints with no URL prefix: **tasks** — `GET /tasks`, `POST /tasks`, `GET|PUT|DELETE /tasks/<int:task_id>`, `GET /tasks/search`, `GET /tasks/stats`; **users** — `GET /users`, `POST /users`, `GET|PUT|DELETE /users/<int:user_id>`, `GET /users/<int:user_id>/tasks`, `POST /login`; **reports** — `GET /reports/summary`, `GET /reports/user/<int:user_id>`, and (misplaced) `GET|POST /categories`, `PUT|DELETE /categories/<int:cat_id>`; **app-level** — `GET /`, `GET /health`. Every one of the 22 routes was exercised; all returned the status codes recorded below.
- Domain flows: (1) seed → list tasks → fetch one task → update status → re-list; (2) create user → login → receive token; (3) create task assigned to user+category → appears in `GET /users/<id>/tasks` and in `GET /reports/user/<id>` statistics; (4) delete user → cascades deletion of that user's tasks in one transaction; (5) delete category → SQLAlchemy nulls `category_id` on the 6 referencing tasks (verified: 0 orphan rows remain).
- Persistence: Observed success statuses — `GET` list/detail 200; `POST /tasks` 201; `POST /users` 201; `POST /categories` 201; `PUT` 200; `DELETE` 200; `POST /login` 200. Observed failure statuses — not-found 404; invalid input 400; duplicate email 409; bad credentials 401; inactive user 403. Observed query counts (seeded fixture: 3 users, 4 categories, 10 tasks) — `GET /tasks` = **17 queries for 10 rows**, `GET /reports/summary` = **19 queries**, `GET /tasks/stats` = 6, `GET /categories` = 5, `GET /users` = 4. These counts are the regression baseline for F-008.
- Proposed security exceptions: `POST /login` and `GET /users/<id>` and `POST /users` currently return the user's password hash in the response body (F-001), and `POST /login` returns a static forgeable token (F-002). Remediating F-001/F-002/F-004 **necessarily changes these response contracts**. These are proposed, not authorized — see Security-Driven Contract Changes.

## Audit Limitations
- No automated test suite exists, so the behavioral baseline is the endpoint/query-count inventory captured in this run rather than a pre-existing regression suite. Any refactor must be validated against that inventory.
- SQLAlchemy is unpinned in `requirements.txt`; 2.0.51 is what a fresh install resolves **today**. A different install date could resolve a different 2.x patch. The F-012 deprecation holds for any SQLAlchemy 2.0.x, but the exact patch is not reproducible without a lockfile.
- The host interpreter is Python 3.14.5. `datetime.utcnow()` (F-013) emits `DeprecationWarning` on 3.12+; on an older interpreter the same code runs silently. Severity is stated for the interpreter actually present.
- Concurrency behavior was not exercised. SQLite + `debug=True` single-process was the only runtime configuration observed; findings make no claim about behavior under a production WSGI server with multiple workers.

## Severity Summary
| Severity | Count |
|---|---:|
| CRITICAL | 3 |
| HIGH | 4 |
| MEDIUM | 6 |
| LOW | 3 |

## Findings

### F-001 — Password hash is serialized into API responses by the shared user serializer
- Rule: critical-sensitive-auth-payment-exposure
- Severity: CRITICAL
- Location: models/user.py:16-25
- Evidence: `User.to_dict()` includes `'password': self.password`. That serializer is the response body for `GET /users/<id>` (`user_routes.py:33`), `POST /users` (`user_routes.py:85-86`), and `POST /login` (`user_routes.py:209`). Runtime-confirmed: `GET /users/1` → `200` with a `password` key present; `POST /login` → `200` with `user.password` present.
- Impact: Every stored credential hash is handed to any unauthenticated caller (see F-002 — no authorization gate exists). Combined with unsalted MD5 storage (F-004), a caller can enumerate `GET /users`, read each hash, and crack it offline at negligible cost, yielding full account takeover. This is a disclosure of the authentication secret itself, not merely of profile data.
- Recommendation: Remove `password` from the serializer entirely and introduce an explicit public projection for user responses. The hash must never leave the persistence boundary; no endpoint has a legitimate need for it. Treat the currently-stored hashes as compromised and force a reset on migration.
- Status: proposed
- Evidence authority: Source (`models/user.py:21`) plus caller trace to three route sites, plus runtime response capture from a disposable seeded instance showing the `password` key in the JSON body.

### F-002 — There is no authentication or authorization boundary; login issues a forgeable static token nothing verifies
- Rule: critical-uncontrolled-privileged-operation
- Severity: CRITICAL
- Location: routes/user_routes.py:185-211
- Evidence: `login()` returns `'token': 'fake-jwt-token-' + str(user.id)` — a guessable, unsigned, non-expiring string. No route in any blueprint reads the `Authorization` header, and no `before_request` or decorator enforces identity; the token is never verified anywhere. Runtime-confirmed with **zero credentials sent**: `PUT /users/2 {"role":"admin"}` → `200` (privilege escalation), and `GET /users/2` → `200` (returns that user's password hash). `CORS(app)` (`app.py:15`) additionally permits any origin.
- Impact: Every destructive and privileged operation in the API is reachable by any anonymous caller: delete any user (cascading deletion of all their tasks), delete any task or category, promote any account to `admin`, and read every credential hash. The `/login` endpoint is decorative — it authenticates but grants nothing, and nothing else checks. This is total loss of access control, not a hardening gap.
- Recommendation: Introduce a real authentication boundary: issue signed, expiring tokens through an established library, verify them in a single enforcement point (`before_request` or a decorator applied to every mutating route), and add ownership/role authorization checks so a user cannot modify another user or escalate their own `role`. Restrict CORS to known origins. This is a deliberate contract change — see Security-Driven Contract Changes.
- Recommendation depends on: F-004 (credential primitive) landing in the same batch.
- Status: proposed
- Evidence authority: Route-to-sink trace over the complete `url_map` (22 routes, none guarded) plus runtime exploitation of unauthenticated role escalation and hash disclosure against a disposable instance.

### F-003 — Flask `SECRET_KEY` is a hardcoded literal in executable configuration
- Rule: critical-exposed-runtime-secret
- Severity: CRITICAL
- Location: app.py:11-13
- Evidence: `app.config['SECRET_KEY']` is assigned a hardcoded literal string (value redacted; present verbatim in source and in git history). The database URI is likewise hardcoded. `python-dotenv` is declared in `requirements.txt` but never imported, and no `.env` or environment-variable read exists anywhere in the codebase.
- Impact: The signing key for Flask's session and any future token/CSRF machinery is public to anyone with repository read access, permanently recorded in version control. Any signed artifact the key protects can be forged. Because the same literal ships to every environment, there is no way to rotate it per-deployment without a code change.
- Recommendation: Load `SECRET_KEY` and `SQLALCHEMY_DATABASE_URI` from the environment (the already-declared `python-dotenv` supports this), fail fast at boot when a required secret is absent rather than falling back to a default, and rotate the exposed value. Purge it from git history if the repository is or becomes public.
- Status: proposed
- Evidence authority: Executable configuration path — `app.py` is the documented entry point (`README.md`), and the assignment executes unconditionally at import. Value redacted per reporting policy.

### F-004 — Passwords are hashed with unsalted MD5
- Rule: high-weak-credential-handling
- Severity: HIGH
- Location: models/user.py:27-32
- Evidence: `set_password()` stores `hashlib.md5(pwd.encode()).hexdigest()`; `check_password()` compares MD5 digests directly. No salt, no key-stretching, no constant-time comparison. `POST /users` accepts passwords as short as 4 characters (`user_routes.py:64-65`), and the seed fixture uses 4-character passwords.
- Impact: MD5 is a fast, unsalted, GPU-friendly hash: a 4-character password falls to exhaustive search essentially instantly, and identical passwords produce identical digests across accounts (no salt), so one crack breaks every user sharing it. Combined with F-001 (hashes are handed out in responses) and F-002 (to anyone at all), this reduces to plaintext credential disclosure in practice.
- Recommendation: Replace with a maintained adaptive hash (`werkzeug.security.generate_password_hash` / `check_password_hash` is already available transitively via Flask, or use `argon2`/`bcrypt`). Since existing MD5 digests cannot be converted, migrate by forcing a password reset. Raise the minimum password length. Treat all currently-stored hashes as compromised.
- Status: proposed
- Evidence authority: Source at the credential creation and comparison sites, plus the full flow from `POST /users` → `set_password` → column → `to_dict` → response body.

### F-005 — Route handlers own validation, domain rules, persistence, and serialization; the service layer is empty
- Rule: high-transport-owns-domain-and-persistence
- Severity: HIGH
- Location: routes/task_routes.py:85-154
- Evidence: `create_task()` is a single function that parses HTTP JSON, runs eight hand-rolled validation branches, applies business rules (status enum, priority range 1–5, title bounds), issues ORM lookups (`User.query.get`, `Category.query.get`), mutates the model field-by-field, owns the transaction (`db.session.add`/`commit`/`rollback`), `print()`s to stdout as its logging, and formats the response. Every mutating handler in all three blueprints follows the same shape. Nothing sits between the route and the ORM: `services/` contains only `NotificationService`, which has zero importers (F-014). Secondary rules: medium-duplicated-business-or-transport-policy (F-011), low-duplicated-serialization (F-015).
- Impact: Business rules are only reachable through HTTP, so they cannot be unit-tested, reused by `seed.py` or a future CLI/worker, or enforced consistently — which is precisely why the same rules drifted across handlers (F-011) and why three endpoints return three different shapes for the same entity (F-015). Any change to a task rule requires editing every route that re-implements it, and testing it requires booting Flask and a database. The blast radius of a domain change is the transport layer.
- Recommendation: Extract a `TaskService` / `UserService` / `CategoryService` application layer that owns the use case and the transaction, and move query construction behind repository functions. Keep the routes as thin adapters: parse request → call service → map result/exception to an HTTP status. Move domain predicates onto the models that already declare them (`Task.is_overdue` already exists — F-011). Preserve every existing path, method, status code, and response field; this is a pure responsibility move, not a contract change.
- Status: proposed
- Evidence authority: Responsibility map built from the handler bodies of all 22 routes plus import graph; `services/` proven to have no executable caller by reference search across the scoped source.

### F-006 — Debug mode is enabled and bound to all interfaces in the documented boot path
- Rule: critical-arbitrary-data-execution
- Severity: HIGH
- Location: app.py:33-34
- Evidence: `app.run(debug=True, host='0.0.0.0', port=5000)`. `README.md` documents `python app.py` as *the* way to run the application, so this is the real boot path, not a local-only convenience. There is no environment guard, no WSGI server, and no separate production entry point.
- Impact: `debug=True` activates the Werkzeug interactive debugger, which executes arbitrary Python from the browser on any unhandled exception — and F-009 proves unhandled exceptions are trivially reachable (seven distinct 500-producing inputs). `host='0.0.0.0'` exposes that console to every interface on the network rather than loopback. The debugger's PIN is derived from predictable host attributes and is a speed bump, not an authorization boundary. Unhandled tracebacks also leak source and environment. Rated HIGH rather than CRITICAL only because the PIN gate stands between an attacker and code execution.
- Recommendation: Drive `debug` from an environment variable defaulting to off, bind to `127.0.0.1` for local development, and document a production WSGI server (gunicorn/uwsgi) as the deployment path. Pair with F-009 so unhandled exceptions stop reaching the debugger at all.
- Status: proposed
- Evidence authority: Source at the boot call plus `README.md` documenting it as the run command; reachability of unhandled exceptions demonstrated at runtime under F-009.

### F-007 — No application factory: module-level app with import-time schema mutation and hardcoded config
- Rule: high-process-global-mutable-state
- Severity: HIGH
- Location: app.py:30-31
- Evidence: `app = Flask(__name__)` is a module-level global, config is assigned to it inline as literals, and `with app.app_context(): db.create_all()` runs unconditionally **at import time**. Confirmed: merely importing `app` (as `seed.py:2` does) opens the database and issues DDL. There is no `create_app(config)` factory and no way to construct the app with different settings.
- Impact: Importing the module has a database side effect, so the schema cannot be separated from the application object — a test suite cannot point the app at an in-memory database, and `seed.py` cannot import the models without also creating the schema. Because config is hardcoded into the global (F-003), the same process cannot be configured for test/staging/production. This is the structural reason the project has no tests: there is no seam to inject one. It also makes `db.create_all()` the de facto migration strategy, which silently cannot apply schema changes to an existing database.
- Recommendation: Introduce a `create_app(config=None)` factory that constructs the app, loads config from the environment, initializes extensions, and registers blueprints; move `db.create_all()` out of import into an explicit CLI command (or adopt Alembic/Flask-Migrate for real migrations). Keep a module-level `app = create_app()` so `python app.py` and existing imports keep working during migration.
- Status: proposed
- Evidence authority: Source at the composition root plus confirmation that `import app` triggers DDL; import graph showing `seed.py` depends on that side effect.

### F-008 — N+1 query explosion in list and report endpoints
- Rule: medium-query-in-loop
- Severity: MEDIUM
- Location: routes/task_routes.py:41-57
- Evidence: `get_tasks()` loads all tasks, then inside the per-task loop issues `User.query.get(t.user_id)` and `Category.query.get(t.category_id)` — two additional round-trips per row — despite `Task.user` and `Task.category` relationships already being declared (`models/task.py:20-21`). Measured on the seeded fixture (10 tasks): **`GET /tasks` = 17 queries**. `GET /reports/summary` = **19 queries** (`report_routes.py:56` re-queries tasks once per user inside a loop over all users, on top of 11 separate `count()` calls). `GET /categories` = 5, `GET /users` = 4, `GET /tasks/stats` = 6.
- Impact: Query count grows linearly with row count, so latency degrades as O(n) round-trips: at 10 000 tasks `GET /tasks` issues ~20 001 queries. `/reports/summary` degrades on two axes simultaneously (tasks × users). These are the API's primary read endpoints, and they are already the slowest paths at fixture scale.
- Recommendation: Eager-load the declared relationships (`joinedload`/`selectinload`) in `get_tasks`, and replace the per-user loop in `summary_report` with a single `GROUP BY` aggregate. Push the `count()` fan-out into one grouped query. Assert the query counts from this baseline (17 → 1–2 for `/tasks`) as the regression check.
- Status: proposed
- Evidence authority: Runtime query counting via a SQLAlchemy `before_cursor_execute` event listener against a disposable seeded instance; counts recorded in the Behavioral Baseline.

### F-009 — Unvalidated input reaches domain logic as unhandled 500s, and bare `except:` masks the failures
- Rule: medium-missing-boundary-validation
- Severity: MEDIUM
- Location: routes/task_routes.py:110-114
- Evidence: `priority` is compared with `if priority < 1 or priority > 5` **without type coercion**, so a JSON string raises `TypeError`. Runtime-confirmed unhandled 500s (7 distinct inputs): `POST /tasks {"priority":"high"}` → `TypeError: '<' not supported between 'str' and 'int'`; `PUT /tasks/1 {"priority":"high"}` → same; `GET /tasks/search?priority=abc` and `?user_id=abc` → `ValueError: invalid literal for int()` (unguarded `int()` at `task_routes.py:261,264`); `PUT /tasks/1 {"title":null}` and `PUT /users/1 {"password":null}` → `TypeError: object of type 'NoneType' has no len()`; `POST /users {"email":123}` → `TypeError: expected string or bytes-like object`. Separately, 12 bare `except:` clauses (e.g. `task_routes.py:62`, `report_routes.py:186,207,221`) swallow *every* exception — including `KeyboardInterrupt` and `SystemExit` — and return a generic `{'error': 'Erro interno'}`. Both symptoms share one root cause: the transport boundary neither validates the request shape nor classifies errors.
- Impact: Malformed input produces 500 instead of 400, so clients cannot distinguish "you sent bad data" from "the server is broken"; the 500s also feed the exposed Werkzeug debugger (F-006). The bare excepts hide real defects — an N+1-induced database error inside `get_tasks` is indistinguishable from a bug — and make the service undebuggable in production, since the true exception is discarded rather than logged.
- Recommendation: Validate and coerce the request body at the boundary with a schema (`marshmallow` is already declared in `requirements.txt` and unused), returning 400 with field-level errors. Replace every bare `except:` with narrow exception types, log the exception with its traceback, and map known domain errors to their HTTP status via a registered error handler. Preserve all currently-correct status codes; only inputs that today produce 500 should begin producing 400.
- Status: proposed
- Evidence authority: Runtime exploitation of all seven crash inputs against a disposable instance (tracebacks captured); bare-except sites enumerated by reference search across scoped source.

### F-010 — List and report endpoints are unbounded and unpaginated
- Rule: medium-unbounded-or-overbroad-data-access
- Severity: MEDIUM
- Location: routes/task_routes.py:11-16
- Evidence: `get_tasks()` calls `Task.query.all()` with no `limit`, `offset`, or pagination parameter. The same unbounded pattern appears in `GET /users` (`user_routes.py:12`), `GET /categories` (`report_routes.py:159`), `GET /tasks/search` (`task_routes.py:266` — filters, but never bounds), `GET /users/<id>/tasks` (`user_routes.py:159`), and `GET /reports/summary`, which materializes every task **and** every user into memory (`report_routes.py:30,53`). No endpoint accepts a page or limit argument. Projection is equally overbroad: `GET /users` returns every column (F-001).
- Impact: Response size and memory grow without limit with the table. `GET /reports/summary` holds the entire task and user tables in Python lists simultaneously, so memory scales with the product of the traversals. At realistic scale these endpoints become the primary availability risk — a single unauthenticated caller (F-002) can force a full-table read on demand.
- Recommendation: Add `page`/`per_page` (or cursor) parameters with a sane default and enforced maximum to all list endpoints; return pagination metadata. Aggregate the summary report in SQL (`GROUP BY`, `COUNT`) rather than loading rows into Python — this converges with the F-008 fix. Project only the fields the endpoint contract needs.
- Status: proposed
- Evidence authority: Query source at each list endpoint plus the endpoint contract (no bounding parameter in any route signature); memory/query behavior corroborated by the recorded query counts.

### F-011 — The same business rules are re-implemented across handlers while the domain methods that own them go uncalled
- Rule: medium-duplicated-business-or-transport-policy
- Severity: MEDIUM
- Location: routes/task_routes.py:30-39
- Evidence: The "is this task overdue" rule (`due_date < now AND status not in (done, cancelled)`) is hand-inlined at **six** route sites — `task_routes.py:31,72,285`, `user_routes.py:172`, `report_routes.py:35,133` — while `Task.is_overdue()` (`models/task.py:50-60`) implements exactly that rule and has **zero call sites**. The completion-rate formula `round((done/total)*100, 2) if total > 0 else 0` is duplicated at **three** sites (`task_routes.py:296`, `report_routes.py:67,151`), while `calculate_percentage()` in `utils/helpers.py` implements it and is *imported by `report_routes.py:7` yet never called*. Status/role/priority enums are re-typed as literals in every validating handler, while `VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH` and friends are declared in `utils/helpers.py:110-116` and used nowhere. Secondary rule: low-magic-value.
- Impact: A change to any of these rules must be applied in three-to-six places or behavior silently diverges — and it already has: `GET /tasks` reports `overdue`, but `GET /tasks/search` returns the same entities *without* the field (F-015), because one site got the rule and the other did not. The canonical implementations exist and are bypassed, so the codebase actively misleads a maintainer into thinking the rule has an owner.
- Recommendation: Make the model the single owner of the domain predicate (`Task.is_overdue()`) and have every serializer/report call it. Route the percentage through the existing `calculate_percentage`. Reference the existing constants instead of literals. This finding is largely *resolved as a side effect* of the F-005 extraction — sequence it after F-005.
- Status: proposed
- Evidence authority: Reference search across scoped source establishing both the six/three duplication sites and the zero call sites of the canonical implementations; behavioral divergence confirmed at runtime.

### F-012 — Deprecated SQLAlchemy legacy `Query.get()` used throughout (16 call sites)
- Rule: medium-deprecated-api
- Severity: MEDIUM
- Location: routes/task_routes.py:65-67
- Evidence: `Task.query.get(task_id)` — the legacy `Query.get()` API — is used at 16 sites across the three blueprints (e.g. `task_routes.py:67,117,122,158,227`, `user_routes.py:29,94,136,155`, `report_routes.py:105,192,213`). Detected version: SQLAlchemy **2.0.51** (resolved; unpinned in `requirements.txt`) with Flask-SQLAlchemy 3.1.1. The SQLAlchemy 2.0 ORM documentation states verbatim: *"Query.get() — Deprecated since version 2.0. Use `Session.get()` instead"*, and further that *"the Query object is legacy as of SQLAlchemy 2.0; the `select()` construct is now preferred for constructing ORM queries."*
- Impact: These calls emit `LegacyAPIWarning` and are on the removal path for a future major version, making the SQLAlchemy upgrade a blocking, repo-wide edit later. The legacy `Query` interface also excludes the project from 2.0-style typed `select()` constructs and the eager-loading ergonomics that F-008 needs.
- Recommendation: Replace `Model.query.get(pk)` with `db.session.get(Model, pk)`, and migrate list queries to `db.session.execute(db.select(Model)...)`. This is a mechanical, behavior-preserving substitution — `Session.get()` has identical primary-key-lookup semantics including returning `None` when absent, so all existing 404 branches are unaffected. No dependency upgrade is required.
- Status: proposed
- Evidence authority: Resolved installed version (SQLAlchemy 2.0.51, confirmed via `importlib.metadata` in the disposable environment) plus current authoritative SQLAlchemy 2.0 ORM documentation fetched this run via Context7 (`/websites/sqlalchemy_en_20_orm`) stating the deprecation and its replacement.

### F-013 — Deprecated `datetime.utcnow()` used throughout (18 call sites)
- Rule: medium-deprecated-api
- Severity: MEDIUM
- Location: models/task.py:15-16
- Evidence: `datetime.utcnow` is used as a column default (`models/task.py:15,16`, `models/user.py:14`, `models/category.py:11`) and called directly in route logic and `seed.py` — 18 sites total. Detected interpreter: Python **3.14.5**. Runtime-confirmed: running `seed.py` under this interpreter emits `DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).`
- Impact: Beyond the removal path, `utcnow()` returns a **naive** datetime that merely happens to hold UTC. Every stored timestamp is therefore timezone-ambiguous, and the overdue comparison (`t.due_date < datetime.utcnow()`, F-011) silently compares two naive values whose intended zone is only a convention. Mixing in any aware datetime later raises `TypeError`, and the API serializes these naive values to clients with `str()`, so consumers receive timestamps with no offset.
- Recommendation: Replace with `datetime.now(datetime.UTC)` and store timezone-aware values (`db.DateTime(timezone=True)`). Note this changes the *string form* of `created_at`/`updated_at`/`due_date` in responses (a `+00:00` offset appears), so it is a visible serialization change — flag it if response-byte compatibility matters, or normalize the serializer to a fixed ISO-8601 format to keep the shape stable.
- Status: proposed
- Evidence authority: Detected interpreter version (3.14.5) plus the CPython runtime `DeprecationWarning` emitted by the interpreter itself during baseline capture, which names both the deprecation and its official replacement.

### F-014 — Dead code across `services/` and `utils/`, including a hardcoded SMTP credential in a module nothing imports
- Rule: low-dead-or-unused-code
- Severity: LOW
- Location: services/notification_service.py:1-48
- Evidence: `NotificationService` has **zero importers** — reference search across all scoped source finds no `import` of it anywhere; it is unreachable. It nevertheless contains a hardcoded SMTP username and password (value redacted; `notification_service.py:9-10`). Likewise dead: all nine functions in `utils/helpers.py` (`format_date`, `calculate_percentage`, `validate_email`, `sanitize_string`, `generate_id`, `log_action`, `parse_date`, `is_valid_color`, `process_task_data`) and all seven constants have **zero executable callers** — `report_routes.py:7` imports `format_date` and `calculate_percentage` but calls neither. `Task.validate_status`, `Task.validate_priority`, `Task.is_overdue`, and `User.is_admin` have zero call sites. Unused imports abound (`app.py:7` imports `os, sys, json`; `task_routes.py:7` imports `json, os, sys, time`). `marshmallow`, `requests`, and `python-dotenv` are declared dependencies that nothing imports.
- Impact: The dead surface actively misleads: `services/` and `utils/` create the appearance of a service layer and a shared-helper layer that do not exist, which is why the real logic silently duplicated into routes (F-005, F-011). The embedded SMTP credential is **not** a live runtime secret — the module never executes — but it is a real credential sitting in source and in git history, so it must be rotated regardless of reachability. Severity is LOW because nothing here runs; the credential is called out for rotation, not as an exploitable runtime exposure.
- Recommendation: Delete `NotificationService` (or wire it up deliberately — but do not leave it half-present), and rotate the SMTP credential it exposes. Delete the unused helpers and the unused imports. Do **not** delete `Task.is_overdue` or `calculate_percentage` — F-011 puts them *back into use*; sequence F-011 before this deletion so the still-needed implementations survive. Drop the three unused dependencies from `requirements.txt`, or start using `marshmallow` as F-009 recommends.
- Status: proposed
- Evidence authority: Reference search across the complete scoped source for each symbol, plus import-graph traversal from both entry points confirming `services/notification_service.py` is unreachable.

### F-015 — Three different response shapes are returned for the same Task entity
- Rule: low-duplicated-serialization
- Severity: LOW
- Location: routes/task_routes.py:16-28
- Evidence: `get_tasks()` hand-builds a task dict field-by-field instead of calling the `Task.to_dict()` that already exists (`models/task.py:23-36`), and `get_user_tasks()` (`user_routes.py:162-181`) hand-builds a *third*, different one. Runtime-confirmed field sets for the same entity: `GET /tasks` returns 14 keys (including `overdue`, `user_name`, `category_name`); `GET /tasks/search` returns 11 keys — **missing `overdue`, `user_name`, and `category_name`**; `GET /users/<id>/tasks` returns 8 keys (has `overdue`, but drops `tags`, `category_id`, `updated_at`, `user_id`).
- Impact: A client that filters tasks via `/tasks/search` cannot see `overdue` even though `/tasks` provides it, so the same UI element breaks depending on which endpoint fed it. Adding a field to the Task contract requires finding and editing three hand-rolled dicts, and forgetting one is exactly how this drift arose. It is also the mechanism by which F-001 leaks the password hash — a serializer that includes everything by default.
- Recommendation: Define explicit projections owned near the transport boundary (a `TaskSchema` with an optional `include_relations` variant), and have all three endpoints serialize through it. Decide deliberately whether `overdue`/`user_name`/`category_name` belong in the search response — this is the one place the refactor should *converge* the contracts rather than preserve them, so confirm the intended shape before changing it.
- Status: proposed
- Evidence authority: Runtime capture of the three response key sets from a disposable seeded instance, plus source at the three hand-rolled serialization sites.

### F-016 — Category CRUD is owned by the reports blueprint
- Rule: low-misleading-name
- Severity: LOW
- Location: routes/report_routes.py:157-223
- Evidence: All four category endpoints — `GET|POST /categories` and `PUT|DELETE /categories/<int:cat_id>` — are registered on `report_bp`. Confirmed against the live `url_map`: the endpoints resolve as `reports.get_categories`, `reports.create_category`, `reports.update_category`, `reports.delete_category`. Categories are a first-class entity with their own model (`models/category.py`) and have nothing to do with reporting.
- Impact: The module name actively lies about its contents, so a maintainer looking for category behavior will not find it where the domain says it should be, and a change to reporting sits in the same file as a change to category writes — two unrelated reasons to change one module. It also means `report_routes.py` is the only route module that owns write operations on an entity it does not report on.
- Recommendation: Extract a `category_routes.py` blueprint owning the four category endpoints and register it in `app.py`. Paths, methods, and response bodies stay byte-identical — only the blueprint name (and thus the internal `endpoint` string, which is not part of the HTTP contract) changes. Low risk, high clarity.
- Status: proposed
- Evidence authority: Live Flask `url_map` dump showing the four `/categories` rules bound to the `reports` blueprint, plus source at the registration site.

## Proposed Refactoring Scope
- **Batch 1 — Security (F-001, F-002, F-003, F-004, F-006).** Establish the authentication boundary and stop leaking credentials. Introduces a real password primitive, signed/expiring tokens, an enforcement point over all mutating routes, environment-loaded secrets, and an environment-guarded debug flag. **This batch deliberately changes the API contract** — see below. Compatibility boundary: all paths/methods/status codes preserved except where listed as a contract change. Rollback boundary: batch is self-contained; reverting restores current (insecure) behavior.
- **Batch 2 — Composition (F-007).** Introduce `create_app()`, move `db.create_all()` out of import, keep `app = create_app()` at module level so `python app.py` and `seed.py` keep working unchanged. Prerequisite for testing the later batches in isolation. No HTTP contract change.
- **Batch 3 — Responsibility extraction (F-005, F-011, F-016).** Extract the application-service layer, move domain predicates onto the models that already declare them, split the category blueprint. Behavior-preserving: every path, method, status code, and response field identical. F-011 must land before F-014's deletions so the newly-reused implementations survive.
- **Batch 4 — Correctness and performance (F-008, F-009, F-010).** Schema validation at the boundary (400 instead of 500), narrow exception handling with real logging, eager loading and SQL aggregation, pagination on list endpoints. Contract change: inputs that currently return 500 begin returning 400 (a fix, but observable); pagination adds parameters with backward-compatible defaults. Regression gate: the recorded query counts (17 → 1–2 for `GET /tasks`).
- **Batch 5 — Modernization and cleanup (F-012, F-013, F-014, F-015).** Mechanical `Session.get()` substitution, timezone-aware datetimes, dead-code deletion, unified serializers. F-013 and F-015 alter timestamp/field serialization — confirm intended shapes.
- Sequencing constraint: F-011 before F-014; F-005 before F-011's cleanup; F-007 before any batch that wants test coverage.

## Security-Driven Contract Changes
Remediating the CRITICAL findings **cannot** preserve the current API contract. These are proposed and require explicit authorization:
1. **`password` disappears from every response body** (F-001). `GET /users/<id>`, `POST /users`, and `POST /login` currently include the credential hash; the fix removes the field. Any client reading it breaks — by design.
2. **`POST /login` returns a real signed token instead of `fake-jwt-token-<id>`** (F-002/F-004). The token becomes opaque, signed, and expiring; clients can no longer construct it by string-concatenating a user id.
3. **Protected endpoints begin requiring an `Authorization` header and will return 401/403** (F-002). Every mutating endpoint and every user-data read is currently anonymous and returns 200; after the fix, unauthenticated calls return 401, and a non-admin attempting to modify another user or set `role` returns 403. This introduces status codes that do not exist on those paths today.
4. **Existing stored passwords stop working** (F-004). MD5 digests cannot be migrated to an adaptive hash; all users (including the seeded fixtures) require a password reset. `seed.py` will be updated to the new primitive.
5. **`SECRET_KEY` and the database URI move to the environment and the app fails fast when they are missing** (F-003). Booting without configuration, which currently succeeds, will refuse to start.
6. **Debug mode defaults off and binds to loopback** (F-006). The Werkzeug debug console will no longer be reachable, and the app will no longer serve on `0.0.0.0` unless explicitly configured.

If any of these is unacceptable, exclude the corresponding finding at approval time and it will be recorded as deferred.

## Approval Required
Reply with explicit approval of this report path and snapshot digest before any target mutation. Identify all findings or the approved finding IDs.

## Audit Snapshot Digest
`sha256:cb2e274fda9b1844c8c36137a730bcdea2cff318bcd3dd372a1a6863c8d3583c`
