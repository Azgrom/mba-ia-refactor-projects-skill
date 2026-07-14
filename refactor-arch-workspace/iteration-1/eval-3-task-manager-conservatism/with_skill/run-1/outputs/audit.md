# Architecture Audit Report

## Target
- Project: task-manager-api
- Target root: fixture/
- Stack: Python (runtime version unresolved), Flask 3.0.0 declared, Flask-SQLAlchemy 3.1.1 declared, Flask-CORS 4.0.0 declared, Marshmallow 3.20.1 declared, Requests 2.31.0 declared, python-dotenv 1.0.0 declared

## Project Fingerprint
- Language: Python; runtime version unresolved because no executed interpreter metadata or version-pinning beyond `requirements.txt` was available
- Framework: Flask app with Flask-SQLAlchemy blueprints; only declared dependency versions were available because the project has no lockfile and installed packages were not inspected
- Entry points: `app.py` for HTTP boot and schema creation, `seed.py` for destructive reseeding
- Persistence: SQLite file database `tasks.db` configured in `app.py`; schema is created on import via `db.create_all()`, and `seed.py` deletes/recreates users, categories, and tasks before repopulating sample data
- Architecture shape: `app.py` acts as a small composition root, `models/` retain useful ORM ownership, but blueprints still own substantial validation, query orchestration, serialization, reporting logic, and security decisions; `utils/helpers.py` contains reusable logic that routes mostly bypass

## Source Scope
- Included: Executable application modules reached from `app.py` plus behavior-shaping seed/config files: `app.py`, `database.py`, `seed.py`, `requirements.txt`, `models/*.py`, `routes/*.py`, `services/notification_service.py`, and `utils/helpers.py`
- Excluded: package marker `__init__.py` files with no runtime logic, dependency directories/virtualenvs, generated caches, the SQLite database file itself, and any external services not wired into the boot path

## Behavioral Baseline
- Boot: `python seed.py` resets and repopulates `tasks.db`, then `python app.py` creates tables if missing and starts Flask on `0.0.0.0:5000` with `debug=True`; dynamic boot was not executed because dependency installation/network use were disallowed and local installed-package state was unknown
- Endpoints: 21 route/method surfaces were discovered — `GET /health`, `GET /`, task CRUD plus `/tasks/search` and `/tasks/stats`, user CRUD plus `/users/<id>/tasks` and `/login`, report endpoints `/reports/summary` and `/reports/user/<id>`, and category CRUD under `/categories`
- Domain flows: task creation/update validates title/status/priority and optional user/category references before writing; user creation hashes passwords and can assign roles; login checks stored credentials and returns a fake token plus serialized user data; reporting aggregates task/user/category metrics and overdue counts; user deletion deletes the user and all assigned tasks
- Persistence: app boot creates schema only; seed execution wipes all current rows in tasks/users/categories and inserts 3 users, 4 categories, and 10 tasks; route handlers use one global SQLAlchemy session, commit directly inside blueprints, and delete dependent tasks before deleting a user

## Audit Limitations
- Live HTTP execution and persistence verification were not performed because the task prohibited dependency installation/network use and no local dependency state was assumed.
- No deprecated-API findings were emitted. Version-sensitive deprecation review would require authoritative current documentation lookup, which was unavailable under the no-network constraint.
- `services/notification_service.py` contains credential and SMTP concerns, but it is not imported by reachable boot or route code, so it was treated as non-executable for finding purposes.

## Severity Summary
| Severity | Count |
|---|---:|
| CRITICAL | 3 |
| HIGH | 2 |
| MEDIUM | 1 |
| LOW | 0 |

## Findings

### F-001 — Application secret key is embedded in executable configuration
- Rule: critical-exposed-runtime-secret
- Severity: CRITICAL
- Location: app.py:11-13
- Evidence: The Flask app config sets `SECRET_KEY` directly in source to a concrete secret-looking value instead of loading it from protected configuration.
- Impact: Anyone with source or deployed process access can forge signed Flask session or token material derived from that key, undermining any future authentication or state-integrity boundary built on the app secret.
- Recommendation: Load the secret key from protected environment-based configuration, fail closed when absent, and rotate the exposed key before any non-disposable deployment.
- Status: proposed
- Evidence authority: Static configuration in `app.py` is part of the executed boot path and is applied before every blueprint is registered.

### F-002 — User serialization exposes stored password hashes in API responses
- Rule: critical-sensitive-auth-payment-exposure
- Severity: CRITICAL
- Location: models/user.py:16-25
- Evidence: `User.to_dict()` includes the `password` field, and route handlers return `user.to_dict()` for user reads, user creation, updates, and login responses.
- Impact: Password hashes are disclosed to any caller who can access user endpoints or log in, enabling offline cracking attempts and leaking sensitive authentication material far beyond storage.
- Recommendation: Remove password material from every public serializer, create explicit safe response shapes for users and login, and audit every endpoint that currently returns `User.to_dict()`.
- Status: proposed
- Evidence authority: `models/user.py` defines the serializer, and it is returned by `routes/user_routes.py` in `get_user`, `create_user`, `update_user`, and `login`.

