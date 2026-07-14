"""Transaction and N+1 checks for findings F-008 and F-010."""
import sqlite3

from loja.services import PedidoService


def _counts(db_path):
    conn = sqlite3.connect(db_path)
    p = conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    i = conn.execute("SELECT COUNT(*) FROM itens_pedido").fetchone()[0]
    estoque = conn.execute("SELECT estoque FROM produtos WHERE id = 2").fetchone()[0]
    conn.close()
    return p, i, estoque


def test_pedido_rollback_em_falha_no_meio(app, config, monkeypatch):
    # F-008: inject a failure after the first write; nothing must persist.
    before = _counts(config.db_path)

    original = PedidoService.criar

    calls = {"n": 0}
    real_add = None

    from loja.repositories import PedidoRepository

    real_add = PedidoRepository.adicionar_item

    def flaky(self, *a, **k):
        calls["n"] += 1
        real_add(self, *a, **k)
        raise RuntimeError("falha simulada após inserir item")

    monkeypatch.setattr(PedidoRepository, "adicionar_item", flaky)

    client = app.test_client()
    r = client.post("/pedidos", json={
        "usuario_id": 2, "itens": [{"produto_id": 2, "quantidade": 2}]})
    assert r.status_code == 500

    after = _counts(config.db_path)
    assert after == before, f"rollback falhou: antes={before} depois={after}"
    assert original is PedidoService.criar  # sanity


def test_pedido_multi_item_atomico(app, config):
    client = app.test_client()
    r = client.post("/pedidos", json={
        "usuario_id": 2,
        "itens": [
            {"produto_id": 2, "quantidade": 1},
            {"produto_id": 3, "quantidade": 1},
        ],
    })
    assert r.status_code == 201
    p, i, _ = _counts(config.db_path)
    assert (p, i) == (1, 2)


def test_listagem_pedidos_sem_n_mais_1(app, config):
    # F-010: query count for the order listing must not scale with row count.
    client = app.test_client()
    for _ in range(5):
        client.post("/pedidos", json={
            "usuario_id": 2, "itens": [{"produto_id": 2, "quantidade": 1}]})

    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    counter = {"n": 0}
    conn.set_trace_callback(lambda *_: counter.__setitem__("n", counter["n"] + 1))

    # Re-run the assembly directly against a counting connection.
    from loja.db import Database
    from loja.repositories import PedidoRepository

    db = Database(config.db_path)
    # bind the counting connection as the request connection
    class _Bound(Database):
        def get(self_inner):
            return conn
    repo = PedidoRepository(_Bound(config.db_path))
    pedidos = repo.listar_todos()
    conn.close()

    assert len(pedidos) == 5
    # 5 orders + their items: bounded number of queries (1 orders + 1 items + 1 names).
    assert counter["n"] <= 3, f"esperava <=3 queries, obtido {counter['n']}"
