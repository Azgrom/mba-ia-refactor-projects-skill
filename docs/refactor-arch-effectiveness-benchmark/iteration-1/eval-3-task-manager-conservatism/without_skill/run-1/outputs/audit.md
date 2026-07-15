# Architecture audit: Task Manager API

## Outcome

The fixture was already partially layered, so the improvement keeps its Flask blueprints, SQLAlchemy models, helpers, and notification service. The refactor targets responsibilities for which the code supplied direct evidence of misplacement:

- HTTP route functions previously performed input handling, business validation, ORM lookup, transaction management, reporting calculations, and response serialization in one place.
- Category CRUD was defined in `report_routes.py`, despite not being reporting behavior.
- Task status, priority, and overdue rules existed on `Task` but were duplicated in multiple routes.
- Application construction was fixed at module import time, making configured test/application instances difficult to create.
- SMTP credentials were embedded in the notification service.

The resulting boundary is:

| Area | Responsibility |
|---|---|
| `routes/` | Flask request parsing, status-code/error translation, and response shaping |
| `services/` | Use-case orchestration, validation, queries, reports, and transaction boundaries |
| `models/` | Persistence mapping, serialization retained for compatibility, and existing task rules |
| `utils/` | Generic calculations and other existing helpers |
| `app.py` | Application construction and blueprint registration |

No repository layer, schema framework, dependency-injection container, or package-wide rewrite was added. Those abstractions were not justified by the fixture's size.

## Changes made

1. Added `TaskService`, `UserService`, `CategoryService`, and `ReportService`. They contain the workflows previously embedded in route functions.
2. Added small typed service errors so HTTP adapters can preserve the existing 400/401/403/404/409/500 mappings without coupling services to Flask response objects.
3. Kept the task, user, and report blueprints; added a category blueprint and moved only `/categories` handlers out of the report module. All public paths and methods remain unchanged.
4. Reused `Task.validate_status`, `Task.validate_priority`, and `Task.is_overdue` instead of repeating those rules. Their external behavior is unchanged.
5. Reused `calculate_percentage` for report/statistics calculations.
6. Added eager loading for task-list user/category relationships, removing its per-task lookup pattern while preserving the enriched list payload.
7. Introduced `create_app(config=None)` while retaining the module-level `app`, automatic table creation, development launch command, blueprint behavior, and default configuration.
8. Made SMTP connection settings constructor/environment inputs (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`) instead of retaining a password in source.
9. Removed dead imports from the modified modules.
10. Added characterization tests for the complete route map and representative task, user, category, search, statistics, report, login, response, and persistence contracts.

## Compatibility assessment

The work deliberately preserves:

- every existing URI and HTTP method;
- success and expected error status codes;
- Portuguese response messages and field meanings;
- the intentionally different task-list and task-detail representations;
- tag and due-date persistence formats;
- user deletion's deletion of assigned tasks;
- category/task/user CRUD commits and rollbacks;
- the current login token and user representation, even where they are insecure;
- `python app.py`, `from app import app`, and seed-script compatibility.

Characterization coverage also checks that a missing task/user takes precedence over an empty update body, matching the prior lookup order.

## Findings intentionally deferred

### Critical: authentication and credential exposure

`User.set_password` uses unsalted MD5. `User.to_dict` includes the password hash, and that serializer is part of create, update, user-detail, and login responses. Login returns a predictable string (`fake-jwt-token-<id>`) rather than an authentication token. The application also retains a source-level Flask secret default.

These should be fixed, but doing so would directly change response meaning and authentication behavior, contrary to this task's compatibility constraint. Recommended follow-up: introduce a public serializer that excludes `password`, migrate hashes with Werkzeug/Argon2/bcrypt on successful login, implement signed expiring tokens, source the Flask secret exclusively from deployment configuration, and version or announce the response-contract change.

### High: weak input/error boundaries

- Numeric search parameters are converted with `int()` without expected validation; malformed values become an internal error.
- Several updates accept semantically empty or invalid field values because that is current behavior.
- Bare/broad exception handling remains at compatibility-sensitive boundaries, especially the task-list fallback and persistence translation.
- The email regex and category color values are only minimally validated.

Changing these cases can alter status semantics. Add explicit contract decisions and tests before tightening them.

### Medium: query growth in reports and user counts

The task list's N+1 lookup was removed, but summary productivity, category task counts, and `len(user.tasks)` still issue queries per parent row. Aggregate/grouped queries would scale better. They were left alone because this fixture has no performance evidence or target dataset and correctness is currently clear.

### Medium: time representation

Models and reports use naive `datetime.utcnow()` values serialized with `str()`. Python 3.14 emits deprecation warnings for this API. Migrating to timezone-aware UTC affects stored and returned representations and should be handled as an explicit database/API migration.

### Medium: notification lifetime and delivery

Notification history is process-local memory, email delivery is synchronous, and failures are reduced to a boolean/print. SMTP secrets are now external, but reliable delivery would require a durable outbox or queue, retry policy, and structured logging. No route currently invokes the service, so integrating it was outside the evidenced scope.

### Low: dormant helper surface

`utils/helpers.py` contains helpers and constants not currently used, including a task-data processor whose validation/date behavior differs from the public API. Reusing it would have silently changed semantics, so it was retained rather than forced into the new flow. Remove or reconcile these helpers only after deciding the canonical API rules.

## Verification

Executed from `fixture/`:

```text
../.venv/bin/pytest -q
7 passed, 33 warnings in 0.24s

../.venv/bin/python -m compileall -q .
completed successfully
```

The warnings are the documented naive-UTC deprecations; the prior SQLAlchemy `Query.get()` legacy warnings were eliminated from application code by using `db.session.get()`.

## Recommended next sequence

1. Treat the authentication/serializer corrections as a versioned security change.
2. Specify malformed-search and empty-field semantics, then add contract tests and validation.
3. Profile realistic data volumes before replacing remaining per-parent report queries with aggregates.
4. Plan a timezone-aware database/API migration rather than changing timestamp strings opportunistically.