### F-003 — Public blueprints expose destructive and administrative operations without any authorization boundary
- Rule: critical-uncontrolled-privileged-operation
- Severity: CRITICAL
- Location: app.py:15-20
- Evidence: The app mounts `task_bp`, `user_bp`, and `report_bp` directly after `CORS(app)` with no authentication middleware, `before_request` guard, or admin-only composition boundary.
- Impact: Anonymous callers can create admin or manager users, delete users, mutate categories, and read administrative reports, allowing unauthorized state changes and sensitive operational data access.
- Recommendation: Introduce an application-wide authentication/authorization boundary at composition, require explicit role checks for privileged routes, and preserve existing route paths while returning 401/403 for unauthorized callers.
- Status: proposed
- Evidence authority: `app.py` registers all blueprints unguarded, while privileged routes such as `routes/user_routes.py:42-148` and `routes/report_routes.py:12-223` contain no auth or role checks of their own.

### F-004 — Authentication relies on MD5 password hashing and a fake bearer token
- Rule: high-weak-credential-handling
- Severity: HIGH
- Location: models/user.py:27-32
- Evidence: `set_password` and `check_password` use plain MD5, and successful login returns a predictable `'fake-jwt-token-' + str(user.id)` string rather than a verifiable expiring credential.
- Impact: Passwords are cheap to crack offline, and the login contract suggests authentication without issuing a trustworthy token, making account compromise and misuse of downstream auth assumptions much easier.
- Recommendation: Replace MD5 with a maintained adaptive password hash, migrate stored credentials safely, and issue verifiable expiring tokens from a dedicated auth boundary instead of synthesizing predictable placeholders in the route layer.
- Status: proposed
- Evidence authority: Credential creation and verification live in `models/user.py`, and the token contract is defined by `routes/user_routes.py:185-211`.

### F-005 — Task blueprint still owns validation, enrichment, search, and persistence orchestration
- Rule: high-transport-owns-domain-and-persistence
- Severity: HIGH
- Location: routes/task_routes.py:11-299
- Evidence: The task blueprint validates title/status/priority, parses due dates, resolves foreign keys, computes overdue rules, builds SQLAlchemy filters, manually serializes related names, and commits session changes directly inside route functions.
- Impact: Task behavior remains tightly coupled to HTTP handlers, making rule reuse inconsistent, encouraging drift from model/helper logic that already exists, and raising the cost of testing or evolving the domain without exercising Flask endpoints end-to-end.
- Recommendation: Keep the existing blueprint and routes, but extract task application services/serializers that own validation, overdue calculation, and persistence coordination while preserving response meaning and current persistence effects.
- Status: proposed
- Evidence authority: `routes/task_routes.py` performs the orchestration directly, while similar rule helpers already exist in `models/task.py` and `utils/helpers.py` yet are mostly bypassed.

### F-006 — Reporting endpoints issue repeated per-user and per-task queries as data grows
- Rule: medium-query-in-loop
- Severity: MEDIUM
- Location: routes/report_routes.py:15-68
- Evidence: The summary report counts several task subsets separately, loads all tasks to compute overdue items, then loads all users and runs one task query per user to build productivity data.
- Impact: Report latency and database load grow with dataset size, turning an administrative read path into an avoidable fan-out workload.
- Recommendation: Consolidate report aggregation into grouped queries or bounded batches and keep the response contract the same while moving the aggregation into a dedicated reporting service.
- Status: proposed
- Evidence authority: The query fan-out is visible in `routes/report_routes.py`, and a similar per-row enrichment pattern also appears in `routes/task_routes.py:14-57`.

## Proposed Refactoring Scope
- F-005,F-006 → Preserve the existing blueprints, models, and route surface, but extract task/report application services plus explicit serializers so transport stops owning validation, aggregation, enrichment, and session orchestration.
- F-001,F-003,F-004 → Introduce a configuration/auth layer at composition, move secrets to environment-backed settings, and enforce authenticated role checks without changing public route paths or successful domain effects for authorized callers.
- F-002 → Retain `User` as a useful model but replace `to_dict()` usage with safe serializers that omit password material while preserving response meaning for non-sensitive fields.

## Security-Driven Contract Changes
- Privileged routes that currently operate anonymously should require authentication and role-based authorization: user mutation, category mutation, and report endpoints should return 401/403 for unauthorized callers.
- `POST /login` should return a verifiable credential representation that does not expose password hashes, and user endpoints should stop serializing password material.

## Approval Required
Reply with explicit approval of this report path and snapshot digest before any target mutation. Identify all findings or the approved finding IDs.

## Audit Snapshot Digest
`sha256:8f272145b1235281166f395f2312425bb596ec237d7acadce5d564d5c2fddfed`
