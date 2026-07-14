# Refactoring Playbook

Select transformations from confirmed findings and the approved audit snapshot. Examples are responsibility patterns; adapt syntax to the detected, version-verified stack.

## Contents

- Preconditions and planning
- Route to application service (Flask)
- Route to application service (Express)
- Controller to domain service
- Query to repository
- God component decomposition
- Application factory and server entry point
- Environment configuration
- Centralized Flask errors
- Centralized Express errors
- Boundary validation
- Transaction-scoped multi-write flow
- Query-in-loop batching
- Maintained password hashing
- Sensitive serialization filtering
- Safe dependent-record deletion
- Batch execution and rollback

## Preconditions and planning

Do not use this playbook without an `ApprovedAuditSnapshot` that matches the current report digest.

For each transformation record:

```markdown
- Transformation: T-001
- Findings: F-001,F-004
- Affected files: [repository-relative paths]
- Responsibility change: [before → after]
- Compatibility boundary: [imports/endpoints/status/response/state]
- Rollback boundary: [small reversible batch]
- Completion criterion: [focused regression and evidence]
```

Order changes from stable inner behavior outward: characterization checks → domain/application extraction → persistence boundary → transport wiring → composition/configuration → compatibility cleanup. Keep adapters until callers migrate.

## 1. Route to application service — Flask-style

**Before:** HTTP, policy, and persistence share one handler.

```python
@bp.post("/orders")
def create_order():
    payload = request.get_json()
    total = sum(item["price"] * item["qty"] for item in payload["items"])
    row = db.execute("INSERT INTO orders(total) VALUES (?)", (total,))
    db.commit()
    return {"id": row.lastrowid, "total": total}, 201
```

**After:** the route maps HTTP; the application service owns the use case.

```python
@bp.post("/orders")
def create_order():
    command = parse_create_order(request.get_json())
    result = order_service.create(command)
    return serialize_order(result), 201

class OrderService:
    def create(self, command):
        order = Order.create(command.items)
        return self.orders.add(order)
```

Verify identical path/method, successful status/meaning, validation errors, and persisted totals.

## 2. Route to application service — Express-style

**Before:** the router coordinates storage and response mapping.

```javascript
router.post('/enrollments', async (req, res) => {
  const course = await db.get('select * from courses where id=?', req.body.courseId)
  await db.run('insert into enrollments(user_id, course_id) values (?, ?)', req.user.id, course.id)
  res.status(201).json({ course })
})
```

**After:** the router supplies transport context to one use case.

```javascript
router.post('/enrollments', asyncHandler(async (req, res) => {
  const result = await enrollmentService.enroll({
    userId: req.user.id,
    courseId: req.body.courseId
  })
  res.status(201).json(enrollmentView(result))
}))
```

Keep SQL and transaction coordination in application/persistence ownership, not the router.

## 3. Controller to domain service

**Before:** orchestration embeds domain rules.

```python
def complete_task(task_id):
    task = tasks.get(task_id)
    if task.status == "archived":
        raise ValueError("cannot complete archived task")
    task.status = "completed"
    task.completed_at = clock.now()
    tasks.save(task)
```

**After:** the domain owns its state transition; the service coordinates persistence.

```python
def complete_task(task_id):
    task = tasks.get_required(task_id)
    task.complete(clock.now())
    tasks.save(task)

class Task:
    def complete(self, now):
        if self.status == "archived":
            raise InvalidTaskTransition("archived", "completed")
        self.status, self.completed_at = "completed", now
```

Test the invariant without Flask/Express and the full endpoint mapping separately.

## 4. Query to repository

**Before:** application code depends on storage syntax.

```javascript
async function getUser(id) {
  return db.get('SELECT id, name, password FROM users WHERE id = ?', id)
}
```

**After:** persistence owns query/projection semantics.

```javascript
class SqliteUsers {
  constructor(db) { this.db = db }
  async findPublicById(id) {
    return this.db.get('SELECT id, name FROM users WHERE id = ?', id)
  }
}
```

Name repository operations for use-case needs and project only required fields.

## 5. God component decomposition

**Before:** one manager constructs dependencies, registers routes, handles checkout, queries reports, and sends notifications.

```javascript
class AppManager {
  constructor(app, db) { /* setup everything */ }
  setupRoutes() { /* every endpoint */ }
  checkout() { /* payment + writes + response */ }
  report() { /* SQL + formatting */ }
}
```

**After:** composition wires cohesive capabilities.

```javascript
function buildApp({ enrollmentService, reportService, errorHandler }) {
  const app = express()
  app.use('/enrollments', enrollmentRoutes(enrollmentService))
  app.use('/reports', reportRoutes(reportService))
  app.use(errorHandler)
  return app
}
```

Split by unrelated reasons to change, not by arbitrary line count. Preserve a delegating compatibility facade when public callers still use the old manager.

## 6. Application factory and server entry point

**Before:** import starts the server and hides dependencies.

```python
app = Flask(__name__)
db = connect("app.db")
register_routes(app, db)
app.run(debug=True)
```

**After:** construction is import-safe and startup is explicit.

```python
def create_app(config=None):
    app = Flask(__name__)
    settings = load_settings(config)
    register_routes(app, build_services(settings))
    register_errors(app)
    return app

if __name__ == "__main__":
    create_app().run()
```

Importing for tests must not seed data, open valuable state, or start a server.

## 7. Environment configuration

**Before:** executable code embeds environment policy and secrets.

```javascript
const config = { port: 3000, adminToken: 'production-secret', debug: true }
```

