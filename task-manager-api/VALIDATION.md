# Validation Evidence

Refactor of `task-manager-api` against approved audit
`ARCHITECTURE_AUDIT.md` — `sha256:cb2e274fda9b1844c8c36137a730bcdea2cff318bcd3dd372a1a6863c8d3583c`
(all 16 findings approved). Validation derived from the pre-change behavioral
baseline, run in a disposable virtualenv + in-memory SQLite; the target root was
never booted or written to.

## Environment
- Python 3.14.5; Flask 3.0.0, SQLAlchemy 2.0.51, Werkzeug 3.1.8, PyJWT 2.10.1 (pinned).
- Disposable copy under the session scratchpad; in-memory DB per test.

## Validation Summary
- Boot: PASS
- Endpoints: 22/22 exercised
- Domain flows: PASS (task lifecycle; user-delete cascade; login)
- Persistence/transactions: PASS
- Security/errors: PASS
- Performance (F-008): PASS (bounded, proven flat at 200 rows)
- Automated tests: 61/61 PASS
- Cleanup: PASS (no generated state in target root; report unedited since approval)
- Blocking failures: none

## Key checks

### Boot & config (F-003, F-006, F-007)
- Importing `app` without `SECRET_KEY` raises `ConfigError` and refuses to boot.
- `create_app()` is import-safe; `db.create_all()` moved to `init_db` / `flask init-db`.
- `DEBUG` defaults False, `HOST` defaults `127.0.0.1`.
- Boot on isolated port 5099: `/health` 200, readiness after 3 polls, clean shutdown.

### Auth boundary (F-002) — was the headline vulnerability
- `PUT /users/2 {"role":"admin"}` anonymous: **was 200, now 401**.
- Authenticated non-admin self-promotion: 403.
- Non-admin modifying/deleting another user: 403.
- `DELETE /users/<id>` requires admin.
- Forged `Bearer fake-jwt-token-<id>`: 401.
- All 18 protected endpoints reject anonymous access (parametrized test).

### Credential handling (F-001, F-004)
- `password` absent from `GET /users/<id>`, `POST /users`, `POST /login`, `GET /users` bodies.
- Stored hash is salted PBKDF2 (Werkzeug), length > 40; legacy MD5 digests fail `check_password`.
- `/login` issues a signed 3-segment JWT (len ~161), not `fake-jwt-token-<id>`.

### Input validation & errors (F-009)
- The 7 inputs that produced unhandled 500s now return 400:
  `priority:"high"` (POST & PUT), `search?priority=abc`, `search?user_id=abc`,
  `title:null` (task & user password null), `email:123`.
- Bare `except:` clauses removed; unexpected errors go through one handler that
  logs the traceback and returns a sanitized `{"error":"Erro interno"}` 500.

### Pagination & shape (F-010, F-015)
- List endpoints return `{items, pagination}` with bounded `per_page` (default 20, max 100).
  **Approved contract change #7** (envelope), confirmed with the user during Batch 4.
- Task shape is identical across `/tasks`, `/tasks/search`, `/users/<id>/tasks`
  (was 14 / 11 / 8 keys).

### Performance (F-008)
| Endpoint | Baseline (10 rows) | After (10 rows) | After (200 rows) |
|---|---:|---:|---:|
| GET /tasks | 17 | 5 | 5 |
| GET /reports/summary | 19 | 9 | 9 |
| GET /tasks/stats | 6 | 2 | — |
Query count is now independent of row count (includes 1 query for auth).

### Deprecations (F-012, F-013)
- Zero `Model.query.get` / legacy `Query` in application source; all use `db.session.get` / `select()`.
- Zero `datetime.utcnow()`; timezone-aware UTC throughout. `seed.py` runs clean under `-W error::DeprecationWarning`. Timestamps now serialize as ISO-8601 with `+00:00` (approved serialization change).

### Dead code (F-014)
- `services/notification_service.py` deleted (zero importers; contained a hardcoded
  SMTP credential — rotate it regardless of reachability).
- `utils/helpers.py` reduced to the one function that is now actually wired in
  (`calculate_percentage`, per F-011).

### Structure (F-005, F-011, F-016)
- Routes are thin adapters (report_routes 223 → 20 lines); use cases live in
  `services/*_service.py`; queries in `repositories/`.
- Overdue rule owned once by `Task.is_overdue`; percentage owned once by
  `calculate_percentage` — both previously duplicated and bypassed.
- Category CRUD moved to `routes/category_routes.py`; paths/methods unchanged.

## Deviations from the audit's suggested remediation
1. **marshmallow not adopted** for F-009. Its default error bodies would have
   silently changed every existing `{"error":...}` 400 response — an unapproved
   contract change. Hand-rolled validators preserve the exact messages instead;
   marshmallow dropped as an unused dependency.
2. **F-010 response envelope** was an extra contract change beyond the approved
   six; confirmed with the user before implementing (recorded as change #7).
