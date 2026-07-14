# Validation Report

Derived from the pre-change `BehavioralBaseline` in `AUDIT_REPORT.md`
(`sha256:09e145591707437dd7dcdeab9ae7c2da61c5d26b950f4d17ac5c34cf62d66ebe`,
all 16 findings approved). Validated against the refactored app on branch
`refactor/arch-audit-findings`, Flask 3.1.1, isolated disposable SQLite databases.

## Method

- **Golden characterization:** the original app's responses to 34 representative
  requests (every endpoint + success/invalid/not-found/conflict cases) were captured
  before any change, timestamps normalized. The refactored app is replayed against the
  same golden, applying only the four approved contract deltas as expected differences.
- **Committed regression suite:** `tests/` (pytest, 26 tests) exercises endpoints,
  security, and transaction atomicity on a fresh temp DB per test.
- **Real boot:** the packaged server was started as a process on an isolated port and
  driven with `curl`.

## Results

### BOOT — real server process
- Command: `DB_PATH=… APP_ENV=development SECRET_KEY=… PORT=5055 python app.py`
- Expected: listens, banner "SERVIDOR INICIADO", `/health` reachable, port released on stop.
- Actual: ready after readiness poll; banner printed; port released after shutdown.
- Result: **PASS**

### ENDPOINTS + DOMAIN FLOWS — golden replay (34 cases) + pytest
- Command: `python compare_refactored.py` and `python -m pytest -q`
- Expected: identical status/body to baseline except approved deltas; full order lifecycle
  (create → stock decrement → list with item names → status update → sales report).
- Actual: **34/34 golden PASS**, **26/26 pytest PASS**.
- Result: **PASS**

### PERSISTENCE / TRANSACTIONS — F-008
- Command: `pytest tests/test_transactions.py`
- Expected: a failure injected after the first write leaves zero pedidos/itens and unchanged stock; multi-item order is atomic.
- Actual: injected `RuntimeError` after `adicionar_item` → 500, counts and stock unchanged (rollback proven); 2-item order persisted exactly 1 pedido + 2 itens.
- Result: **PASS**

### PERFORMANCE — F-010 (N+1)
- Command: `pytest tests/test_transactions.py::test_listagem_pedidos_sem_n_mais_1`
- Expected: order-listing query count bounded, not scaling per order/item.
- Actual: 5 orders assembled in ≤3 SQL statements (orders + items-by-IN + names-by-IN).
- Result: **PASS**

### SECURITY / ERRORS — F-001..F-005, F-013
- Command: `pytest tests/test_security.py` + curl smoke
- Checks and actual results:
  - `/admin/query`, `/admin/reset-db` → **404** (removed). PASS
  - Login auth-bypass payload `' OR '1'='1` → **401** (parameterized + hashed). PASS
  - Search injection returns literal match (no rows), not all rows. PASS
  - `/health` body has no `secret_key` / `debug` / `db_path`. PASS
  - Seeded password stored as `pbkdf2:…` hash, not `123456`. PASS
  - `APP_ENV=production` without `SECRET_KEY` → boot refused (RuntimeError). PASS
  - Unexpected error → `{"erro":"Erro interno do servidor"}`, internal detail not leaked. PASS
  - Source scan: hardcoded secret absent; no string-concatenated SQL in `loja/`. PASS
- Result: **PASS**

## Validation Summary
- Boot: PASS
- Endpoints: 34/34 golden, 26/26 pytest
- Domain flows: PASS (order lifecycle, auth, report)
- Persistence/transactions: PASS (rollback proven)
- Security/errors: PASS
- Performance: PASS (N+1 bounded)
- Cleanup: PASS (disposable DBs removed; `.venv`, `*.db`, caches git-ignored; `requirements.txt` unchanged)
- Blocking failures: none

## Deferred (require a separate contract-change approval, not done here)
- **F-011 (remainder):** sensitive-column over-exposure is fixed (`senha` removed, ties to
  F-005/F-014), but **pagination/limits and authorization were not added** — both change the
  list contract or require an auth system that the approved snapshot did not authorize.
- **F-012 (remainder):** numeric typing and order-existence 404 were added; **email format
  and uniqueness** were not (uniqueness needs a DB constraint + new conflict contract).
- **F-016 (partial by design):** dead imports removed; the `ativo` column is **retained** in
  schema and serialization to preserve the `"ativo": 1` response contract.