**After:** configuration normalizes inputs and fails for required secrets.

```javascript
function loadConfig(env) {
  if (!env.ADMIN_TOKEN) throw new Error('ADMIN_TOKEN is required')
  return {
    port: Number(env.PORT ?? 3000),
    adminToken: env.ADMIN_TOKEN,
    debug: env.DEBUG === 'true'
  }
}
```

Preserve documented non-sensitive defaults; treat secret rotation and deployment changes as explicit obligations.

## 8. Centralized errors — Flask-style

**Before:** handlers leak inconsistent internal exceptions.

```python
try:
    return service.run(request.json)
except Exception as exc:
    return {"error": str(exc)}, 500
```

**After:** typed errors map once; unknown details stay internal.

```python
@app.errorhandler(AppError)
def handle_app_error(error):
    return {"errorCode": error.code, "message": error.safe_message}, error.status

@app.errorhandler(Exception)
def handle_unexpected(error):
    app.logger.exception("unexpected request failure")
    return {"errorCode": "internal_error", "message": "Internal error"}, 500
```

Verify registration syntax against the detected Flask version and preserve approved error semantics.

## 9. Centralized errors — Express-style

**Before:** each handler chooses a different error body or forgets async rejection handling.

```javascript
router.get('/:id', async (req, res) => {
  try { res.json(await service.get(req.params.id)) }
  catch (error) { res.status(500).json({ error: error.stack }) }
})
```

**After:** async failures reach terminal error middleware.

```javascript
router.get('/:id', asyncHandler(async (req, res) => {
  res.json(await service.get(req.params.id))
}))

app.use((error, req, res, next) => {
  const mapped = mapError(error)
  req.log?.error({ error, correlationId: req.id }, 'request failed')
  res.status(mapped.status).json({ errorCode: mapped.code, message: mapped.safeMessage })
})
```

Register the error middleware after routes and verify current framework async/error semantics for the installed version.

## 10. Boundary validation

**Before:** malformed values flow into domain/storage assumptions.

```python
limit = int(request.args.get("limit"))
items = service.search(request.args["q"], limit)
```

**After:** the boundary returns a typed validation failure.

```python
query = (request.args.get("q") or "").strip()
limit = parse_bounded_int(request.args.get("limit", "20"), minimum=1, maximum=100)
if not query:
    raise ValidationError("query_required", "Query is required")
items = service.search(query, limit)
```

Keep domain invariants in domain code even after transport validation.

## 11. Transaction-scoped multi-write flow

**Before:** partial commits can survive a later failure.

```javascript
await payments.insert(payment)
await enrollments.insert(enrollment)
await audit.insert(event)
```

**After:** the application service owns one atomic unit.

```javascript
return unitOfWork.transaction(async tx => {
  const payment = await tx.payments.insert(paymentData)
  const enrollment = await tx.enrollments.insert({ userId, courseId, paymentId: payment.id })
  await tx.audit.insert({ type: 'enrolled', enrollmentId: enrollment.id })
  return enrollment
})
```

Inject failure after each write and prove no partial records remain.

## 12. Query-in-loop to batch loading

**Before:** one query per parent.

```python
orders = order_repo.list()
for order in orders:
    order.items = item_repo.list_for_order(order.id)
```

**After:** load once and index in memory, or use an appropriate join/eager load.

```python
orders = order_repo.list()
items = item_repo.list_for_orders([order.id for order in orders])
by_order = group_by(items, key=lambda item: item.order_id)
for order in orders:
    order.items = by_order.get(order.id, [])
```

Measure query count and representative latency before and after under the same state.

## 13. Maintained password hashing

**Before:** fast unsalted hashes are used as password storage.

```python
user.password_hash = hashlib.md5(password.encode()).hexdigest()
```

**After:** use the maintained adaptive primitive already supported by the stack.

```python
from werkzeug.security import check_password_hash, generate_password_hash

user.password_hash = generate_password_hash(password)
is_valid = check_password_hash(user.password_hash, candidate)
```

Plan migration for existing hashes, avoid logging either value, and never serialize `password_hash`.

## 14. Sensitive serialization filtering

**Before:** generic object serialization leaks internal fields.

```javascript
res.json(user)
```

**After:** serialize an explicit public projection.

```javascript
function publicUser(user) {
  return { id: user.id, name: user.name, email: user.email }
}

res.json(publicUser(user))
```

Test the absence of passwords, hashes, tokens, internal errors, and payment secrets.

## 15. Safe dependent-record deletion

**Before:** parent deletion relies on implicit or inconsistent child behavior.

```python
users.delete(user_id)
```

**After:** make ownership policy explicit and transactional.

```python
with unit_of_work.transaction():
    if tasks.exists_for_owner(user_id):
        raise ConflictError("user_has_tasks", "Reassign or delete owned tasks first")
    users.delete(user_id)
```

Choose restrict, cascade, soft-delete, or reassignment from domain ownership and the approved contract. Enforce it in application behavior and database constraints.

## Batch execution and rollback

For each small batch:

1. confirm approved finding IDs and clean/pre-existing work state;
2. run the focused failing regression check when behavior changes;
3. apply one coherent responsibility change;
4. run focused tests and static checks;
5. inspect diff for scope and secret leakage;
6. record resolved/deferred status and evidence;
7. keep or remove compatibility adapters only when all callers are proven migrated.

If a batch fails, return to its recorded rollback boundary. Do not broaden scope or opportunistically upgrade dependencies without new approval.
