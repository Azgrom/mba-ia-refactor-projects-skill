# Plan: Architecture Audit of `code-smells-project` (refactor-arch, Phase 1–2)

## Context

You invoked `/refactor-arch` on `code-smells-project`, a deliberately smelly Flask/SQLite
e-commerce API (the input to the "Architecture Audit and Refactoring" challenge). The skill's
**core invariant** is that *an audit request is not mutation authority*: the only valid output
before you approve findings is project analysis, a validated audit report, and an approval request.

So this plan covers **Phase 1 (Project Analysis, already done) and Phase 2 (Architecture Audit)**
only. Approving this plan authorizes me to create exactly one new file — `AUDIT_REPORT.md` — and
nothing else. **Refactoring is a separate, second gate** that requires you to reply with the
report's path *and* its sha256 digest.

## Phase 1 results (complete — read-only, already done)

**ProjectFingerprint**
- Python 3.14.5 / Flask `3.1.1` + flask-cors `5.0.1` (exact pins; **not installed**, no venv).
- Domain: e-commerce (produtos, usuarios, pedidos, itens_pedido, relatório de vendas).
- Entry point `app.py`; 17 routes (15 via `add_url_rule`, 2 via `@app.route`, incl. 2 undocumented
  `/admin/*` routes); persistence = SQLite `loja.db` via a **module-global connection** in
  `database.py` that also creates the schema and seeds data on first call.
- Source scope: 4 files / 780 lines (`app.py` 88, `controllers.py` 292, `models.py` 314,
  `database.py` 86). Excluded: `.git/`, `.claude/`, `.agents/` (the skill itself, not app code).
- Architecture shape: nominally MVC by filename, but **no layer owns one responsibility** —
  `controllers.py` holds business rules + notification side effects + raw SQL; `models.py` holds
  data access + domain policy + use-case orchestration; `app.py` holds two DB-touching handlers.

**BehavioralBaseline**
- Boot: `pip install -r requirements.txt && python app.py` → `http://localhost:5000`; `loja.db`
  auto-created and seeded (10 produtos, 3 usuarios).
- Domain flows: create produto → create pedido (stock check, total, stock decrement) → update status
  → sales report (tiered discount); register usuario → login.

**Deprecated-API check (done):** Context7 `/pallets/flask/3_1_1` confirms `add_url_rule`, `jsonify`,
and `request.get_json()` are all **current, not deprecated**. No deprecation finding will be emitted.

**Mutation snapshot:** `git status --short` = `?? .claude/` (pre-existing, yours). Nothing else.

## Phase 2: what I will do

Write `AUDIT_REPORT.md` at the project root, in the skill's exact report contract, then validate it:

```bash
python .agents/skills/refactor-arch/scripts/validate_audit_report.py \
  AUDIT_REPORT.md . --minimum-findings 5
```

Fix any report-generation defects, recompute the digest, rerun until `VALID`, then re-check
`git status` to prove `AUDIT_REPORT.md` is the only new artifact.

### Findings I will document (16, merged by root cause — not one-file-one-finding)

| ID | Sev | Root cause | Location |
|---|---|---|---|
| F-001 | CRITICAL | `/admin/query` executes arbitrary client-supplied SQL, unauthenticated | `app.py:59-78` |
| F-002 | CRITICAL | Every query in `models.py` is built by string concatenation → SQL injection; `login_usuario` is an auth bypass | `models.py:105-120` |
| F-003 | CRITICAL | `/admin/reset-db` wipes all four tables, unauthenticated | `app.py:47-57` |
| F-004 | CRITICAL | Insecure hardcoded config: literal `SECRET_KEY`, `DEBUG=True` on `0.0.0.0`, wildcard CORS — and `/health` echoes the secret back to clients | `app.py:6-9` |
| F-005 | CRITICAL | Passwords stored, compared, and **returned by `GET /usuarios`** in plaintext | `models.py:72-103` |
| F-006 | HIGH | `models.py` is a God Module: persistence + domain policy (stock, totals, discount tiers) + orchestration | `models.py:133-169` |
| F-007 | HIGH | Controllers own domain rules, notification side effects, and raw SQL (`health_check`) | `controllers.py:24-62` |
| F-008 | HIGH | `criar_pedido` does 3 dependent writes with no transaction boundary/rollback; stock check is TOCTOU | `models.py:148-169` |
| F-009 | HIGH | Process-global SQLite connection, `check_same_thread=False`, DDL + seed as a side effect of first access | `database.py:4-13` |
| F-010 | MEDIUM | N+1 queries: per-order and per-item lookups in the order listings | `models.py:171-201` |
| F-011 | MEDIUM | Unbounded/overbroad reads: `SELECT *`, no pagination, no authorization on list endpoints | `models.py:4-22` |
| F-012 | MEDIUM | Missing boundary validation: no email format/uniqueness, no numeric typing, status update on a nonexistent order returns 200 | `controllers.py:146-165` |
| F-013 | MEDIUM | Duplicated policy that has already drifted — `atualizar_produto` silently lost the name-length and category checks `criar_produto` enforces; `except: jsonify(str(e)), 500` repeated 15× leaks internals | `controllers.py:64-96` |
| F-014 | LOW | Row→dict serialization hand-written 8×, with inconsistent `senha` exposure | `models.py:4-41` |
| F-015 | LOW | Magic values: discount tiers/thresholds, status and category enums, port, db path | `models.py:256-262` |
| F-016 | LOW | Dead code: unused `sqlite3`/`os` imports; `ativo` column never read or written | `models.py:1-3` |

Counts: 5 CRITICAL, 4 HIGH, 4 MEDIUM, 3 LOW.

### Security-driven contract changes I will *propose* (not perform)

These intentionally **break** the current API contract, so they need explicit approval:
1. Delete `/admin/query` and `/admin/reset-db` (or gate them behind auth + non-prod env).
2. Stop returning `senha` from `GET /usuarios` and `GET /usuarios/<id>`; hash passwords
   (existing seeded plaintext logins stop working unless migrated).
3. Stop returning `secret_key` / `debug` / `db_path` from `GET /health`.
4. Replace `jsonify({"erro": str(e)}), 500` with a sanitized error contract (message text changes).

## Verification (Phase 2)

- `validate_audit_report.py … --minimum-findings 5` exits `VALID` (checks section order, severity
  counts, finding order/IDs, path containment, **real line ranges in real files**, digest integrity).
- `git status --short` afterwards shows only `?? .claude/` and `?? AUDIT_REPORT.md`.
- I will print the report path + `sha256:<digest>` + the finding IDs, and **stop**.

## The second gate (not authorized by this plan)

To move to Phase 3 (Refactoring: extract a real service/repository layer, parameterize SQL, hash
credentials, add transaction boundaries) and Phase 4 (Validation: boot, all 17 endpoints, domain
flows, persistence, rollback, security checks), you must reply:

```text
Approve AUDIT_REPORT.md sha256:<digest> [all findings | F-001,F-004,…]
```

Nothing in `app.py`, `controllers.py`, `models.py`, or `database.py` changes before that reply.
