"""Data access: parameterized SQL and explicit projections.

All queries use bound parameters (finding F-002). Projections are defined once per
entity (finding F-014); the public user projection never includes ``senha`` (F-005).
Repositories own query construction and batching only — no business policy, no HTTP.
"""
from __future__ import annotations

from .db import Database


def _produto_dict(row) -> dict:
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def _usuario_publico(row) -> dict:
    # Deliberately excludes ``senha`` — the only public projection of a user.
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }


class ProdutoRepository:
    def __init__(self, db: Database):
        self.db = db

    def listar(self) -> list[dict]:
        rows = self.db.get().execute("SELECT * FROM produtos ORDER BY id").fetchall()
        return [_produto_dict(r) for r in rows]

    def obter(self, produto_id: int):
        row = self.db.get().execute(
            "SELECT * FROM produtos WHERE id = ?", (produto_id,)
        ).fetchone()
        return _produto_dict(row) if row else None

    def criar(self, nome, descricao, preco, estoque, categoria) -> int:
        cur = self.db.get().execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria)"
            " VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
        return cur.lastrowid

    def atualizar(self, produto_id, nome, descricao, preco, estoque, categoria) -> None:
        self.db.get().execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?,"
            " categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )

    def deletar(self, produto_id) -> None:
        self.db.get().execute("DELETE FROM produtos WHERE id = ?", (produto_id,))

    def buscar(self, termo, categoria=None, preco_min=None, preco_max=None) -> list[dict]:
        query = "SELECT * FROM produtos WHERE 1=1"
        params: list = []
        if termo:
            query += " AND (nome LIKE ? OR descricao LIKE ?)"
            like = "%" + termo + "%"
            params.extend([like, like])
        if categoria:
            query += " AND categoria = ?"
            params.append(categoria)
        if preco_min is not None:
            query += " AND preco >= ?"
            params.append(preco_min)
        if preco_max is not None:
            query += " AND preco <= ?"
            params.append(preco_max)
        query += " ORDER BY id"
        rows = self.db.get().execute(query, params).fetchall()
        return [_produto_dict(r) for r in rows]

    def decrementar_estoque(self, produto_id, quantidade) -> int:
        """Atomic conditional decrement. Returns affected row count (0 = insufficient)."""
        cur = self.db.get().execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
            (quantidade, produto_id, quantidade),
        )
        return cur.rowcount

    def contar(self) -> int:
        return self.db.get().execute("SELECT COUNT(*) FROM produtos").fetchone()[0]


class UsuarioRepository:
    def __init__(self, db: Database):
        self.db = db

    def listar(self) -> list[dict]:
        rows = self.db.get().execute("SELECT * FROM usuarios ORDER BY id").fetchall()
        return [_usuario_publico(r) for r in rows]

    def obter(self, usuario_id: int):
        row = self.db.get().execute(
            "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        return _usuario_publico(row) if row else None

    def obter_por_email(self, email: str):
        """Internal projection including the password hash, for authentication only."""
        row = self.db.get().execute(
            "SELECT * FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
        return row

    def criar(self, nome, email, senha_hash, tipo="cliente") -> int:
        cur = self.db.get().execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, senha_hash, tipo),
        )
        return cur.lastrowid

    def contar(self) -> int:
        return self.db.get().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]


class PedidoRepository:
    def __init__(self, db: Database):
        self.db = db

    def obter(self, pedido_id: int):
        row = self.db.get().execute(
            "SELECT * FROM pedidos WHERE id = ?", (pedido_id,)
        ).fetchone()
        return dict(row) if row else None

    def criar(self, usuario_id, status, total) -> int:
        cur = self.db.get().execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, status, total),
        )
        return cur.lastrowid

    def adicionar_item(self, pedido_id, produto_id, quantidade, preco_unitario) -> None:
        self.db.get().execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario)"
            " VALUES (?, ?, ?, ?)",
            (pedido_id, produto_id, quantidade, preco_unitario),
        )

    def atualizar_status(self, pedido_id, status) -> None:
        self.db.get().execute(
            "UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id)
        )

    def listar_todos(self) -> list[dict]:
        rows = self.db.get().execute("SELECT * FROM pedidos ORDER BY id").fetchall()
        return self._montar(rows)

    def listar_por_usuario(self, usuario_id) -> list[dict]:
        rows = self.db.get().execute(
            "SELECT * FROM pedidos WHERE usuario_id = ? ORDER BY id", (usuario_id,)
        ).fetchall()
        return self._montar(rows)

    def _montar(self, pedido_rows) -> list[dict]:
        """Assemble pedidos with their itens using batched lookups (fixes N+1, F-010)."""
        pedidos = [
            {
                "id": r["id"],
                "usuario_id": r["usuario_id"],
                "status": r["status"],
                "total": r["total"],
                "criado_em": r["criado_em"],
                "itens": [],
            }
            for r in pedido_rows
        ]
        if not pedidos:
            return pedidos

        conn = self.db.get()
        pedido_ids = [p["id"] for p in pedidos]
        marks = ",".join("?" * len(pedido_ids))
        itens = conn.execute(
            f"SELECT * FROM itens_pedido WHERE pedido_id IN ({marks}) ORDER BY id",
            pedido_ids,
        ).fetchall()

        produto_ids = sorted({i["produto_id"] for i in itens})
        nomes: dict[int, str] = {}
        if produto_ids:
            pmarks = ",".join("?" * len(produto_ids))
            for row in conn.execute(
                f"SELECT id, nome FROM produtos WHERE id IN ({pmarks})", produto_ids
            ).fetchall():
                nomes[row["id"]] = row["nome"]

        by_pedido: dict[int, list] = {p["id"]: p["itens"] for p in pedidos}
        for i in itens:
            by_pedido[i["pedido_id"]].append({
                "produto_id": i["produto_id"],
                "produto_nome": nomes.get(i["produto_id"], "Desconhecido"),
                "quantidade": i["quantidade"],
                "preco_unitario": i["preco_unitario"],
            })
        return pedidos

    def contar(self) -> int:
        return self.db.get().execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]

    def agregados(self) -> dict:
        conn = self.db.get()
        total_pedidos = conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
        faturamento = conn.execute("SELECT SUM(total) FROM pedidos").fetchone()[0] or 0
        by_status = {
            "pendente": 0, "aprovado": 0, "cancelado": 0,
        }
        for row in conn.execute(
            "SELECT status, COUNT(*) AS n FROM pedidos GROUP BY status"
        ).fetchall():
            by_status[row["status"]] = row["n"]
        return {
            "total_pedidos": total_pedidos,
            "faturamento": faturamento,
            "pendentes": by_status.get("pendente", 0),
            "aprovados": by_status.get("aprovado", 0),
            "cancelados": by_status.get("cancelado", 0),
        }
